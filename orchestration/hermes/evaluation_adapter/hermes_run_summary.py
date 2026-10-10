#!/usr/bin/env python3
"""Thin Hermes -> Evaluation observability adapter (stdlib only).

Reads real Hermes smoke evidence (the profile's read-only state.db) and emits a
single `hermes-run-summary.json`. Missing fields are null or "NOT_AVAILABLE" -
nothing is ever guessed.

Inputs (all real evidence):
  --db <state.db>            Hermes profile state DB (opened READ-ONLY)
  --root-session <id>        the root session id of the run
  --kanban-json <file>       optional `hermes kanban list --json` capture
  --out <path>               output hermes-run-summary.json
  --evidence-out <path>      optional raw child rows (evidence)
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys

NA = "NOT_AVAILABLE"


def _connect(db: str) -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def _session(con, sid: str):
    return con.execute("select * from sessions where id=?", (sid,)).fetchone()


def _children(con, root: str):
    return con.execute("select * from sessions where parent_session_id=? order by started_at", (root,)).fetchall()


def max_overlap(intervals: list[tuple[float, float]]) -> tuple[int, float]:
    """(max_concurrent, concurrent_wall_seconds) from [(start,end), ...].

    concurrent_wall = wall time during which >= 2 intervals were simultaneously
    active (interval-union of each pairwise overlap), computed by a sweep.
    """
    iv = [(s, e) for s, e in intervals if s is not None and e is not None and e >= s]
    if not iv:
        return 0, 0.0
    events = []
    for s, e in iv:
        events.append((s, 1))
        events.append((e, -1))
    events.sort(key=lambda x: (x[0], x[1]))  # open before close at equal time
    cur = mx = 0
    concurrent = 0.0
    prev = None
    for t, d in events:
        if prev is not None and cur >= 2:
            concurrent += t - prev
        cur += d
        mx = max(mx, cur)
        prev = t
    return mx, concurrent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--root-session", required=True)
    ap.add_argument("--kanban-json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--evidence-out")
    args = ap.parse_args()

    con = _connect(args.db)
    root = _session(con, args.root_session)
    if root is None:
        print(f"ROOT_SESSION_NOT_FOUND {args.root_session}", file=sys.stderr)
        return 2
    kids = _children(con, args.root_session)

    child_rows = [{
        "session_id": k["id"],
        "title": k["title"],
        "started_at": k["started_at"],
        "ended_at": k["ended_at"],
        "status": "completed" if k["ended_at"] else "running",
        "input_tokens": k["input_tokens"],
        "output_tokens": k["output_tokens"],
        "api_call_count": k["api_call_count"],
    } for k in kids]

    intervals = [(k["started_at"], k["ended_at"]) for k in kids]
    max_conc, overlap = max_overlap(intervals)

    api_calls = root["api_call_count"] if root["api_call_count"] is not None else None
    wall = None
    if root["started_at"] is not None and root["ended_at"] is not None:
        wall = round(root["ended_at"] - root["started_at"], 3)

    kanban_tasks = NA
    failed_tasks = NA
    if args.kanban_json:
        try:
            with open(args.kanban_json, encoding="utf-8") as fh:
                data = json.load(fh)
            tasks = data if isinstance(data, list) else data.get("tasks", [])
            kanban_tasks = [{"id": t.get("id"), "status": t.get("status"), "title": t.get("title")} for t in tasks]
            failed_tasks = [t.get("id") for t in tasks if t.get("status") in ("blocked", "failed")]
        except (OSError, ValueError):
            kanban_tasks = NA
            failed_tasks = NA

    summary = {
        "root_session": args.root_session,
        "provider": root["billing_provider"] if "billing_provider" in root.keys() else NA,
        "model": root["model"],
        "children_started": len(kids),
        "children_completed": sum(1 for k in kids if k["ended_at"]),
        "max_concurrent_children": max_conc,
        "parallel_overlap_sec": round(overlap, 3) if kids else NA,
        "kanban_tasks": kanban_tasks,
        "failed_tasks": failed_tasks,
        "root_tool_calls": root["tool_call_count"] if root["tool_call_count"] is not None else NA,
        "root_message_count": root["message_count"] if root["message_count"] is not None else NA,
        "wall_sec": wall,
        "api_calls": api_calls if api_calls is not None else NA,
        "tokens": {
            "input": root["input_tokens"] if root["input_tokens"] is not None else NA,
            "output": root["output_tokens"] if root["output_tokens"] is not None else NA,
            "cache_read": root["cache_read_tokens"] if root["cache_read_tokens"] is not None else NA,
            "cache_write": root["cache_write_tokens"] if root["cache_write_tokens"] is not None else NA,
        },
        "children": child_rows,
        "source": {"db": args.db, "read_only": True},
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    if args.evidence_out:
        with open(args.evidence_out, "w", encoding="utf-8") as fh:
            json.dump({"root": dict(root), "children": child_rows}, fh, indent=2, default=str)
    print(f"HERMES_RUN_SUMMARY={args.out} children={len(kids)} max_concurrent={max_conc} overlap_s={summary['parallel_overlap_sec']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
