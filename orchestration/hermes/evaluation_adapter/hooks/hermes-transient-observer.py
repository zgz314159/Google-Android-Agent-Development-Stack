#!/usr/bin/env python3
"""STACK-SIMPLIFICATION-S2-WAVE1A — Hermes transient shell-hook observer.

STATUS: SHADOW_ONLY
    This script is deliberately NOT registered in any live Hermes profile. WAVE1A only creates,
    tests and inerts it; enabling it in the live profile (and the live telemetry A/B) is WAVE1B.
    ``/home/zhong/.hermes/profiles/android-stack/config.yaml`` is byte-identical across WAVE1A.

WHAT IT IS
    An *observer-only* shell hook compatible with the pinned Hermes hook contract
    (environment: /home/zhong/.hermes/hermes-agent, HERMES-LOCK.json commit
    af90026aa09949579bd423d24def3d38f743cde0). The wire format comes from the pinned source,
    never from assumption:

        agent/shell_hooks.py::_serialize_payload -> json.dumps({"hook_event_name": event,
            **_payload_fields(kwargs)})
        agent/shell_hooks.py::_payload_fields   -> {tool_name, tool_input, session_id, cwd,
            profile, extra};  every other kwarg lands under "extra"
        (``session_id`` is promoted from ``session_id`` or ``parent_session_id``)

    So stdin is one JSON object per firing with the promoted keys
    ``hook_event_name, tool_name, tool_input, session_id, cwd, profile, extra``.

WHAT IT DOES
    Appends one JSON object per handled event to an append-only JSONL log, capturing METADATA
    ONLY (identifiers, status, timings, model/provider, and the *names* of the payload keys that
    were present). It never captures prompt text, message bodies, tool-result bodies, assistant
    content, attachment/binary data, raw request/response objects, or any secret value.

    Handled events (when present): post_tool_call, pre_api_request, post_api_request,
    api_request_error.

CONTRACT (observer-only, deliberately)
    * writes nothing to stdout, so it can never produce a block/allow/modify directive;
    * always exits 0;
    * malformed / empty / non-object stdin fails SAFE — nothing is written, exit 0;
    * writes only its JSONL target (default below, overridable with ``HERMES_OBSERVER_LOG``),
      in append mode — an existing file is never truncated or rewritten;
    * touches nothing in the product tree and no Guard decision.

This module is intentionally stdlib-only and has no import-time side effects.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

# --------------------------------------------------------------------------- #
# paths
# --------------------------------------------------------------------------- #
# <repo>/orchestration/hermes/evaluation_adapter/hooks/hermes-transient-observer.py
_HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_HOOK_DIR))))

def _default_log() -> str:
    _lib = os.path.join(_REPO_ROOT, "scripts", "lib")
    if _lib not in sys.path:
        sys.path.insert(0, _lib)
    import stack_paths  # noqa: PLC0415

    return str(stack_paths.telemetry_root() / "transient-hook-events.jsonl")


DEFAULT_LOG = _default_log()
LOG_ENV = "HERMES_OBSERVER_LOG"

# Events this observer records when the runtime fires them.
HANDLED_EVENTS = frozenset({
    "post_tool_call",
    "pre_api_request",
    "post_api_request",
    "api_request_error",
})

# Promoted top-level payload keys (pinned shell_hooks.py). Not captured except by name.
PROMOTED_KEYS = ("hook_event_name", "tool_name", "tool_input", "session_id", "cwd", "profile", "extra")

# Scalar metadata fields captured when present (top-level or under "extra").
CAPTURE_FIELDS = (
    "session_id", "profile", "cwd", "tool_name",
    "tool_call_id", "task_id", "turn_id", "api_request_id",
    "status", "error_type", "duration_ms", "api_call_count", "model", "provider",
)

_SCALARS = (str, int, float, bool)


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _lookup(payload: dict, extra: dict, key: str):
    """A scalar field from the top level, else from ``extra`` — never a nested object."""
    for source in (payload, extra):
        if key in source:
            value = source[key]
            if value is None or isinstance(value, _SCALARS):
                return value
    return None


def build_record(payload: dict, event: str) -> dict:
    """Build the metadata-only record for one firing."""
    extra = payload.get("extra")
    if not isinstance(extra, dict):
        extra = {}

    record = {"hook_event_name": event, "captured_at": _utc_now()}
    for key in CAPTURE_FIELDS:
        value = _lookup(payload, extra, key)
        if value is not None:
            record[key] = value

    # Key names actually present (top level + extra), sorted. Names only — never values.
    names = set(payload.keys()) | set(extra.keys())
    record["payload_keys"] = sorted(str(n) for n in names)
    return record


def observe(raw: str) -> int:
    """Write at most one JSONL line for ``raw``; fail safe and silent. Returns exit code 0."""
    try:
        if not raw or not raw.strip():
            return 0
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            return 0
        event = payload.get("hook_event_name")
        if not isinstance(event, str) or event not in HANDLED_EVENTS:
            return 0

        record = build_record(payload, event)
        line = json.dumps(record, ensure_ascii=False, sort_keys=True)

        path = os.environ.get(LOG_ENV) or DEFAULT_LOG
        directory = os.path.dirname(os.path.abspath(path))
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:  # append-only; never truncate
            fh.write(line + "\n")
    except Exception:  # noqa: BLE001 — an observer must never disturb the agent turn
        return 0
    return 0


def main() -> int:
    try:
        raw = sys.stdin.read()
    except Exception:  # noqa: BLE001
        raw = ""
    observe(raw)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
