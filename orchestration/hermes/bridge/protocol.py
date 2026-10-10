#!/usr/bin/env python3
"""HERMES_TASK_V1 control-envelope protocol.

Phase 4 — minimal GPT <-> Hermes control kernel.

Deterministic, standard library only. No LLM, no network, no shell, no arbitrary
path, no arbitrary action.

The ONLY executable control surface is a single block inside the LATEST COMPLETED
assistant response::

    <<<HERMES_TASK_V1>>>
    { JSON }
    <<<END_HERMES_TASK_V1>>>

Everything outside that block is UNTRUSTED_RESPONSE_DATA: DOM prose, assistant
commentary and any instruction smuggled into it MUST NOT become control.

Transport authenticity is not semantic authorization. A well-formed envelope is
only a *candidate*; it still has to pass schema, chain, replay, risk and contract
gates before anything is executed (see bridge_cli.round).

This module owns:

  * envelope extraction + counting (NO_CONTROL_MESSAGE / AMBIGUOUS_CONTROL_MESSAGE)
  * strict JSON decoding (duplicate keys are an error, never last-wins)
  * canonical JSON + SHA-256 (UTF-8, sorted keys, compact separators)
  * HERMES_TASK_V1 field validation against the expected bridge state
  * HERMES_RESULT_V1 result-envelope construction

It deliberately contains no I/O.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

# --------------------------------------------------------------------------- #
# Protocol constants
# --------------------------------------------------------------------------- #

PROTOCOL_TASK = "HERMES_TASK_V1"
PROTOCOL_RESULT = "HERMES_RESULT_V1"

TASK_OPEN = "<<<HERMES_TASK_V1>>>"
TASK_CLOSE = "<<<END_HERMES_TASK_V1>>>"
RESULT_OPEN = "<<<HERMES_RESULT_V1>>>"
RESULT_CLOSE = "<<<END_HERMES_RESULT_V1>>>"

# Exact field set. Unknown fields are rejected (default deny), missing fields are
# rejected, and no field is optional.
TASK_FIELDS = (
    "protocol",
    "task_id",
    "sequence",
    "nonce",
    "in_reply_to",
    "project",
    "action",
    "contract_package",
    "contract_manifest_sha256",
    "risk",
    "max_runtime_s",
)

ALLOWED_PROJECTS = frozenset({"Google-Android-Agent-Development-Stack"})
ALLOWED_ACTIONS = frozenset({"EXECUTE_CONTRACT", "STOP"})
ALLOWED_RISK = frozenset({"LOW", "MEDIUM", "HIGH"})

# Only LOW may auto-execute; MEDIUM / HIGH park in AWAITING_APPROVAL.
AUTO_EXECUTE_RISK = frozenset({"LOW"})

MAX_RUNTIME_MIN = 1
MAX_RUNTIME_MAX = 3600

TASK_ID_MIN_LEN = 1
TASK_ID_MAX_LEN = 128
TASK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")

MANIFEST_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
GENESIS = "GENESIS"

_BLOCK_RE = re.compile(
    re.escape(TASK_OPEN) + r"(.*?)" + re.escape(TASK_CLOSE),
    re.DOTALL,
)

# --------------------------------------------------------------------------- #
# Status vocabulary
# --------------------------------------------------------------------------- #

S_ACCEPTED = "ACCEPTED"
S_REJECTED = "REJECTED"
S_NO_CONTROL = "NO_CONTROL_MESSAGE"
S_AMBIGUOUS = "AMBIGUOUS_CONTROL_MESSAGE"
S_ALREADY_PRESENT = "ALREADY_PRESENT"

BRIDGE_STATUSES = (
    "IDLE",
    "VALIDATING",
    "EXECUTING",
    "REPORTING",
    "WAITING_FOR_GPT",
    "AWAITING_APPROVAL",
    "STOPPED",
    "ERROR",
)


# --------------------------------------------------------------------------- #
# Canonical JSON / hashing
# --------------------------------------------------------------------------- #

class DuplicateKeyError(ValueError):
    """Raised when a JSON object repeats a key. Duplicate keys are never last-wins."""


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict:
    obj: dict = {}
    for key, value in pairs:
        if key in obj:
            raise DuplicateKeyError("duplicate JSON key: %r" % (key,))
        obj[key] = value
    return obj


def load_json_strict(text: str) -> Any:
    """json.loads with duplicate-key rejection and NaN/Infinity rejection."""
    return json.loads(text, object_pairs_hook=_no_duplicate_keys, parse_constant=_reject_constant)


def _reject_constant(name: str) -> Any:
    raise ValueError("non-finite JSON literal not allowed: %s" % name)


def canonical_json(obj: Any) -> str:
    """Canonical JSON: UTF-8, sorted keys, compact separators."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(obj: Any) -> str:
    return sha256_text(canonical_json(obj))


