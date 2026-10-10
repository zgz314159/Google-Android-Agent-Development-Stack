#!/usr/bin/env python3
"""Measurement classification / deny-by-default tests for measure.py.

Verifies that the aggregator is allowlist-driven: runs absent from the manifest are excluded
as diagnostic (deny-by-default), warmups are excluded, and the HARDEN-* self-test runs can
never enter the measured set.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HARNESS))
import measure  # noqa: E402

CLASSES = ["measured", "control", "warmup", "diagnostic", "failed-pre-fix"]


def write_run(results: Path, run_id: str, engine: str, journey: str):
    d = results / run_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "benchmark-run.json").write_text(json.dumps({
        "run_id": run_id, "engine": engine, "journey": journey, "outcome": "PASS",
        "total_wall_ms": 1000, "setup_wall_ms": 10, "t7a_ms": 1.0, "t7b_ms": 2.0,
        "t7c_ms": 0.5, "assertions": 1, "screenshots": 0, "layout_dumps": 0,
        "retries": 0, "human_interventions": 0, "model_requests": 0,
    }))


class TestClassification(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.results = self.tmp / "results"
        self.results.mkdir()
        write_run(self.results, "T1-B-1", "B", "J1")
        write_run(self.results, "A-J1", "A", "J1")
        write_run(self.results, "HARDEN-B-J1-1", "B", "J1")
        write_run(self.results, "J1-B-WARMUP", "B", "J1")
        manifest = {
            "version": "1.0", "classes": CLASSES,
            "runs": [
                {"run_id": "T1-B-1", "engine": "B", "journey": "J1", "iteration": 1,
                 "measurement_class": "measured", "excluded_from_baseline": False,
                 "exclusion_reason": None},
                {"run_id": "A-J1", "engine": "A", "journey": "J1", "iteration": 1,
                 "measurement_class": "control", "excluded_from_baseline": False,
                 "exclusion_reason": None},
                {"run_id": "J1-B-WARMUP", "engine": None, "journey": None, "iteration": None,
                 "measurement_class": "warmup", "excluded_from_baseline": True,
                 "exclusion_reason": "discarded warm-up"},
            ],
        }
        (self.results / "baseline-manifest.json").write_text(json.dumps(manifest))
        self._orig = (measure.RESULTS, measure.MANIFEST)
        measure.RESULTS = self.results
        measure.MANIFEST = self.results / "baseline-manifest.json"

    def tearDown(self):
        measure.RESULTS, measure.MANIFEST = self._orig

    def test_deny_by_default(self):
        included, excluded = measure.load_runs()
        ids = {r["run_id"] for r in included}
        self.assertEqual(ids, {"T1-B-1", "A-J1"})
        ex = {e["run_id"]: e for e in excluded}
        self.assertIn("HARDEN-B-J1-1", ex)
        self.assertEqual(ex["HARDEN-B-J1-1"]["measurement_class"], "diagnostic")
        self.assertIn("deny by default", ex["HARDEN-B-J1-1"]["reason"])
        self.assertIn("J1-B-WARMUP", ex)

    def test_measured_control_separation(self):
        included, _ = measure.load_runs()
        measured = [r for r in included if r["measurement_class"] == "measured"]
        control = [r for r in included if r["measurement_class"] == "control"]
        self.assertEqual([r["run_id"] for r in measured], ["T1-B-1"])
        self.assertEqual([r["run_id"] for r in control], ["A-J1"])

    def test_harden_never_measured(self):
        included, _ = measure.load_runs()
        self.assertFalse(any(r["run_id"].startswith("HARDEN") and
                             r["measurement_class"] == "measured" for r in included))

    def test_reduction_pct(self):
        self.assertEqual(measure.reduction_pct(100.0, 3.4), 96.6)
        self.assertEqual(measure.reduction_pct(100.0, 10.6), 89.4)
        self.assertIsNone(measure.reduction_pct(None, 1.0))
        self.assertIsNone(measure.reduction_pct(0, 1.0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
