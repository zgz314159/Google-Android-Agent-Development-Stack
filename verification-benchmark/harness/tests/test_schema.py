#!/usr/bin/env python3
"""Schema/enum validation tests for harness/schema.py."""
import sys
import unittest
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HARNESS))
import schema  # noqa: E402


def valid_run(**overrides) -> dict:
    run = {
        "engine": "B", "journey": "J1", "iteration": 1, "run_id": "J1-B-1",
        "outcome": "PASS",
        "apk_sha256": "a" * 64,
        "git_commit": "NO_GIT", "device_serial": "87296ada",
        "device_model": "Redmi Note 7 Pro", "api": "36",
        "setup_wall_ms": 1000, "t7a_ms": 1.0, "t7b_ms": 2.0, "t7c_ms": 0.5,
        "total_wall_ms": 2000,
        "model_requests": 0, "input_tokens": 0, "output_tokens": 0,
        "assertions": 4, "screenshots": 0, "layout_dumps": 0,
        "retries": 0, "human_interventions": 0,
        "ui_evidence": "uiautomator", "database_evidence": "PASS",
        "process_evidence": "no-crash", "visual_evidence": "failure-only",
        "spans": [], "launch_test": "com.keeplab.app.benchmark.J1JourneyTest",
    }
    run.update(overrides)
    return run


class TestSchema(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(schema.validate_benchmark_run(valid_run()), [])

    def test_engine_c_nulls_allowed(self):
        r = valid_run(engine="C", ui_evidence="maestro", t7a_ms=None, t7b_ms=None)
        self.assertEqual(schema.validate_benchmark_run(r), [])

    def test_api_must_be_string(self):
        errs = schema.validate_benchmark_run(valid_run(api=36))
        self.assertTrue(any("api must be a string" in e for e in errs))

    def test_bad_outcome(self):
        errs = schema.validate_benchmark_run(valid_run(outcome="OK"))
        self.assertTrue(any("outcome" in e for e in errs))

    def test_bad_process_evidence(self):
        errs = schema.validate_benchmark_run(valid_run(process_evidence="MAYBE"))
        self.assertTrue(any("process_evidence" in e for e in errs))

    def test_bad_ui_evidence(self):
        errs = schema.validate_benchmark_run(valid_run(ui_evidence="robot"))
        self.assertTrue(any("ui_evidence" in e for e in errs))

    def test_unknown_measurement_class_fails(self):
        errs = schema.validate_benchmark_run(valid_run(measurement_class="warm-up"))
        self.assertTrue(any("measurement_class" in e for e in errs))

    def test_known_measurement_class_ok(self):
        for c in schema.MEASUREMENT_CLASSES:
            self.assertEqual(
                schema.validate_benchmark_run(valid_run(measurement_class=c)), [],
                f"class {c} should validate")

    def test_missing_required(self):
        r = valid_run()
        del r["total_wall_ms"]
        errs = schema.validate_benchmark_run(r)
        self.assertTrue(any("missing required field: total_wall_ms" in e for e in errs))

    def test_excluded_from_baseline_bool(self):
        self.assertEqual(
            schema.validate_benchmark_run(valid_run(excluded_from_baseline=True)), [])
        errs = schema.validate_benchmark_run(valid_run(excluded_from_baseline="yes"))
        self.assertTrue(any("excluded_from_baseline" in e for e in errs))

    def test_span_shape(self):
        errs = schema.validate_benchmark_run(valid_run(spans=[{"kind": "ACTION"}]))
        self.assertTrue(any("spans[0]" in e for e in errs))


if __name__ == "__main__":
    unittest.main(verbosity=2)