def task_envelope_sha256(task: dict) -> str:
    """SHA-256 of the canonical task JSON — the chain link the next result cites."""
    return canonical_sha256(task)


# --------------------------------------------------------------------------- #
# Envelope extraction
# --------------------------------------------------------------------------- #

def extract_control_message(text: str | None) -> dict:
    """Extract the single control envelope from an assistant message.

    Returns one of:

      {"status": "NO_CONTROL_MESSAGE"}
      {"status": "AMBIGUOUS_CONTROL_MESSAGE", "blocks": n, "reason": ...}
      {"status": "ACCEPTED", "task": {...}, "task_envelope_sha256": "..."}

    The count is taken over the whole message: zero blocks is no control, more
    than one block (or an unbalanced marker) is ambiguous and stops the round.
    """
    if not isinstance(text, str) or not text.strip():
        return {"status": S_NO_CONTROL}

    blocks = list(_BLOCK_RE.finditer(text))
    opens = text.count(TASK_OPEN)
    closes = text.count(TASK_CLOSE)

    if len(blocks) != opens or opens != closes:
        return {
            "status": S_AMBIGUOUS,
            "blocks": len(blocks),
            "opens": opens,
            "closes": closes,
            "reason": "unbalanced or malformed HERMES_TASK_V1 markers",
        }

    if not blocks:
        return {"status": S_NO_CONTROL}

    if len(blocks) > 1:
        return {
            "status": S_AMBIGUOUS,
            "blocks": len(blocks),
            "opens": opens,
            "closes": closes,
            "reason": "more than one HERMES_TASK_V1 envelope in the latest assistant response",
        }

    payload = blocks[0].group(1)
    try:
        task = load_json_strict(payload)
    except DuplicateKeyError as exc:
        return {"status": S_REJECTED, "code": "E_DUPLICATE_KEY", "message": str(exc)}
    except ValueError as exc:
        return {"status": S_REJECTED, "code": "E_MALFORMED_JSON", "message": str(exc)}

    if not isinstance(task, dict):
        return {"status": S_REJECTED, "code": "E_NOT_OBJECT", "message": "envelope JSON must be an object"}

    return {
        "status": S_ACCEPTED,
        "task": task,
        "task_envelope_sha256": task_envelope_sha256(task),
    }


# --------------------------------------------------------------------------- #
# Task validation
# --------------------------------------------------------------------------- #

def _expected_state(expected: Any) -> dict:
    """Accept a BridgeState-like object or a plain mapping."""
    if hasattr(expected, "as_dict"):
        return expected.as_dict()
    return dict(expected)


