#!/usr/bin/env python3
"""v0.2.1 task-window + clock + completion regression tests.

Two fixtures:
  * a committed minimal-schema JSONL fixture (task_window_v021.jsonl) that
    reproduces the hardening session's shape: task prompt -> assistant ->
    ask_user_question -> continuation -> plan approval -> device smoke ->
    mid-task steering ping -> two fixes -> FINAL report -> terminal completion
    -> genuinely independent task B;
  * optional replay of the real hardening session if its raw JSONL is present
    on this machine (skipped otherwise; the raw file is never copied).

These tests never run an Android build/test/device and never touch product code.
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "commandcode"))
import core  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, "fixtures", "task_window_v021.jsonl")
REAL_SESSION = os.path.expanduser(
    "~/.commandcode/projects/mnt-android-dev-projects/085ba36c-bdde-4919-9ff5-32f0260d816d.jsonl"
)
# message-row index of the last row inside the v0.2 truncated window (the first
# steering ping was file row 130; load_session drops the session row, so the
# truncated window ended at message-row 128).
OLD_CUTOFF_ROW = 128


def load_fixture_spans(run):
    return run["_spans"]


class TestTaskWindowFixture(unittest.TestCase):
    def analyze(self, **kw):
        return core.analyze(FIXTURE, run_id="FIXTURE", project="proj",
                            prompt_contains="TASK-A", **kw)

    def test_window_follows_structural_sources(self):
        run = self.analyze()
        tw = run["task_window"]
        self.assertEqual(tw["matched_prompt_index"], 0)
        self.assertEqual(tw["start_index"], 0)
        # closes at task B's prompt, not at the first steering ping
        self.assertEqual(tw["end_index_exclusive"], 22)
        self.assertEqual(tw["in_task_continuations"], 2)       # s1, s2
        self.assertEqual(tw["excluded_independent_tasks"], 1)  # task B
        self.assertEqual(tw["uncertainty"],
                         "none: every user-side row carries message.meta.source")

    def test_steering_pings_do_not_truncate_window(self):
        run = self.analyze()
        spans = load_fixture_spans(run)
        rows = [s["row_index"] for s in spans]
        # task A's terminal completion (row 21) is the window tail; the window
        # does not stop at the first steering ping (row 11)
        self.assertEqual(max(rows), 21)
        # post-steering work is covered: two fixes and the FINAL report
        fixes = [s for s in spans if s["tool"] == "edit_file"]
        self.assertEqual(len(fixes), 2)
        self.assertTrue(all(s["row_index"] > 11 for s in fixes))
        final = [s for s in spans if "FINAL-VERIFICATION-HARNESS-HARDENING" in (s["evidence"] or "")]
        self.assertTrue(final)
        self.assertGreater(final[0]["row_index"], 16)
        # task B's completion (row 23) is NOT in task A
        self.assertNotIn(23, rows)

    def test_device_smoke_covered(self):
        run = self.analyze()
        smoke = [s for s in load_fixture_spans(run)
                 if s["tool"] == "monitor_command" and "selftest_device" in (s["evidence"] or "")]
        self.assertTrue(smoke, "device smoke monitor span missing from window")
        self.assertEqual(smoke[0]["phase"], "T6")
        self.assertEqual(smoke[0]["wait_tag"], "WAIT_DEVICE")

    def test_final_report_and_completion_covered(self):
        run = self.analyze()
        self.assertTrue(run["task_completion_detected"])
        self.assertEqual(run["task_completion"]["final_assistant_row"], 21)
        self.assertTrue(run["task_completion"]["terminal_assistant_turn"])
        final = [s for s in load_fixture_spans(run) if s["row_index"] == 21]
        self.assertTrue(final)
        self.assertIn("TASK-A COMPLETE", final[0]["evidence"])

    def test_clock_model(self):
        run = self.analyze()
        c = run["clocks"]
        self.assertAlmostEqual(c["task_elapsed_wall_sec"], 533.628, places=3)
        # v0.2.2: the human wait is the boundary turn's OWN span (question emit ->
        # resume). This fixture carries no meta.createdAt, so the whole boundary
        # span is the UPPER BOUND: a2 span 53.628 s + a4 span 60.0 s = 113.628 s.
        self.assertAlmostEqual(c["interactive_user_wait_sec"], 113.628, places=3)
        self.assertTrue(c["interactive_user_wait_upper_bound"])
        self.assertEqual(c["unattributed_idle_wall_sec"], 0.0)
        self.assertAlmostEqual(c["agent_owned_wall_sec"], 420.0, places=3)
        self.assertEqual(len(c["human_loop_boundaries"]), 2)
        self.assertTrue(run["reconciliation"]["ok"])

    def test_result_not_keyword_inferred(self):
        # the transcript literally says "PROMOTION_READINESS = READY" but the
        # observer must not turn that into PASS.
        run = self.analyze()
        self.assertEqual(run["result"], "UNKNOWN")
        # ... unless the caller asserts it.
        run2 = self.analyze(explicit_result="PASS")
        self.assertEqual(run2["result"], "PASS")

    def test_unknown_is_zero_on_fixture(self):
        run = self.analyze()
        self.assertEqual(run["unknown_ratio"], 0.0)
        self.assertEqual(run["observability_quality"], "GREEN")


class TestLegacyFallback(unittest.TestCase):
    """Sessions without message.meta.source keep working, with explicit uncertainty."""

    def test_legacy_window_is_flagged_uncertain(self):
        import tempfile
        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "legacy.jsonl")

        rows = [
            {"type": "session", "version": 3, "id": "legacy", "timestamp": "2026-01-01T00:00:00.000Z", "cwd": "/p"},
            {"type": "message", "id": "p", "timestamp": "2026-01-01T00:00:05.000Z",
             "message": {"role": "user", "content": [{"type": "text", "text": "legacy task"}]}},
            {"type": "message", "id": "a", "timestamp": "2026-01-01T00:00:10.000Z",
             "message": {"role": "assistant", "content": [{"type": "text", "text": "done"}]}},
        ]
        with open(path, "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        run = core.analyze(path, run_id="L", project="p", prompt_contains="legacy")
        self.assertIn("lack message.meta.source", run["task_window"]["uncertainty"])


@unittest.skipUnless(os.path.exists(REAL_SESSION), "real hardening session JSONL not present")
class TestRealHardeningSessionRegression(unittest.TestCase):
    """Replay the real session: the truncated v0.2 window must be superseded."""

    @classmethod
    def setUpClass(cls):
        cls.result = core.analyze(REAL_SESSION, run_id="KEEPLAB-VERIFICATION-HARDENING-001-v021",
                               project="KeepLab", prompt_contains="Verification Harness Hardening v0.1")
        cls.spans = cls.result["_spans"]

    def test_window_now_extends_past_old_cutoff(self):
        tw = self.result["task_window"]
        self.assertEqual(tw["in_task_continuations"], 10)
        self.assertEqual(tw["excluded_independent_tasks"], 0)
        end = self.result["source"]["task_end_timestamp"]
        self.assertGreaterEqual(end, "2026-10-03T15:41:30.000Z")
        self.assertGreater(self.result["clocks"]["task_elapsed_wall_sec"], 5000)

    def test_final_completion_included(self):
        self.assertTrue(self.result["task_completion_detected"])
        self.assertTrue(self.result["task_completion"]["terminal_assistant_turn"])
        self.assertGreaterEqual(self.result["task_completion"]["final_assistant_row"], OLD_CUTOFF_ROW)

    def test_covers_device_smoke(self):
        smoke = [s for s in self.spans
                 if s["tool"] == "monitor_command" and "selftest_device" in (s["evidence"] or "")]
        self.assertGreaterEqual(len(smoke), 1)
        self.assertTrue(any(s["wait_tag"] == "WAIT_DEVICE" for s in smoke))

    def test_covers_both_hardening_fixes(self):
        # both bug-fix turns happened after the old 14:55 cutoff
        fixes = [s for s in self.spans
                 if s["row_index"] is not None and s["row_index"] > OLD_CUTOFF_ROW
                 and s["tool"] == "edit_file"]
        self.assertGreaterEqual(len(fixes), 2)

    def test_covers_final_doc_and_promotion_summary(self):
        final_doc = [s for s in self.spans if "FINAL-VERIFICATION-HARNESS-HARDENING" in (s["evidence"] or "")]
        self.assertGreaterEqual(len(final_doc), 1)
        completion = self.result["task_completion"]["evidence"]
        self.assertTrue(completion)

    def test_old_window_was_truncated(self):
        tr = self.result["tokens_raw"]
        # the v0.2 window reported 64 requests / 7,954,297 input tokens
        self.assertGreater(tr["requests"], 64)
        self.assertGreater(tr["input"], 7954297)

    def test_unknown_within_target(self):
        self.assertLessEqual(self.result["unknown_ratio"], 0.05)
        self.assertEqual(self.result["observability_quality"], "GREEN")


if __name__ == "__main__":
    unittest.main(verbosity=2)
