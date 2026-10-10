#!/usr/bin/env python3
"""Hermes execution source for the Auto-Finalizer (S1.1).

The existing Auto-Finalizer only understands one *execution source*: Command Code
session JSONL under ``~/.commandcode/projects/*/*.jsonl``. This module adds the
second one: a **completed Hermes root session** persisted in the pinned Hermes
SQLite store (``state.db``).

It is deliberately thin and additive:

  * it produces only the *input* the frozen Evaluation Core already consumes --
    a Command Code JSONL v3-shaped transcript (``type=session`` header with
    ``version=3`` + ``type=message`` rows carrying ``message.meta.source``);
  * the canonical finalization path
    (``evaluation/commandcode/finalize_session.py::finalize`` ->
    ``core.analyze``) is reused verbatim; no second evaluation system exists;
  * the Hermes store is opened READ-ONLY; the shim transcript is the only file
    this module writes, and it never lands under ``~/.commandcode/projects``;
  * nothing is guessed: fields Hermes does not persist stay absent (the core
    reports missing data as null / zero, never an estimate);
  * an unfinished session (``ended_at IS NULL``) is never normalized for
    finalization.

Source of truth for the Hermes schema: the pinned install at
``/home/zhong/.hermes/hermes-agent`` (see ``orchestration/hermes/HERMES-LOCK.json``),
tables ``sessions`` / ``messages`` in ``state.db`` (schema_version 31).
"""

from __future__ import annotations

import glob
import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone

SOURCE = "hermes"
SOURCE_TYPE = "hermes_root_session"
SHIM_SCHEMA_VERSION = 3           # Command Code JSONL v3 (core.SUPPORTED_SCHEMA_VERSIONS)
MESSAGE_ROLES = ("user", "assistant", "tool")

# --------------------------------------------------------------------------- #
# Tool-identity canonicalisation (P0B-CLOSE)
# --------------------------------------------------------------------------- #
# The frozen Evaluation Core's phase rules are written in the *Command Code* tool vocabulary
# (`shell_command`, `edit_file`, `grep`, ...). A Hermes transcript carries *native* Hermes tool
# names, so before P0B-CLOSE every `terminal` / `patch` / `search_files` span fell through to
# `no_rule_match` and was counted as UNKNOWN purely because the source was Hermes.
#
# Only HIGH-CONFIDENCE equivalences are listed. Anything absent keeps its native name and stays
# UNKNOWN rather than being forced into a phase to lower the UNKNOWN ratio.
HERMES_TOOL_ALIAS = {
    "terminal": "shell_command",   # Command Code's command executor
    "patch": "edit_file",          # Command Code's in-place file editor
    "search_files": "grep",        # Command Code's content/name search
}


def canonical_tool_name(name: str) -> str:
    """Map a native Hermes tool name onto its Command Code equivalent, or return it unchanged."""
    return HERMES_TOOL_ALIAS.get(name, name)



class HermesSourceError(RuntimeError):
    """Raised when a Hermes session cannot be read or normalized."""


# --------------------------------------------------------------------------- #
# store discovery
# --------------------------------------------------------------------------- #
def db_candidates(explicit: str = None, profile: str = None) -> list:
    """Ordered candidate paths for the Hermes state.db (first existing wins)."""
    out = []
    if explicit:
        out.append(os.path.expanduser(explicit))
    env_db = os.environ.get("HERMES_EVAL_DB")
    if env_db:
        out.append(os.path.expanduser(env_db))
    home = os.path.expanduser("~/.hermes")
    if profile:
        out.append(os.path.join(home, "profiles", profile, "state.db"))
    hermes_home = os.environ.get("HERMES_HOME")
    if hermes_home:
        out.append(os.path.join(os.path.expanduser(hermes_home), "state.db"))
        # HERMES_HOME can be the profile dir itself (~/.hermes/profiles/<name>)
        out.append(os.path.join(os.path.dirname(os.path.expanduser(hermes_home)), "state.db"))
    out.append(os.path.join(home, "state.db"))
    out.extend(sorted(glob.glob(os.path.join(home, "profiles", "*", "state.db"))))
    return [p for p in out if p]


