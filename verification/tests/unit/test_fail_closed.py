#!/usr/bin/env python3
"""Fail-closed evidence gate regression tests (Verification Layer v1.0.1).

A run that requires a terminal oracle can NEVER be PASS without valid, complete evidence.
Absence of required evidence is a FAILURE, not a default success.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

VERIFY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(VERIFY / "core"))
import result_emit as re_mod  # noqa: E402
import schema  # noqa: E402


def make_plan(tmp: Path, **extra) -> Path:
    plan = {
        "verification_id": "GATE", "project": "P", "engine": "uiautomator",
        "android": {"package_name": "com.example.app", "apk": "/a.apk"},
        "journey": {"id": "J1", "test_class": "com.example.app.J1"},
        "measurement_class": "diagnostic", "excluded_from_baseline": True,
    }
    plan.update(extra)
    p = tmp / "plan.json"
    p.write_text(json.dumps(plan))
    return p


def make_run(tmp: Path, verify_part="__valid__") -> Path:
    run = tmp / "RUN"
    (run / "bench").mkdir(parents=True)
    (run / "executor.txt").write_text("OK (1 test)")
    (run / "logcat.txt").write_text("no crash")
    if verify_part == "__valid__":
        verify_part = {"journey": "J1", "outcome": "PASS",
                       "database": {"checked": True, "checks": [{"name": "c", "pass": True}]}}
    if verify_part is not None:
        (run / "bench/verify-part.json").write_text(
            verify_part if isinstance(verify_part, str) else json.dumps(verify_part))
    (run / "provenance.json").write_text(json.dumps(
        {"apk_sha256": "a" * 64, "test_apk_sha256": "b" * 64,
         "device_serial": "s", "device_model": "m", "device_api": "36"}))
    return run


def emit(run: Path, plan: Path, extra=None):
    cmd = [sys.executable, str(VERIFY / "core/result_emit.py"),
           "--plan", str(plan), "--run-dir", str(run), "--provenance", str(run / "provenance.json"),
           "--started-at", "2026-10-03T00:00:00Z", "--finished-at", "2026-10-03T00:00:05Z",
           "--total-ms", "5000", "--setup-ms", "1000"]
    cmd += extra or []
    r = subprocess.run(cmd, capture_output=True, text=True)
    result = json.loads((run / "verification-result.json").read_text())
    return r, result


class TestDefaultPolicy(unittest.TestCase):
    def test_uiautomator_requires_verify_part_by_default(self):
        plan = {"engine": "uiautomator", "journey": {"id": "J1"}}
        self.assertTrue(re_mod.require_verify_part(plan, "uiautomator"))

    def test_oracle_declaration_requires_verify_part(self):
        plan = {"engine": "maestro", "oracle": {"class": "X"}}
        self.assertTrue(re_mod.require_verify_part(plan, "maestro"))

    def test_explicit_opt_out(self):
        plan = {"engine": "uiautomator", "require_verify_part": False}
        self.assertFalse(re_mod.require_verify_part(plan, "uiautomator"))


class TestFailClosedGate(unittest.TestCase):
    def test_missing_verify_part_fails_closed(self):
        tmp = Path(tempfile.mkdtemp())
        run = make_run(tmp, verify_part=None)
        plan = make_plan(tmp)
        _, result = emit(run, plan)
        self.assertEqual(result["outcome"], "FAIL")
        self.assertEqual(result["checks"]["database"]["checked"], False)
        self.assertEqual(result["failure"]["marker"], re_mod.MISSING_EVIDENCE)
        self.assertEqual(schema.validate_result(result), [])
        # a mechanical failure bundle exists so no human inspection is needed
        self.assertTrue((run / "failure/failed-assertion.json").is_file())
        self.assertTrue((run / "failure/gate.json").is_file())

    def test_database_checked_false_fails(self):
        tmp = Path(tempfile.mkdtemp())
        run = make_run(tmp, verify_part={"journey": "J1", "outcome": "PASS",
                                         "database": {"checked": False}})
        plan = make_plan(tmp)
        _, result = emit(run, plan)
        self.assertEqual(result["outcome"], "FAIL")
        self.assertEqual(result["failure"]["marker"], re_mod.MISSING_EVIDENCE)

    def test_oracle_fail_propagates(self):
        tmp = Path(tempfile.mkdtemp())
        run = make_run(tmp, verify_part={"journey": "J1", "outcome": "FAIL",
                                         "database": {"checked": True,
                                                      "checks": [{"name": "c", "pass": False}]}})
        plan = make_plan(tmp)
        _, result = emit(run, plan)
        self.assertEqual(result["outcome"], "FAIL")
        self.assertEqual(result["failure"]["marker"], re_mod.ORACLE_FAIL)

    def test_malformed_verify_part_fails(self):
        tmp = Path(tempfile.mkdtemp())
        run = make_run(tmp, verify_part="{not json")
        plan = make_plan(tmp)
        _, result = emit(run, plan)
        self.assertEqual(result["outcome"], "FAIL")
        self.assertEqual(result["failure"]["marker"], re_mod.INVALID_EVIDENCE)

    def test_genuine_complete_evidence_passes(self):
        tmp = Path(tempfile.mkdtemp())
        run = make_run(tmp)
        plan = make_plan(tmp)
        r, result = emit(run, plan)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(result["outcome"], "PASS")
        self.assertEqual(result["checks"]["database"]["outcome"], "PASS")
        self.assertNotIn("failure", result)
        self.assertFalse((run / "failure/failed-assertion.json").exists())

    def test_explicit_opt_out_allows_pass_without_part(self):
        tmp = Path(tempfile.mkdtemp())
        run = make_run(tmp, verify_part=None)
        plan = make_plan(tmp, require_verify_part=False)
        _, result = emit(run, plan)
        self.assertEqual(result["outcome"], "PASS")

    def test_ui_failure_still_fails(self):
        tmp = Path(tempfile.mkdtemp())
        run = make_run(tmp)
        (run / "executor.txt").write_text("Tests run: 1, Failures: 1\nFAILURES!!!")
        plan = make_plan(tmp)
        _, result = emit(run, plan)
        self.assertEqual(result["outcome"], "FAIL")


if __name__ == "__main__":
    unittest.main(verbosity=2)
