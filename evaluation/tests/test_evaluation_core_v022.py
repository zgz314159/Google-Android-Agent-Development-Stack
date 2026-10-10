#!/usr/bin/env python3
"""v0.2.2 regression tests.

Covers the three fixes the Verification Layer Promotion exposed:
  1. human-wait attribution (ask_user_question / plan approval) - the boundary
     turn's OWN span is the human wait; it must never be agent-owned or T3;
  2. failure false-positive - a unittest/JUnit "... ok" line (even with a
     timeout/error/failure word in the test name) is never a logical failure,
     while "... FAIL"/"... ERROR" is;
  3. agent-owned phase denominator - phase shares and UNKNOWN use agent_owned_wall.

Observer-only: synthetic JSONL plus an optional read-only replay of the real
promotion session. Never runs a build/test/device, never touches product code.
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
REAL_SESSION = os.path.expanduser(
    "~/.commandcode/projects/mnt-android-dev-projects/7817d580-8869-4931-abe7-6fc0217d56e1.jsonl"
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

    def prompt(self, text, sec, source="user"):
        self.rows.append({"type": "message", "id": f"p{self._n}", "timestamp": ts(sec),
                          "message": {"role": "user",
                                      "content": [{"type": "text", "text": text}],
                                      "meta": {"source": source}}})
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


class TestHumanWaitAttribution(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def _ask_session(self, idle=21600.0):
        b = Builder()
        b.session(0)
        b.prompt("TASK-WAIT do the thing", 0)
        b.assistant(10, [("todo_write", {"todos": []})])          # T3, span (0,10]
        ids = b.assistant(11 + idle,                               # question emit @11, resume @11+idle
                          [("ask_user_question", {"questions": [{"question": "q?"}]})],
                          created=11)
        b.result(11 + idle, [(ids[0], "user answered")])
        b.assistant(16 + idle, [], text="done")                    # T9 final answer
        return analyze(b, self.tmp)

    def test_long_idle_is_not_agent_owned(self):
        run = self._ask_session(idle=21600.0)   # 6 hours
        c = run["clocks"]
        self.assertAlmostEqual(c["task_elapsed_wall_sec"], 21616.0, places=3)
        self.assertAlmostEqual(c["interactive_user_wait_sec"], 21600.0, places=3)
        self.assertFalse(c["interactive_user_wait_upper_bound"])
        self.assertAlmostEqual(c["agent_owned_wall_sec"], 16.0, places=3)
        self.assertEqual(c["unattributed_idle_wall_sec"], 0.0)
        self.assertTrue(run["reconciliation"]["ok"])

    def test_long_idle_is_not_T3(self):
        run = self._ask_session(idle=21600.0)
        ask = [s for s in run["_spans"] if s["tool"] == "ask_user_question"][0]
        self.assertEqual(ask["phase"], "T3")
        self.assertEqual(ask["wait_tag"], "USER_WAIT")
        self.assertAlmostEqual(ask["wait_seconds"], 21600.0, places=3)
        self.assertAlmostEqual(ask["agent_seconds"], 1.0, places=3)
        # the first assistant turn is T0 (intake); T3 holds only the 1 s of
        # question generation - the 6 h idle is NEVER in a phase
        self.assertAlmostEqual(run["phase_totals"]["T3"]["wall_seconds"], 1.0, places=3)
        self.assertAlmostEqual(run["phase_totals"]["T0"]["wall_seconds"], 10.0, places=3)
        # every phase second is agent-owned; the 6 h is reported as USER_WAIT only
        self.assertAlmostEqual(
            sum(v["wall_seconds"] for v in run["phase_totals"].values()),
            run["clocks"]["agent_owned_wall_sec"], places=3)
        self.assertAlmostEqual(run["wait_totals"]["USER_WAIT"], 21600.0, places=3)

    def test_plan_review_wait_is_not_agent_owned(self):
        b = Builder()
        b.session(0)
        b.prompt("TASK-PLAN", 0)
        b.assistant(10, [("todo_write", {"todos": []})])
        ids = b.assistant(301, [("plan_review", {})], created=11)   # 290 s approval wait
        b.result(301, [(ids[0], "Plan approved")])
        b.assistant(306, [], text="done")
        run = analyze(b, self.tmp)
        c = run["clocks"]
        self.assertAlmostEqual(c["interactive_user_wait_sec"], 290.0, places=3)
        self.assertAlmostEqual(c["agent_owned_wall_sec"], 16.0, places=3)
        pr = [s for s in run["_spans"] if s["tool"] == "plan_review"][0]
        self.assertEqual(pr["phase"], "T3")
        self.assertEqual(pr["wait_tag"], "USER_WAIT")
        self.assertAlmostEqual(pr["wait_seconds"], 290.0, places=3)
        self.assertLess(pr["agent_seconds"], 2.0)

    def test_whole_span_upper_bound_without_created_at(self):
        # no meta.createdAt -> the boundary span is the (conservative) upper bound
        b = Builder()
        b.session(0)
        b.prompt("TASK-U", 0)
        b.assistant(10, [("todo_write", {"todos": []})])
        ids = b.assistant(310, [("ask_user_question", {"questions": [{"question": "q?"}]})])
        b.result(310, [(ids[0], "answered")])
        b.assistant(320, [], text="done")
        run = analyze(b, self.tmp)
        c = run["clocks"]
        self.assertTrue(c["interactive_user_wait_upper_bound"])
        self.assertAlmostEqual(c["interactive_user_wait_sec"], 300.0, places=3)  # span (10,310]
        self.assertAlmostEqual(c["agent_owned_wall_sec"], 20.0, places=3)


def _call(result_text, command="bash tests/smoke/selftest_static.sh"):
    return core.Call(call_id="c1", name="shell_command",
                     input={"command": command}, row_index=1, result_text=result_text)


class TestFailureFalsePositive(unittest.TestCase):
    def test_ok_line_with_timeout_name_is_not_a_failure(self):
        t = ("test_timeout_error_handling (tests.unit.test_x.TestX.test_timeout_error_handling) ... ok\n"
             "test_failure_recovery (tests.unit.test_x.TestX.test_failure_recovery) ... ok\n"
             "Ran 2 tests in 0.01s\n\nOK\n")
        self.assertEqual(core.test_run_verdict(t)["verdict"], "pass")
        self.assertIsNone(core.classify_failure(_call(t)))

    def test_single_ok_line_is_not_a_failure(self):
        t = "test_timeout_error_handling (tests.unit.test_x.TestX.test_timeout_error_handling) ... ok"
        self.assertIsNone(core.classify_failure(_call(t)))

    def test_fail_line_is_a_failure(self):
        t = "test_x (tests.unit.test_y.TestY.test_x) ... FAIL\nFAILED (failures=1)"
        v = core.test_run_verdict(t)
        self.assertEqual(v["verdict"], "fail")
        mark = core.classify_failure(_call(t))
        self.assertEqual(mark[0], "TEST_PROBLEM")
        self.assertIn("test_x", mark[1])

    def test_error_line_is_a_failure(self):
        t = "test_x (tests.unit.test_y.TestY.test_x) ... ERROR\nRan 1 test in 0.0s\n\nFAILED (errors=1)"
        mark = core.classify_failure(_call(t))
        self.assertEqual(mark[0], "TEST_PROBLEM")

    def test_mixed_transcript_evidence_is_the_failing_line(self):
        t = ("test_timeouts (tests.unit.test_p.TestP.test_timeouts) ... ok\n"
             "test_bad_process_evidence (tests.unit.test_s.TestS.test_bad) ... FAIL\n"
             "Ran 2 tests in 0.1s\n\nFAILED (failures=1)\nSELFTEST_STATIC=FAIL\n")
        mark = core.classify_failure(_call(t))
        self.assertEqual(mark[0], "TEST_PROBLEM")
        self.assertIn("FAIL", mark[1])
        self.assertNotIn("... ok", mark[1])

    def test_build_failure_is_not_misread_as_test(self):
        t = "FAILURE: Build failed with an exception.\n\nExecution failed for task ':app:assembleDebug'."
        mark = core.classify_failure(_call(t, command="./gradlew :app:assembleDebug"))
        self.assertEqual(mark[0], "BUILD_ERROR")


class TestPhaseDenominator(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_denominator_is_agent_owned(self):
        b = Builder()
        b.session(0)
        b.prompt("TASK-D", 0)
        b.assistant(5, [("todo_write", {"todos": []})])
        ids = b.assistant(6010, [("ask_user_question", {"questions": [{"question": "q?"}]})], created=10)
        b.result(6010, [(ids[0], "answered")])
        b.assistant(6020, [], text="done")
        run = analyze(b, self.tmp)
        self.assertEqual(run["phase_share_denominator"], "agent_owned_wall")
        self.assertAlmostEqual(run["phase_share_denominator_sec"], 20.0, places=3)
        self.assertAlmostEqual(run["clocks"]["agent_owned_wall_sec"], 20.0, places=3)


class TestProjectIdentity(unittest.TestCase):
    def test_explicit_project_wins(self):
        self.assertEqual(core.discover_project_identity("/whatever", "Explicit"), "Explicit")

    def test_nearest_config_wins(self):
        tmp = tempfile.mkdtemp()
        deep = os.path.join(tmp, "a", "b", "c")
        os.makedirs(deep)
        with open(os.path.join(tmp, ".evaluation.json"), "w", encoding="utf-8") as f:
            json.dump({"project": "StackX"}, f)
        self.assertEqual(core.discover_project_identity(deep), "StackX")

    def test_basename_fallback(self):
        tmp = tempfile.mkdtemp()
        proj = os.path.join(tmp, "myproj")
        os.makedirs(proj)
        self.assertEqual(core.discover_project_identity(proj), "myproj")


@unittest.skipUnless(os.path.exists(REAL_SESSION), "real promotion session JSONL not present")
class TestRealPromotionSessionV022(unittest.TestCase):
    """Replay the real Verification Layer Promotion session through v0.2.2."""

    @classmethod
    def setUpClass(cls):
        cls.report = core.analyze(
            REAL_SESSION, run_id="REPLAY-v022",
            project="Google-Android-Agent-Development-Stack",
            prompt_contains="Verification Layer Promotion")
        cls.spans = {s["span_id"]: s for s in cls.report["_spans"]}

    def test_turn_0012_ask_wait_excluded_from_agent(self):
        s = self.spans["TURN-0012"]
        self.assertGreater(s["duration_seconds"], 23000)   # ~23114 s span
        self.assertGreater(s["wait_seconds"], 23000)       # human wait
        self.assertLess(s["agent_seconds"], 60)            # model work only
        self.assertEqual(s["wait_tag"], "USER_WAIT")
        self.assertEqual(s["phase"], "T3")

    def test_clocks_four_way(self):
        c = self.report["clocks"]
        self.assertAlmostEqual(c["task_elapsed_wall_sec"], 25321.663, places=3)
        self.assertGreater(c["interactive_user_wait_sec"], 23000)
        self.assertEqual(c["unattributed_idle_wall_sec"], 0.0)
        self.assertLess(c["agent_owned_wall_sec"], 3000)

    def test_t3_no_longer_inflated(self):
        t3 = self.report["phase_totals"]["T3"]["wall_seconds"]
        self.assertLess(t3, 1000)                          # was 23265.961 s in v0.2.1
        self.assertEqual(self.report["phase_share_denominator"], "agent_owned_wall")

    def test_t2_t6_reported(self):
        pt = self.report["phase_totals"]
        self.assertGreater(pt["T2"]["wall_seconds"], 0)
        self.assertGreater(pt["T6"]["wall_seconds"], 0)
        self.assertAlmostEqual(
            sum(v["wall_seconds"] for v in pt.values()),
            self.report["clocks"]["agent_owned_wall_sec"], places=3)

    def test_no_false_positive_from_ok_line(self):
        for f in self.report["logical_failures"]:
            self.assertNotIn("... ok", f["evidence"])
            self.assertNotEqual(f["type"], "INFRASTRUCTURE_ERROR")

    def test_unknown_green(self):
        self.assertLessEqual(self.report["unknown_ratio"], 0.02)
        self.assertEqual(self.report["observability_quality"], "GREEN")

    def test_reconciliation(self):
        self.assertTrue(self.report["reconciliation"]["ok"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