def resolve_db(explicit: str = None, profile: str = None) -> str | None:
    for p in db_candidates(explicit, profile):
        if os.path.isfile(p):
            return p
    return None


def _connect(db_path: str) -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


# --------------------------------------------------------------------------- #
# discovery
# --------------------------------------------------------------------------- #
def index_key(session_id: str) -> str:
    """Index key namespace for a Hermes source record (index stays a str->obj dict)."""
    return f"{SOURCE}:{session_id}"


def fingerprint(con: sqlite3.Connection, session_id: str) -> str:
    """Cheap, stable change-detector for a session (no full transcript read)."""
    s = con.execute(
        "SELECT ended_at, message_count FROM sessions WHERE id = ?", (session_id,)
    ).fetchone()
    m = con.execute(
        "SELECT COUNT(*) AS c, COALESCE(MAX(id), 0) AS m, COALESCE(MAX(timestamp), 0) AS t "
        "FROM messages WHERE session_id = ? AND active = 1",
        (session_id,),
    ).fetchone()
    payload = "|".join(str(x) for x in (
        session_id, s["ended_at"] if s else None, s["message_count"] if s else None,
        m["c"], m["m"], m["t"],
    ))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _descriptor(con: sqlite3.Connection, row) -> dict:
    ended_at = row["ended_at"]
    return {
        "source": SOURCE,
        "source_type": SOURCE_TYPE,
        "session_id": row["id"],
        "parent_session_id": row["parent_session_id"],
        "started_at": row["started_at"],
        "ended_at": ended_at,
        "end_reason": row["end_reason"],
        "cwd": row["cwd"],
        "model": row["model"],
        "billing_provider": row["billing_provider"],
        "title": row["title"],
        "message_count": row["message_count"],
        "tool_call_count": row["tool_call_count"],
        "input_tokens": row["input_tokens"],
        "output_tokens": row["output_tokens"],
        "profile_name": row["profile_name"],
        "completed": ended_at is not None,
        "fingerprint": fingerprint(con, row["id"]),
    }


def list_root_sessions(db_path: str, session_id: str = None, include_incomplete: bool = True,
                       limit: int = None) -> list:
    """Completed Hermes ROOT sessions (``parent_session_id IS NULL``).

    Child/subagent sessions are intentionally NOT enumerated in S1.1: the target
    is the Hermes root session, and child-agent metrics are out of scope.
    """
    con = _connect(db_path)
    try:
        if session_id:
            rows = con.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            ).fetchall()
        else:
            sql = "SELECT * FROM sessions WHERE parent_session_id IS NULL"
            if not include_incomplete:
                sql += " AND ended_at IS NOT NULL"
            sql += " ORDER BY started_at ASC"
            if limit:
                sql += f" LIMIT {int(limit)}"
            rows = con.execute(sql).fetchall()
        return [_descriptor(con, r) for r in rows]
    finally:
        con.close()


