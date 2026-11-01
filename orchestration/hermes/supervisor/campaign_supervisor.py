#!/usr/bin/env python3
"""campaign_supervisor.py — the bounded wake-up / scheduling loop.

The Supervisor decides only WHEN to invoke the Bridge. It wraps the EXISTING Bridge
interfaces and the deterministic ChatGPT adapter READ seam READ-ONLY; it never
executes a Hermes contract, never sends a ChatGPT message and never edits Bridge
state.

Dispatch policy (default deny at every step):

  1. one campaign lock (a second worker is refused before any work)
  2. startup reconciliation of a durable Bridge pending result (exactly ONE Bridge
     round for the Bridge's own startup reconciliation)
  3. each poll reads the LATEST COMPLETED assistant response through the adapter READ
     seam; the response sha256 is the primary new-response guard
  4. a NEW response is classified: no control -> mark seen / wait; exactly one
     candidate Bridge task -> require the campaign is RUNNING and the Bridge status
     permits a round and sequence/nonce/in_reply_to equal the Bridge challenge, then
     invoke ``bridge_cli.py round`` exactly ONCE; campaign terminal -> validate,
     persist terminal state and exit WITHOUT a Bridge round; malformed / ambiguous /
     mixed / invalid -> fail-closed PAUSED
  5. every Bridge safety state (AWAITING_APPROVAL, RECOVERY_REQUIRED, SEND_UNCERTAIN,
     STOPPED, ERROR) pauses the campaign and exits non-zero, never auto-repairing
  6. ``max_rounds`` and the wall deadline bound autonomy; reaching either persists
     PAUSED with outcome LIMIT_REACHED

Standard library only.
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_BRIDGE = _HERE.parent / "bridge"
for _p in (str(_HERE), str(_BRIDGE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:  # imported as ``supervisor.campaign_supervisor``
    from . import campaign_protocol as cproto
    from . import campaign_state as cstate
except ImportError:  # imported as a top-level module
    import campaign_protocol as cproto
    import campaign_state as cstate

import bridge_state as bridge_state_mod  # noqa: E402  (Bridge, read-only)
import bridge_cli as bridge_cli_mod  # noqa: E402  (Bridge, read-only)
import chatgpt_adapter as chatgpt_adapter_mod  # noqa: E402  (adapter READ seam)

SAFETY_STATUSES = (
    "AWAITING_APPROVAL",
    "RECOVERY_REQUIRED",
    "SEND_UNCERTAIN",
    "STOPPED",
    "ERROR",
)
ROUND_READY_STATUSES = ("WAITING_FOR_GPT", "IDLE")
ACTIVE_CAMPAIGN_STATUSES = ("RUNNING", "WAITING_FOR_GPT")

EXIT_OK = 0
EXIT_PAUSED = 3
EXIT_LOCK_BUSY = 4

OUTCOME_FAILED = "FAILED"
OUTCOME_SAFETY = "SAFETY_STOP"
OUTCOME_LIMIT = "LIMIT_REACHED"


# --------------------------------------------------------------------------- #
# Default (live) seams — overridden by injected fakes in tests
# --------------------------------------------------------------------------- #

def _default_read_latest_assistant():
    return chatgpt_adapter_mod.read_latest_assistant()


def _default_bridge_status():
    return bridge_state_mod.load_state().as_dict()


def _default_bridge_round():
    return bridge_cli_mod.run_round()


def _default_read_pending():
    return bridge_state_mod.read_pending()


def _default_progress(line: str) -> None:
    print(line)
    sys.stdout.flush()


_STAGE_ALLOWED = frozenset({
    "EXECUTED", "ENTRY_REJECTED", "SEND_UNCERTAIN", "WAITING_FOR_GPT",
    "CONTRACT_REJECTED", "TASK_REJECTED", "ENVELOPE_REJECTED", "REPLAY_REJECTED",
    "SELF_MODIFY_REJECTED", "AMBIGUOUS_CONTROL_MESSAGE", "NO_CONTROL_MESSAGE",
    "AWAITING_APPROVAL", "RECOVERY_REQUIRED", "STOPPED", "STOPPED_LATCHED", "ERROR",
})
_CLEANUP_ALLOWED = frozenset({"CONFIRMED", "UNCONFIRMED", "UNKNOWN"})
_SEND_ALLOWED = frozenset({"CONFIRMED_SENT", "ALREADY_PRESENT", "SEND_UNCERTAIN", "UNKNOWN"})
_PHASE_ALLOWED = ("TERM", "KILL")
_TASK_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def _enum(value, allowed):
    return value if isinstance(value, str) and value in allowed else "UNKNOWN"


def _integer(value):
    return str(value) if isinstance(value, int) and not isinstance(value, bool) else "UNKNOWN"


def _ident(value):
    return value if isinstance(value, str) and _TASK_ID_RE.fullmatch(value) else "UNKNOWN"


def _hash(value):
    return value if isinstance(value, str) and _HASH_RE.fullmatch(value) else "UNKNOWN"


def _bool_or_unknown(value):
    if value is True:
        return "True"
    if value is False:
        return "False"
    return "UNKNOWN"


def _phases(value):
    if not isinstance(value, (list, tuple)):
        return "UNKNOWN"
    allowed = sorted({p for p in value if isinstance(p, str) and p in _PHASE_ALLOWED})
    return ",".join(allowed) if allowed else "UNKNOWN"


def _round_diagnostic_fields(round_result) -> str:
    """Whitelisted per-round diagnostic, type- and value-constrained.

    Every field is validated against an allowlist / format; an illegal or missing value
    becomes UNKNOWN. No newlines and no arbitrary strings are passed through. Emits only
    task_id, stage, exit code, timed_out, timeout_phases, cleanup, send status and the
    result hash — never stdout/stderr, prompts, model text, headers or credentials.
    """
    rr = round_result if isinstance(round_result, dict) else {}
    diag = rr.get("diagnostic") if isinstance(rr.get("diagnostic"), dict) else {}
    result = rr.get("result") if isinstance(rr.get("result"), dict) else {}
    send = rr.get("send") if isinstance(rr.get("send"), dict) else {}

    def get(key, fallback=None):
        return diag[key] if key in diag else fallback

    return ("task_id=%s stage=%s exit_code=%s timed_out=%s timeout_phases=%s "
            "cleanup=%s send_status=%s result_sha256=%s"
            % (_ident(get("task_id", rr.get("task_id"))),
               _enum(get("stage", rr.get("decision")), _STAGE_ALLOWED),
               _integer(get("exit_code")),
               _bool_or_unknown(get("timed_out")),
               _phases(get("timeout_phases")),
               _enum(get("cleanup"), _CLEANUP_ALLOWED),
               _enum(get("send_status", send.get("status")), _SEND_ALLOWED),
               _hash(get("result_sha256",
                         rr.get("result_sha256") or result.get("result_sha256")))))


class CampaignSupervisor:
    """Bounded, one-round-at-a-time Supervisor for a single milestone."""

    def __init__(self, *, campaign_id, milestone, max_rounds, max_wall_seconds,
                 poll_seconds, start_sequence=None, start_nonce=None,
                 start_in_reply_to=None, store=None, read_latest_assistant=None,
                 bridge_status=None, bridge_round=None, read_pending=None,
                 clock=None, sleep=None, progress=None,
                 lock_timeout=cstate.LOCK_TIMEOUT_S):
        self.campaign_id = campaign_id
        self.milestone = milestone
        self.max_rounds = int(max_rounds)
        self.max_wall_seconds = float(max_wall_seconds)
        self.poll_seconds = float(poll_seconds)
        self.start_sequence = start_sequence
        self.start_nonce = start_nonce
        self.start_in_reply_to = start_in_reply_to
        self.store = store or cstate.CampaignStore(campaign_id)
        self.read_latest_assistant = read_latest_assistant or _default_read_latest_assistant
        self.bridge_status = bridge_status or _default_bridge_status
        self.bridge_round = bridge_round or _default_bridge_round
        self.read_pending = read_pending or _default_read_pending
        self.clock = clock or time.time
        self.sleep = sleep or time.sleep
        self.progress = progress or _default_progress
        self.lock_timeout = lock_timeout
        self.round_calls = 0  # informational counter of Bridge rounds invoked

    # -- progress ------------------------------------------------------------ #
    def _progress_line(self, line: str) -> None:
        self.progress(line)

    # -- run ----------------------------------------------------------------- #
    def run(self) -> dict:
        """Run the campaign to CLOSED / PAUSED / safety stop / limit.

        Acquires the campaign lock FIRST; a second worker is refused with a
        lock-busy outcome without touching the Bridge or the campaign state.
        """
        try:
            with self.store.lock(timeout=self.lock_timeout):
                return self._run_locked()
        except cstate.CampaignLockBusy as exc:
            self._progress_line("CAMPAIGN_LOCK_BUSY campaign_id=%s" % self.campaign_id)
            return {"status": "LOCK_BUSY", "outcome": "LOCK_BUSY",
                    "exit_code": EXIT_LOCK_BUSY, "reason": str(exc)}

    def _run_locked(self) -> dict:
        state = self.store.load()

        if state is None:
            bridge = self.bridge_status()
            initial_sequence = (
                self.start_sequence
                if self.start_sequence is not None
                else bridge.get("expected_sequence")
            )
            now = self.clock()
            state = cstate.initial_state(
                campaign_id=self.campaign_id,
                milestone=self.milestone,
                started_at=now,
                deadline=now + self.max_wall_seconds,
                max_rounds=self.max_rounds,
                initial_sequence=initial_sequence,
            )
            self.store.create(state)
            self.store.journal({
                "event": "CAMPAIGN_START",
                "campaign_id": self.campaign_id,
                "milestone": self.milestone,
                "initial_sequence": initial_sequence,
                "start_nonce": self.start_nonce,
                "start_in_reply_to": self.start_in_reply_to,
                "max_rounds": self.max_rounds,
                "max_wall_seconds": self.max_wall_seconds,
            })

        # -- startup reconciliation of a durable Bridge pending result ------- #
        pending = self.read_pending()
        if pending is not None:
            self._progress_line("CAMPAIGN_RECONCILE campaign_id=%s" % self.campaign_id)
            self.store.journal({
                "event": "CAMPAIGN_RECONCILE",
                "campaign_id": self.campaign_id,
                "task_id": pending.get("task_id") if isinstance(pending, dict) else None,
            })
            self.round_calls += 1
            round_result = self.bridge_round() or {}
            self._progress_line("CAMPAIGN_ROUND_DIAG " + _round_diagnostic_fields(round_result))
            after = self.bridge_status()
            if after.get("status") in SAFETY_STATUSES:
                return self._pause(
                    state, OUTCOME_SAFETY,
                    "bridge safety state after startup reconciliation: %s" % after.get("status"),
                )
            state["last_bridge_result_sha256"] = after.get("last_result_sha256")
            self.store.save(state)

        # -- bounded main loop ---------------------------------------------- #
        while True:
            if state.get("status") == "CLOSED":
                return {"status": "CLOSED", "outcome": state.get("terminal_outcome"),
                        "exit_code": EXIT_OK, "reason": "campaign already closed"}

            now = self.clock()
            if now >= state["deadline"]:
                return self._pause(state, OUTCOME_LIMIT, "wall clock deadline reached")
            if int(state["round_count"]) >= int(state["max_rounds"]):
                return self._pause(state, OUTCOME_LIMIT, "max_rounds reached")

            bridge = self.bridge_status()
            bridge_state_name = bridge.get("status")
            if bridge_state_name in SAFETY_STATUSES:
                return self._pause(
                    state, OUTCOME_SAFETY, "bridge safety state: %s" % bridge_state_name,
                )

            message = self.read_latest_assistant()
            sha = message.get("sha256") if isinstance(message, dict) else None

            if sha is not None and sha == state.get("last_seen_assistant_sha256"):
                self._set_waiting(state)
                self.sleep(self.poll_seconds)
                continue

            text = message.get("text") if isinstance(message, dict) else None
            decision = cproto.classify_response(
                text,
                campaign_id=self.campaign_id,
                milestone=self.milestone,
                last_result_sha256=bridge.get("last_result_sha256"),
            )
            kind = decision["status"]

            if kind == cproto.S_NO_CONTROL:
                self._mark_seen(state, sha)
                self._set_waiting(state)
                self.sleep(self.poll_seconds)
                continue

            if kind == cproto.S_CAMPAIGN_TERMINAL:
                return self._close(state, decision["campaign"], sha)

            if kind == cproto.S_TASK_CANDIDATE:
                terminal = self._dispatch(state, decision, bridge, sha)
                if terminal is not None:
                    return terminal
                continue

            # S_MALFORMED / S_AMBIGUOUS / S_MIXED / S_CAMPAIGN_INVALID -> fail closed
            reason = decision.get("code") or decision.get("reason") or kind
            return self._pause(state, OUTCOME_FAILED, "%s: %s" % (kind, reason))

    # -- dispatch ------------------------------------------------------------ #
    def _dispatch(self, state, decision, bridge, sha):
        """Invoke the Bridge exactly once for a valid new task, or pause."""
        if state.get("status") not in ACTIVE_CAMPAIGN_STATUSES:
            return self._pause(state, OUTCOME_FAILED, "campaign is not RUNNING")

        bridge_state_name = bridge.get("status")
        if bridge_state_name not in ROUND_READY_STATUSES:
            return self._pause(
                state, OUTCOME_FAILED,
                "bridge status does not permit a round: %s" % bridge_state_name,
            )

        task = decision["task"]
        if (task.get("sequence") != bridge.get("expected_sequence")
                or task.get("nonce") != bridge.get("expected_nonce")
                or task.get("in_reply_to") != bridge.get("expected_in_reply_to")):
            return self._pause(
                state, OUTCOME_FAILED,
                "task chain does not match the Bridge challenge",
            )

        self._progress_line("CAMPAIGN_DISPATCH sequence=%s task_id=%s"
                            % (task.get("sequence"), task.get("task_id")))

        # Exactly one Bridge round for this valid new task.
        self.round_calls += 1
        round_result = self.bridge_round() or {}
        self._progress_line("CAMPAIGN_ROUND_DIAG " + _round_diagnostic_fields(round_result))

        state["round_count"] = int(state.get("round_count", 0)) + 1
        state["last_dispatched_task_id"] = task.get("task_id")
        self._mark_seen(state, sha)
        self.store.journal({
            "event": "CAMPAIGN_DISPATCH",
            "campaign_id": self.campaign_id,
            "sequence": task.get("sequence"),
            "task_id": task.get("task_id"),
            "round_count": state["round_count"],
        })

        after = self.bridge_status()
        state["last_bridge_result_sha256"] = after.get("last_result_sha256")
        self.store.save(state)

        if after.get("status") in SAFETY_STATUSES:
            return self._pause(
                state, OUTCOME_SAFETY,
                "bridge safety state after round: %s" % after.get("status"),
            )

        self._progress_line("CAMPAIGN_ROUND_COMPLETE result_sha256=%s"
                            % state.get("last_bridge_result_sha256"))
        return None

    # -- helpers ------------------------------------------------------------- #
    def _mark_seen(self, state, sha) -> None:
        state["last_seen_assistant_sha256"] = sha
        self.store.save(state)

    def _set_waiting(self, state) -> None:
        if state.get("status") not in ("CLOSED", "PAUSED"):
            state["status"] = "WAITING_FOR_GPT"
            self.store.save(state)
        self._progress_line("CAMPAIGN_WAITING_FOR_GPT campaign_id=%s" % self.campaign_id)

    def _close(self, state, campaign, sha) -> dict:
        status = campaign["status"]
        outcome = campaign["outcome"]
        state["status"] = status
        state["terminal_outcome"] = outcome
        if sha is not None:
            state["last_seen_assistant_sha256"] = sha
        self.store.save(state)
        self.store.journal({
            "event": "CAMPAIGN_TERMINAL",
            "campaign_id": self.campaign_id,
            "status": status,
            "outcome": outcome,
            "in_reply_to": campaign.get("in_reply_to"),
        })
        if status == "CLOSED":
            self._progress_line("CAMPAIGN_CLOSED outcome=%s" % outcome)
            return {"status": "CLOSED", "outcome": outcome, "exit_code": EXIT_OK,
                    "reason": "campaign terminal accepted"}
        self._progress_line("CAMPAIGN_PAUSED outcome=%s" % outcome)
        return {"status": "PAUSED", "outcome": outcome, "exit_code": EXIT_PAUSED,
                "reason": "campaign terminal accepted"}

    def _pause(self, state, outcome, reason) -> dict:
        state["status"] = "PAUSED"
        state["terminal_outcome"] = outcome
        self.store.save(state)
        self.store.journal({
            "event": "CAMPAIGN_PAUSED",
            "campaign_id": self.campaign_id,
            "outcome": outcome,
            "reason": reason,
        })
        self._progress_line("CAMPAIGN_PAUSED outcome=%s reason=%s" % (outcome, reason))
        return {"status": "PAUSED", "outcome": outcome, "exit_code": EXIT_PAUSED,
                "reason": reason}
