#!/usr/bin/env python3
"""Exit-code integrity tests (Verification Layer v1.0.1).

A pipeline that ends in `tail` replaces the upstream exit status with tail's 0 and hides
build/test/verification failures. core/run_capture.sh preserves the real status.
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

VERIFY = Path(__file__).resolve().parents[2]
RUN_CAPTURE = VERIFY / "core/run_capture.sh"


class TestExitIntegrity(unittest.TestCase):
    def test_run_capture_returns_upstream_rc(self):
        log = Path(tempfile.mkdtemp()) / "cmd.log"
        r = subprocess.run(["bash", str(RUN_CAPTURE), str(log),
                            "bash", "-c", "echo hello; exit 7"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 7)
        self.assertIn("hello", log.read_text())

    def test_run_capture_preserves_zero(self):
        log = Path(tempfile.mkdtemp()) / "cmd.log"
        r = subprocess.run(["bash", str(RUN_CAPTURE), str(log),
                            "bash", "-c", "echo ok"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)

    def test_tail_pipeline_masks_exit_code(self):
        # Document the hazard the layer now forbids (no pipefail => tail owns the status).
        masked = subprocess.run(["bash", "-c", "false | tail -1"], capture_output=True, text=True)
        self.assertEqual(masked.returncode, 0)
        # pipefail restores the upstream status.
        piped = subprocess.run(["bash", "-c", "set -o pipefail; false | tail -1"],
                               capture_output=True, text=True)
        self.assertNotEqual(piped.returncode, 0)

    def test_layer_scripts_do_not_pipe_to_tail_the_primary_command(self):
        # A cheap static guard: no verification helper executes its PRIMARY command as
        # `cmd | tail` (the masking pattern). Parsing helpers may pipe inside $().
        offenders = []
        for sh in sorted((VERIFY / "android").glob("*.sh")) + sorted((VERIFY / "runner").glob("*.sh")) \
                + [VERIFY / "core/run_capture.sh"]:
            for line in sh.read_text().splitlines():
                s = line.strip()
                if s.startswith("#") or "|" not in s:
                    continue
                # flag only a bare command line whose last pipe stage is tail (not command subst)
                if s.endswith("| tail") or "| tail -" in s and not s.startswith(("echo", "printf", "layout_out=", "meta=")):
                    if s.startswith(("adb", "python3", "./gradlew", "bash ", "am ")):
                        offenders.append(f"{sh.name}: {s}")
        self.assertEqual(offenders, [], f"masking pipelines found: {offenders}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
