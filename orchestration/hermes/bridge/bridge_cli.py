#!/usr/bin/env python3
"""bridge_cli.py — ONE ROUND of the GPT <-> Hermes control kernel.

    python3 bridge_cli.py round                   # LATCH/RECONCILE -> READ -> VALIDATE -> maybe EXECUTE -> REPORT -> STOP
    python3 bridge_cli.py recover                 # official bounded recovery (RECOVERY_REQUIRED only)
    python3 bridge_cli.py resolve-send-uncertain  # HUMAN-ONLY resolution of a SEND_UNCERTAIN pending result
    python3 bridge_cli.py status                  # print the persistent chain state

Exactly one round per invocation. This is deliberately NOT an infinite loop; a
launcher may loop it later.

Gate order (default deny at every step):

  0. acquire the single-worker lock (MAX_IN_FLIGHT_TASKS = 1)
  1. STOPPED LATCH — a persisted status == STOPPED is terminal: STOPPED_LATCHED,
     returned BEFORE any browser read, with no state mutation and no adapter call.
  2. STARTUP RECONCILIATION — a durable pending result is resolved by read-only
     confirmation (never a resend); an ACCEPTED task with no terminal RESULT/STOPPED
     and no pending result fails closed into RECOVERY_REQUIRED. This also covers the
     kill -9 / power-loss shape.
  3. READ the latest completed assistant response
  4. EXTRACT exactly one HERMES_TASK_V1 envelope (0 -> NO_CONTROL_MESSAGE,
     >1 -> AMBIGUOUS_CONTROL_MESSAGE)
  5. schema + chain validation (protocol, task_id, sequence, nonce, in_reply_to,
     project, action, risk, max_runtime_s; unknown fields rejected)
  6. RISK GATE — LOW auto-executes; MEDIUM/HIGH -> AWAITING_APPROVAL, no execution
  7. CONTRACT GATE — real path, under the project root, no symlink escape,
     READY, manifest hash match, existing compiler validator
  8. SELF-MODIFICATION GATE — a live EXECUTE_CONTRACT whose validated contract
     authorizes a control-plane path is rejected with E_SELF_MODIFY_CONTROL_PLANE
     BEFORE consumption
  9. REPLAY GATE — consume task identity BEFORE invoking Hermes
 10. EXECUTING progress — one compact flushed record (decision/status, task_id,
     max_runtime_s) before blocking on the child
 11. EXECUTE under the Contract Guard (HERMES_CONTRACT_PACKAGE + EXECUTOR-PROMPT.md);
     a KeyboardInterrupt is durably journaled and enters RECOVERY_REQUIRED (exit 130)
 12. RESULT TRANSACTION — BUILD RESULT -> FSYNC pending_result.json -> status
     REPORTING -> mark send_attempted durably -> ONE browser send attempt -> CONFIRM
     the exact canonical result message in a USER TURN -> journal RESULT -> commit
     chain state -> remove pending result -> WAITING_FOR_GPT. An unconfirmed attempt
     stops as SEND_UNCERTAIN and is NEVER resent. Confirmation is EXACT canonical
     message equality (CRLF/LF + surrounding-whitespace normalised), never an
     identifier / result_sha256 substring.
 13. HUMAN-ONLY SEND_UNCERTAIN RESOLVER — `resolve-send-uncertain [--resend-once
     --reason REASON]`. Never called automatically. It confirms the exact canonical
     pending message read-only; an already-delivered message commits with zero
     sends; an absent message without --resend-once stops as HUMAN_ACTION_REQUIRED;
     an absent message with --resend-once durably journals the authorization and the
     human_resend_count BEFORE exactly one send attempt. Hermes is never executed.

Assistant prose outside the envelope is UNTRUSTED_RESPONSE_DATA and is never
turned into control.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bridge_state as bs  # noqa: E402
import chatgpt_adapter as adapter  # noqa: E402
import contract_executor as ce  # noqa: E402
import protocol as proto  # noqa: E402

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_STOPPED = 2
EXIT_REJECTED = 3
EXIT_AMBIGUOUS = 4
EXIT_SEND_UNCERTAIN = 5
EXIT_INTERRUPTED = 130


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _emit(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def _progress(payload: dict) -> None:
    """One compact, flushed progress record. Never a streamed model log."""
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    sys.stdout.flush()


# --------------------------------------------------------------------------- #
# Pending-result transaction helpers
# --------------------------------------------------------------------------- #

def _commit_pending(pending: dict, *, root, state, send) -> dict:
    """Journal the terminal result, commit the chain, drop the pending record.

    Called only after the send is CONFIRMED_SENT, is ALREADY_PRESENT, or has been
    confirmed already-present by a read-only recovery check. The chain is never
    advanced before this point.
    """
    result = pending.get("result") or {}
    task_id = pending.get("task_id")
    sequence = pending.get("sequence")
    result_sha = pending.get("result_sha256")

    bs.journal_outcome(
        task_id=task_id,
        sequence=sequence,
        outcome=result.get("outcome"),
        exit_code=int(result.get("exit_code", 0)),
        result_sha256=result_sha,
        root=root,
    )
    state.chain(
        next_sequence=pending.get("next_sequence"),
        next_nonce=pending.get("next_nonce"),
        next_in_reply_to=pending.get("in_reply_to"),
        status="WAITING_FOR_GPT",
        last_task_id=task_id,
        last_result_sha256=result_sha,
    )
    bs.remove_pending(root)
    return {
        "decision": "WAITING_FOR_GPT",
        "task_id": task_id,
        "sequence": sequence,
        "outcome": result.get("outcome"),
        "exit_code": EXIT_OK,
        "status": "WAITING_FOR_GPT",
        "result": result,
        "send": send,
        "recovered": True,
    }


def _recover_pending(pending: dict, *, root, state, journal, send_fn, confirm_fn) -> dict:
    """Resolve a durable pending result at startup. Never resends blindly."""
    result_sha = pending.get("result_sha256")
    message = pending.get("message")
    if not isinstance(result_sha, str) or not isinstance(message, str):
        state.set_status("RECOVERY_REQUIRED")
        journal({"event": "PENDING_UNREADABLE"})
        return {"decision": "RECOVERY_REQUIRED", "reason": "PENDING_RESULT_UNREADABLE",
                "task_id": pending.get("task_id"), "exit_code": EXIT_ERROR,
                "status": "RECOVERY_REQUIRED"}

    if pending.get("send_attempted") is True:
        # The send may already have landed. Confirm the EXACT canonical message
        # read-only (DEC-001); NEVER resend.
        try:
            present = bool(confirm_fn(message))
        except Exception as exc:  # noqa: BLE001 - a transport failure cannot be a green light
            state.set_status("ERROR")
            journal({"event": "PENDING_CONFIRM_FAILED", "error": type(exc).__name__,
                     "task_id": pending.get("task_id")})
            return {"decision": "SEND_UNCERTAIN", "reason": "CONFIRMATION_UNAVAILABLE",
                    "task_id": pending.get("task_id"), "result": pending.get("result"),
                    "exit_code": EXIT_SEND_UNCERTAIN, "status": "ERROR"}
        if not present:
            state.set_status("ERROR")
            journal({"event": "SEND_UNCERTAIN", "task_id": pending.get("task_id"),
                     "result_sha256": result_sha})
            return {"decision": "SEND_UNCERTAIN", "task_id": pending.get("task_id"),
                    "sequence": pending.get("sequence"), "result_sha256": result_sha,
                    "exit_code": EXIT_SEND_UNCERTAIN, "status": "ERROR",
                    "result": pending.get("result")}
        journal({"event": "PENDING_CONFIRMED_ALREADY_PRESENT", "task_id": pending.get("task_id"),
                 "result_sha256": result_sha})
        return _commit_pending(pending, root=root, state=state, send={"status": adapter.ALREADY_PRESENT})

    # send_attempted=false: the single send attempt has not been made yet.
    bs.mark_send_attempted(root)
    send = send_fn(message, result_sha)
    if send.get("status") == adapter.SEND_UNCERTAIN:
        state.set_status("ERROR")
        journal({"event": "SEND_UNCERTAIN", "task_id": pending.get("task_id"),
                 "result_sha256": result_sha})
        return {"decision": "SEND_UNCERTAIN", "task_id": pending.get("task_id"),
                "sequence": pending.get("sequence"), "exit_code": EXIT_SEND_UNCERTAIN,
                "status": "ERROR", "result": pending.get("result"), "send": send}
    return _commit_pending(pending, root=root, state=state, send=send)


# --------------------------------------------------------------------------- #
# One round
# --------------------------------------------------------------------------- #

def _round_impl(*, root: Path | None, read_fn, gate_fn, execute_fn, send_fn,
                confirm_timeout_s: float, progress_fn=None, confirm_fn=None) -> dict:
    state = bs.load_state(root)
    journal = lambda entry: bs.journal_append(entry, root)  # noqa: E731
    progress = progress_fn or _progress
    confirm = confirm_fn or (lambda message: adapter.confirm_message_present(message))

    # -- 1. STOPPED LATCH (before any browser read; no state mutation) ------
    if state.get("status") == "STOPPED":
        journal({"event": "STOPPED_LATCHED"})
        return {"decision": "STOPPED_LATCHED", "status": "STOPPED",
                "exit_code": EXIT_STOPPED}

    # -- 2. STARTUP RECONCILIATION ------------------------------------------
    pending = bs.read_pending(root)
    if pending is not None:
        return _recover_pending(pending, root=root, state=state, journal=journal,
                                send_fn=send_fn, confirm_fn=confirm)

    unresolved = bs.unresolved_accepted(root)
    if unresolved:
        state.set_status("RECOVERY_REQUIRED")
        journal({"event": "RECOVERY_REQUIRED",
                 "task_id": unresolved[0].get("task_id"), "count": len(unresolved)})
        return {"decision": "RECOVERY_REQUIRED", "status": "RECOVERY_REQUIRED",
                "unresolved_task_ids": [entry.get("task_id") for entry in unresolved],
                "exit_code": EXIT_ERROR}

    # -- 3. READ ------------------------------------------------------------
    state.set_status("VALIDATING")
    try:
        message = read_fn()
    except Exception as exc:  # noqa: BLE001 - transport failure is reported, not raised
        state.set_status("ERROR")
        journal({"event": "READ_FAILED", "error": type(exc).__name__, "message": str(exc)})
        return {"decision": "READ_FAILED", "error": type(exc).__name__,
                "message": str(exc), "exit_code": EXIT_ERROR, "status": state.get("status")}

    assistant_text = message.get("text") if isinstance(message, dict) else None

    # -- 4. EXTRACT ---------------------------------------------------------
    extracted = proto.extract_control_message(assistant_text)

    if extracted["status"] == proto.S_NO_CONTROL:
        state.set_status("WAITING_FOR_GPT")
        return {"decision": proto.S_NO_CONTROL, "exit_code": EXIT_OK,
                "status": state.get("status"), "assistant_sha256": (message or {}).get("sha256")}

    if extracted["status"] == proto.S_AMBIGUOUS:
        # Fail closed: never guess which envelope is the control message.
        state.set_status("ERROR")
        journal({"event": "AMBIGUOUS_CONTROL_MESSAGE", **{k: extracted[k] for k in ("blocks", "opens", "closes")}})
        return {"decision": proto.S_AMBIGUOUS, "blocks": extracted["blocks"],
                "reason": extracted["reason"], "exit_code": EXIT_AMBIGUOUS,
                "status": state.get("status")}

    if extracted["status"] != proto.S_ACCEPTED:
        state.set_status("ERROR")
        journal({"event": "ENVELOPE_REJECTED", "code": extracted.get("code")})
        return {"decision": "ENVELOPE_REJECTED", "code": extracted.get("code"),
                "message": extracted.get("message"), "exit_code": EXIT_REJECTED,
                "status": state.get("status")}

    task = extracted["task"]
    task_sha = extracted["task_envelope_sha256"]

    # -- 5. VALIDATE (schema + chain) --------------------------------------
    verdict = proto.validate_task(task, state)
    if verdict["status"] != proto.S_ACCEPTED:
        state.set_status("ERROR")
        journal({"event": "TASK_REJECTED", "code": verdict["code"],
                 "task_id": task.get("task_id"), "task_envelope_sha256": task_sha})
        return {"decision": "TASK_REJECTED", "code": verdict["code"],
                "message": verdict["message"], "task_id": task.get("task_id"),
                "exit_code": EXIT_REJECTED, "status": state.get("status")}

    # -- STOP --------------------------------------------------------------
    if task["action"] == "STOP":
        bs.consume_task(task, task_envelope_sha256=task_sha, root=root)
        state.chain(
            next_sequence=task["sequence"] + 1,
            next_nonce=bs.new_nonce(),
            next_in_reply_to=proto.sha256_text("STOPPED:" + task_sha),
            status="STOPPED",
            last_task_id=task["task_id"],
        )
        journal({"event": "STOPPED", "task_id": task["task_id"], "sequence": task["sequence"]})
        return {"decision": "STOPPED", "task_id": task["task_id"],
                "sequence": task["sequence"], "exit_code": EXIT_STOPPED,
                "status": "STOPPED"}

    # -- 6. RISK GATE -------------------------------------------------------
    if not verdict["auto_execute"]:
        journal({"event": "AWAITING_APPROVAL", "task_id": task["task_id"],
                 "sequence": task["sequence"], "risk": task["risk"]})
        state.set_status("AWAITING_APPROVAL")
        return {"decision": "AWAITING_APPROVAL", "task_id": task["task_id"],
                "sequence": task["sequence"], "risk": task["risk"],
                "exit_code": EXIT_OK, "status": "AWAITING_APPROVAL"}

    # -- 7. CONTRACT GATE ---------------------------------------------------
    try:
        gate = gate_fn(task["contract_package"], task["contract_manifest_sha256"])
    except ce.GateError as exc:
        state.set_status("ERROR")
        journal({"event": "CONTRACT_REJECTED", "task_id": task["task_id"],
                 "sequence": task["sequence"], "code": exc.code})
        return {"decision": "CONTRACT_REJECTED", "code": exc.code, "message": exc.message,
                "task_id": task["task_id"], "exit_code": EXIT_REJECTED,
                "status": state.get("status")}

    # -- 8. SELF-MODIFICATION GATE (before consumption) ---------------------
    try:
        ce.check_self_modification(gate.get("allowed_paths", []))
    except ce.GateError as exc:
        state.set_status("ERROR")
        journal({"event": "SELF_MODIFY_REJECTED", "task_id": task["task_id"],
                 "sequence": task["sequence"], "code": exc.code})
        return {"decision": "SELF_MODIFY_REJECTED", "code": exc.code, "message": exc.message,
                "task_id": task["task_id"], "exit_code": EXIT_REJECTED,
                "status": state.get("status")}

    # -- 9. REPLAY GATE (consume BEFORE invoking Hermes) --------------------
    consumed = bs.consume_task(task, task_envelope_sha256=task_sha, root=root)
    if consumed["status"] != "CONSUMED":
        state.set_status("ERROR")
        return {"decision": "REPLAY_REJECTED", "reason": consumed["reason"],
                "task_id": task["task_id"], "exit_code": EXIT_REJECTED,
                "status": state.get("status")}

    # -- 10/11. EXECUTE under the Contract Guard ----------------------------
    state.set_status("EXECUTING")
    progress({"decision": "EXECUTING", "status": "EXECUTING",
              "task_id": task["task_id"], "max_runtime_s": task["max_runtime_s"]})
    try:
        execution = execute_fn(gate["package"], Path(gate["prompt"]), task["max_runtime_s"])
    except KeyboardInterrupt:
        # Durable interruption record; no terminal result; never a synthesized SUCCESS.
        journal({"event": "INTERRUPTED", "task_id": task["task_id"],
                 "sequence": task["sequence"], "exit_code": EXIT_INTERRUPTED})
        state.set_status("RECOVERY_REQUIRED")
        return {"decision": "RECOVERY_REQUIRED", "reason": "INTERRUPTED_BY_OPERATOR",
                "task_id": task["task_id"], "sequence": task["sequence"],
                "exit_code": EXIT_INTERRUPTED, "status": "RECOVERY_REQUIRED"}

    # -- 12. RESULT TRANSACTION --------------------------------------------
    next_nonce = bs.new_nonce()
    core = proto.build_result_core(
        task_id=task["task_id"],
        sequence=task["sequence"],
        outcome=execution["outcome"],
        exit_code=execution["exit_code"],
        next_sequence=task["sequence"] + 1,
        next_nonce=next_nonce,
        in_reply_to=task_sha,
    )
    envelope = proto.build_result_envelope(core)
    message_out = proto.render_result_message(envelope)
    result_sha = envelope["result_sha256"]

    pending = {
        "task_id": task["task_id"],
        "sequence": task["sequence"],
        "result": envelope,
        "result_sha256": result_sha,
        "message": message_out,
        "next_sequence": envelope["next_sequence"],
        "next_nonce": next_nonce,
        "in_reply_to": result_sha,
        "send_attempted": False,
    }

    # FSYNC PENDING RESULT before any send, then REPORTING, then mark the
    # non-idempotent attempt durably. Only then is the single send allowed.
    bs.write_pending(pending, root)
    state.set_status("REPORTING")
    bs.mark_send_attempted(root)

    send = send_fn(message_out, result_sha)

    if send.get("status") == adapter.SEND_UNCERTAIN:
        state.set_status("ERROR")
        journal({"event": "SEND_UNCERTAIN", "task_id": task["task_id"],
                 "sequence": task["sequence"], "result_sha256": result_sha})
        return {"decision": "SEND_UNCERTAIN", "task_id": task["task_id"],
                "sequence": task["sequence"], "outcome": execution["outcome"],
                "exit_code": EXIT_SEND_UNCERTAIN, "status": "ERROR",
                "result": envelope, "send": send}

    # CONFIRMED_SENT or ALREADY_PRESENT: the chain may now advance.
    return _commit_pending(pending, root=root, state=state, send=send)


def run_round(*, root: Path | None = None, read_fn=None, gate_fn=None,
              execute_fn=None, send_fn=None,
              confirm_timeout_s: float = adapter.DEFAULT_CONFIRM_TIMEOUT_S,
              progress_fn=None, confirm_fn=None) -> dict:
    """One round, under the single-worker lock."""
    read_fn = read_fn or (lambda: adapter.read_latest_assistant())
    gate_fn = gate_fn or ce.gate
    execute_fn = execute_fn or (
        lambda package, prompt, max_runtime_s: ce.execute(package, prompt, max_runtime_s)
    )
    send_fn = send_fn or (
        # The normal result path confirms delivery by the exact canonical result
        # message, never by an identifier substring (DEC-001 / TASK-04).
        lambda text, identifier: adapter.send_once(text, identifier,
                                                   confirm_timeout_s=confirm_timeout_s,
                                                   exact=True)
    )
    with bs.bridge_lock(root):
        return _round_impl(root=root, read_fn=read_fn, gate_fn=gate_fn,
                           execute_fn=execute_fn, send_fn=send_fn,
                           confirm_timeout_s=confirm_timeout_s,
                           progress_fn=progress_fn, confirm_fn=confirm_fn)


# --------------------------------------------------------------------------- #
# Official bounded recovery (RECOVERY_REQUIRED only)
# --------------------------------------------------------------------------- #

def _recover_precheck(state, root) -> tuple[dict | None, dict | None]:
    """Evaluate the RECOVERY_REQUIRED preconditions EXACTLY ONCE (DEC-005).

    Returns ``(rejection, entry)``: ``rejection`` is a terminal payload when the
    invocation must not proceed, ``entry`` is the single unresolved ACCEPTED
    journal entry when it may.

    This is the ONLY place the preconditions are evaluated. The transaction below
    never consults ``status`` again, so one invocation cannot transition to
    ``REPORTING`` and then re-enter this precondition against its own new state —
    the defect that produced ``RECOVERY_REJECTED`` / ``NOT_IN_RECOVERY_REQUIRED``
    while a durable pending result already existed.
    """
    status = state.get("status")
    if status != "RECOVERY_REQUIRED":
        return ({"decision": "RECOVERY_REJECTED", "reason": "NOT_IN_RECOVERY_REQUIRED",
                 "status": status, "exit_code": EXIT_REJECTED}, None)

    if bs.read_pending(root) is not None:
        return ({"decision": "RECOVERY_REJECTED", "reason": "PENDING_RESULT_PRESENT",
                 "status": status, "exit_code": EXIT_REJECTED}, None)

    unresolved = bs.unresolved_accepted(root)
    if len(unresolved) != 1:
        return ({"decision": "RECOVERY_REJECTED",
                 "reason": "NO_UNRESOLVED_TASK" if not unresolved else "AMBIGUOUS_UNRESOLVED_TASK",
                 "count": len(unresolved), "status": status,
                 "exit_code": EXIT_AMBIGUOUS if unresolved else EXIT_REJECTED}, None)

    return (None, unresolved[0])


def _recover_impl(*, root: Path | None, exit_code: int, reason: str,
                  send_fn, confirm_fn) -> dict:
    """Resolve exactly one unresolved consumed task into one BLOCKED result.

    One invocation performs, in order and inside that single invocation:

      build BLOCKED result -> write pending -> REPORTING -> send transaction
      (confirm the exact canonical result) -> journal RESULT -> advance chain ->
      remove pending -> WAITING_FOR_GPT.

    Operates only in RECOVERY_REQUIRED, which is checked exactly once up front.
    Never executes Hermes again, never synthesizes SUCCESS, and advances the chain
    only after confirmed delivery.
    """
    state = bs.load_state(root)
    journal = lambda entry: bs.journal_append(entry, root)  # noqa: E731

    rejection, entry = _recover_precheck(state, root)
    if rejection is not None:
        return rejection

    task_id = entry["task_id"]
    sequence = entry["sequence"]
    task_sha = entry.get("task_envelope_sha256") or ""

    next_nonce = bs.new_nonce()
    core = proto.build_result_core(
        task_id=task_id,
        sequence=sequence,
        outcome="BLOCKED",
        exit_code=exit_code,
        next_sequence=sequence + 1,
        next_nonce=next_nonce,
        in_reply_to=task_sha,
    )
    envelope = proto.build_result_envelope(core)
    message_out = proto.render_result_message(envelope)
    result_sha = envelope["result_sha256"]

    pending = {
        "task_id": task_id,
        "sequence": sequence,
        "result": envelope,
        "result_sha256": result_sha,
        "message": message_out,
        "next_sequence": envelope["next_sequence"],
        "next_nonce": next_nonce,
        "in_reply_to": result_sha,
        "send_attempted": False,
        "recovery": {"exit_code": exit_code, "reason": reason},
    }

    journal({"event": "RECOVERY_BLOCKED", "task_id": task_id, "sequence": sequence,
             "reason": reason, "result_sha256": result_sha})

    bs.write_pending(pending, root)
    state.set_status("REPORTING")
    bs.mark_send_attempted(root)

    send = send_fn(message_out, result_sha)

    if send.get("status") == adapter.SEND_UNCERTAIN:
        state.set_status("ERROR")
        journal({"event": "SEND_UNCERTAIN", "task_id": task_id, "sequence": sequence,
                 "result_sha256": result_sha})
        return {"decision": "SEND_UNCERTAIN", "task_id": task_id, "sequence": sequence,
                "outcome": "BLOCKED", "exit_code": EXIT_SEND_UNCERTAIN, "status": "ERROR",
                "result": envelope, "send": send}

    committed = _commit_pending(pending, root=root, state=state, send=send)
    committed["decision"] = "BLOCKED"
    return committed


def run_recover(*, root: Path | None = None, exit_code: int = EXIT_INTERRUPTED,
                reason: str = "INTERRUPTED_BY_OPERATOR", send_fn=None, confirm_fn=None,
                confirm_timeout_s: float = adapter.DEFAULT_CONFIRM_TIMEOUT_S) -> dict:
    """The one official recovery command, under the single-worker lock."""
    send_fn = send_fn or (
        lambda text, identifier: adapter.send_once(text, identifier,
                                                   confirm_timeout_s=confirm_timeout_s,
                                                   exact=True)
    )
    confirm_fn = confirm_fn or (lambda message: adapter.confirm_message_present(message))
    with bs.bridge_lock(root):
        return _recover_impl(root=root, exit_code=exit_code, reason=reason,
                             send_fn=send_fn, confirm_fn=confirm_fn)


# --------------------------------------------------------------------------- #
# HUMAN-ONLY SEND_UNCERTAIN resolver (never called automatically)
# --------------------------------------------------------------------------- #

def _resolve_send_uncertain_impl(*, root: Path | None, resend_once: bool, reason: str,
                                 send_fn, confirm_fn, execute_fn) -> dict:
    """Resolve ONE SEND_UNCERTAIN pending result, human-authorized.

    Preconditions (DEC-008): ``status == ERROR``, a pending result exists, the
    pending ``send_attempted == True``, exactly one unresolved ACCEPTED task, and
    the pending task matches it.

    Then (DEC-006 / DEC-007):

      * exact read-only canonical confirmation present -> commit with ZERO sends,
        journal ``HUMAN_CONFIRMED_EXISTING_RESULT``, ``WAITING_FOR_GPT``;
      * absent and no ``--resend-once`` -> ``HUMAN_ACTION_REQUIRED``: no send, no
        state or chain advance;
      * absent with ``--resend-once`` and a non-empty reason -> durably journal
        ``HUMAN_RESEND_AUTHORIZED`` and durably record ``human_resend_count``
        BEFORE exactly ONE send attempt; confirmed -> journal RESULT, commit chain,
        remove pending, ``WAITING_FOR_GPT``; not confirmed -> stay ``ERROR``,
        retain pending, return ``SEND_UNCERTAIN``.

    A pending result with ``human_resend_count >= 1`` refuses another resend.
    ``execute_fn`` is accepted for the never-executes-Hermes proof and is NEVER
    invoked on any path.
    """
    state = bs.load_state(root)
    journal = lambda entry: bs.journal_append(entry, root)  # noqa: E731

    # -- preconditions ------------------------------------------------------
    if state.get("status") != "ERROR":
        return {"decision": "RESOLVE_REJECTED", "reason": "NOT_IN_ERROR",
                "status": state.get("status"), "exit_code": EXIT_REJECTED}

    pending = bs.read_pending(root)
    if pending is None:
        return {"decision": "RESOLVE_REJECTED", "reason": "NO_PENDING_RESULT",
                "status": state.get("status"), "exit_code": EXIT_REJECTED}

    task_id = pending.get("task_id")
    result_sha = pending.get("result_sha256")

    if pending.get("send_attempted") is not True:
        return {"decision": "RESOLVE_REJECTED", "reason": "SEND_NOT_ATTEMPTED",
                "task_id": task_id, "status": state.get("status"),
                "exit_code": EXIT_REJECTED}

    unresolved = bs.unresolved_accepted(root)
    if len(unresolved) != 1:
        return {"decision": "RESOLVE_REJECTED",
                "reason": "NO_UNRESOLVED_TASK" if not unresolved else "AMBIGUOUS_UNRESOLVED_TASK",
                "count": len(unresolved), "status": state.get("status"),
                "exit_code": EXIT_AMBIGUOUS if unresolved else EXIT_REJECTED}

    if pending.get("task_id") != unresolved[0].get("task_id"):
        return {"decision": "RESOLVE_REJECTED", "reason": "PENDING_TASK_MISMATCH",
                "task_id": task_id, "unresolved_task_id": unresolved[0].get("task_id"),
                "status": state.get("status"), "exit_code": EXIT_REJECTED}

    message = pending.get("message")
    if not isinstance(message, str) or not message.strip():
        return {"decision": "RESOLVE_REJECTED", "reason": "PENDING_MESSAGE_UNREADABLE",
                "task_id": task_id, "status": state.get("status"),
                "exit_code": EXIT_REJECTED}

    # -- 1. exact read-only confirmation: already delivered? ----------------
    try:
        present = bool(confirm_fn(message))
    except Exception as exc:  # noqa: BLE001 - a transport failure is never a green light
        journal({"event": "HUMAN_CONFIRM_FAILED", "error": type(exc).__name__,
                 "task_id": task_id})
        return {"decision": "HUMAN_ACTION_REQUIRED", "reason": "CONFIRMATION_UNAVAILABLE",
                "task_id": task_id, "exit_code": EXIT_ERROR, "status": state.get("status")}

    if present:
        journal({"event": "HUMAN_CONFIRMED_EXISTING_RESULT", "task_id": task_id,
                 "result_sha256": result_sha, "send_attempted": False})
        committed = _commit_pending(pending, root=root, state=state,
                                    send={"status": adapter.ALREADY_PRESENT, "sent": False})
        committed["human_resolution"] = "HUMAN_CONFIRMED_EXISTING_RESULT"
        committed["resend_attempted"] = False
        return committed

    # -- 2. absent: no automatic resend ------------------------------------
    if not resend_once:
        journal({"event": "HUMAN_ACTION_REQUIRED", "task_id": task_id,
                 "result_sha256": result_sha})
        return {"decision": "HUMAN_ACTION_REQUIRED", "reason": "CANONICAL_MESSAGE_ABSENT",
                "task_id": task_id, "sequence": pending.get("sequence"),
                "result_sha256": result_sha, "exit_code": EXIT_ERROR,
                "status": state.get("status")}

    reason_text = (reason or "").strip()
    if not reason_text:
        return {"decision": "HUMAN_ACTION_REQUIRED", "reason": "REASON_REQUIRED",
                "task_id": task_id, "exit_code": EXIT_REJECTED,
                "status": state.get("status")}

    used = int(pending.get("human_resend_count") or 0) if isinstance(
        pending.get("human_resend_count"), int) else 0
    if used >= 1:
        journal({"event": "HUMAN_RESEND_REJECTED", "task_id": task_id,
                 "human_resend_count": used})
        return {"decision": "RESEND_REJECTED", "reason": "HUMAN_RESEND_ALREADY_USED",
                "task_id": task_id, "human_resend_count": used,
                "exit_code": EXIT_REJECTED, "status": state.get("status")}

    # -- 3. durable authorization BEFORE the single send attempt -----------
    journal({"event": "HUMAN_RESEND_AUTHORIZED", "task_id": task_id,
             "reason": reason_text, "result_sha256": result_sha})
    persisted = bs.record_human_resend(root, reason=reason_text)
    resend_count = int(persisted.get("human_resend_count") or 1)

    # `execute_fn` is deliberately NOT referenced below: the resolver never
    # executes Hermes on any path.
    send = send_fn(message, result_sha)

    if send.get("status") == adapter.SEND_UNCERTAIN:
        state.set_status("ERROR")
        journal({"event": "SEND_UNCERTAIN", "task_id": task_id,
                 "sequence": pending.get("sequence"), "result_sha256": result_sha,
                 "human_resend_count": resend_count})
        return {"decision": "SEND_UNCERTAIN", "task_id": task_id,
                "sequence": pending.get("sequence"), "result_sha256": result_sha,
                "human_resend_count": resend_count, "exit_code": EXIT_SEND_UNCERTAIN,
                "status": "ERROR", "result": pending.get("result"), "send": send}

    committed = _commit_pending(pending, root=root, state=state, send=send)
    committed["human_resolution"] = "HUMAN_RESEND_CONFIRMED"
    committed["resend_attempted"] = True
    committed["human_resend_count"] = resend_count
    return committed


def resolve_send_uncertain(*, root: Path | None = None, resend_once: bool = False,
                           reason: str = "", send_fn=None, confirm_fn=None,
                           execute_fn=None,
                           confirm_timeout_s: float = adapter.DEFAULT_CONFIRM_TIMEOUT_S) -> dict:
    """HUMAN-ONLY resolution of a SEND_UNCERTAIN pending result.

    Never called automatically by ``round`` or ``recover``: the only entry point is
    the explicit ``resolve-send-uncertain`` CLI subcommand, under the single-worker
    lock.
    """
    send_fn = send_fn or (
        lambda text, identifier: adapter.send_once(text, identifier,
                                                   confirm_timeout_s=confirm_timeout_s,
                                                   exact=True)
    )
    confirm_fn = confirm_fn or (lambda message: adapter.confirm_message_present(message))
    execute_fn = execute_fn or (
        lambda package, prompt, max_runtime_s: ce.execute(package, prompt, max_runtime_s)
    )
    with bs.bridge_lock(root):
        return _resolve_send_uncertain_impl(root=root, resend_once=resend_once,
                                            reason=reason, send_fn=send_fn,
                                            confirm_fn=confirm_fn, execute_fn=execute_fn)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def _cmd_round(args) -> int:
    result = run_round(confirm_timeout_s=args.confirm_timeout)
    _emit(result)
    return int(result.get("exit_code", EXIT_ERROR))


def _cmd_recover(args) -> int:
    result = run_recover(exit_code=args.exit_code, reason=args.reason,
                         confirm_timeout_s=args.confirm_timeout)
    _emit(result)
    return int(result.get("exit_code", EXIT_ERROR))


def _cmd_resolve_send_uncertain(args) -> int:
    result = resolve_send_uncertain(resend_once=args.resend_once, reason=args.reason,
                                    confirm_timeout_s=args.confirm_timeout)
    _emit(result)
    return int(result.get("exit_code", EXIT_ERROR))


def _cmd_status(args) -> int:
    state = bs.load_state()
    task_ids, pairs = bs.consumed_identities()
    _emit({
        "state": state.as_dict(),
        "consumed_task_ids": len(task_ids),
        "consumed_sequences": len(pairs),
        "unresolved_tasks": [entry.get("task_id") for entry in bs.unresolved_accepted()],
        "pending_result": bool(bs.read_pending() is not None),
        "journal_entries": len(bs.read_journal()),
        "state_dir": str(bs.state_dir()),
        "checked_at": _now(),
    })
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GPT <-> Hermes control-kernel bridge (one round)")
    sub = parser.add_subparsers(dest="command", required=True)
    p_round = sub.add_parser("round")
    p_round.add_argument("--confirm-timeout", type=float,
                         default=adapter.DEFAULT_CONFIRM_TIMEOUT_S)
    p_round.set_defaults(func=_cmd_round)
    p_recover = sub.add_parser("recover")
    p_recover.add_argument("--exit-code", type=int, default=EXIT_INTERRUPTED)
    p_recover.add_argument("--reason", default="INTERRUPTED_BY_OPERATOR")
    p_recover.add_argument("--confirm-timeout", type=float,
                           default=adapter.DEFAULT_CONFIRM_TIMEOUT_S)
    p_recover.set_defaults(func=_cmd_recover)
    p_resolve = sub.add_parser("resolve-send-uncertain")
    p_resolve.add_argument("--resend-once", action="store_true")
    p_resolve.add_argument("--reason", default="")
    p_resolve.add_argument("--confirm-timeout", type=float,
                           default=adapter.DEFAULT_CONFIRM_TIMEOUT_S)
    p_resolve.set_defaults(func=_cmd_resolve_send_uncertain)
    sub.add_parser("status").set_defaults(func=_cmd_status)
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except bs.BridgeBusy as exc:
        _emit({"decision": "BRIDGE_BUSY", "message": str(exc), "exit_code": EXIT_ERROR})
        return EXIT_ERROR
    except KeyboardInterrupt:
        _emit({"decision": "INTERRUPTED", "exit_code": EXIT_INTERRUPTED})
        return EXIT_INTERRUPTED
    except Exception as exc:  # noqa: BLE001 - one round never crashes the launcher
        _emit({"decision": "ERROR", "error": type(exc).__name__, "message": str(exc),
               "exit_code": EXIT_ERROR})
        return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
