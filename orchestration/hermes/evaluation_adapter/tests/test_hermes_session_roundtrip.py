#!/usr/bin/env python3
"""WAVE1A adapter round-trip test for the Hermes execution source.

Contract: STACK-SIMPLIFICATION-S2-WAVE1A-001  (TASK-02, AC-W1A-006)

Proves that ``hermes_session_source.normalize_session`` still round-trips a Hermes root session
into a Command Code v3-shaped shim after the WAVE1A classification change: the pre-existing
tool-name aliases are preserved, the wrapper tool is NOT aliased, and the shim carries the
native tool identity, the persisted model and the persisted usage block unchanged.

Deterministic and offline: a synthetic in-memory-backed ``state.db`` is written to a temp dir.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ADAPTER = os.path.join(HERE, os.pardir, "hermes_session_source.py")


def load_adapter():
    spec = importlib.util.spec_from_file_location("hermes_session_source_rt", ADAPTER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SESSION_COLUMNS = (
    "id", "parent_session_id", "started_at", "ended_at", "end_reason", "cwd", "model",
    "billing_provider", "title", "message_count", "tool_call_count", "input_tokens",
    "output_tokens", "profile_name", "cost_status", "estimated_cost_usd", "api_call_count",
    "cache_read_tokens", "cache_write_tokens", "reasoning_tokens",
)
MESSAGE_COLUMNS = (
    "id", "session_id", "role", "content", "tool_call_id", "tool_calls", "tool_name",
    "timestamp", "reasoning", "reasoning_content", "active",
)


def build_db(path: str) -> None:
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE sessions (%s)" % ", ".join(SESSION_COLUMNS))
    con.execute("CREATE TABLE messages (%s)" % ", ".join(MESSAGE_COLUMNS))
    con.execute(
        "INSERT INTO sessions VALUES (%s)" % ",".join(["?"] * len(SESSION_COLUMNS)),
        ("sess-rt", None, 1000.0, 1100.0, "cli_close", "/repo", "deepseek/deepseek-v4.1-flash",
         "commandcode", "roundtrip", 4, 3, 111, 222, "android-stack", "unknown", None, 7,
         333, 0, 9),
    )
    rows = [
        (1, "sess-rt", "user", "do the thing", None, None, None, 1000.0, None, None, 1),
        (2, "sess-rt", "assistant", "on it", None,
         json.dumps([{"id": "call_a", "function": {"name": "terminal",
                                                   "arguments": json.dumps({"command": "ls -la"})}},
                     {"id": "call_b", "function": {"name": "tool_call",
                                                   "arguments": json.dumps({"calls": [{"name": "process_manage"}]})}}]),
         None, 1001.0, None, None, 1),
        (3, "sess-rt", "tool", "total 0", "call_a", None, "terminal", 1002.0, None, None, 1),
        (4, "sess-rt", "assistant", "done", None, None, None, 1003.0, None, None, 1),
    ]
    con.executemany(
        "INSERT INTO messages VALUES (%s)" % ",".join(["?"] * len(MESSAGE_COLUMNS)), rows)
    con.commit()
    con.close()


class RoundTripTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "state.db")
        build_db(self.db)
        self.mod = load_adapter()
        self.dest = os.path.join(self.tmp.name, "shim.jsonl")

    def tearDown(self):
        self.tmp.cleanup()

    def test_alias_map_preserved_and_wrapper_not_aliased(self):
        self.assertEqual(self.mod.HERMES_TOOL_ALIAS,
                         {"terminal": "shell_command", "patch": "edit_file", "search_files": "grep"})
        self.assertEqual(self.mod.canonical_tool_name("tool_call"), "tool_call")

    def test_normalisation_round_trips(self):
        meta = self.mod.normalize_session(self.db, "sess-rt", self.dest)
        with open(self.dest, "r", encoding="utf-8") as fh:
            objects = [json.loads(ln) for ln in fh if ln.strip()]

        header = objects[0]
        self.assertEqual(header["type"], "session")
        self.assertEqual(header["version"], 3)
        self.assertEqual(header["source"], "hermes")
        self.assertEqual(header["model"], "deepseek/deepseek-v4.1-flash")

        rows = [o for o in objects[1:]]
        self.assertEqual(len(rows), 4)
        self.assertEqual(meta["session_messages"], 4)
        self.assertEqual(meta["tool_use_parts"], 2)
        self.assertEqual(meta["tool_result_parts"], 1)

        # the assistant row carries BOTH the canonicalised and the native tool name
        assistant = rows[1]["message"]["content"]
        tool_uses = [p for p in assistant if p.get("type") == "tool_use"]
        self.assertEqual(tool_uses[0]["name"], "shell_command")
        self.assertEqual(tool_uses[0]["native_name"], "terminal")
        self.assertEqual(tool_uses[0]["input"], {"command": "ls -la"})
        # the wrapper tool keeps its own identity
        self.assertEqual(tool_uses[1]["name"], "tool_call")
        self.assertEqual(tool_uses[1]["native_name"], "tool_call")

        # persisted usage round-trips verbatim (no estimate)
        usage = meta["identity"]["usage"]
        self.assertEqual(usage["requests"], 7)
        self.assertEqual(usage["input"], 111)
        self.assertEqual(usage["output"], 222)
        self.assertEqual(usage["cache_read"], 333)
        self.assertEqual(usage["cache_write"], 0)
        self.assertEqual(meta["identity"]["tool_name_map"],
                         {"terminal": "shell_command", "patch": "edit_file", "search_files": "grep"})

    def test_incomplete_session_is_refused(self):
        con = sqlite3.connect(self.db)
        con.execute("UPDATE sessions SET ended_at = NULL WHERE id = 'sess-rt'")
        con.commit()
        con.close()
        with self.assertRaises(self.mod.HermesSourceError):
            self.mod.normalize_session(self.db, "sess-rt", self.dest)


if __name__ == "__main__":
    unittest.main(verbosity=2)
