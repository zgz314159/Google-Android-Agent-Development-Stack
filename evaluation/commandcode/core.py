#!/usr/bin/env python3
"""Command Code Evaluation Core v0.2.

Deterministic, offline, standard-library-only observer.

Design source:
  Google-Android-Agent-Stack-v1.3-Evaluation-Layer-v0.2-Implementation-Design.md

This module only observes, computes and reports. It never changes agent
behaviour, never re-runs builds/tests/devices, and makes zero LLM/network calls.

Pipeline:  JSONL -> task window -> turn-owned wall timeline -> phase mapper
           -> tags -> metrics -> run.json / phase-timeline.csv / analysis.md
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

CORE_VERSION = "0.2.3"
SUPPORTED_SCHEMA_VERSIONS = {3}

_HERE = Path(__file__).resolve().parent
_DEFAULT_TAXONOMY = _HERE.parent / "taxonomy"

TIMING_KEYS = (
    "inputTokens",
    "outputTokens",
    "cacheReadTokens",
    "cacheWriteTokens",
    "costUsd",
)


# --------------------------------------------------------------------------- #
# errors
# --------------------------------------------------------------------------- #
class EvaluationError(Exception):
    pass


class UnsupportedSchema(EvaluationError):
    def __init__(self, version):
        super().__init__(f"UNSUPPORTED_SCHEMA: {version}")
        self.version = version


class SessionLocateError(EvaluationError):
    pass


# --------------------------------------------------------------------------- #
# time helpers
# --------------------------------------------------------------------------- #
def parse_ts(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def secs(a: datetime, b: datetime) -> float:
    return (b - a).total_seconds()


# --------------------------------------------------------------------------- #
# redaction
# --------------------------------------------------------------------------- #
class Redactor:
    def __init__(self, config: dict):
        self.key_re = re.compile(config.get("sensitive_key_regex", r"(?i)(token|key|secret)"))
        self.text_patterns = [
            (re.compile(p["regex"]), p["replace"]) for p in config.get("text_patterns", [])
        ]

    def text(self, value) -> str:
        if value is None:
            return ""
        s = str(value)
        for rx, repl in self.text_patterns:
            s = rx.sub(repl, s)
        return s

    def obj(self, value):
        if isinstance(value, dict):
            return {
                k: ("<REDACTED>" if self.key_re.search(str(k)) else self.obj(v))
                for k, v in value.items()
            }
        if isinstance(value, list):
            return [self.obj(v) for v in value]
        if isinstance(value, str):
            return self.text(value)
        return value


# --------------------------------------------------------------------------- #
# session loading / identity
# --------------------------------------------------------------------------- #
@dataclass
class SessionData:
    path: str
    session: dict
    rows: list  # message rows only (type == "message")
    schema_version: int
    sha256: str
    size_bytes: int
    models: list


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_session(path: str) -> SessionData:
    session = None
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if obj.get("type") == "session":
                session = obj
            elif obj.get("type") == "message":
                rows.append(obj)
    if session is None:
        raise EvaluationError(f"no session row found in {path}")
    version = session.get("version")
    models = []
    for r in rows:
        if r.get("model") and r["model"] not in models:
            models.append(r["model"])
    return SessionData(
        path=os.path.abspath(path),
        session=session,
        rows=rows,
        schema_version=version,
        sha256=_sha256(path),
        size_bytes=os.path.getsize(path),
        models=models,
    )


def check_schema(session: SessionData) -> None:
    if session.schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise UnsupportedSchema(session.schema_version)


# --------------------------------------------------------------------------- #
# row helpers
# --------------------------------------------------------------------------- #
def role(row: dict) -> str:
    return row.get("message", {}).get("role", "")


def parts(row: dict) -> list:
    c = row.get("message", {}).get("content")
    return c if isinstance(c, list) else []


def part_text(part: dict) -> str:
    c = part.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return "".join(
            x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text"
        )
    return ""


def input_path(inp: dict) -> str:
    if not isinstance(inp, dict):
        return ""
    for key in ("file_path", "path"):
        if inp.get(key):
            return str(inp[key])
    if inp.get("paths"):
        p = inp["paths"]
        return ",".join(map(str, p)) if isinstance(p, list) else str(p)
    if inp.get("pattern"):
        return str(inp["pattern"])
    return ""


# Command Code JSONL v3 tags every message with a structured origin in
# message.meta.source. This is the authoritative task-boundary signal:
#   "user"     -> a genuine user-authored message (independent task prompt)
#   "model"    -> assistant output
#   "tool"     -> tool result injected as a user-side message
#   "steering" -> runtime-injected control message (monitor pings, approvals…)
# Only "user" opens/closes a task window. "tool" and "steering" are same-task
# continuations and must never truncate the window.
USER_MESSAGE_SOURCES = ("user", "tool", "steering")


def message_source(row: dict):
    meta = (row.get("message") or {}).get("meta")
    if isinstance(meta, dict):
        src = meta.get("source")
        if isinstance(src, str):
            return src
    return None


def has_tool_result(row: dict) -> bool:
    return any(p.get("type") == "tool_result" for p in parts(row))


def is_legacy_prompt(row: dict) -> bool:
    """Fallback heuristic, used only when message.meta.source is absent.

    Kept so historical/synthetic sessions without the structured field still
    parse; such windows are flagged as uncertain by analyze().
    """
    if role(row) != "user":
        return False
    ps = parts(row)
    has_text = any(p.get("type") == "text" for p in ps)
    has_result = any(p.get("type") == "tool_result" for p in ps)
    return has_text and not has_result


def is_task_prompt(row: dict) -> bool:
    """True iff this row is an independent user task prompt (a task boundary)."""
    if role(row) != "user":
        return False
    if has_tool_result(row):
        return False
    src = message_source(row)
    if src is not None:
        return src == "user"
    return is_legacy_prompt(row)


def is_steering(row: dict) -> bool:
    return role(row) == "user" and message_source(row) == "steering"


def prompt_text(row: dict) -> str:
    return "".join(p.get("text", "") for p in parts(row) if p.get("type") == "text")


def find_task_prompts(rows: list) -> list:
    return [i for i, r in enumerate(rows) if is_task_prompt(r)]


def resolve_task_window(rows: list, prompt_contains=None):
    """Return (start_idx, end_idx_exclusive, matched_idx).

    The window closes only at the *next independent task prompt*. Same-task
    continuations (tool results, steering/control pings, ask_user_question and
    plan-approval responses) stay inside the window.
    """
    prompts = find_task_prompts(rows)
    if not prompts:
        raise EvaluationError("session has no independent user task prompt")
    matched = None
    if prompt_contains:
        for i in prompts:
            if prompt_contains in prompt_text(rows[i]):
                matched = i
                break
        if matched is None:
            raise EvaluationError(
                f"no prompt matched prompt-contains={prompt_contains!r}; "
                f"session has {len(prompts)} independent task prompt(s)"
            )
    else:
        matched = prompts[0]
    later = [i for i in prompts if i > matched]
    end = later[0] if later else len(rows)
    return matched, end, matched


# --------------------------------------------------------------------------- #
# v0.2.2 human-in-the-loop clock model + task completion
# --------------------------------------------------------------------------- #
# A human-in-the-loop tool (ask_user_question / plan approval) blocks the agent
# until a human responds. Command Code commits an assistant row when its turn
# completes; for a turn ending in such a blocking tool the row is committed on
# RESUME, so the turn-owned span (previous turn end, resume] is where the human
# wait actually lives. v0.2.1 instead measured the gap *after* the answer (to the
# next assistant turn) and left the real wait inside the ask/review span.
#
# message.meta.createdAt (when the assistant message was actually produced) vs the
# row timestamp (resume) brackets the human round-trip exactly when present. When
# it is absent the whole boundary span is used as an upper bound - but it is never
# counted as agent work. Nothing is keyword-guessed.
HUMAN_LOOP_TOOLS = ("ask_user_question", "plan_review", "exit_plan_mode")
USER_WAIT_TAG = "USER_WAIT"


def created_at(row: dict):
    """Structured assistant-message creation time (message.meta.createdAt, ms)."""
    meta = (row.get("message") or {}).get("meta")
    if isinstance(meta, dict):
        v = meta.get("createdAt")
        if isinstance(v, (int, float)):
            return datetime.fromtimestamp(v / 1000.0, tz=timezone.utc)
    return None


def compute_task_clocks(rows: list, start: int, end: int, calls_by_row: dict) -> dict:
    """Derive the v0.2.2 clocks for one task window.

    task_elapsed_wall      = task prompt -> final assistant completion (wall)
    interactive_user_wait  = model->human->resume time proven from a structured
                             human-in-the-loop boundary. Separated exactly via
                             message.meta.createdAt when present (question emit ->
                             resume); otherwise the whole boundary span is an UPPER
                             BOUND. Never counted as agent work.
    unattributed_idle_wall = task wall proven non-agent but not provably a human
                             boundary (OS idle / client suspend). Stays 0 unless
                             such evidence exists; nothing is guessed into it.
    agent_owned_wall       = task_elapsed_wall - interactive_user_wait
                             - unattributed_idle_wall
    """
    assistant_rows = [i for i in range(start, end) if role(rows[i]) == "assistant"]
    if not assistant_rows:
        raise EvaluationError("task window has no assistant turn")

    task_start = parse_ts(rows[start]["timestamp"])
    completion_row = assistant_rows[-1]
    task_end = parse_ts(rows[completion_row]["timestamp"])

    boundaries = []
    wait_by_row = {}
    prev_end = task_start
    upper_bound_only = False
    for i in assistant_rows:
        ts = parse_ts(rows[i]["timestamp"])
        span = secs(prev_end, ts)
        names = {c.name for c in calls_by_row.get(i, [])}
        hit = sorted(names.intersection(HUMAN_LOOP_TOOLS))
        if hit:
            ca = created_at(rows[i])
            if ca is not None and ca >= prev_end:
                wait = max(0.0, min(span, secs(ca, ts)))
                model_secs = span - wait
                basis = "meta.createdAt->resume"
            else:
                # emit vs resume cannot be separated -> whole span is an upper bound
                wait = span
                model_secs = 0.0
                basis = "whole-span-upper-bound"
                upper_bound_only = True
            boundaries.append({
                "row": i,
                "tool": hit[0],
                "span_seconds": round(span, 3),
                "model_seconds": round(model_secs, 3),
                "wait_seconds": round(wait, 3),
                "basis": basis,
            })
            if wait > 0:
                wait_by_row[i] = round(wait, 3)
        prev_end = ts

    elapsed = round(secs(task_start, task_end), 3)
    if boundaries:
        interactive = min(round(sum(w["wait_seconds"] for w in boundaries), 3), elapsed)
        agent_owned = round(elapsed - interactive, 3)
    else:
        interactive = None
        agent_owned = elapsed
    unattributed = 0.0

    return {
        "task_start": task_start,
        "task_end": task_end,
        "completion_row": completion_row,
        "elapsed": elapsed,
        "agent_owned": agent_owned,
        "interactive": interactive,
        "unattributed": unattributed,
        "human_loop_waits": boundaries,
        "wait_by_row": wait_by_row,
        "interactive_user_wait_upper_bound": upper_bound_only,
        "steering_rows": [i for i in range(start, end) if is_steering(rows[i])],
    }


def detect_completion(rows: list, start: int, end: int, completion_row: int) -> dict:
    """Structurally confirm the window ends on a terminal assistant completion."""
    row = rows[completion_row]
    ps = parts(row)
    has_tool_use = any(p.get("type") == "tool_use" for p in ps)
    text = "".join(p.get("text", "") for p in ps if p.get("type") == "text").strip()
    terminal = not has_tool_use
    is_tail = completion_row == end - 1
    detected = bool(terminal and text and is_tail)
    return {
        "task_completion_detected": detected,
        "final_assistant_row": completion_row,
        "final_assistant_id": row.get("id"),
        "final_assistant_timestamp": iso(parse_ts(row["timestamp"])),
        "terminal_assistant_turn": terminal,
        "final_message_is_window_tail": is_tail,
        "evidence": text.splitlines()[0][:160] if text else "",
    }


# --------------------------------------------------------------------------- #
# calls + results indexing
# --------------------------------------------------------------------------- #
@dataclass
class Call:
    call_id: str
    name: str
    input: dict
    row_index: int
    result_text: str = ""
    result_row: int = None
    task_id: str = None
    op_id: str = None
    status: str = "unknown"
    exit_code: int = None
    wait_seconds: float = None


@dataclass
class Turn:
    turn_id: str
    row_index: int
    timestamp: datetime
    calls: list = field(default_factory=list)
    usage: dict = None
    final_text: str = ""


def index_calls(rows: list, indices: list):
    """Build calls (with results) and a task-id -> origin map for the window."""
    calls = []
    by_id = {}
    for abs_i in indices:
        row = rows[abs_i]
        r = role(row)
        for p in parts(row):
            pt = p.get("type")
            if pt == "tool_use" and r == "assistant":
                c = Call(call_id=p.get("id"), name=p.get("name"), input=p.get("input") or {}, row_index=abs_i)
                calls.append(c)
                by_id[c.call_id] = c
            elif pt == "tool_result" and r == "user":
                c = by_id.get(p.get("tool_use_id"))
                if c is not None and not c.result_text:
                    c.result_text = part_text(p)
                    c.result_row = abs_i

    # parse structured status / exit / wait for every call result
    for c in calls:
        _parse_result_signals(c)

    # task-id origins (background jobs)
    origins = {}
    for c in calls:
        if c.task_id:
            origins[c.task_id] = c
    # a command that merely tails a background job's log is the same logical
    # operation as that job (raw failure dedup, design section 10).
    for c in calls:
        if c.task_id is None and c.name == "shell_command":
            m = re.search(r"shellout/[^/\s]*?-([a-z0-9]{6,})\.log", (c.input or {}).get("command", "") or "")
            if m and m.group(1) in origins:
                c.task_id = m.group(1)
    for c in calls:
        if c.name in ("shell_output", "shell_tasks", "kill_shell"):
            tid = c.input.get("id")
            if isinstance(tid, str) and tid in origins:
                c.op_id = "bg:" + tid
            elif isinstance(tid, str):
                c.op_id = "bg:" + tid
        if c.op_id is None:
            if c.task_id:
                c.op_id = "bg:" + c.task_id
            else:
                c.op_id = "call:" + str(c.call_id)
    return calls, by_id, origins


def _parse_result_signals(c: Call) -> None:
    t = c.result_text or ""
    m = re.search(r"Task:\s*([A-Za-z0-9]+)", t)
    if m and (c.name == "monitor_command"
              or (c.name == "shell_command" and c.input.get("run_in_background"))):
        c.task_id = m.group(1)
    m = re.search(r"Exit code:\s*(-?\d+)", t)
    if m:
        c.exit_code = int(m.group(1))
    m = re.search(r"\bEXIT=(-?\d+)", t)
    if m and c.exit_code is None:
        c.exit_code = int(m.group(1))
    m = re.search(r"\((?:shell|monitor|background),\s*(completed|failed|running)\)", t)
    if m:
        c.status = m.group(1)
    elif c.exit_code == 0 or c.name in ("read_file", "read_directory", "glob", "write_file", "edit_file") and t:
        c.status = "completed"
    if c.status in (None, "unknown"):
        tv = test_run_verdict(t)
        if tv is not None:
            c.status = "completed" if tv["verdict"] == "pass" else "failed"
        elif re.search(r"(?i)BUILD FAILED|FAILURE:\s*Build failed|Execution failed for task|TESTS FAILED|Traceback \(most recent", t):
            c.status = "failed"
        elif re.search(r"(?i)BUILD SUCCESSFUL|BUILD OK|TESTS PASSED|UNIT_PASSED|CHECKS_OK", t):
            c.status = "completed"
    m = re.search(r"\[waited ([^\]]+)\]", t)
    if m:
        c.wait_seconds = _parse_duration(m.group(1))


def _parse_duration(s: str):
    total = 0.0
    found = False
    for val, unit in re.findall(r"(\d+(?:\.\d+)?)\s*(h|m|s)", s):
        found = True
        total += float(val) * {"h": 3600, "m": 60, "s": 1}[unit]
    if not found:
        m = re.match(r"(\d+(?:\.\d+)?)\s*$", s.strip())
        if m:
            return float(m.group(1))
    return total if found else None


def build_turns(rows: list, indices: list, task_start: datetime) -> list:
    turns = []
    prev_end = task_start
    n = 0
    for abs_i in indices:
        row = rows[abs_i]
        if role(row) != "assistant":
            continue
        ts = parse_ts(row["timestamp"])
        n += 1
        use = row.get("usage") if isinstance(row.get("usage"), dict) else None
        final_text = "".join(
            p.get("text", "") for p in parts(row) if p.get("type") == "text"
        )
        turns.append(
            Turn(
                turn_id=f"TURN-{n:04d}",
                row_index=abs_i,
                timestamp=ts,
                calls=[],
                usage=use,
                final_text=final_text,
            )
        )
        prev_end = ts
    return turns


def attach_calls(turns: list, calls: list) -> None:
    by_row = defaultdict(list)
    for c in calls:
        by_row[c.row_index].append(c)
    for t in turns:
        t.calls = by_row.get(t.row_index, [])


# --------------------------------------------------------------------------- #
# phase mapper
# --------------------------------------------------------------------------- #
class PhaseMapper:
    def __init__(self, rules: dict):
        self.rules = rules.get("rules", [])

    def _effective_items(self, turn: Turn, origins: dict):
        items = []
        for c in turn.calls:
            items.append(
                {
                    "name": c.name,
                    "command": (c.input or {}).get("command", "") or (c.input or {}).get("description", "") or "",
                    "path": input_path(c.input or {}),
                    "result": c.result_text or "",
                    "subagent": (c.input or {}).get("subagent_type", "") or "",
                }
            )
            if c.name in ("shell_output", "shell_tasks") and c.input.get("id") in origins:
                o = origins[c.input["id"]]
                items.append(
                    {
                        "name": "shell_command",
                        "command": (o.input or {}).get("command", "") or "",
                        "path": "",
                        "result": c.result_text or "",
                    }
                )
        return items

    @staticmethod
    def _match(rule: dict, item: dict) -> bool:
        tools = rule.get("tools")
        if tools and item["name"] not in tools:
            return False
        for field_name, probe in (
            ("tool_regex", item["name"]),
            ("subagent_regex", item.get("subagent", "")),
            ("command_regex", item["command"]),
            ("path_regex", item["path"]),
            ("result_regex", item["result"]),
        ):
            rx = rule.get(field_name)
            if rx and not re.search(rx, probe or ""):
                return False
        return True

    def map_turn(self, turn: Turn, origins: dict, is_first: bool, is_last: bool):
        """Return dict(phase, subphase, confidence, rule_id, time_class, wait_tag, matched_tool)."""
        if is_first:
            return _assignment("T0", None, "HIGH", "t0_first_turn", "PRODUCTIVE", None, None)
        items = self._effective_items(turn, origins)
        for rule in self.rules:
            for it in items:
                if self._match(rule, it):
                    return _assignment(
                        rule["phase"],
                        rule.get("subphase"),
                        rule.get("confidence", "LOW"),
                        rule["id"],
                        rule.get("time_class"),
                        rule.get("wait_tag"),
                        it["name"],
                    )
        if not turn.calls:
            if is_last:
                return _assignment("T9", None, "MEDIUM", "t9_final_answer", "PRODUCTIVE", None, None)
            return _assignment("UNKNOWN", None, "LOW", "text_only", None, None, None)
        return _assignment("UNKNOWN", None, "LOW", "no_rule_match", None, None, None)


def _assignment(phase, subphase, confidence, rule_id, time_class, wait_tag, tool):
    return {
        "phase": phase,
        "subphase": subphase,
        "confidence": confidence,
        "rule_id": rule_id,
        "time_class": time_class,
        "wait_tag": wait_tag,
        "matched_tool": tool,
    }


# --------------------------------------------------------------------------- #
# failure taxonomy
# --------------------------------------------------------------------------- #
_FAIL_PATTERNS = [
    ("BUILD_ERROR", re.compile(r"(?i)BUILD FAILED|FAILURE:\s*Build failed|Execution failed for task")),
    ("TEST_PROBLEM", re.compile(r"(?i)TESTS FAILED|[0-9]+\s+tests?\s+failed|\bTests? failed\b")),
    ("PROVIDER_QUOTA", re.compile(r"(?i)quota exhausted|Request rejected \(429\)|HTTP[_ ]?429|status[^\n]{0,12}429")),
    ("PROVIDER_MODEL", re.compile(r"(?i)unrecognized_model|unknown model|model not found")),
    ("PROVIDER_AUTH", re.compile(r"(?i)\b401\b[^\n]{0,40}(unauthor|api|provider)|authentication failed|invalid api key|api error[^\n]{0,20}401")),
    ("DEVICE_STATE_GAP", re.compile(r"(?i)device with serial or avd name .*not found|no devices/emulators found|device offline")),
    ("INFRASTRUCTURE_ERROR", re.compile(r"(?i)Cannot determine git remote")),
]

_SEVERITY = [
    "BUILD_ERROR", "TEST_PROBLEM", "INTEGRATION_ERROR", "REGRESSION",
    "PROVIDER_QUOTA", "PROVIDER_AUTH", "PROVIDER_MODEL", "PROVIDER_TIMEOUT",
    "INFRASTRUCTURE_ERROR", "DEVICE_STATE_GAP", "ENVIRONMENT_CONTAMINATION",
    "GENERIC_ERROR",
]


_COMMAND_TOOLS = {"shell_command", "shell_output", "shell_tasks", "kill_shell", "monitor_command"}
_CONDITIONAL_FAILURES = {"DEVICE_STATE_GAP", "INFRASTRUCTURE_ERROR"}

# unittest / JUnit / Gradle per-test verdict lines: "<name> ... ok|FAIL|ERROR".
_TEST_LINE_RE = re.compile(r"^.*?\.\.\.\s+(ok|FAIL|ERROR|skipped|expected failure|unexpected success)\s*$")
# A line that proves this is a test-runner transcript (not a build log / prose).
_TEST_TRANSCRIPT_RE = re.compile(
    r"(?i)\bRan \d+ tests?\b|FAILED \(failures=|\.\.\.\s+(?:ok|FAIL|ERROR)\s*$", re.M)
# Aggregate failure signals only (never a failure-like word inside a test name).
_TEST_SUMMARY_FAIL_RE = re.compile(
    r"FAILED\s*\((?=[^)]*(?:failures|errors)\s*=)|^\s*FAILED\s*$|"
    r"\bSELFTEST_[A-Z_]*=FAIL\b|\b\d+\s+tests?\s+failed\b",
    re.I | re.M)


def test_run_verdict(text):
    """Structured verdict for a test-runner transcript, else None.

    A per-test line ending in "... ok" is a PASS and must never be read as a
    failure - even when the test name contains timeout/error/failure. Only a
    "... FAIL"/"... ERROR" line or an aggregate failure summary counts.
    """
    if not text or not _TEST_TRANSCRIPT_RE.search(text):
        return None
    fail_lines = []
    ok_lines = 0
    for ln in text.splitlines():
        m = _TEST_LINE_RE.match(ln.strip())
        if not m:
            continue
        if m.group(1) in ("FAIL", "ERROR"):
            fail_lines.append(ln.strip())
        else:
            ok_lines += 1
    if fail_lines:
        return {"verdict": "fail", "evidence": fail_lines[0][:160]}
    if _TEST_SUMMARY_FAIL_RE.search(text):
        return {"verdict": "fail", "evidence": _first_line(text, _TEST_SUMMARY_FAIL_RE)[:160]}
    if ok_lines:
        return {"verdict": "pass", "evidence": None}
    return None


def classify_failure(c: Call):
    """Return (type, evidence_text) or None for a logical failure marker.

    Only command-executing tools can produce logical failures; free-form file
    reads must never be misread as provider/auth failures from their content.
    """
    if c.name not in _COMMAND_TOOLS:
        return None
    t = c.result_text or ""
    cmd = (c.input or {}).get("command", "") or ""
    exit_code = c.exit_code
    failed = c.status == "failed" or (exit_code not in (0, None))

    # A structured test-runner transcript is authoritative: "... ok" lines are
    # passes and must never become failures (v0.2.1 mis-typed a passing
    # "test_timeouts ... ok" line as a provider/infrastructure failure).
    tv = test_run_verdict(t)
    if tv is not None:
        if tv["verdict"] == "pass":
            return None
        return "TEST_PROBLEM", tv["evidence"]

    for ftype, rx in _FAIL_PATTERNS:
        if rx.search(t):
            if ftype == "BUILD_ERROR" and re.search(
                r"(?i)testdebug|connected\w*test|androidtest|unittest|:app:test", cmd
            ):
                ftype = "TEST_PROBLEM"
            if ftype in _CONDITIONAL_FAILURES and not failed:
                continue
            return ftype, _first_line(t, rx)
    # Real timeout signal only: v0.2.1 matched the substring "timeout" anywhere,
    # so a passing test named test_timeouts became an INFRASTRUCTURE_ERROR.
    timeout_like = (
        exit_code == 124
        or bool(re.search(r"(?i)\[TIMEOUT\]|\bEXIT=124\b|\btimed out\b|\bcommand timed out\b", t))
        or bool(re.search(r"(?im)^\s*timeout[:=]", t))
    )
    timeout_rx = re.compile(r"(?i)\[TIMEOUT\]|EXIT=124|timed out")
    if timeout_like and re.search(r"(?i)\bclaude\b|probe|provider", cmd):
        return "PROVIDER_TIMEOUT", _first_line(t, timeout_rx)
    if timeout_like and c.status == "failed":
        return "INFRASTRUCTURE_ERROR", _first_line(t, timeout_rx)
    if c.status == "failed" and exit_code not in (0, None):
        if re.search(r"(?i)gradle|assemble|compile|:app:", cmd):
            return "BUILD_ERROR", _first_line(t, re.compile(r"(?i)error|failed"))
        return "GENERIC_ERROR", _first_line(t, re.compile(r"(?i)error|failed|exit"))
    return None


def _first_line(text: str, rx) -> str:
    for line in (text or "").splitlines():
        if rx.search(line):
            return line.strip()[:160]
    return (text or "").strip().splitlines()[0][:160] if text.strip() else ""


def _logical_key(c) -> str:
    """Group failures by operation TARGET so repeated failures chain into one.

    Background operations keep their shared ``bg:<task_id>`` id; a foreground
    command groups by its operation signature, so "run X -> FAIL -> edit -> run X
    -> FAIL -> edit -> run X -> PASS" is ONE logical failure with a repair chain,
    not three independent product faults. Falls back to the call id.
    """
    if c.op_id and str(c.op_id).startswith("bg:"):
        return c.op_id
    cmd = (c.input or {}).get("command", "") or ""
    if cmd:
        return "sig:" + _op_signature(cmd)
    return c.op_id or ("call:" + str(c.call_id))


def detect_logical_failures(calls: list):
    """Deduplicate raw failure markers into logical failures keyed by operation target."""
    op_cmd = {}
    for c in calls:
        cmd = (c.input or {}).get("command", "") or ""
        if cmd:
            op_cmd.setdefault(c.op_id, cmd)
            op_cmd.setdefault(_logical_key(c), cmd)

    groups = defaultdict(list)
    for c in calls:
        mark = classify_failure(c)
        if mark:
            groups[_logical_key(c)].append((c, mark[0], mark[1]))

    logical = []
    op_origin_row = {}
    for c in calls:
        key = _logical_key(c)
        if key not in op_origin_row or c.row_index < op_origin_row[key]:
            op_origin_row[key] = c.row_index

    for idx, (key, marks) in enumerate(sorted(groups.items(), key=lambda kv: op_origin_row[kv[0]]), 1):
        types = [m[1] for m in marks]
        ftype = min(types, key=lambda x: _SEVERITY.index(x) if x in _SEVERITY else 999)
        raw_events = sorted({m[0].row_index for m in marks})
        evidence = next(m[2] for m in marks if m[1] == ftype)
        logical.append(
            {
                "logical_failure_id": f"FAIL-{idx:03d}",
                "logical_operation_id": key,
                "operation_target": op_cmd.get(key, ""),
                "type": ftype,
                "raw_events": raw_events,
                "owner_row": op_origin_row[key],
                "raw_types": sorted(set(types)),
                "evidence": evidence,
                "repair_id": None,
                "repair_status": None,
                "phase": None,
            }
        )
    return logical


# --------------------------------------------------------------------------- #
# repairs
# --------------------------------------------------------------------------- #
# Editable source / test / config surfaces a real fix can touch. Generic across
# ecosystems; .md is deliberately excluded (documentation is not a code fix).
_CODE_PATH = re.compile(
    r"(?i)\.(kt|kts|java|xml|gradle|toml|pro|properties|py|sh|bash|zsh|js|jsx|mjs|cjs|ts|tsx|"
    r"go|rs|rb|c|h|cc|cpp|hpp|cs|swift|sql|cfg|ini|yml|yaml|json)$"
    r"|AndroidManifest|Dockerfile|Makefile"
)
_SCRATCH = re.compile(r"(?i)/scratchpad/|^/tmp/")


def _op_signature(command: str) -> str:
    c = command or ""
    m = re.search(
        r"(?i)\b(assemble\w*|test\w*|connected\w*|bundle\w*|compile\w*|ci)\b", c
    )
    if "gradlew" in c and m:
        return "gradle:" + m.group(1).lower()
    if "ci.py" in c:
        return "ci"
    return "cmd:" + re.sub(r"\s+", " ", c).strip()[:80]


def _turn_fix_paths(turn: Turn) -> list:
    """The code/test/config paths a turn actually edited (the fix evidence)."""
    paths = []
    for c in turn.calls:
        if c.name in ("write_file", "edit_file"):
            p = input_path(c.input or {})
            if p and not _SCRATCH.search(p) and _CODE_PATH.search(p) and p not in paths:
                paths.append(p)
    return paths


def _turn_is_fix(turn: Turn, redactor: Redactor):
    return bool(_turn_fix_paths(turn))


def _turn_has_success_op(turn: Turn, sig: str, origins: dict):
    for c in turn.calls:
        cmd = (c.input or {}).get("command", "") or ""
        if c.name in ("shell_output", "shell_tasks") and isinstance(c.input.get("id"), str):
            o = origins.get(c.input["id"])
            if o:
                cmd = (o.input or {}).get("command", "") or ""
        if not cmd:
            continue
        if _op_signature(cmd) == sig and c.status == "completed" and c.exit_code in (0, None):
            return True
    return False


def detect_repairs(turns: list, failures: list, origins: dict, op_cmd: dict = None):
    """Link FAIL -> relevant code edit -> successful re-run of the SAME target.

    Structured evidence only: the fix must edit a code/test/config path, and the
    re-run must be the same operation signature and complete with exit 0. A
    failure whose linkage cannot be proven is labelled ``repair_status`` rather
    than counted. No repair is credited from "a later test passed" alone.
    """
    op_cmd = op_cmd or {}
    repairs = []
    overrides = {}
    rid = 0
    row_to_turn = {t.row_index: t for t in turns}
    for f in sorted(failures, key=lambda x: x["owner_row"]):
        fail_row = f["owner_row"]
        origin_cmd = f.get("operation_target") or op_cmd.get(f["logical_operation_id"], "")
        if not origin_cmd:
            origin_call = next((c for c in origins.values() if c.op_id == f["logical_operation_id"]), None)
            origin_cmd = (origin_call.input or {}).get("command", "") if origin_call else ""
        sig = _op_signature(origin_cmd)
        fix_turn = None
        fix_paths = []
        for t in turns:
            if t.row_index > fail_row:
                paths = _turn_fix_paths(t)
                if paths:
                    fix_turn = t
                    fix_paths = paths
                    break
        if fix_turn is None:
            f["repair_status"] = "UNPROVABLE_NO_FIX_EDIT"
            continue
        rerun_turn = None
        for t in turns:
            if t.row_index > fix_turn.row_index and _turn_has_success_op(t, sig, origins):
                rerun_turn = t
                break
        if rerun_turn is None:
            f["repair_status"] = "UNPROVABLE_NO_SUCCESSFUL_RERUN"
            continue
        rid += 1
        repair_id = f"REPAIR-{rid:03d}"
        f["repair_id"] = repair_id
        f["repair_status"] = "REPAIRED"
        overrides[fix_turn.row_index] = ("T8", None)
        overrides[rerun_turn.row_index] = ("T8", None)
        fail_turn = row_to_turn.get(fail_row)
        repairs.append(
            {
                "repair_id": repair_id,
                "failure_id": f["logical_failure_id"],
                "trigger_failure": f["logical_failure_id"],
                "type": f["type"],
                "phase": f["phase"],
                "failure_timestamp": iso(fail_turn.timestamp) if fail_turn else None,
                "first_fix_timestamp": iso(fix_turn.timestamp),
                "verification_timestamp": iso(rerun_turn.timestamp),
                "changed_paths": fix_paths,
                "rerun_operation": sig,
                "rerun_result": "PASS",
                "repair_wall_seconds": (
                    round(secs(fail_turn.timestamp, rerun_turn.timestamp), 3) if fail_turn else None
                ),
                "fix_span": fix_turn.turn_id,
                "fix_row": fix_turn.row_index,
                "rerun_span": rerun_turn.turn_id,
                "rerun_row": rerun_turn.row_index,
                "result": "PASS",
            }
        )
    return repairs, overrides


# --------------------------------------------------------------------------- #
# deviations
# --------------------------------------------------------------------------- #
def detect_deviations(calls: list, failures: list):
    out = {}

    def add(dtype, evidence):
        if dtype not in out:
            out[dtype] = {"type": dtype, "count": 0, "evidence": evidence}
        out[dtype]["count"] += 1

    for c in calls:
        t = c.result_text or ""
        cmd = (c.input or {}).get("command", "") or ""
        if re.search(r"(?i)Cannot determine git remote", t):
            add("NO_REMOTE", "workflow could not determine git remote")
        if re.search(r"(?i)--no-worktree", cmd):
            add("NO_WORKTREE", "--no-worktree used")
        if re.search(r"(?i)device with serial or avd name .*not found", t):
            add("DEVICE_FALLBACK", "emulator unavailable, fell back to physical device")
        if re.search(r"(?i)\bime set\b", cmd):
            add("IME_SWITCH", "IME switched for text input")
        if re.search(r"(?i)No apks specified|interactive-class|is interactive", t):
            add("TOOL_WORKAROUND", "tool invocation adjusted to work around CLI limitation")
        if re.search(r"(?i)RUNTIME_NOT_RUN|OPTIONAL_CHECK_PENDING", t):
            add("OPTIONAL_CHECK_PENDING", "optional runtime check deferred")
    if any(f["type"].startswith("PROVIDER_") for f in failures):
        add("PROVIDER_FALLBACK", "provider probe failed and execution fell back")
    return list(out.values())


# --------------------------------------------------------------------------- #
# metrics + spans
# --------------------------------------------------------------------------- #
def build_spans(turns, task_start, task_end, mapper, origins, redactor, overrides, failure_by_row, repairs_by_row, wait_by_row=None):
    spans = []
    prev_end = task_start
    n = len(turns)
    wait_by_row = wait_by_row or {}
    for i, turn in enumerate(turns):
        a = mapper.map_turn(turn, origins, is_first=(i == 0), is_last=(i == n - 1))
        phase, subphase, confidence, rule_id, time_class, wait_tag, matched_tool = (
            a["phase"], a["subphase"], a["confidence"], a["rule_id"],
            a["time_class"], a["wait_tag"], a["matched_tool"],
        )
        repair_id = None
        if turn.row_index in overrides:
            phase, subphase = overrides[turn.row_index]
            confidence = "HIGH"
            repair_id = repairs_by_row.get(turn.row_index)
            time_class = "NECESSARY_OVERHEAD"
        if time_class is None:
            time_class = _default_time_class(phase)
        status = "failed" if any(c.call_id in failure_by_row or c.op_id in failure_by_row for c in turn.calls) else "ok"
        primary = _primary_tool(turn, matched_tool)
        usage = turn.usage or {}
        tokens = {k: usage.get(k) for k in TIMING_KEYS}
        full = round(secs(prev_end, turn.timestamp), 3)
        wait = round(min(wait_by_row.get(turn.row_index, 0.0), full), 3)
        agent_owned = round(full - wait, 3)
        if wait > 0:
            wait_tag = USER_WAIT_TAG
        spans.append(
            {
                "span_id": turn.turn_id,
                "turn_id": turn.turn_id,
                "start_time": iso(prev_end),
                "end_time": iso(turn.timestamp),
                "start_dt": prev_end,
                "end_dt": turn.timestamp,
                "duration_seconds": full,
                "agent_seconds": agent_owned,
                "wait_seconds": wait,
                "phase": phase,
                "subphase": subphase,
                "confidence": confidence,
                "primary_event": "assistant_turn",
                "tool": primary,
                "logical_operation_id": _primary_op(turn),
                "status": status,
                "time_class": time_class,
                "wait_tag": wait_tag,
                "failure_id": _failure_ids(turn, failure_by_row),
                "repair_id": repair_id,
                "secondary_tags": [],
                "rule_id": rule_id,
                "input_tokens": tokens["inputTokens"],
                "output_tokens": tokens["outputTokens"],
                "cache_read_tokens": tokens["cacheReadTokens"],
                "cache_write_tokens": tokens["cacheWriteTokens"],
                "cost": tokens["costUsd"],
                "evidence": redactor.text(_evidence(turn, primary)),
                "row_index": turn.row_index,
            }
        )
        prev_end = turn.timestamp

    if turns and task_end > turns[-1].timestamp:
        spans.append(
            {
                "span_id": "TURN-UNKNOWN-TAIL",
                "turn_id": "TURN-UNKNOWN-TAIL",
                "start_time": iso(turns[-1].timestamp),
                "end_time": iso(task_end),
                "start_dt": turns[-1].timestamp,
                "end_dt": task_end,
                "duration_seconds": round(secs(turns[-1].timestamp, task_end), 3),
                "agent_seconds": round(secs(turns[-1].timestamp, task_end), 3),
                "wait_seconds": 0.0,
                "phase": "UNKNOWN",
                "subphase": None,
                "confidence": "LOW",
                "primary_event": "unattributed",
                "tool": None,
                "logical_operation_id": None,
                "status": "unknown",
                "time_class": "UNKNOWN",
                "wait_tag": None,
                "failure_id": None,
                "repair_id": None,
                "secondary_tags": [],
                "rule_id": "unknown_tail",
                "input_tokens": None,
                "output_tokens": None,
                "cache_read_tokens": None,
                "cache_write_tokens": None,
                "cost": None,
                "evidence": "wall after last assistant turn with no owner",
                "row_index": None,
            }
        )
    return spans


def _default_time_class(phase):
    return {
        "T0": "PRODUCTIVE", "T1": "NECESSARY_OVERHEAD", "T2": "NECESSARY_OVERHEAD",
        "T3": "PRODUCTIVE", "T4": "PRODUCTIVE", "T5": "NECESSARY_OVERHEAD",
        "T6": "NECESSARY_OVERHEAD", "T7": "NECESSARY_OVERHEAD", "T8": "NECESSARY_OVERHEAD",
        "T9": "PRODUCTIVE", "UNKNOWN": "UNKNOWN",
    }.get(phase, "UNKNOWN")


def _primary_tool(turn, matched_tool):
    if matched_tool:
        return matched_tool
    if turn.calls:
        return turn.calls[0].name
    return None


def _primary_op(turn):
    return turn.calls[0].op_id if turn.calls else None


def _failure_ids(turn, failure_by_row):
    ids = []
    for f in failure_by_row.values():
        if f["owner_row"] == turn.row_index:
            ids.append(f["logical_failure_id"])
    return ",".join(ids) if ids else None


def _evidence(turn, primary_tool):
    if not turn.calls:
        snippet = (turn.final_text or "").strip().splitlines()
        return "answer: " + (snippet[0][:120] if snippet else "")
    c = turn.calls[0]
    if c.name == "shell_command":
        cmd = (c.input or {}).get("command", "") or ""
        return "cmd: " + re.sub(r"\s+", " ", cmd).strip()[:200]
    if c.name in ("write_file", "edit_file", "read_file", "read_directory"):
        return f"{c.name}: {input_path(c.input or '')}"[:200]
    return f"{c.name}: {json.dumps(redactor_safe(c.input))[:160]}"


def redactor_safe(obj):
    try:
        return obj
    except Exception:
        return {}


# --------------------------------------------------------------------------- #
# aggregation
# --------------------------------------------------------------------------- #
def aggregate(spans, turns, failures, repairs, deviations, clocks):
    phase_wall = defaultdict(float)
    phase_spans = Counter()
    sub_wall = defaultdict(float)
    wait_wall = defaultdict(float)
    class_wall = defaultdict(float)
    conf = Counter()
    tokens_by_phase = defaultdict(lambda: {"requests": 0, "input": 0, "output": 0,
                                            "cache_read": 0, "cache_write": 0, "cost": 0.0})
    for s in spans:
        d = s.get("agent_seconds", s["duration_seconds"])
        w = s.get("wait_seconds", 0.0)
        phase_wall[s["phase"]] += d
        phase_spans[s["phase"]] += 1
        if s["subphase"]:
            sub_wall[s["subphase"]] += d
        if s["wait_tag"]:
            wait_wall[s["wait_tag"]] += w if s["wait_tag"] == USER_WAIT_TAG else d
        class_wall[s["time_class"]] += d
        conf[s["confidence"]] += 1
        u = s
        if u["input_tokens"] is not None:
            tp = tokens_by_phase[s["phase"]]
            tp["requests"] += 1
            tp["input"] += u["input_tokens"] or 0
            tp["output"] += u["output_tokens"] or 0
            tp["cache_read"] += u["cache_read_tokens"] or 0
            tp["cache_write"] += u["cache_write_tokens"] or 0
            tp["cost"] += u["cost"] or 0.0

    token_raw = {"requests": 0, "input": 0, "output": 0, "cache_read": 0,
                 "cache_write": 0, "cost": 0.0, "provider": None, "models": []}
    for t in turns:
        if not t.usage:
            continue
        token_raw["requests"] += 1
        token_raw["input"] += t.usage.get("inputTokens", 0) or 0
        token_raw["output"] += t.usage.get("outputTokens", 0) or 0
        token_raw["cache_read"] += t.usage.get("cacheReadTokens", 0) or 0
        token_raw["cache_write"] += t.usage.get("cacheWriteTokens", 0) or 0
        token_raw["cost"] += t.usage.get("costUsd", 0) or 0
    token_raw["cost"] = round(token_raw["cost"], 6)

    tool_stats = defaultdict(lambda: {"calls": 0, "failed": 0, "wall_seconds": 0.0})
    for t in turns:
        for c in t.calls:
            tool_stats[c.name]["calls"] += 1
            if c.status == "failed":
                tool_stats[c.name]["failed"] += 1

    task_wall = clocks["task_wall_sec"]
    # Phase share and observability are measured against AGENT-OWNED wall, never
    # against task_elapsed_wall: otherwise proven human wait dilutes every phase.
    denom = clocks.get("agent_owned_wall_sec")
    if not denom:
        denom = task_wall
    unknown = phase_wall.get("UNKNOWN", 0.0)
    unknown_ratio = (unknown / denom) if denom else 0.0
    unknown_ratio_of_task = (unknown / task_wall) if task_wall else 0.0
    quality = "GREEN" if unknown_ratio <= 0.02 else ("WARNING" if unknown_ratio <= 0.05 else "REVIEW")

    wait_total = {k: round(v, 3) for k, v in sorted(wait_wall.items(), key=lambda kv: -kv[1])}
    class_total = {k: round(v, 3) for k, v in class_wall.items()}
    waste_exclusive = round(class_wall.get("AVOIDABLE_WASTE", 0.0), 3)

    background = _background_metrics(turns)

    top_consumers = sorted(spans, key=lambda s: -s["duration_seconds"])[:10]
    top_agent = sorted(spans, key=lambda s: -(s.get("agent_seconds", s["duration_seconds"])))[:10]
    top_waste = sorted(
        [s for s in spans if s["time_class"] == "AVOIDABLE_WASTE"],
        key=lambda s: -s["duration_seconds"],
    )[:10]

    return {
        "phase_share_denominator": "agent_owned_wall",
        "phase_share_denominator_sec": round(denom, 3),
        "task_elapsed_wall_sec": round(task_wall, 3),
        "user_wait_seconds": round(sum(wait_wall.get(k, 0.0) for k in wait_wall), 3),
        "total_wait_tag_wall_sec": round(sum(wait_wall.get(k, 0.0) for k in wait_wall), 3),
        "phase_totals": {
            p: {
                "wall_seconds": round(phase_wall[p], 3),
                "share": round(phase_wall[p] / denom, 4) if denom else 0.0,
                "spans": phase_spans[p],
            }
            for p in sorted(phase_wall)
        },
        "subphase_totals": {
            sp: {"wall_seconds": round(sub_wall[sp], 3),
                 "share": round(sub_wall[sp] / denom, 4) if denom else 0.0}
            for sp in sorted(sub_wall)
        },
        "wait_totals": wait_total,
        "time_class_totals": class_total,
        "waste": {
            "exclusive_wall_sec": waste_exclusive,
            "overlapped_background_sec": None,
            "note": "exclusive wall = AVOIDABLE_WASTE turn-owned spans; overlapped marginal background wall NOT AVAILABLE",
        },
        "background": background,
        "confidence": dict(conf),
        "tokens_raw": token_raw,
        "tokens_by_phase": {
            p: {
                "requests": v["requests"],
                "input": v["input"],
                "output": v["output"],
                "cache_read": v["cache_read"],
                "cache_write": v["cache_write"],
                "cost": round(v["cost"], 6),
            }
            for p, v in sorted(tokens_by_phase.items())
        },
        "tools": {k: dict(v) for k, v in sorted(tool_stats.items())},
        "unknown_ratio": round(unknown_ratio, 6),
        "unknown_ratio_of_task_wall": round(unknown_ratio_of_task, 6),
        "observability_quality": quality,
        "top_time_consumers": [
            {"span_id": s["span_id"], "phase": s["phase"], "subphase": s["subphase"],
             "seconds": s["duration_seconds"], "agent_seconds": s.get("agent_seconds"),
             "wait_seconds": s.get("wait_seconds"), "tool": s["tool"], "evidence": s["evidence"]}
            for s in top_consumers
        ],
        "top_agent_consumers": [
            {"span_id": s["span_id"], "phase": s["phase"], "subphase": s["subphase"],
             "agent_seconds": s.get("agent_seconds"), "tool": s["tool"], "evidence": s["evidence"]}
            for s in top_agent
        ],
        "top_avoidable_waste": [
            {"span_id": s["span_id"], "phase": s["phase"], "seconds": s["duration_seconds"],
             "tool": s["tool"], "evidence": s["evidence"]}
            for s in top_waste
        ],
        "failure_count": len(failures),
        "repair_count": len(repairs),
        "deviations": deviations,
    }


def _background_metrics(turns):
    jobs = {}
    for t in turns:
        for c in t.calls:
            if c.task_id:
                jobs.setdefault(c.task_id, {"task_id": c.task_id, "op_id": c.op_id,
                                            "wait_seconds": 0.0, "polls": 0, "final_status": None})
            if c.name == "shell_output" and isinstance(c.input.get("id"), str):
                j = jobs.setdefault(c.input["id"], {"task_id": c.input["id"], "op_id": "bg:" + c.input["id"],
                                                    "wait_seconds": 0.0, "polls": 0, "final_status": None})
                j["polls"] += 1
                if c.wait_seconds:
                    j["wait_seconds"] += c.wait_seconds
                if c.status:
                    j["final_status"] = c.status
    return {
        "jobs": list(jobs.values()),
        "background_duration_seconds": round(sum(j["wait_seconds"] for j in jobs.values()), 3),
        "exclusive_wall_seconds": None,
        "overlapped_background_seconds": None,
        "note": "background durations parsed from shell_output waits; marginal wall contribution NOT AVAILABLE",
    }


# --------------------------------------------------------------------------- #
# result heuristic
# --------------------------------------------------------------------------- #
def detect_result(turns, explicit=None):
    """v0.2.1: no keyword inference.

    The raw JSONL carries no authoritative task outcome field, so the observer
    cannot prove PASS/FAIL from the transcript alone. Result is only reported
    when the caller asserts it (--result); otherwise it stays UNKNOWN. Task
    *completion* is reported separately via task_completion_detected, which IS
    structurally provable.
    """
    if explicit:
        return explicit
    return "UNKNOWN"


# --------------------------------------------------------------------------- #
# writers
# --------------------------------------------------------------------------- #
CSV_COLUMNS = [
    "span_id", "turn_id", "start_time", "end_time", "duration_seconds",
    "agent_seconds", "wait_seconds",
    "phase", "subphase", "confidence", "primary_event", "tool",
    "logical_operation_id", "status", "time_class", "wait_tag", "failure_id",
    "repair_id", "secondary_tags", "input_tokens", "output_tokens",
    "cache_read_tokens", "cache_write_tokens", "cost", "evidence",
]


def write_csv(path, spans):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for s in spans:
            row = dict(s)
            row["secondary_tags"] = ";".join(s.get("secondary_tags") or [])
            w.writerow(row)


def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def _fmt_pct(x):
    return f"{x * 100:.1f}%"


def write_analysis_md(path, run, spans, redactor):
    c = run["clocks"]
    ev = run["source"]
    L = []
    A = L.append
    A("# Command Code Evaluation - v0.2.3 Evaluation Core")
    A("")
    A(f"**Run ID:** `{run['run_id']}`  ")
    A(f"**Project:** {run['project']}  ")
    A(f"**Workflow:** {run.get('workflow') or 'unknown'}  ")
    A(f"**Agent host:** {run['agent_host']}  ")
    A(f"**Model(s):** {', '.join(ev['models']) or 'unknown'}")
    A("")
    A("## Evidence Identity")
    A("")
    A(f"- JSONL path: `{ev['jsonl_path']}`")
    A(f"- Session ID: `{ev['session_id']}`")
    A(f"- Schema version: {ev['schema_version']}")
    A(f"- File size: {ev['file_size_bytes']} bytes")
    A(f"- SHA256: `{ev['sha256']}`")
    A(f"- First session timestamp: {ev['first_session_timestamp']}")
    A(f"- Task prompt timestamp: {ev['task_prompt_timestamp']}")
    A(f"- Task end timestamp: {ev['task_end_timestamp']}")
    A(f"- Final session timestamp: {ev['final_session_timestamp']}")
    A(f"- cwd: `{ev['cwd']}`")
    A(f"- Prompt match: {ev['prompt_match']['detail']}")
    A("")
    A("## Task Window")
    A("")
    tw = run.get("task_window", {})
    A(f"- Classification: **{tw.get('classification', 'legacy')}**")
    A(f"- Window rows (start, end-exclusive): **{tw.get('start_index')} -> {tw.get('end_index_exclusive')}**")
    A(f"- In-task continuations (steering/control pings kept inside window): "
      f"**{tw.get('in_task_continuations', 0)}**")
    A(f"- Genuinely independent later tasks excluded: **{tw.get('excluded_independent_tasks', 0)}**")
    A(f"- Window uncertainty: {tw.get('uncertainty', 'n/a')}")
    A("")
    A("## Task Completion")
    A("")
    tc = run.get("task_completion", {})
    A(f"- task_completion_detected: **{run.get('task_completion_detected')}**")
    A(f"- Final assistant row: {tc.get('final_assistant_row')} "
      f"(id `{tc.get('final_assistant_id')}`) at {tc.get('final_assistant_timestamp')}")
    A(f"- Terminal assistant turn (no pending tool_use): **{tc.get('terminal_assistant_turn')}**")
    A(f"- Is window tail: **{tc.get('final_message_is_window_tail')}**")
    A(f"- Evidence: {tc.get('evidence', '')}")
    A("")
    A("## Clock Model (v0.2.3)")
    A("")
    A(f"- **task_elapsed_wall** (task prompt -> final assistant completion): "
      f"**{c.get('task_elapsed_wall_sec', c['task_wall_sec'])} s**")
    iw = c.get("interactive_user_wait_sec")
    ub = c.get("interactive_user_wait_upper_bound")
    A(f"- **interactive_user_wait** (proven model->human->resume time"
      f"{', UPPER BOUND' if ub else ', separated via meta.createdAt'}): "
      f"**{iw if iw is not None else 'null (none provable)'} s**")
    A(f"- **unattributed_idle_wall** (proven non-agent, not a human boundary): "
      f"**{c.get('unattributed_idle_wall_sec', 0.0)} s**")
    A(f"- **agent_owned_wall** (elapsed minus human wait minus unattributed idle): "
      f"**{c.get('agent_owned_wall_sec')} s**")
    A(f"- **total_wait_tag_wall_sec** (sum of ALL wait tags - NOT human wait): "
      f"**{run.get('total_wait_tag_wall_sec')} s**")
    A(f"- **phase_share_denominator = agent_owned_wall** "
      f"(**{run.get('phase_share_denominator_sec')} s**) - NOT task_elapsed_wall")
    for w in c.get("human_loop_boundaries", []):
        A(f"  - row {w['row']} via `{w['tool']}`: wait {w['wait_seconds']} s "
          f"(model {w.get('model_seconds')} s, span {w.get('span_seconds')} s, {w.get('basis')})")
    A("")
    A("## Clock Reconciliation")
    A("")
    A(f"- Session Wall (open -> task end): **{c['session_wall_sec']} s**")
    A(f"- Task Wall (task prompt -> task end): **{c['task_wall_sec']} s**")
    A(f"- Pre-Prompt User Wait (open -> prompt): **{c['pre_prompt_user_wait_sec']} s**")
    A(f"- Sum of span wall: **{run['reconciliation']['sum_span_wall_sec']} s**")
    A(f"- Sum of agent_owned span wall: **{run['reconciliation'].get('sum_agent_wall_sec')} s** "
      f"(clock {c.get('agent_owned_wall_sec')} s)")
    A(f"- Sum of human-wait span wall: **{run['reconciliation'].get('sum_wait_wall_sec')} s** "
      f"(clock {iw if iw is not None else 'null'} s)")
    A(f"- Reconciliation: **{'PASS' if run['reconciliation']['ok'] else 'FAIL'}** "
      f"(delta {run['reconciliation']['delta_sec']} s)")
    if c.get("trailing_prompts_excluded"):
        A(f"- Independent later task prompt(s) excluded from this task: "
          f"**{c['trailing_prompts_excluded']}**")
    A("")
    A("Command Code's own `Worked for …` UI timer is a *client clock* that can include "
      "human input and idle time; `agent_owned_wall` is the observer's agent/tool-owned "
      "decomposition of that same elapsed window. They measure different things and are not "
      "required to match.")
    A("")
    A("## Phases (T0-T9)")
    A("")
    A(f"Shares use the **agent_owned_wall** denominator "
      f"({run.get('phase_share_denominator_sec')} s), not task_elapsed_wall.")
    A("")
    A("| Phase | Agent wall (s) | Share of agent-owned | Spans |")
    A("|---|---:|---:|---:|")
    order = [f"T{i}" for i in range(10)] + ["UNKNOWN"]
    pt = run["phase_totals"]
    for p in order:
        if p in pt:
            v = pt[p]
            A(f"| {p} | {v['wall_seconds']} | {_fmt_pct(v['share'])} | {v['spans']} |")
    t2 = pt.get("T2", {}).get("wall_seconds", 0.0)
    t6 = pt.get("T6", {}).get("wall_seconds", 0.0)
    denom = run.get("phase_share_denominator_sec") or 0.0
    A("")
    A(f"- **T2 + T6**: {round(t2 + t6, 3)} s "
      f"({_fmt_pct((t2 + t6) / denom) if denom else '0.0%'} of agent-owned)")
    A("")
    A("## Subphases")
    A("")
    A("| Subphase | Wall (s) | Share |")
    A("|---|---:|---:|")
    for sp, v in run["subphase_totals"].items():
        A(f"| {sp} | {v['wall_seconds']} | {_fmt_pct(v['share'])} |")
    A("")
    A("## Token by Phase (raw provider fields)")
    A("")
    A("| Phase | Requests | Input | Output | Cache Read | Cache Write | Cost |")
    A("|---|---:|---:|---:|---:|---:|---:|")
    for p, v in run["tokens_by_phase"].items():
        A(f"| {p} | {v['requests']} | {v['input']:,} | {v['output']:,} | "
          f"{v['cache_read']:,} | {v['cache_write']:,} | ${v['cost']:.4f} |")
    tr = run["tokens_raw"]
    A(f"| **TOTAL** | {tr['requests']} | {tr['input']:,} | {tr['output']:,} | "
      f"{tr['cache_read']:,} | {tr['cache_write']:,} | ${tr['cost']:.4f} |")
    A("")
    A("## Tool Statistics")
    A("")
    A("| Tool | Calls | Failed |")
    A("|---|---:|---:|")
    for name, v in sorted(run["tools"].items(), key=lambda kv: -kv[1]["calls"]):
        A(f"| {name} | {v['calls']} | {v['failed']} |")
    A("")
    A("## Logical Failures")
    A("")
    if run["logical_failures"]:
        A("| ID | Type | Phase | Raw events | Repair | Evidence |")
        A("|---|---|---|---:|---|---|")
        for f in run["logical_failures"]:
            A(f"| {f['logical_failure_id']} | {f['type']} | {f.get('phase') or '-'} | "
              f"{len(f['raw_events'])} | {f.get('repair_id') or '-'} | {redactor.text(f['evidence'])} |")
    else:
        A("_None detected._")
    A("")
    A("## Repairs (Failure -> Fix -> Rerun)")
    A("")
    if run["repairs"]:
        A("| Repair | Trigger | Phase | Fix span | Rerun span | Result |")
        A("|---|---|---|---|---|---|")
        for r in run["repairs"]:
            A(f"| {r['repair_id']} | {r['trigger_failure']} | {r['phase']} | "
              f"{r['fix_span']} | {r['rerun_span']} | {r['result']} |")
    else:
        A("_None detected._")
    A("")
    A("## Human Interventions")
    A("")
    A(f"- Count: **{run['human_interventions']['count']}**")
    for h in run["human_interventions"]["events"]:
        A(f"  - {h}")
    A("")
    A("## Execution Deviations")
    A("")
    if run["execution_deviations"]:
        A("| Deviation | Count | Evidence |")
        A("|---|---:|---|")
        for d in run["execution_deviations"]:
            A(f"| {d['type']} | {d['count']} | {redactor.text(d['evidence'])} |")
    else:
        A("_None detected._")
    A("")
    A("## WAIT Breakdown")
    A("")
    A("| WAIT tag | Wall (s) |")
    A("|---|---:|")
    for k, v in run["wait_totals"].items():
        A(f"| {k} | {v} |")
    A(f"| **total_wait_tag_wall_sec (all tags)** | {run.get('total_wait_tag_wall_sec')} |")
    A("")
    A("_`user_wait_seconds` is a DEPRECATED alias for this total and is **not** human wait; the "
      "human-in-the-loop figure is `clocks.interactive_user_wait_sec`._")
    A("")
    A("## Productive / Necessary / Waste")
    A("")
    A("| Class | Wall (s) |")
    A("|---|---:|")
    for k in ("PRODUCTIVE", "NECESSARY_OVERHEAD", "AVOIDABLE_WASTE", "UNKNOWN"):
        if k in run["time_class_totals"]:
            A(f"| {k} | {run['time_class_totals'][k]} |")
    A("")
    A("## Background Jobs")
    A("")
    bg = run["background"]
    A(f"- Background duration (sum of waits): **{bg['background_duration_seconds']} s**")
    A(f"- Exclusive marginal wall: **NOT AVAILABLE**")
    A(f"- Overlapped background wall: **NOT AVAILABLE**")
    for j in bg["jobs"]:
        A(f"  - {j['task_id']}: waits {round(j['wait_seconds'], 1)} s, polls {j['polls']}, "
          f"status {j['final_status'] or '-'}")
    A("")
    A("## Top Time Consumers")
    A("")
    A("| Span | Phase | Span (s) | Agent (s) | Wait (s) | Tool | Evidence |")
    A("|---|---|---:|---:|---:|---|---|")
    for s in run["top_time_consumers"]:
        A(f"| {s['span_id']} | {s['phase']}{('/'+s['subphase']) if s['subphase'] else ''} | "
          f"{s['seconds']} | {s.get('agent_seconds')} | {s.get('wait_seconds')} | "
          f"{s['tool']} | {redactor.text(s['evidence'])} |")
    A("")
    A("## Top Avoidable Waste")
    A("")
    if run["top_avoidable_waste"]:
        A("| Span | Phase | Seconds | Tool | Evidence |")
        A("|---|---|---:|---|---|")
        for s in run["top_avoidable_waste"]:
            A(f"| {s['span_id']} | {s['phase']} | {s['seconds']} | {s['tool']} | {redactor.text(s['evidence'])} |")
    else:
        A("_None._")
    A("")
    A("## UNKNOWN")
    A("")
    A(f"- UNKNOWN agent wall: **{pt.get('UNKNOWN', {}).get('wall_seconds', 0)} s** "
      f"({_fmt_pct(run['unknown_ratio'])} of agent-owned)")
    A(f"- UNKNOWN as share of task_elapsed_wall: "
      f"**{_fmt_pct(run.get('unknown_ratio_of_task_wall', 0))}**")
    A(f"- Observability quality: **{run['observability_quality']}** "
      f"(GREEN <=2%, WARNING 2-5%, REVIEW >5%, vs agent-owned wall)")
    A(f"- Rule confidence distribution: {run['confidence']}")
    A("")
    A("## Observability Quality / Design-Reality Mismatch")
    A("")
    for note in run["design_reality_notes"]:
        A(f"- {note}")
    A("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")


# --------------------------------------------------------------------------- #
# top level
# --------------------------------------------------------------------------- #
def analyze(
    session_path: str,
    run_id: str,
    project: str,
    workflow: str = None,
    prompt_contains: str = None,
    explicit_result: str = None,
    projects_root: str = None,
    session_evidence=None,
) -> dict:
    rules = json.loads((_HERE / "phase_rules.json").read_text())
    red_cfg = json.loads((_HERE / "redaction_rules.json").read_text())
    redactor = Redactor(red_cfg)

    data = load_session(session_path)
    check_schema(data)

    rows = data.rows
    start, end, matched = resolve_task_window(rows, prompt_contains)
    indices = list(range(start, end))

    session_open = parse_ts(data.session["timestamp"])
    final_session_ts = parse_ts(rows[-1]["timestamp"]) if rows else session_open

    calls, by_id, origins = index_calls(rows, indices)
    calls_by_row = defaultdict(list)
    for c in calls:
        calls_by_row[c.row_index].append(c)

    tc = compute_task_clocks(rows, start, end, calls_by_row)
    task_start = tc["task_start"]
    task_end = tc["task_end"]
    turns = build_turns(rows, indices, task_start)
    attach_calls(turns, calls)

    completion = detect_completion(rows, start, end, tc["completion_row"])

    trailing = [i for i in find_task_prompts(rows) if i > matched]
    uncertain_rows = [i for i in range(start, end)
                      if role(rows[i]) == "user" and message_source(rows[i]) is None]
    window_uncertainty = (
        "none: every user-side row carries message.meta.source"
        if not uncertain_rows
        else f"{len(uncertain_rows)} user row(s) lack message.meta.source; classified by legacy heuristic"
    )

    clocks = {
        "session_open": iso(session_open),
        "task_start": iso(task_start),
        "task_end": iso(task_end),
        "session_wall_sec": round(secs(session_open, task_end), 3),
        "task_wall_sec": tc["elapsed"],
        "task_elapsed_wall_sec": tc["elapsed"],
        "agent_owned_wall_sec": tc["agent_owned"],
        "interactive_user_wait_sec": tc["interactive"],
        "interactive_user_wait_upper_bound": tc["interactive_user_wait_upper_bound"],
        "unattributed_idle_wall_sec": tc["unattributed"],
        "phase_share_denominator": "agent_owned_wall",
        "human_loop_boundaries": tc["human_loop_waits"],
        "pre_prompt_user_wait_sec": round(secs(session_open, task_start), 3),
        "trailing_prompts_excluded": len(trailing),
        "excluded_independent_tasks": [
            {"row": i, "head": prompt_text(rows[i]).strip().replace("\n", " ")[:120]}
            for i in trailing
        ],
        "in_task_continuations": len(tc["steering_rows"]),
        "final_session_timestamp": iso(final_session_ts),
    }

    mapper = PhaseMapper(rules)
    failures = detect_logical_failures(calls)

    # assign failure -> owner phase after mapping via temp spans pass
    for f in failures:
        for t in turns:
            if t.row_index == f["owner_row"]:
                a = mapper.map_turn(t, origins, is_first=(t is turns[0]), is_last=(t is turns[-1]))
                f["phase"] = a["phase"] + (("/" + a["subphase"]) if a["subphase"] else "")
                break

    op_cmd = {}
    for c in calls:
        cmd = (c.input or {}).get("command", "") or ""
        if cmd and c.name == "shell_command":
            op_cmd.setdefault(c.op_id, cmd)

    repairs, overrides = detect_repairs(turns, failures, origins, op_cmd)
    deviations = detect_deviations(calls, failures)

    repair_linkage = {
        "repairs": len(repairs),
        "repaired_failures": sum(1 for f in failures if f.get("repair_status") == "REPAIRED"),
        "unprovable": [
            {"failure_id": f["logical_failure_id"], "reason": f.get("repair_status")}
            for f in failures
            if f.get("repair_status") and f.get("repair_status") != "REPAIRED"
        ],
    }
    repair_linkage["status"] = (
        "REPAIR_LINKAGE_UNPROVABLE" if repair_linkage["unprovable"] else "OK"
    )

    failure_by_row = {f["owner_row"]: f for f in failures}
    repairs_by_row = {r["rerun_row"]: r["repair_id"] for r in repairs}
    repairs_by_row.update({r["fix_row"]: r["repair_id"] for r in repairs})

    spans = build_spans(turns, task_start, task_end, mapper, origins, redactor,
                        overrides, failure_by_row, repairs_by_row, wait_by_row=tc["wait_by_row"])
    metrics = aggregate(spans, turns, failures, repairs, deviations, clocks)

    sum_wall = round(sum(s["duration_seconds"] for s in spans), 3)
    sum_agent = round(sum(s.get("agent_seconds", s["duration_seconds"]) for s in spans), 3)
    sum_wait = round(sum(s.get("wait_seconds", 0.0) for s in spans), 3)
    delta = round(sum_wall - clocks["task_wall_sec"], 3)
    agent_delta = round(sum_agent - clocks["agent_owned_wall_sec"], 3)
    wait_delta = round(sum_wait - (clocks["interactive_user_wait_sec"] or 0.0), 3)
    reconciliation = {
        "sum_span_wall_sec": sum_wall,
        "sum_agent_wall_sec": sum_agent,
        "sum_wait_wall_sec": sum_wait,
        "delta_sec": delta,
        "agent_delta_sec": agent_delta,
        "wait_delta_sec": wait_delta,
        "ok": abs(delta) < 0.05 and abs(agent_delta) < 0.05 and abs(wait_delta) < 0.05,
    }

    prompt_head = redactor.text(prompt_text(rows[matched]).strip().replace("\n", " ")[:160])
    prompt_match = {
        "contains": prompt_contains,
        "matched": bool(prompt_contains) if prompt_contains else True,
        "prompt_index": matched,
        "prompt_head": prompt_head,
        "detail": (f"prompt-contains {prompt_contains!r} matched at row {matched}"
                   if prompt_contains else f"first task prompt at row {matched}"),
    }

    source = {
        "jsonl_path": data.path,
        "session_id": data.session.get("id"),
        "schema_version": data.schema_version,
        "file_size_bytes": data.size_bytes,
        "sha256": data.sha256,
        "first_session_timestamp": iso(session_open),
        "task_prompt_timestamp": iso(task_start),
        "task_end_timestamp": iso(task_end),
        "final_session_timestamp": iso(final_session_ts),
        "cwd": data.session.get("cwd"),
        "models": data.models,
        "model": data.models[0] if data.models else None,
        "prompt_match": prompt_match,
    }

    human_events = [f"row {i}: {redactor.text(prompt_text(rows[i]).strip()[:100])}"
                    for i in find_task_prompts(rows) if matched < i < end]
    # an independent task prompt inside the window (before end) is impossible by
    # construction; steering/control pings are runtime events, not human input.

    task_window = {
        "start_index": start,
        "end_index_exclusive": end,
        "matched_prompt_index": matched,
        "classification": "structural:message.meta.source",
        "in_task_continuations": len(tc["steering_rows"]),
        "excluded_independent_tasks": len(trailing),
        "uncertainty": window_uncertainty,
    }

    run = {
        "run_id": run_id,
        "project": project,
        "workflow": workflow,
        "agent_host": "Command Code",
        "model": source["model"],
        "source": source,
        "clocks": clocks,
        "task_window": task_window,
        "task_completion_detected": completion["task_completion_detected"],
        "task_completion": completion,
        "result": detect_result(turns, explicit_result),
        "result_contract": (
            "UNKNOWN unless caller asserts --result: the raw JSONL has no authoritative "
            "task outcome field; completion is reported structurally instead"
        ),
        "completion_rate": None,
        "reconciliation": reconciliation,
        "phase_totals": metrics["phase_totals"],
        "subphase_totals": metrics["subphase_totals"],
        "tokens_raw": metrics["tokens_raw"],
        "tokens_by_phase": metrics["tokens_by_phase"],
        "tools": metrics["tools"],
        "logical_failures": failures,
        "repairs": repairs,
        "repair_linkage": repair_linkage,
        "human_interventions": {"count": len(human_events), "events": human_events},
        "execution_deviations": deviations,
        "wait_totals": metrics["wait_totals"],
        "time_class_totals": metrics["time_class_totals"],
        "waste": metrics["waste"],
        "background": metrics["background"],
        "unknown_ratio": metrics["unknown_ratio"],
        "unknown_ratio_of_task_wall": metrics["unknown_ratio_of_task_wall"],
        "observability_quality": metrics["observability_quality"],
        "phase_share_denominator": metrics["phase_share_denominator"],
        "phase_share_denominator_sec": metrics["phase_share_denominator_sec"],
        "user_wait_seconds": metrics["user_wait_seconds"],
        "total_wait_tag_wall_sec": metrics["total_wait_tag_wall_sec"],
        "deprecated_fields": {
            "user_wait_seconds": (
                "deprecated in v0.2.3: it is the sum of ALL wait tags, never a human-in-the-loop "
                "figure; use total_wait_tag_wall_sec for that sum and "
                "clocks.interactive_user_wait_sec for proven human wait"
            ),
        },
        "confidence": metrics["confidence"],
        "top_time_consumers": metrics["top_time_consumers"],
        "top_agent_consumers": metrics["top_agent_consumers"],
        "top_avoidable_waste": metrics["top_avoidable_waste"],
        "schema_version": data.schema_version,
        "parser": {"additional_model_calls": 0, "network_calls": 0},
        "design_reality_notes": [],
    }
    run["design_reality_notes"] = _design_notes(clocks, data)
    run["_spans"] = spans
    run["_redactor"] = redactor
    return run


def _design_notes(clocks, data):
    notes = []
    notes.append(
        "DESIGN/REALITY v0.2.1: task boundaries are detected structurally from "
        "message.meta.source (only 'user' opens/closes a task). Same-task continuations "
        "('tool' results and 'steering' control pings such as monitor pings and plan/ask "
        "responses) stay inside the window. v0.2's text-only heuristic mis-split a task "
        "whenever a monitor ping landed mid-task."
    )
    if clocks["trailing_prompts_excluded"]:
        notes.append(
            "DESIGN/REALITY: a Command Code JSONL session can hold more than one independent "
            "task; v0.2.1 scopes the run to the matched task window and excludes "
            f"{clocks['trailing_prompts_excluded']} genuinely independent later task prompt(s)."
        )
    notes.append(
        "CLOCK MODEL v0.2.2: four clocks. task_elapsed_wall = task prompt -> final assistant "
        "completion. interactive_user_wait = model->human->resume time at a proven human-in-the-loop "
        "boundary (ask_user_question / plan approval), separated exactly via message.meta.createdAt "
        "(question emit) -> row timestamp (resume), or the whole boundary span as an UPPER BOUND when "
        "createdAt is absent. unattributed_idle_wall = proven non-agent wall that is not a provable "
        "human boundary (0 unless such evidence exists). agent_owned_wall = task_elapsed_wall - "
        "interactive_user_wait - unattributed_idle_wall. The v0.2.1 model measured only the gap AFTER "
        "the answer and left the real human wait inside the ask/review turn span, inflating T3."
    )
    notes.append(
        "PHASE DENOMINATOR v0.2.2: T0-T9 shares and the UNKNOWN ratio are computed against "
        "agent_owned_wall (phase_share_denominator_sec), never task_elapsed_wall, so proven human "
        "wait cannot dilute every phase."
    )
    notes.append(
        "WAIT SEMANTICS v0.2.3: total_wait_tag_wall_sec is the sum of ALL wait tags (build / device / "
        "AI-node / tool / provider / dependency) and is NOT human wait. user_wait_seconds is a "
        "deprecated alias for that total. The only human-in-the-loop figure is "
        "clocks.interactive_user_wait_sec."
    )
    notes.append(
        "REPAIR ATTRIBUTION v0.2.3: a repair links a logical failure to a later code/test/config "
        "edit AND a successful re-run of the SAME operation target (same signature, completed with "
        "exit 0). Logical failures are grouped by operation target, so repeated failures of one "
        "target form a single failure with a repair chain, never several product faults. A failure "
        "whose linkage cannot be proven is labelled in logical_failures[].repair_status "
        "(UNPROVABLE_NO_FIX_EDIT / UNPROVABLE_NO_SUCCESSFUL_RERUN) and rolled up in repair_linkage."
    )
    notes.append(
        "RESULT CONTRACT v0.2.1: no keyword inference. result stays UNKNOWN unless the caller "
        "asserts --result; task completion is reported structurally as task_completion_detected."
    )
    notes.append(
        "DESIGN/REALITY: the design listed an evidence-manifest.json artifact; per the v0.2 "
        "implementation brief only run.json / phase-timeline.csv / analysis.md are emitted, so "
        "evidence identity lives inside run.json and analysis.md."
    )
    notes.append(
        "NOTE: background job marginal wall is NOT AVAILABLE (only summed shell_output waits "
        "are reported); raw JSONL is never modified or copied."
    )
    return notes


def write_outputs(run: dict, output_dir: str) -> None:
    os.makedirs(output_dir, exist_ok=True)
    spans = run.pop("_spans")
    redactor = run.pop("_redactor")
    write_json(os.path.join(output_dir, "run.json"), run)
    write_csv(os.path.join(output_dir, "phase-timeline.csv"), spans)
    write_analysis_md(os.path.join(output_dir, "analysis.md"), run, spans, redactor)


# --------------------------------------------------------------------------- #
# project identity (deterministic, never prompt-NLP)
# --------------------------------------------------------------------------- #
PROJECT_CONFIG_FILENAME = ".evaluation.json"


def discover_project_identity(cwd: str = None, explicit: str = None) -> str:
    """Resolve the project label deterministically.

    Precedence: explicit caller project -> nearest ancestor ``.evaluation.json``
    containing ``{"project": "..."}`` (walking up from ``cwd``) -> ``cwd``
    basename -> ``"unknown"``. Project identity is never inferred from prompt
    text. The config is optional; when absent the previous basename fallback
    still applies, so existing behaviour is unchanged.
    """
    if explicit:
        return explicit
    if cwd:
        p = Path(os.path.abspath(cwd))
        for d in (p, *p.parents):
            cfg = d / PROJECT_CONFIG_FILENAME
            if cfg.is_file():
                try:
                    data = json.loads(cfg.read_text(encoding="utf-8"))
                except Exception:
                    data = None
                if isinstance(data, dict):
                    name = data.get("project") or data.get("project_id") or data.get("name")
                    if isinstance(name, str) and name.strip():
                        return name.strip()
        base = os.path.basename(os.path.abspath(cwd).rstrip("/"))
        if base:
            return base
    return "unknown"


# --------------------------------------------------------------------------- #
# session locator (mode B)
# --------------------------------------------------------------------------- #
def _cwd_key(path: str) -> str:
    p = os.path.abspath(path).rstrip("/")
    return p


def locate_sessions(project_cwd: str, prompt_contains: str, projects_root: str = None):
    root = Path(projects_root) if projects_root else Path.home() / ".commandcode" / "projects"
    if not root.exists():
        raise SessionLocateError(f"projects root not found: {root}")
    want = _cwd_key(project_cwd)
    candidates = []
    reasons = []
    for f in sorted(root.glob("*/*.jsonl")):
        if f.name.endswith(".checkpoints.jsonl"):
            continue
        try:
            session_row = None
            first_prompt = None
            with open(f, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    obj = json.loads(line)
                    if obj.get("type") == "session" and session_row is None:
                        session_row = obj
                    elif obj.get("type") == "message" and first_prompt is None:
                        m = obj.get("message", {})
                        meta = m.get("meta")
                        src = meta.get("source") if isinstance(meta, dict) else None
                        if m.get("role") == "user" and src != "steering":
                            text = "".join(
                                p.get("text", "") for p in (m.get("content") or [])
                                if isinstance(p, dict)
                            )
                            if text:
                                first_prompt = text
                    if session_row is not None and first_prompt is not None:
                        break
        except Exception:
            continue
        if not session_row:
            continue
        cwd_ok = _cwd_key(str(session_row.get("cwd") or "")) == want
        prompt_ok = bool(first_prompt and prompt_contains in first_prompt)
        if cwd_ok and prompt_ok:
            candidates.append(str(f))
        elif cwd_ok or prompt_ok:
            reasons.append(f"{f}: cwd_ok={cwd_ok} prompt_ok={prompt_ok}")
    return candidates, reasons
