#!/usr/bin/env python3
"""Evaluation-Core external adapter tests (P1 #14).

The adapter is an add-on that only reads harness artifacts; these tests assert its shape and
its null-honesty, and that a corrected `process_evidence` flows through unchanged.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
DAG_ROOT = HARNESS.parent.parent
ADAPTER_DIR = DAG_ROOT / "evaluation" / "commandcode"
sys.path.insert(0, str(ADAPTER_DIR))
import external_adapter as adapter  # noqa: E402


SAMPLE = {
    "run_id": "J1-B-1", "engine": "B", "journey": "J1", "iteration": 1, "outcome": "PASS",
    "apk_sha256": "a" * 64, "git_commit": "NO_GIT", "device_serial": "87296ada",
    "device_model": "Redmi Note 7 Pro", "api": "36",
    "setup_wall_ms": 1000, "total_wall_ms": 2000, "t7a_ms": 1.0, "t7b_ms": 2.0, "t7c_ms": 0.5,
    "model_requests": 0, "input_tokens": 0, "output_tokens": 0,
    "ui_evidence": "uiautomator", "database_evidence": "PASS",
    "process_evidence": "no-crash", "visual_evidence": "failure-only",
    "screenshots": 0, "layout_dumps": 0, "human_interventions": 0,
}


class TestAdapter(unittest.TestCase):
    def test_normalize_shape(self):
        n = adapter.normalize(SAMPLE)
        self.assertEqual(n["run_id"], "J1-B-1")
        self.assertEqual(n["identity"]["apk_sha256"], "a" * 64)
        self.assertEqual(n["phases"]["T7"]["T7b_ui_driving_ms"], 2.0)
        self.assertEqual(n["provenance"]["T7b"], "harness-monotonic-events")

    def test_null_honesty_engine_c(self):
        c = dict(SAMPLE, engine="C", ui_evidence="maestro", t7a_ms=None, t7b_ms=None, t7c_ms=1.0)
        n = adapter.normalize(c)
        self.assertIsNone(n["phases"]["T7"]["T7a_deploy_ms"])
        self.assertEqual(n["provenance"]["T7a"], "NOT_AVAILABLE")
        self.assertEqual(n["provenance"]["T7c"], "harness-monotonic-events")

    def test_corrected_process_evidence_flows(self):
        corr = dict(SAMPLE, process_evidence="no-crash", process_evidence_raw="CRASH")
        n = adapter.normalize(corr)
        self.assertEqual(n["evidence"]["process"], "no-crash")

    def test_load_runs_skips_warmup_and_test(self):
        tmp = Path(tempfile.mkdtemp())
        for rid in ("J1-B-1", "J1-B-WARMUP", "FAILTEST-B"):
            d = tmp / rid
            d.mkdir()
            (d / "benchmark-run.json").write_text(json.dumps(dict(SAMPLE, run_id=rid)))
        runs = adapter.load_runs(tmp)
        self.assertEqual([r["run_id"] for r in runs], ["J1-B-1"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
