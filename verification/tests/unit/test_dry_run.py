#!/usr/bin/env python3
"""Fixture integration test (no device): the runner dry-run produces a schema-valid result."""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

VERIFY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(VERIFY / "core"))
import schema  # noqa: E402


class TestDryRun(unittest.TestCase):
    def test_dry_run_schema_valid(self):
        d = Path(tempfile.mkdtemp())
        apk = d / "app-debug.apk"
        apk.write_text("SYNTHETIC-APK-CONTENT")
        sha = hashlib.sha256(apk.read_bytes()).hexdigest()
        plan = d / "plan.json"
        plan.write_text(json.dumps({
            "verification_id": "SYNTHETIC-DRY-RUN", "project": "Synthetic",
            "android": {"package_name": "com.example.synth", "apk": str(apk),
                        "expected_app_sha256": sha},
            "engine": "uiautomator",
            "journey": {"id": "J1", "test_class": "com.example.synth.J1JourneyTest"},
            "measurement_class": "diagnostic", "excluded_from_baseline": True,
            "evidence_policy": "failure-only",
        }))
        run_root = d / "runs"
        r = subprocess.run(["bash", str(VERIFY / "runner/run_verification.sh"),
                            str(plan), "--dry-run", "--run-root", str(run_root)],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        result = json.loads((run_root / "SYNTHETIC-DRY-RUN" / "verification-result.json").read_text())
        self.assertEqual(schema.validate_result(result), [])
        self.assertEqual(result["measurements"]["class"], "diagnostic")
        self.assertTrue(result["measurements"]["excluded_from_baseline"])

    def test_dry_run_rejects_bad_plan(self):
        d = Path(tempfile.mkdtemp())
        plan = d / "plan.json"
        plan.write_text(json.dumps({"verification_id": "X"}))
        r = subprocess.run(["bash", str(VERIFY / "runner/run_verification.sh"), str(plan), "--dry-run"],
                           capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("PLAN_VALID=false", r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
