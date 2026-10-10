#!/usr/bin/env python3
"""Evaluation adapter tests for adapters/evaluation/verification_adapter.py.

Proves the Verification Layer hands the Evaluation Layer a T7-attributable, null-honest
document without touching the Evaluation Core.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

VERIFY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(VERIFY / "adapters/evaluation"))
import verification_adapter as adapter  # noqa: E402

SAMPLE = {
    "verification_id": "V1", "project": "P", "engine": "uiautomator", "journey": "J1",
    "outcome": "PASS", "app_apk_sha256": "a" * 64, "test_apk_sha256": "b" * 64,
    "verification_layer_version": "1.0.0", "runner_version": "r",
    "device": {"serial": "s", "model": "m", "api": "36"},
    "measurements": {"class": "diagnostic", "excluded_from_baseline": True,
                     "setup_wall_ms": 1, "total_wall_ms": 2, "t7a_ms": 1.0, "t7b_ms": 2.0, "t7c_ms": 0.5},
    "checks": {"ui": {"evidence": "uiautomator", "reachable": True},
               "database": {"checked": True, "outcome": "PASS", "checks": []},
               "process": {"crashed": False, "executor_ok": True, "evidence": "no-crash"},
               "visual": {"mode": "failure-only", "screenshots": 0}},
    "evidence": {"policy": "failure-only", "bundle": None, "complete": None},
}


class TestAdapter(unittest.TestCase):
    def test_normalize_shape(self):
        n = adapter.normalize(SAMPLE)
        self.assertEqual(n["verification_id"], "V1")
        self.assertEqual(n["phases"]["T7"]["T7a_deploy_ms"], 1.0)
        self.assertEqual(n["phases"]["T7"]["T7c_evidence_state_ms"], 0.5)
        self.assertEqual(n["provenance"]["T7b"], "verification-events")

    def test_null_honesty(self):
        c = dict(SAMPLE, engine="maestro")
        c["measurements"] = dict(SAMPLE["measurements"], t7a_ms=None, t7b_ms=None, t7c_ms=1.0)
        n = adapter.normalize(c)
        self.assertIsNone(n["phases"]["T7"]["T7a_deploy_ms"])
        self.assertEqual(n["provenance"]["T7a"], "NOT_AVAILABLE")
        self.assertEqual(n["provenance"]["T7c"], "verification-events")

    def test_cli_writes_document(self):
        d = Path(tempfile.mkdtemp())
        res = d / "verification-result.json"; res.write_text(json.dumps(SAMPLE))
        out = d / "handoff.json"
        rc = subprocess.run([sys.executable, str(VERIFY / "adapters/evaluation/verification_adapter.py"),
                             "--result", str(res), "--output", str(out)],
                            capture_output=True, text=True).returncode
        self.assertEqual(rc, 0)
        doc = json.loads(out.read_text())
        self.assertEqual(doc["verification"]["journey"], "J1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