def validate_task(task: dict, expected: Any) -> dict:
    """Validate a decoded task against the expected bridge state.

    Returns {"status": "ACCEPTED"|"REJECTED", "code": ..., "message": ...}.

    Default deny: every check must pass.
    """
    state = _expected_state(expected)

    def reject(code: str, message: str) -> dict:
        return {"status": S_REJECTED, "code": code, "message": message}

    # -- shape ---------------------------------------------------------------
    if not isinstance(task, dict):
        return reject("E_NOT_OBJECT", "task must be a JSON object")

    unknown = sorted(set(task) - set(TASK_FIELDS))
    if unknown:
        return reject("E_UNKNOWN_FIELD", "unknown fields: %s" % ", ".join(unknown))

    missing = sorted(set(TASK_FIELDS) - set(task))
    if missing:
        return reject("E_MISSING_FIELD", "missing fields: %s" % ", ".join(missing))

    # -- protocol ------------------------------------------------------------
    if task["protocol"] != PROTOCOL_TASK:
        return reject("E_PROTOCOL", "protocol must equal %s" % PROTOCOL_TASK)

    # -- task_id -------------------------------------------------------------
    task_id = task["task_id"]
    if not isinstance(task_id, str) or not (TASK_ID_MIN_LEN <= len(task_id) <= TASK_ID_MAX_LEN):
        return reject("E_TASK_ID", "task_id must be a bounded non-empty string")
    if not TASK_ID_RE.match(task_id):
        return reject("E_TASK_ID", "task_id has characters outside [A-Za-z0-9._:-]")

    # -- sequence ------------------------------------------------------------
    sequence = task["sequence"]
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
        return reject("E_SEQUENCE", "sequence must be an integer >= 1")
    expected_sequence = state.get("expected_sequence")
    if sequence != expected_sequence:
        return reject(
            "E_SEQUENCE",
            "sequence %r does not match expected_sequence %r" % (sequence, expected_sequence),
        )

    # -- nonce ---------------------------------------------------------------
    nonce = task["nonce"]
    if not isinstance(nonce, str) or not nonce:
        return reject("E_NONCE", "nonce must be a non-empty string")
    expected_nonce = state.get("expected_nonce")
    if nonce != expected_nonce:
        return reject("E_NONCE", "nonce does not match expected_nonce")

    # -- in_reply_to -----------------------------------------------------------
    in_reply_to = task["in_reply_to"]
    if not isinstance(in_reply_to, str) or not in_reply_to:
        return reject("E_IN_REPLY_TO", "in_reply_to must be a non-empty string")
    expected_reply = state.get("expected_in_reply_to")
    if in_reply_to != expected_reply:
        return reject("E_IN_REPLY_TO", "in_reply_to does not match the expected chain link")

    # -- project -------------------------------------------------------------
    project = task["project"]
    if project not in ALLOWED_PROJECTS:
        return reject("E_PROJECT", "project %r is not in the allowlist" % (project,))

    # -- action --------------------------------------------------------------
    action = task["action"]
    if action not in ALLOWED_ACTIONS:
        return reject("E_ACTION", "action %r is not allowed" % (action,))

    # -- risk ----------------------------------------------------------------
    risk = task["risk"]
    if risk not in ALLOWED_RISK:
        return reject("E_RISK", "risk %r is not one of LOW/MEDIUM/HIGH" % (risk,))

    # -- max_runtime_s -------------------------------------------------------
    max_runtime_s = task["max_runtime_s"]
    if isinstance(max_runtime_s, bool) or not isinstance(max_runtime_s, int):
        return reject("E_MAX_RUNTIME", "max_runtime_s must be an integer")
    if not (MAX_RUNTIME_MIN <= max_runtime_s <= MAX_RUNTIME_MAX):
        return reject(
            "E_MAX_RUNTIME",
            "max_runtime_s must be within %d..%d" % (MAX_RUNTIME_MIN, MAX_RUNTIME_MAX),
        )

    # -- contract package fields --------------------------------------------
    package = task["contract_package"]
    manifest_sha = task["contract_manifest_sha256"]
    if not isinstance(package, str):
        return reject("E_CONTRACT_PACKAGE", "contract_package must be a string")
    if not isinstance(manifest_sha, str):
        return reject("E_CONTRACT_MANIFEST_SHA256", "contract_manifest_sha256 must be a string")

    if action == "STOP":
        # STOP carries no package, but still has to pass the whole chain above.
        if package != "":
            return reject("E_STOP_PACKAGE", "STOP requires contract_package to be empty")
        if manifest_sha != "":
            return reject("E_STOP_PACKAGE", "STOP requires contract_manifest_sha256 to be empty")
        if risk != "LOW":
            return reject("E_STOP_RISK", "STOP requires risk=LOW")
    else:  # EXECUTE_CONTRACT
        if not package:
            return reject("E_CONTRACT_PACKAGE", "EXECUTE_CONTRACT requires a contract_package")
        if not MANIFEST_SHA_RE.match(manifest_sha):
            return reject("E_CONTRACT_MANIFEST_SHA256", "contract_manifest_sha256 must be 64 lowercase hex")

    return {
        "status": S_ACCEPTED,
        "code": "OK",
        "message": "task validated",
        "auto_execute": risk in AUTO_EXECUTE_RISK,
    }


# --------------------------------------------------------------------------- #
# Result envelope
# --------------------------------------------------------------------------- #

RESULT_CORE_FIELDS = (
    "protocol",
    "task_id",
    "sequence",
    "outcome",
    "exit_code",
    "next_sequence",
    "next_nonce",
    "in_reply_to",
)

OUTCOMES = ("SUCCESS", "FAILED", "BLOCKED", "STOPPED")


def build_result_core(
    *,
    task_id: str,
    sequence: int,
    outcome: str,
    exit_code: int,
    next_sequence: int,
    next_nonce: str,
    in_reply_to: str,
) -> dict:
    """The result core: everything except result_sha256."""
    if outcome not in OUTCOMES:
        raise ValueError("outcome %r must be one of %s" % (outcome, ", ".join(OUTCOMES)))
    return {
        "protocol": PROTOCOL_RESULT,
        "task_id": task_id,
        "sequence": sequence,
        "outcome": outcome,
        "exit_code": exit_code,
        "next_sequence": next_sequence,
        "next_nonce": next_nonce,
        "in_reply_to": in_reply_to,
    }


def build_result_envelope(core: dict) -> dict:
    """Add result_sha256 = SHA256(canonical core). The chain link for task N+1."""
    core = {key: core[key] for key in RESULT_CORE_FIELDS}
    envelope = dict(core)
    envelope["result_sha256"] = canonical_sha256(core)
    return envelope


def render_result_message(envelope: dict) -> str:
    """Render the control message back to ChatGPT: result block + next challenge."""
    body = json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    next_sequence = envelope["next_sequence"]
    next_nonce = envelope["next_nonce"]
    result_sha = envelope["result_sha256"]
    return "\n".join(
        [
            RESULT_OPEN,
            body,
            RESULT_CLOSE,
            "",
            "NEXT_CONTROL_CHALLENGE:",
            "sequence=%s" % next_sequence,
            "nonce=%s" % next_nonce,
            "in_reply_to=%s" % result_sha,
        ]
    )
