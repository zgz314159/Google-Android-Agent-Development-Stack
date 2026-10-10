#!/usr/bin/env python3
"""Verification-plan contract tests for core/plan_validate.py."""
import sys
import unittest
from pathlib import Path

VERIFY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(VERIFY / "core"))
import plan_validate  # noqa: E402


def valid_plan(**overrides) -> dict:
    p = {
        "verification_id": "V1", "project": "P", "engine": "uiautomator",
        "android": {"package_name": "com.example.app", "apk": "/a.apk"},
        "journey": {"id": "J1", "test_class": "com.example.app.J1"},
    }
    p.update(overrides)
    return p


class TestPlanValidate(unittest.TestCase):
    def test_valid_minimal(self):
        self.assertEqual(plan_validate.validate_plan(valid_plan()), [])

    def test_missing_required(self):
        p = valid_plan()
        del p["journey"]
        self.assertTrue(any("journey" in e for e in plan_validate.validate_plan(p)))

    def test_bad_engine(self):
        self.assertTrue(any("engine" in e for e in plan_validate.validate_plan(valid_plan(engine="B"))))

    def test_sha_pattern(self):
        p = valid_plan()
        p["android"]["expected_app_sha256"] = "xyz"
        self.assertTrue(any("sha256" in e for e in plan_validate.validate_plan(p)))

    def test_sha_valid(self):
        p = valid_plan()
        p["android"]["expected_app_sha256"] = "a" * 64
        self.assertEqual(plan_validate.validate_plan(p), [])

    def test_maestro_requires_flow(self):
        p = valid_plan(engine="maestro")
        self.assertTrue(any("journey.flow" in e for e in plan_validate.validate_plan(p)))
        p["journey"]["flow"] = "/x.yaml"
        self.assertEqual(plan_validate.validate_plan(p), [])

    def test_timeouts(self):
        p = valid_plan()
        p["timeouts"] = {"preflight": 30, "bogus": 5}
        self.assertTrue(any("bogus" in e for e in plan_validate.validate_plan(p)))
        p["timeouts"] = {"preflight": 0}
        self.assertTrue(any("positive integer" in e for e in plan_validate.validate_plan(p)))

    def test_measurement_class(self):
        p = valid_plan(measurement_class="diagnostic")
        self.assertEqual(plan_validate.validate_plan(p), [])
        p["measurement_class"] = "nope"
        self.assertTrue(any("measurement_class" in e for e in plan_validate.validate_plan(p)))

    def test_oracle_expected_outcome(self):
        p = valid_plan()
        p["oracle"] = {"class": "X", "expected_outcome": "MAYBE"}
        self.assertTrue(any("expected_outcome" in e for e in plan_validate.validate_plan(p)))

    def test_example_keeplab_plan_is_valid(self):
        example = VERIFY / "examples/keeplab/verification-plan.json"
        self.assertEqual(plan_validate.validate_plan(plan_validate.load_plan(example)), [])
        example_m = VERIFY / "examples/keeplab/verification-plan.maestro.json"
        self.assertEqual(plan_validate.validate_plan(plan_validate.load_plan(example_m)), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