# --------------------------------------------------------------------------- #
# normalization: Hermes store -> Command Code JSONL v3 shim
# --------------------------------------------------------------------------- #
def _iso(epoch_seconds) -> str:
    """Hermes stores epoch seconds (REAL) -> the ISO-8601 ms form the core parses."""
    dt = datetime.fromtimestamp(float(epoch_seconds), tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def _tool_calls(raw) -> list:
    """Hermes messages.tool_calls (OpenAI-style JSON string) -> tool_use parts."""
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    out = []
    for i, c in enumerate(data):
        if not isinstance(c, dict):
            continue
        fn = c.get("function") if isinstance(c.get("function"), dict) else {}
        name = fn.get("name") or c.get("name") or ""
        call_id = c.get("call_id") or c.get("id") or f"call_{i}"
        args = fn.get("arguments", c.get("arguments"))
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except ValueError:
                args = {}
        if not isinstance(args, dict):
            args = {}
        out.append({"id": call_id, "name": name, "input": args})
    return out


def _messages(con: sqlite3.Connection, session_id: str) -> list:
    return con.execute(
        "SELECT id, role, content, tool_call_id, tool_calls, tool_name, timestamp, "
        "       reasoning, reasoning_content "
        "FROM messages WHERE session_id = ? AND active = 1 "
        "ORDER BY timestamp ASC, id ASC",
        (session_id,),
    ).fetchall()


def _rows_from_messages(msgs: list, model: str = None) -> list:
    """Normalise Hermes message rows into Command Code v3 rows.

    ``model`` (the session's persisted model) is stamped on every message row so the frozen
    core's ``load_session`` can populate ``source.models`` / ``run.model`` from real stored
    data instead of returning null. The tool_use part keeps its ``input`` payload EXACTLY as
    Hermes stored it and gains a sibling ``native_name`` so the original tool identity is
    preserved even after canonicalisation.
    """
    rows = []
    parent = None
    n = 0
    for m in msgs:
        role = m["role"]
        if role not in MESSAGE_ROLES:
            continue
        n += 1
        rid = f"h{n:06d}"
        ts = _iso(m["timestamp"])
        if role == "user":
            content = [{"type": "text", "text": m["content"] or ""}]
            source = "user"
            out_role = "user"
        elif role == "assistant":
            content = []
            text = (m["content"] or "").strip()
            if text:
                content.append({"type": "text", "text": m["content"]})
            thinking = (m["reasoning"] or m["reasoning_content"] or "").strip()
            if thinking:
                content.append({"type": "thinking", "thinking": thinking})
            for call in _tool_calls(m["tool_calls"]):
                content.append({"type": "tool_use", "id": call["id"],
                                "name": canonical_tool_name(call["name"]),
                                "native_name": call["name"],
                                "input": call["input"]})
            if not content:
                content = [{"type": "text", "text": ""}]
            source = "model"
            out_role = "assistant"
        else:  # tool result -> user-side row, exactly like Command Code v3
            content = [{"type": "tool_result", "tool_use_id": m["tool_call_id"],
                        "content": m["content"] or ""}]
            source = "tool"
            out_role = "user"
        row = {
            "type": "message",
            "id": rid,
            "parentId": parent,
            "timestamp": ts,
            "message": {"role": out_role, "content": content, "meta": {"source": source}},
        }
        if model:
            row["model"] = model
        rows.append(row)
        parent = rid
    return rows


def normalize_session(db_path: str, session_id: str, dest_path: str,
                      allow_incomplete: bool = False) -> dict:
    """Write a Command Code JSONL v3 shim for one Hermes session.

    Returns a metadata dict. Raises HermesSourceError when the session is absent,
    has not ended (unless ``allow_incomplete``), or carries no transcript.
    """
    con = _connect(db_path)
    try:
        srow = con.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if srow is None:
            raise HermesSourceError(f"HERMES_SESSION_NOT_FOUND: {session_id}")
        if srow["ended_at"] is None and not allow_incomplete:
            raise HermesSourceError(
                f"HERMES_SESSION_INCOMPLETE: {session_id} has not ended (ended_at is NULL)"
            )
        msgs = _messages(con, session_id)
        if not msgs:
            raise HermesSourceError(f"HERMES_SESSION_EMPTY: no active messages for {session_id}")
        rows = _rows_from_messages(msgs, model=srow["model"])
        if not rows:
            raise HermesSourceError(f"HERMES_SESSION_EMPTY: no usable rows for {session_id}")

        # ---- persisted identity (P0B-CLOSE) -------------------------------- #
        # Everything below is READ from the Hermes store: nothing is inferred. `cost` is only
        # carried when Hermes actually priced the session (its cost_status says so); otherwise
        # it is reported as not available rather than as a zero that would read like "free".
        cost_status = srow["cost_status"]
        estimated_cost = srow["estimated_cost_usd"]
        priced = cost_status not in (None, "", "unknown", "none") and estimated_cost is not None
        identity = {
            "agent_host": "Hermes",                     # the agent runtime, NOT the upstream provider
            "provider": srow["billing_provider"],       # upstream inference provider (e.g. commandcode)
            "model": srow["model"],
            "agent_product": "Hermes Agent (Nous Research)",
            "tool_name_map": dict(HERMES_TOOL_ALIAS),
            "usage_provenance": "hermes_session_totals",
            "usage": {
                "requests": srow["api_call_count"],
                "input": srow["input_tokens"],
                "output": srow["output_tokens"],
                "cache_read": srow["cache_read_tokens"],
                "cache_write": srow["cache_write_tokens"],
                "reasoning": srow["reasoning_tokens"],
                "cost": (round(float(estimated_cost), 6) if priced else None),
                "cost_status": cost_status,
            },
            "not_available": [
                "per-turn token usage (Hermes persists session-level totals only; "
                "messages.token_count is NULL in this build)",
                "persisted per-tool-call timing, turn id and api request id (transient hook "
                "payloads only, not stored in state.db)",
            ],
        }

        first_ts = _iso(msgs[0]["timestamp"])
        started = _iso(srow["started_at"]) if srow["started_at"] is not None else first_ts
        # The header must never open the session AFTER the first row, or the
        # core's pre_prompt_user_wait would go negative.
        header_ts = min(started, first_ts)
        header = {
            "type": "session",
            "version": SHIM_SCHEMA_VERSION,
            "id": session_id,
            "timestamp": header_ts,
            "cwd": srow["cwd"],
            "source": SOURCE,               # additive marker; core ignores unknown keys
            "source_type": SOURCE_TYPE,
            "profile_name": srow["profile_name"],
            "end_reason": srow["end_reason"],
            "model": srow["model"],
            "agent_host": identity["agent_host"],
            "provider": identity["provider"],
            "hermes_usage": identity["usage"],
        }

        os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
        with open(dest_path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(header, ensure_ascii=False) + "\n")
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")

        tool_uses = sum(1 for r in rows for p in r["message"]["content"] if p.get("type") == "tool_use")
        tool_results = sum(1 for r in rows for p in r["message"]["content"] if p.get("type") == "tool_result")
        return {
            "source": SOURCE,
            "source_type": SOURCE_TYPE,
            "session_id": session_id,
            "shim_path": os.path.abspath(dest_path),
            "shim_sha256": _sha256_file(dest_path),
            "shim_rows": len(rows) + 1,
            "shim_schema_version": SHIM_SCHEMA_VERSION,
            "session_messages": len(msgs),
            "tool_use_parts": tool_uses,
            "tool_result_parts": tool_results,
            "started_at": started,
            "ended_at": _iso(srow["ended_at"]) if srow["ended_at"] is not None else None,
            "end_reason": srow["end_reason"],
            "cwd": srow["cwd"],
            "model": srow["model"],
            "completed": srow["ended_at"] is not None,
            "fingerprint": fingerprint(con, session_id),
            # P0B-CLOSE: the persisted identity/usage block that the canonical finalizer applies
            # additively so model/provider/token attribution is real rather than null.
            "identity": identity,
            # Persisted Hermes metadata that has NO Command Code equivalent is
            # reported verbatim (never guessed into the evaluation).
            "hermes_totals": {
                "message_count": srow["message_count"],
                "tool_call_count": srow["tool_call_count"],
                "input_tokens": srow["input_tokens"],
                "output_tokens": srow["output_tokens"],
                "cache_read_tokens": srow["cache_read_tokens"],
                "cache_write_tokens": srow["cache_write_tokens"],
                "reasoning_tokens": srow["reasoning_tokens"],
                "api_call_count": srow["api_call_count"],
                "estimated_cost_usd": srow["estimated_cost_usd"],
                "cost_status": srow["cost_status"],
            },
            "not_available": [
                "per-turn token usage (Hermes persists only session-level totals "
                "in sessions/session_model_usage; messages.token_count is NULL here)",
                "Hermes child/subagent session metrics (out of scope in S1.1)",
            ],
        }
    finally:
        con.close()


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
