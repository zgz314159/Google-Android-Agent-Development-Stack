#!/usr/bin/env python3
"""Hermes execution-source tests for the Auto-Finalizer (S1.1, stdlib only).

Fully offline: a temporary SQLite fixture stands in for the pinned Hermes
``state.db`` (same table/column names the adapter reads), so nothing here touches
the real Hermes store, the real Command Code index, or `/mnt/AndroidDev/Projects/_evaluation`.

Covers:
  A/B. Hermes source: discover + normalize -> canonical finalization (SUCCESS)
  C.   Idempotency: second trigger is a NO-OP (ALREADY_FINALIZED / SKIP_UNCHANGED)
  D.   Command Code regression: a legacy index record survives a hermes scan
  +    Incomplete session (ended_at IS NULL) is never finalized
  +    Missing session -> FAIL, never fabricates a record
"""
import json
import os
import sqlite3
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "evaluation", "commandcode"))
sys.path.insert(0, os.path.join(REPO, "orchestration", "hermes", "evaluation_adapter"))

import auto_finalize as af          # noqa: E402
import finalize_session as fin      # noqa: E402
import hermes_session_source as hs  # noqa: E402

SESSIONS_DDL = """
CREATE TABLE sessions (
  id TEXT PRIMARY KEY, source TEXT NOT NULL, created_source TEXT, parent_session_id TEXT,
  started_at REAL NOT NULL, ended_at REAL, end_reason TEXT,
  message_count INTEGER DEFAULT 0, tool_call_count INTEGER DEFAULT 0,
  input_tokens INTEGER DEFAULT 0, output_tokens INTEGER DEFAULT 0,
  cache_read_tokens INTEGER DEFAULT 0, cache_write_tokens INTEGER DEFAULT 0,
  reasoning_tokens INTEGER DEFAULT 0, cwd TEXT, model TEXT, billing_provider TEXT,
  estimated_cost_usd REAL, cost_status TEXT, api_call_count INTEGER DEFAULT 0,
  title TEXT, profile_name TEXT
);
CREATE TABLE messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL, role TEXT NOT NULL,
  content TEXT, tool_call_id TEXT, tool_calls TEXT, tool_name TEXT, timestamp REAL NOT NULL,
  reasoning TEXT, reasoning_content TEXT, active INTEGER DEFAULT 1
);
"""

T0 = 1791130698.0
FAILS = []


def bad(msg):
    FAILS.append(msg)
    print("FAIL:", msg)


def build_fixture(db_path):
    con = sqlite3.connect(db_path)
    con.executescript(SESSIONS_DDL)
    con.execute(
        "INSERT INTO sessions (id, source, parent_session_id, started_at, ended_at, end_reason,"
        " message_count, tool_call_count, input_tokens, output_tokens, cache_read_tokens,"
        " cache_write_tokens, reasoning_tokens, cwd, model, billing_provider, estimated_cost_usd,"
        " cost_status, api_call_count, title, profile_name)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("sess-complete", "oneshot", None, T0, T0 + 120.0, "cli_close", 4, 1, 100, 50, 10, 0, 0,
         "/mnt/AndroidDev/Projects/Demo-Project", "deepseek/deepseek-v4.1-flash", "commandcode",
         0.0, "unknown", 3, "Demo session", "android-stack"),
    )
    con.execute(
        "INSERT INTO sessions (id, source, parent_session_id, started_at, ended_at, end_reason,"
        " message_count, cwd, title, profile_name) VALUES (?,?,?,?,?,?,?,?,?,?)",
        ("sess-running", "oneshot", None, T0 + 500.0, None, None, 1,
         "/mnt/AndroidDev/Projects/Demo-Project", "Still running", "android-stack"),
    )
    con.execute(
        "INSERT INTO sessions (id, source, parent_session_id, started_at, ended_at,"
        " cwd, title, profile_name) VALUES (?,?,?,?,?,?,?,?)",
        ("sess-child", "delegate", "sess-complete", T0 + 10.0, T0 + 20.0,
         "/mnt/AndroidDev/Projects/Demo-Project", "child", "android-stack"),
    )
    # completed session: user prompt -> assistant tool_use -> tool result -> assistant terminal
    msgs = [
        ("sess-complete", "user", "Do the thing and report back.", None, None, None, T0 + 0.1, None),
        ("sess-complete", "assistant", "Running the check.", None,
         json.dumps([{"id": "call_1", "call_id": "call_1", "type": "function",
                      "function": {"name": "terminal", "arguments": "{\"command\": \"echo ok\"}"}}]),
         None, T0 + 1.0, None),
        ("sess-complete", "tool", '{"output": "ok"}', "call_1", None, "terminal", T0 + 1.2, None),
        ("sess-complete", "assistant", "Done. Result: ok.", None, None, None, T0 + 2.0, "reasoned"),
        ("sess-running", "user", "still going", None, None, None, T0 + 500.1, None),
    ]
    con.executemany(
        "INSERT INTO messages (session_id, role, content, tool_call_id, tool_calls, tool_name,"
        " timestamp, reasoning) VALUES (?,?,?,?,?,?,?,?)", msgs)
    con.commit()
    con.close()


