#!/usr/bin/env python3
"""Evaluation Core v0.2.3 regression tests.

Covers the executor-measurement calibration:
  1. repair attribution - FAIL -> relevant code edit -> successful re-run of the
     SAME operation target links ONE repair; unrelated edits / different targets
     link none; repeated failures of one target are ONE logical failure, not many;
  2. android executor taxonomy - main source edit, test source edit, gradle build,
     gradle test, verification-run execution and report/result all classify to the
     right phase (never UNKNOWN);
  3. wait semantics - total_wait_tag_wall_sec (all wait tags) is distinct from the
     human-in-the-loop interactive_user_wait_sec; user_wait_seconds is deprecated;
  4. a read-only replay of the real P0 compiler session, proving the repair is now
     detected.

Observer-only: synthetic JSONL plus an optional read-only replay. Never runs a
build/test/device, never touches product code, never makes an LLM/network call.
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
REAL_P0_SESSION = os.path.expanduser(
    "~/.commandcode/projects/mnt-android-dev-projects/dc164656-58b4-4b96-9a1a-f42c724a1507.jsonl"
)


def ts(sec):
    return (BASE + timedelta(seconds=sec)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def ms(sec):
    return int((BASE + timedelta(seconds=sec)).timestamp() * 1000)


class Builder:
    def __init__(self):
        self.rows = []
        self._n = 0

    def session(self, sec=0):
        self.rows.append({"type": "session", "version": 3, "id": "s",
                          "timestamp": ts(sec), "cwd": "/proj"})

    def prompt(self, text, sec):
        self.rows.append({"type": "message", "id": f"p{self._n}", "timestamp": ts(sec),
                          "message": {"role": "user", "content": [{"type": "text", "text": text}],
                                      "meta": {"source": "user"}}})
        self._n += 1

    def assistant(self, sec, calls=None, text="", created=None):
        content = []
        if text:
            content.append({"type": "text", "text": text})
        ids = []
        for name, inp in (calls or []):
            cid = f"c{self._n}_{len(ids)}"
            content.append({"type": "tool_use", "id": cid, "name": name, "input": inp})
            ids.append(cid)
        meta = {"source": "model"}
        if created is not None:
            meta["createdAt"] = ms(created)
        self.rows.append({"type": "message", "id": f"a{self._n}", "timestamp": ts(sec),
                          "message": {"role": "assistant", "content": content, "meta": meta},
                          "model": "test/model",
                          "usage": {"inputTokens": 100, "outputTokens": 10,
                                    "cacheReadTokens": 0, "cacheWriteTokens": 0, "costUsd": 0.0}})
        self._n += 1
        return ids

    def result(self, sec, results):
        content = [{"type": "tool_result", "tool_use_id": cid,
                    "content": [{"type": "text", "text": t}]} for cid, t in results]
        self.rows.append({"type": "message", "id": f"r{self._n}", "timestamp": ts(sec),
                          "message": {"role": "user", "content": content,
                                      "meta": {"source": "tool"}}})
        self._n += 1

    def write(self, path):
        with open(path, "w", encoding="utf-8") as f:
            for r in self.rows:
                f.write(json.dumps(r) + "\n")
        return path


def analyze(b, tmp, **kw):
    path = os.path.join(tmp, "s.jsonl")
    b.write(path)
    return core.analyze(path, run_id="T", project="proj", **kw)


RUN_X = "python3 -m unittest tests/test_x.py -v"
RUN_Y = "python3 -m unittest tests/test_y.py -v"
FAILED = "Ran 1 test in 0.01s\n\ntest_x (tests.test_x.TestX.test_x) ... FAIL\nFAILED (failures=1)"
PASSED = "test_x (tests.test_x.TestX.test_x) ... ok\nRan 1 test in 0.01s\n\nOK"


def _cmd(b, sec, command, result):
    ids = b.assistant(sec, [("shell_command", {"command": command})])
    b.result(sec, [(ids[0], result)])


def _edit(b, sec, path):
    ids = b.assistant(sec, [("edit_file", {"file_path": path, "old_string": "a", "new_string": "b"})])
    b.result(sec, [(ids[0], "Edited")])


class TestRepairAttribution(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_relevant_edit_and_same_target_rerun_is_one_repair(self):
        b = Builder()
        b.session(0)
        b.prompt("TASK run the tests", 0)
        b.assistant(1, [("todo_write", {"todos": []})])
        _cmd(b, 5, RUN_X, FAILED)
        _edit(b, 10, "/proj/src/x.py")
        _cmd(b, 20, RUN_X, PASSED)
        b.assistant(25, [], text="done")
        run = analyze(b, self.tmp)

        self.assertEqual(len(run["logical_failures"]), 1)
        self.assertEqual(len(run["repairs"]), 1)
        rep = run["repairs"][0]
        self.assertEqual(rep["result"], "PASS")
        self.assertEqual(rep["rerun_result"], "PASS")
        self.assertEqual(rep["changed_paths"], ["/proj/src/x.py"])
        self.assertEqual(rep["failure_id"], run["logical_failures"][0]["logical_failure_id"])
        self.assertEqual(rep["failure_timestamp"], ts(5))
        self.assertEqual(rep["first_fix_timestamp"], ts(10))
        self.assertEqual(rep["verification_timestamp"], ts(20))
        self.assertAlmostEqual(rep["repair_wall_seconds"], 15.0, places=3)
        self.assertEqual(run["logical_failures"][0]["repair_status"], "REPAIRED")
        self.assertEqual(run["repair_linkage"]["repaired_failures"], 1)
        self.assertEqual(run["repair_linkage"]["status"], "OK")

    def test_unrelated_edit_does_not_become_a_repair(self):
        b = Builder()
        b.session(0)
        b.prompt("TASK run the tests", 0)
        b.assistant(1, [("todo_write", {"todos": []})])
        _cmd(b, 5, RUN_X, FAILED)
        _edit(b, 10, "/proj/notes.md")          # documentation, not a code fix
        _cmd(b, 20, RUN_Y, PASSED)              # a different target passes
        b.assistant(25, [], text="done")
        run = analyze(b, self.tmp)

        self.assertEqual(len(run["repairs"]), 0)
        self.assertEqual(run["logical_failures"][0]["repair_status"], "UNPROVABLE_NO_FIX_EDIT")
        self.assertEqual(run["repair_linkage"]["status"], "REPAIR_LINKAGE_UNPROVABLE")

    def test_rerun_of_a_different_target_is_not_a_repair(self):
        b = Builder()
        b.session(0)
        b.prompt("TASK run the tests", 0)
        b.assistant(1, [("todo_write", {"todos": []})])
        _cmd(b, 5, RUN_X, FAILED)
        _edit(b, 10, "/proj/src/x.py")          # a real code edit...
        _cmd(b, 20, RUN_Y, PASSED)              # ...but a different target passes
        b.assistant(25, [], text="done")
        run = analyze(b, self.tmp)

        self.assertEqual(len(run["repairs"]), 0)
        self.assertEqual(
            run["logical_failures"][0]["repair_status"], "UNPROVABLE_NO_SUCCESSFUL_RERUN"
        )

    def test_repeated_failure_is_one_failure_with_a_repair_chain(self):
        b = Builder()
        b.session(0)
        b.prompt("TASK run the tests", 0)
        b.assistant(1, [("todo_write", {"todos": []})])
        _cmd(b, 5, RUN_X, FAILED)
        _edit(b, 10, "/proj/src/x.py")
        _cmd(b, 20, RUN_X, FAILED)              # same target fails again
        _edit(b, 30, "/proj/src/x.py")
        _cmd(b, 40, RUN_X, PASSED)
        b.assistant(45, [], text="done")
        run = analyze(b, self.tmp)

        self.assertEqual(len(run["logical_failures"]), 1)   # not three product faults
        self.assertEqual(len(run["logical_failures"][0]["raw_events"]), 2)
        self.assertEqual(len(run["repairs"]), 1)
        self.assertEqual(run["repairs"][0]["verification_timestamp"], ts(40))


class TestAndroidExecutorTaxonomy(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_executor_surfaces_classify(self):
        b = Builder()
        b.session(0)
        b.prompt("TASK android change", 0)
        b.assistant(1, [("todo_write", {"todos": []})])                       # 0: T0 intake

        ids = b.assistant(2, [("write_file", {"file_path": "/proj/app/src/main/java/A.kt"})])
        b.result(2, [(ids[0], "ok")])                                          # 1: main source -> T4

        ids = b.assistant(3, [("write_file", {"file_path": "/proj/app/src/androidTest/java/BTest.kt"})])
        b.result(3, [(ids[0], "ok")])                                          # 2: test source -> T6

        ids = b.assistant(4, [("shell_command", {"command": "cd /proj && ./gradlew :app:compileDebugKotlin"})])
        b.result(4, [(ids[0], "BUILD SUCCESSFUL")])                            # 3: build -> T5

        ids = b.assistant(5, [("shell_command", {"command": "cd /proj && ./gradlew :app:testDebugUnitTest"})])
        b.result(5, [(ids[0], "BUILD SUCCESSFUL")])                            # 4: test -> T6

        ids = b.assistant(6, [("shell_command", {"command": "bash verification/runner/run_verification.sh plan.json"})])
        b.result(6, [(ids[0], "VERIFICATION=PASS")])                           # 5: verification -> T7

        ids = b.assistant(7, [("write_file", {"file_path": "/proj/reports/FINAL-X.md"})])
        b.result(7, [(ids[0], "ok")])                                          # 6: report -> T9

        ids = b.assistant(8, [("read_file", {"file_path": "/proj/app/src/main/java/A.kt"})])
        b.result(8, [(ids[0], "class A")])                                     # 7: read source -> T2

        ids = b.assistant(9, [("write_file", {"file_path": "/proj/specs/foo/requirements.md"})])
        b.result(9, [(ids[0], "ok")])                                          # 8: spec -> T3

        b.assistant(10, [], text="done")
        run = analyze(b, self.tmp)
        ph = [s["phase"] for s in run["_spans"]]
        self.assertEqual(ph[0], "T0")
        self.assertEqual(ph[1], "T4", "android main source edit must be T4")
        self.assertEqual(ph[2], "T6", "android test source edit must be T6")
        self.assertEqual(ph[3], "T5", "gradle compile must be T5")
        self.assertEqual(ph[4], "T6", "gradle unit test must be T6")
        self.assertEqual(ph[5], "T7", "verification runner execution must be T7")
        self.assertEqual(ph[6], "T9", "report write must be T9")
        self.assertEqual(ph[7], "T2", "production source read must be T2")
        self.assertEqual(ph[8], "T3", "spec write must be T3")


class TestWaitSemantics(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_total_wait_tag_is_not_human_wait(self):
        b = Builder()
        b.session(0)
        b.prompt("TASK build and ask", 0)
        b.assistant(5, [("todo_write", {"todos": []})])            # intake
        ids = b.assistant(15, [("shell_command", {"command": "./gradlew :app:assembleDebug"})])
        b.result(15, [(ids[0], "BUILD SUCCESSFUL")])               # WAIT_BUILD span
        ids = b.assistant(25, [("ask_user_question", {"questions": [{"question": "q?"}]})], created=16)
        b.result(25, [(ids[0], "answered")])                       # 9 s human wait
        b.assistant(30, [], text="done")
        run = analyze(b, self.tmp)

        total = run["total_wait_tag_wall_sec"]
        self.assertAlmostEqual(total, round(sum(run["wait_totals"].values()), 3), places=3)
        self.assertAlmostEqual(run["clocks"]["interactive_user_wait_sec"], 9.0, places=3)
        self.assertNotEqual(total, run["clocks"]["interactive_user_wait_sec"])
        self.assertAlmostEqual(run["user_wait_seconds"], total, places=3)
        self.assertIn("user_wait_seconds", run["deprecated_fields"])


@unittest.skipUnless(os.path.exists(REAL_P0_SESSION), "real P0 compiler session JSONL not present")
class TestRealP0CompilerSessionV023(unittest.TestCase):
    """Read-only replay of the real Specification Compiler P0 session."""

    @classmethod
    def setUpClass(cls):
        cls.report = core.analyze(
            REAL_P0_SESSION, run_id="REPLAY-v023",
            project="Google-Android-Agent-Development-Stack",
        )

    def test_real_failure_detected(self):
        self.assertTrue(self.report["logical_failures"])

    def test_real_repair_linkage_is_repairable(self):
        repairs = self.report["repairs"]
        self.assertGreaterEqual(len(repairs), 1, self.report["repair_linkage"])
        linked = [
            r for r in repairs
            if any("test_validate_package.py" in p for p in r.get("changed_paths", []))
        ]
        self.assertTrue(linked, [r.get("changed_paths") for r in repairs])
        self.assertEqual(linked[0]["rerun_result"], "PASS")
        self.assertGreaterEqual(linked[0]["repair_wall_seconds"], 0)
        self.assertEqual(self.report["repair_linkage"]["repaired_failures"], len(repairs))

    def test_linked_failure_is_repaired_test_problem(self):
        repaired = [f for f in self.report["logical_failures"] if f.get("repair_status") == "REPAIRED"]
        self.assertTrue(repaired)
        self.assertIn(repaired[0]["type"], ("TEST_PROBLEM", "BUILD_ERROR", "GENERIC_ERROR"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
