#!/usr/bin/env python3
"""result_emit.py contract tests: a synthetic run produces a schema-valid result."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

VERIFY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(VERIFY / "core"))
import schema  # noqa: E402


def make_run(tmp: Path, outcome_events=True) -> Path:
    run = tmp / "RUN"
    (run / "bench").mkdir(parents=True)
    (run / "executor.txt").write_text("OK (1 test)")
    (run / "logcat.txt").write_text("no crash here")
    (run / "bench/verify-part.json").write_text(json.dumps({
        "journey": "J1", "outcome": "PASS",
        "database": {"checked": True, "checks": [{"name": "c", "expected": "1", "actual": "1", "pass": True}]},
    }))
    if outcome_events:
        (run / "bench/events-J1.jsonl").write_text(
            "\n".join([
                json.dumps({"kind": "ACTION_START", "name": "launch", "elapsed_realtime_ns": 0}),
                json.dumps({"kind": "ACTION_END", "name": "launch", "elapsed_realtime_ns": 1_000_000}),
                json.dumps({"kind": "EVIDENCE_START", "name": "db-oracle", "elapsed_realtime_ns": 2_000_000}),
                json.dumps({"kind": "EVIDENCE_END", "name": "db-oracle", "elapsed_realtime_ns": 2_500_000}),
            ]))
    prov = run / "provenance.json"
    prov.write_text(json.dumps({"apk_sha256": "a" * 64, "test_apk_sha256": "b" * 64,
                                "device_serial": "s", "device_model": "m", "device_api": "36"}))
    return run


def make_plan(tmp: Path) -> Path:
    plan = tmp / "plan.json"
    plan.write_text(json.dumps({
        "verification_id": "V1", "project": "P", "engine": "uiautomator",
        "android": {"package_name": "com.example.app", "apk": "/a.apk"},
        "journey": {"id": "J1", "test_class": "com.example.app.J1"},
        "measurement_class": "diagnostic", "excluded_from_baseline": True,
    }))
    return plan


class TestResultEmit(unittest.TestCase):
    def _emit(self, run, plan, extra=None):
        cmd = [sys.executable, str(VERIFY / "core/result_emit.py"),
               "--plan", str(plan), "--run-dir", str(run), "--provenance", str(run / "provenance.json"),
               "--started-at", "2026-10-03T00:00:00Z", "--finished-at", "2026-10-03T00:00:05Z",
               "--total-ms", "5000", "--setup-ms", "1000"]
        if extra:
            cmd += extra
        return subprocess.run(cmd, capture_output=True, text=True)

    def test_pass_result_schema_valid(self):
        tmp = Path(tempfile.mkdtemp())
        run = make_run(tmp); plan = make_plan(tmp)
        r = self._emit(run, plan)
        self.assertEqual(r.returncode, 0, r.stderr)
        result = json.loads((run / "verification-result.json").read_text())
        self.assertEqual(schema.validate_result(result), [])
        self.assertEqual(result["outcome"], "PASS")
        self.assertEqual(result["measurements"]["t7a_ms"], 1.0)
        self.assertEqual(result["measurements"]["t7c_ms"], 0.5)

    def test_crash_scoped_to_app(self):
        tmp = Path(tempfile.mkdtemp())
        run = make_run(tmp); plan = make_plan(tmp)
        (run / "logcat.txt").write_text(
            "FATAL EXCEPTION: main\nProcess: com.example.app.other, PID: 1\n")
        r = self._emit(run, plan)
        self.assertEqual(r.returncode, 0, r.stderr)
        result = json.loads((run / "verification-result.json").read_text())
        # 'com.example.app.other' must NOT count as the app process
        self.assertFalse(result["checks"]["process"]["crashed"])

    def test_explicit_failure_stage(self):
        tmp = Path(tempfile.mkdtemp())
        run = make_run(tmp); plan = make_plan(tmp)
        r = self._emit(run, plan, ["--outcome", "FAIL", "--failed-stage", "journey",
                                   "--marker", "STAGE_FAIL=journey"])
        self.assertEqual(r.returncode, 0, r.stderr)
        result = json.loads((run / "verification-result.json").read_text())
        self.assertEqual(result["outcome"], "FAIL")
        self.assertEqual(result["failure"]["stage"], "journey")
        self.assertEqual(schema.validate_result(result), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