def main():
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "state.db")
        out = os.path.join(d, "_evaluation")
        build_fixture(db)

        # ---- discovery: root sessions only, child excluded --------------------
        descs = hs.list_root_sessions(db, include_incomplete=True)
        ids = [x["session_id"] for x in descs]
        if "sess-child" in ids:
            bad("child/delegated session leaked into root discovery")
        if "sess-complete" not in ids:
            bad(f"completed root session not discovered: {ids}")
        comp = next((x for x in descs if x["session_id"] == "sess-complete"), {})
        if comp.get("completed") is not True or not comp.get("fingerprint"):
            bad(f"descriptor wrong: {comp}")
        else:
            print("ok: discovery -> root session found, completed=True, fingerprint present")

        # ---- normalize -> shim has the frozen core's schema -------------------
        shim = os.path.join(d, "shim.jsonl")
        meta = hs.normalize_session(db, "sess-complete", shim)
        with open(shim, encoding="utf-8") as fh:
            lines = [json.loads(l) for l in fh if l.strip()]
        if lines[0].get("type") != "session" or lines[0].get("version") != 3:
            bad(f"shim header wrong: {lines[0]!r}")
        sources = {r["message"]["meta"]["source"] for r in lines[1:]}
        if sources != {"user", "model", "tool"}:
            bad(f"shim message.meta.source set wrong: {sources}")
        tool_use = [p for r in lines[1:] for p in r["message"]["content"] if p.get("type") == "tool_use"]
        if not tool_use or tool_use[0]["input"] != {"command": "echo ok"}:
            bad(f"tool_use not reconstructed: {tool_use!r}")
        if meta["shim_schema_version"] != 3 or not meta["shim_sha256"]:
            bad(f"normalize metadata incomplete: {meta}")
        else:
            print(f"ok: normalize -> CC-v3 shim ({meta['shim_rows']} rows, sha256 present)")

        # ---- canonical finalize (reuses the frozen core) ----------------------
        diag = fin.finalize(session_path=shim, run_id="HERMES-sess-complete", project="Demo-Project",
                            workflow="hermes", output_root=out, require_completion=True,
                            execution_source={"source": "hermes", "session_id": "sess-complete"})
        if diag["evaluation_outcome"] != "SUCCESS" or not diag["task_completion_detected"]:
            bad(f"finalize outcome={diag['evaluation_outcome']} err={diag.get('evaluation_error')}")
        else:
            print("ok: canonical finalize -> SUCCESS, task completion detected")

        # ---- idempotency: same session again is a NO-OP -----------------------
        # Layer 1 (canonical core): the run id already has a finalization.json.
        results = af.scan_hermes(output_root=out, db=db, session_id="sess-complete")
        st = results[0]["status"] if results else None
        if st != "ALREADY_FINALIZED":
            bad(f"second trigger status={st!r} (expected ALREADY_FINALIZED)")
        # Layer 2 (index/fingerprint): the record is known -> no core run at all.
        results = af.scan_hermes(output_root=out, db=db, session_id="sess-complete")
        st2 = results[0]["status"] if results else None
        if st2 != "SKIP_UNCHANGED":
            bad(f"third trigger status={st2!r} (expected SKIP_UNCHANGED)")
        diag2 = fin.finalize(session_path=shim, run_id="HERMES-sess-complete", project="Demo-Project",
                             workflow="hermes", output_root=out, require_completion=True)
        if diag2["evaluation_outcome"] != "ALREADY_FINALIZED":
            bad(f"core idempotency broken: {diag2['evaluation_outcome']}")
        else:
            print("ok: idempotent -> ALREADY_FINALIZED then SKIP_UNCHANGED (no re-evaluation)")

        # ---- one finalize record only -----------------------------------------
        recs = [p for p in os.listdir(os.path.join(out, "Demo-Project"))]
        if len(recs) != 1:
            bad(f"duplicate evaluation records: {recs}")
        else:
            print("ok: exactly one evaluation record for (hermes, sess-complete)")

        # ---- incomplete session is never finalized ----------------------------
        results = af.scan_hermes(output_root=out, db=db, session_id="sess-running")
        r = results[0]
        if r["status"] != "INCOMPLETE":
            bad(f"running session status={r['status']!r} (expected INCOMPLETE)")
        idx = af._load_index(out)
        if "hermes:sess-running" in idx:
            bad("running session was indexed/finalized")
        if os.path.exists(os.path.join(out, "Demo-Project", "HERMES-sess-running")):
            bad("running session produced an output dir")
        if r.get("completed") is not False:
            bad("running session not flagged completed=false")
        else:
            print("ok: incomplete session -> INCOMPLETE, nothing written, not indexed")

        # ---- missing session -> NOT_FOUND, no fabrication ---------------------
        results = af.scan_hermes(output_root=out, db=db, session_id="does-not-exist")
        if results[0]["status"] != "NOT_FOUND":
            bad(f"missing session status={results[0]['status']!r}")
        else:
            print("ok: missing session -> NOT_FOUND (no fabricated record)")

        # ---- Command Code index regression: legacy records survive ------------
        legacy_key = "/home/zhong/.commandcode/projects/home-zhong/legacy.jsonl"
        idx = af._load_index(out)
        idx[legacy_key] = {"mtime_ns": 111, "size": 222, "run_id": "LEGACY-RUN",
                           "output_dir": "/old/path", "session_id": "legacy-id"}
        af._save_index(out, idx)
        af.scan_hermes(output_root=out, db=db, session_id="sess-complete")
        idx = af._load_index(out)
        if idx.get(legacy_key, {}).get("run_id") != "LEGACY-RUN":
            bad("legacy Command Code index record was lost or mutated by a hermes scan")
        elif idx[legacy_key].get("mtime_ns") != 111 or idx[legacy_key].get("size") != 222:
            bad("legacy index fields changed")
        else:
            print("ok: Command Code index record preserved verbatim across a hermes scan")

        # ---- index key namespace is a plain string (dict-compatible) ----------
        if not isinstance(hs.index_key("x"), str) or hs.index_key("x") != "hermes:x":
            bad("index_key namespace wrong")
        else:
            print("ok: hermes index key namespace is dict-compatible")

    if FAILS:
        print(f"HERMES_SOURCE_TEST=FAIL ({len(FAILS)} problem(s))")
        return 1
    print("HERMES_SOURCE_TEST=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
