#!/usr/bin/env python3
"""Crash-attribution + span-parsing tests for emit_run.py.

Regression guard for the audit finding where a FATAL from the harness-side
`com.android.cli.interact.instrumentation` was misattributed to KeepLab.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HARNESS))
import emit_run  # noqa: E402


class TestCrashAttribution(unittest.TestCase):
    def test_case1_app_process_fatal_is_crash(self):
        logcat = (
            "10-03 20:00:00.000 E AndroidRuntime: FATAL EXCEPTION: main\n"
            "10-03 20:00:00.001 E AndroidRuntime: Process: com.keeplab.app, PID: 1234\n"
            "10-03 20:00:00.002 E AndroidRuntime: java.lang.RuntimeException: boom\n"
        )
        self.assertTrue(emit_run.detect_app_crash(logcat))
        self.assertEqual(emit_run.detect_process_evidence(logcat)[0], "CRASH")

    def test_case2_instrumentation_fatal_is_not_app_crash(self):
        logcat = (
            "10-03 20:00:00.000 E AndroidRuntime: FATAL EXCEPTION: Thread-2\n"
            "10-03 20:00:00.001 E AndroidRuntime: Process: com.android.cli.interact.instrumentation, PID: 31929\n"
            "10-03 20:00:00.002 E AndroidRuntime: at com.android.cli.interact.instrumentation.InstrumentationServer.finish\n"
        )
        self.assertFalse(emit_run.detect_app_crash(logcat))
        self.assertEqual(emit_run.detect_process_evidence(logcat)[0], "no-crash")
        # raw signal still recorded for traceability
        self.assertEqual(emit_run.detect_process_evidence(logcat)[1], "CRASH")

    def test_case3_anr_in_app_is_crash(self):
        logcat = "10-03 20:00:00.000 W ActivityManager: ANR in com.keeplab.app\n"
        self.assertTrue(emit_run.detect_app_crash(logcat))
        self.assertEqual(emit_run.detect_process_evidence(logcat)[0], "CRASH")

    def test_case4_unrelated_system_fatal_is_not_app_crash(self):
        logcat = (
            "10-03 20:00:00.000 E AndroidRuntime: FATAL EXCEPTION: main\n"
            "10-03 20:00:00.001 E AndroidRuntime: Process: com.android.systemui, PID: 991\n"
        )
        self.assertFalse(emit_run.detect_app_crash(logcat))
        self.assertEqual(emit_run.detect_process_evidence(logcat)[0], "no-crash")

    def test_test_process_fatal_is_not_app_crash(self):
        logcat = (
            "10-03 20:00:00.000 E AndroidRuntime: FATAL EXCEPTION: main\n"
            "10-03 20:00:00.001 E AndroidRuntime: Process: com.keeplab.app.test, PID: 77\n"
        )
        self.assertFalse(emit_run.detect_app_crash(logcat))

    def test_anr_in_test_process_is_not_app_crash(self):
        logcat = "ANR in com.keeplab.app.test\n"
        self.assertFalse(emit_run.detect_app_crash(logcat))


class TestExecutorOk(unittest.TestCase):
    def test_ok_single_test(self):
        self.assertTrue(emit_run.executor_ok("...\nOK (1 test)\n"))

    def test_ok_multiple_tests(self):
        self.assertTrue(emit_run.executor_ok("OK (3 tests)"))

    def test_not_ok(self):
        self.assertFalse(emit_run.executor_ok("Tests run: 1, Failures: 0"))
        self.assertFalse(emit_run.executor_ok(""))


class TestParseSpans(unittest.TestCase):
    def test_pairs_start_end(self):
        d = Path(tempfile.mkdtemp())
        f = d / "events-R.jsonl"
        rows = [
            {"kind": "ACTION_START", "name": "launch", "elapsed_realtime_ns": 1_000_000_000},
            {"kind": "ACTION_END", "name": "launch", "elapsed_realtime_ns": 1_002_000_000},
            {"kind": "EVIDENCE_START", "name": "db-oracle", "elapsed_realtime_ns": 2_000_000_000},
            {"kind": "EVIDENCE_END", "name": "db-oracle", "elapsed_realtime_ns": 2_000_500_000},
        ]
        f.write_text("\n".join(json.dumps(r) for r in rows))
        spans = emit_run.parse_spans(f)
        by_name = {s["name"]: s for s in spans}
        self.assertEqual(by_name["launch"]["ms"], 2.0)
        self.assertEqual(by_name["db-oracle"]["ms"], 0.5)

    def test_missing_file_is_empty(self):
        self.assertEqual(emit_run.parse_spans(Path("/nonexistent/nope.jsonl")), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
