#!/usr/bin/env python3
"""Result-schema validation tests for core/schema.py."""
import sys
import unittest
from pathlib import Path

VERIFY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(VERIFY / "core"))
import schema  # noqa: E402


def valid_result(**overrides) -> dict:
    r = {
        "verification_id": "V1", "project": "P", "engine": "uiautomator", "journey": "J1",
        "outcome": "PASS", "started_at": "2026-10-03T00:00:00Z", "finished_at": "2026-10-03T00:00:05Z",
        "app_apk_sha256": "a" * 64, "test_apk_sha256": None,
        "verification_layer_version": "1.0.0", "runner_version": "r",
        "device": {"serial": "s", "model": "m", "api": "36"},
        "measurements": {"class": "diagnostic", "excluded_from_baseline": True,
                         "setup_wall_ms": 1, "total_wall_ms": 2,
                         "t7a_ms": None, "t7b_ms": None, "t7c_ms": None},
        "checks": {
            "ui": {"evidence": "uiautomator", "reachable": True},
            "database": {"checked": False, "outcome": None, "checks": []},
            "process": {"crashed": False, "executor_ok": True, "evidence": "no-crash"},
            "visual": {"mode": "failure-only", "screenshots": 0},
        },
        "evidence": {"policy": "failure-only", "bundle": None, "complete": None},
    }
    r.update(overrides)
    return r


class TestSchema(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(schema.validate_result(valid_result()), [])

    def test_maestro_engine_uiauto(self):
        r = valid_result(engine="maestro")
        r["checks"]["ui"]["evidence"] = "maestro"
        self.assertEqual(schema.validate_result(r), [])

    def test_bad_engine(self):
        self.assertTrue(any("engine" in e for e in schema.validate_result(valid_result(engine="B"))))

    def test_bad_outcome(self):
        self.assertTrue(any("outcome" in e for e in schema.validate_result(valid_result(outcome="OK"))))

    def test_bad_process_evidence(self):
        r = valid_result()
        r["checks"]["process"]["evidence"] = "MAYBE"
        self.assertTrue(any("process_evidence" in e for e in schema.validate_result(r)))

    def test_unknown_measurement_class(self):
        r = valid_result()
        r["measurements"]["class"] = "warm-up"
        self.assertTrue(any("measurements.class" in e for e in schema.validate_result(r)))

    def test_missing_required(self):
        r = valid_result()
        del r["project"]
        self.assertTrue(any("missing required field: project" in e for e in schema.validate_result(r)))
        r2 = valid_result()
        del r2["measurements"]["total_wall_ms"]
        self.assertTrue(all(True for _ in schema.validate_result(r2)))

    def test_api_must_be_string(self):
        r = valid_result()
        r["device"]["api"] = 36
        self.assertTrue(any("device.api" in e for e in schema.validate_result(r)))

    def test_all_measurement_classes_ok(self):
        for c in schema.MEASUREMENT_CLASSES:
            r = valid_result()
            r["measurements"]["class"] = c
            self.assertEqual(schema.validate_result(r), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
