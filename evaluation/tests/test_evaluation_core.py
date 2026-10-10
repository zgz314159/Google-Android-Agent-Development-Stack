#!/usr/bin/env python3
"""Unit tests for the Command Code Evaluation Core v0.2.

These tests only exercise the Evaluation Core itself with synthetic JSONL.
They never run an Android build/test and never touch product code.
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "commandcode"))
import core  # noqa: E402

BASE = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


def ts(sec):
    dt = BASE + timedelta(seconds=sec)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def usage(inp=100, out=10, cr=50, cw=0, cost=0.01):
    return {"inputTokens": inp, "outputTokens": out, "cacheReadTokens": cr,
            "cacheWriteTokens": cw, "costUsd": cost}


class SessionBuilder:
    def __init__(self, cwd="/proj", session_id="sess-x"):
        self.rows = []
        self.cwd = cwd
        self.session_id = session_id
        self._n = 0

    def session_row(self, sec=0):
        self.rows.append({"type": "session", "version": 3, "id": self.session_id,
                          "timestamp": ts(sec), "cwd": self.cwd})

    def prompt(self, text, sec):
        self.rows.append({"type": "message", "id": f"p{self._n}", "timestamp": ts(sec),
                          "message": {"role": "user", "content": [{"type": "text", "text": text}]}})
        self._n += 1

    def assistant(self, sec, calls=None, text="", use=None):
        content = []
        if text:
            content.append({"type": "text", "text": text})
        ids = []
        for name, inp in (calls or []):
            cid = f"c{self._n}_{len(ids)}"
            content.append({"type": "tool_use", "id": cid, "name": name, "input": inp})
            ids.append(cid)
        row = {"type": "message", "id": f"a{self._n}", "timestamp": ts(sec),
               "message": {"role": "assistant", "content": content}}
        if use is not None:
            row["usage"] = use
            row["model"] = "test/model"
        self.rows.append(row)
        self._n += 1
        return ids

    def result(self, sec, results):
        content = [{"type": "tool_result", "tool_use_id": cid,
                    "content": [{"type": "text", "text": txt}]} for cid, txt in results]
        self.rows.append({"type": "message", "id": f"r{self._n}", "timestamp": ts(sec),
                          "message": {"role": "user", "content": content}})
        self._n += 1

    def write(self, path):
        with open(path, "w", encoding="utf-8") as f:
            for r in self.rows:
                f.write(json.dumps(r) + "\n")
        return path


def analyze_builder(builder, tmp, **kw):
    path = os.path.join(tmp, "session.jsonl")
    builder.write(path)
    return core.analyze(path, run_id="T", project="proj", **kw)


def phases_by_turn(run):
    return {s["turn_id"]: s["phase"] for s in run["_spans"]}


class TestCore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    # 1. timestamp parsing
    def test_timestamp_parsing(self):
        dt = core.parse_ts("2026-10-03T03:09:58.272Z")
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.tzinfo, timezone.utc)
        dt2 = core.parse_ts("2026-10-03T03:09:58+00:00")
        self.assertEqual((dt - dt2).total_seconds(), 0.272)
        self.assertEqual(core._parse_duration("2m 28s"), 148.0)
        self.assertEqual(core._parse_duration("13.4s"), 13.4)
        self.assertEqual(core._parse_duration("34.4s"), 34.4)

    # 2. clock reconciliation
    def test_clock_reconciliation(self):
        b = SessionBuilder()
        b.session_row(0)
        b.prompt("do the task", 53)
        b.assistant(53, [("todo_write", {"todos": []})])
        b.result(53, [])
        b.assistant(153, [("read_file", {"file_path": "/x/y.kt"})], use=usage())
        b.result(153, [("", "ok")])
        b.assistant(400, [], text="done")
        run = analyze_builder(b, self.tmp)
        self.assertEqual(run["clocks"]["pre_prompt_user_wait_sec"], 53.0)
        self.assertEqual(run["clocks"]["task_wall_sec"], 347.0)
        self.assertEqual(run["clocks"]["session_wall_sec"], 400.0)
        self.assertTrue(run["reconciliation"]["ok"])
        self.assertEqual(round(sum(s["duration_seconds"] for s in run["_spans"]), 3), 347.0)

    # 3. phase rule priority
    def test_phase_rule_priority(self):
        b = SessionBuilder()
        b.session_row(0)
        b.prompt("task", 1)
        b.assistant(1, [("todo_write", {"todos": []})])
        b.result(1, [])
        b.assistant(10, [("shell_command", {"command": "cd p && ./gradlew testDebugUnitTest"})])
        b.result(10, [("", "BUILD SUCCESSFUL")])
        b.assistant(20, [("shell_command", {"command": "cd p && ./gradlew :app:assembleDebug"})])
        b.result(20, [("", "BUILD SUCCESSFUL")])
        b.assistant(30, [("shell_command", {"command": "adb -s X shell input tap 5 5"})])
        b.result(30, [("", "ok")])
        b.assistant(40, [("write_file", {"file_path": "/p/app/src/main/java/A.kt"})])
        b.result(40, [("", "ok")])
        b.assistant(50, [], text="done")
        run = analyze_builder(b, self.tmp)
        ph = [s["phase"] for s in run["_spans"]]
        self.assertEqual(ph[0], "T0")           # first turn = intake
        self.assertEqual(ph[1], "T6")           # gradle test beats generic
        self.assertEqual(ph[2], "T5")           # assemble = build
        self.assertEqual(ph[3], "T7")           # ui driving
        self.assertEqual(run["_spans"][3]["subphase"], "T7b")
        self.assertEqual(ph[4], "T4")           # kotlin write
        self.assertEqual(ph[5], "T9")           # final text answer

    # 4. UNKNOWN fallback (no guessing)
    def test_unknown_fallback(self):
        b = SessionBuilder()
        b.session_row(0)
        b.prompt("task", 1)
        b.assistant(1, [("todo_write", {"todos": []})])
        b.result(1, [])
        b.assistant(20, [("mystery_tool", {"blah": 1})])
        b.result(20, [("", "?")])
        b.assistant(40, [], text="done")
        run = analyze_builder(b, self.tmp)
        self.assertEqual(run["_spans"][1]["phase"], "UNKNOWN")
        self.assertGreater(run["unknown_ratio"], 0)

    # 5. background overlap must not double count wall
    def test_background_no_double_count(self):
        b = SessionBuilder()
        b.session_row(0)
        b.prompt("task", 1)
        b.assistant(1, [("todo_write", {"todos": []})])
        b.result(1, [])
        bg = b.assistant(10, [("shell_command", {"command": "./gradlew :app:assembleDebug",
                                                 "run_in_background": True})])[0]
        b.result(10, [(bg, "Started shell command in the background.\nTask: sBG1\nStatus: running")])
        poll1 = b.assistant(70, [("shell_output", {"id": "sBG1", "wait": "output"})])[0]
        b.result(70, [(poll1, "Task: sBG1 (shell, running)\n[waited 1m 0s, new output arrived]")])
        poll2 = b.assistant(130, [("shell_output", {"id": "sBG1", "wait": "exit"})])[0]
        b.result(130, [(poll2, "Task: sBG1 (shell, completed)\nExit code: 0\n[waited 1m 0s]")])
        b.assistant(160, [], text="done")
        run = analyze_builder(b, self.tmp)
        self.assertTrue(run["reconciliation"]["ok"])
        self.assertEqual(round(sum(s["duration_seconds"] for s in run["_spans"]), 3),
                         run["clocks"]["task_wall_sec"])
        self.assertEqual(run["background"]["background_duration_seconds"], 120.0)
        self.assertIsNone(run["background"]["exclusive_wall_seconds"])

    # 6. failure dedup (one logical failure for one background build)
    def test_failure_dedup(self):
        b = SessionBuilder()
        b.session_row(0)
        b.prompt("task", 1)
        b.assistant(1, [("todo_write", {"todos": []})])
        b.result(1, [])
        bg = b.assistant(10, [("shell_command", {"command": "./gradlew :app:assembleDebug",
                                                 "run_in_background": True})])[0]
        b.result(10, [(bg, "Started shell command in the background.\nTask: sBG1\nStatus: running")])
        poll1 = b.assistant(20, [("shell_output", {"id": "sBG1", "wait": "exit"})])[0]
        b.result(20, [(poll1, "Task: sBG1 (shell, failed)\nExit code: 1\n"
                              "FAILURE: Build failed with an exception.")])
        poll2 = b.assistant(30, [("shell_output", {"id": "sBG1", "wait": "exit"})])[0]
        b.result(30, [(poll2, "Task: sBG1 (shell, failed)\nExit code: 1\n"
                              "FAILURE: Build failed with an exception.")])
        b.assistant(40, [], text="done")
        run = analyze_builder(b, self.tmp)
        self.assertEqual(len(run["logical_failures"]), 1)
        self.assertEqual(run["logical_failures"][0]["type"], "BUILD_ERROR")
        self.assertGreaterEqual(len(run["logical_failures"][0]["raw_events"]), 2)

    # 7. repair linkage (FAIL -> fix -> rerun PASS)
    def test_repair_linkage(self):
        b = SessionBuilder()
        b.session_row(0)
        b.prompt("task", 1)
        b.assistant(1, [("todo_write", {"todos": []})])
        b.result(1, [])
        bg = b.assistant(10, [("shell_command", {"command": "./gradlew :app:assembleDebug",
                                                 "run_in_background": True})])[0]
        b.result(10, [(bg, "Started shell command in the background.\nTask: sBG1\nStatus: running")])
        poll = b.assistant(20, [("shell_output", {"id": "sBG1", "wait": "exit"})])[0]
        b.result(20, [(poll, "Task: sBG1 (shell, failed)\nExit code: 1\n"
                             "FAILURE: Build failed with an exception.")])
        fix = b.assistant(40, [("edit_file", {"file_path": "/p/app/src/main/java/A.kt",
                                              "old_string": "a", "new_string": "b"})])[0]
        b.result(40, [(fix, "Edited A.kt")])
        bg2 = b.assistant(60, [("shell_command", {"command": "./gradlew :app:assembleDebug",
                                                  "run_in_background": True})])[0]
        b.result(60, [(bg2, "Started shell command in the background.\nTask: sBG2\nStatus: running")])
        poll2 = b.assistant(80, [("shell_output", {"id": "sBG2", "wait": "exit"})])[0]
        b.result(80, [(poll2, "Task: sBG2 (shell, completed)\nExit code: 0\nBUILD SUCCESSFUL")])
        b.assistant(90, [], text="done")
        run = analyze_builder(b, self.tmp)
        self.assertEqual(len(run["repairs"]), 1)
        rep = run["repairs"][0]
        self.assertEqual(rep["result"], "PASS")
        self.assertEqual(rep["trigger_failure"], run["logical_failures"][0]["logical_failure_id"])
        # fix + rerun spans were reclassified to T8
        phases = [s["phase"] for s in run["_spans"]]
        self.assertIn("T8", phases)

    # 8. secret redaction
    def test_redaction(self):
        with open(os.path.join(os.path.dirname(core.__file__), "redaction_rules.json")) as fh:
            cfg = json.loads(fh.read())
        r = core.Redactor(cfg)
        out = r.text("export MY_TOKEN=supersecret123 Bearer abc.def.ghi api_key=zzz")
        self.assertNotIn("supersecret123", out)
        self.assertNotIn("abc.def.ghi", out)
        self.assertNotIn("zzz", out)
        self.assertIn("REDACTED", out)
        obj = r.obj({"authorization": "Bearer x", "model": "m"})
        self.assertEqual(obj["authorization"], "<REDACTED>")
        self.assertEqual(obj["model"], "m")

    # 9. token aggregation
    def test_token_aggregation(self):
        b = SessionBuilder()
        b.session_row(0)
        b.prompt("task", 1)
        b.assistant(1, [("todo_write", {"todos": []})], use=usage(1, 1, 1, 0, 0.1))
        b.result(1, [])
        b.assistant(10, [("read_file", {"file_path": "/x.kt"})], use=usage(100, 5, 20, 0, 0.2))
        b.result(10, [("", "ok")])
        b.assistant(20, [("write_file", {"file_path": "/y.kt"})], use=usage(200, 7, 30, 0, 0.3))
        b.result(20, [("", "ok")])
        b.assistant(30, [], text="done")
        run = analyze_builder(b, self.tmp)
        tr = run["tokens_raw"]
        self.assertEqual(tr["requests"], 3)
        self.assertEqual(tr["input"], 301)
        self.assertEqual(tr["output"], 13)
        self.assertAlmostEqual(tr["cost"], 0.6, places=6)
        by = run["tokens_by_phase"]
        self.assertEqual(sum(v["input"] for v in by.values()), 301)
        self.assertEqual(sum(v["requests"] for v in by.values()), 3)
        # raw cache fields preserved even if cache_write is 0
        self.assertIn("cache_write", tr)

    # 10. multi-session ambiguity rejection
    def test_multi_session_ambiguity(self):
        root = tempfile.mkdtemp()
        cwd = "/proj/ambig"
        for i in (1, 2):
            d = os.path.join(root, f"proj-{i}")
            os.makedirs(d)
            b = SessionBuilder(cwd=cwd, session_id=f"s{i}")
            b.session_row(0)
            b.prompt("unique marker string", 1)
            b.assistant(2, [("todo_write", {"todos": []})])
            b.write(os.path.join(d, f"s{i}.jsonl"))
        cands, reasons = core.locate_sessions(cwd, "unique marker string", root)
        self.assertEqual(len(cands), 2)  # ambiguity must be surfaced, not guessed
        cands0, _ = core.locate_sessions("/other", "unique marker string", root)
        self.assertEqual(len(cands0), 0)

    # 11. unsupported schema guard
    def test_unsupported_schema(self):
        path = os.path.join(self.tmp, "s.jsonl")
        with open(path, "w") as f:
            f.write(json.dumps({"type": "session", "version": 99, "id": "x",
                                "timestamp": ts(0), "cwd": "/p"}) + "\n")
            f.write(json.dumps({"type": "message", "timestamp": ts(1),
                                "message": {"role": "user", "content": [{"type": "text", "text": "hi"}]}}) + "\n")
        with self.assertRaises(core.UnsupportedSchema):
            core.analyze(path, run_id="T", project="p")


if __name__ == "__main__":
    unittest.main(verbosity=2)
