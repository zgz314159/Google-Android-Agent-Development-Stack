#!/usr/bin/env python3
"""Non-model tests for the root wrapper's runtime supervisor (TERM/grace/KILL)."""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

BRIDGE_DIR = Path(__file__).resolve().parent.parent
WRAPPER = BRIDGE_DIR / "run_registered_task"
sys.path.insert(0, str(BRIDGE_DIR))
import contract_executor as ce  # noqa: E402


def supervisor_function() -> str:
    text = WRAPPER.read_text(encoding="utf-8")
    start = text.index("# SUPERVISE_START") + len("# SUPERVISE_START")
    end = text.index("# SUPERVISE_END")
    return text[start:end]


class RuntimeSupervisorTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="runtime-supervisor-test-")
        self.dir = Path(self.tmp.name)
        self.harness = self.dir / "harness.sh"
        self.harness.write_text(
            "#!/usr/bin/env bash\n"
            "set -u\n"
            "TASK_ID=test-task\n"
            "SUPERVISED_PGID=\"\"\n"
            "SUPERVISE_GRACE=0\n"
            + supervisor_function()
            + "\nset +e\n"
            "supervise \"$@\"\n"
            "rc=$?\n"
            "set -e\n"
            "echo \"SUPERVISE_RC=$rc\"\n"
            "exit \"$rc\"\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, max_runtime, grace, command, timeout=20, env=None):
        started = time.monotonic()
        proc = subprocess.run(
            ["bash", str(self.harness), str(max_runtime), str(grace), *command],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return proc, time.monotonic() - started

    def _markers(self, proc):
        return ce._wrapper_markers(
            proc.stderr, task_id="test-task", exit_code=proc.returncode
        )

    def _assert_no_group(self, proc):
        match = re.search(r"pgid=(\d+)", proc.stderr)
        if match:
            leftover = subprocess.run(
                ["pgrep", "-g", match.group(1)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(leftover.returncode, 1, leftover.stdout)

    def test_normal_exit_returns_zero(self):
        proc, elapsed = self._run(5, 1, ["/bin/sh", "-c", "sleep 0.2"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("SUPERVISE_RC=0", proc.stdout)
        self.assertIn("AEGL_TASK_CLEANUP=CONFIRMED", proc.stderr)
        self.assertEqual(self._markers(proc)["cleanup"], "CONFIRMED")
        self.assertLess(elapsed, 5)

    def test_normal_nonzero_exit_preserves_rc_and_confirms_cleanup(self):
        proc, _ = self._run(5, 1, ["/bin/sh", "-c", "exit 7"])
        self.assertEqual(proc.returncode, 7, proc.stderr)
        self.assertIn("SUPERVISE_RC=7", proc.stdout)
        self.assertIn("AEGL_TASK_CLEANUP=CONFIRMED", proc.stderr)
        markers = self._markers(proc)
        self.assertEqual(markers["cleanup"], "CONFIRMED")
        self.assertFalse(markers["timed_out"])

    def test_probe_error_is_not_confirmed(self):
        stub = self.dir / "pgrep"
        stub.write_text("#!/bin/sh\nexit 2\n", encoding="utf-8")
        stub.chmod(0o755)
        env = dict(os.environ)
        env["PATH"] = str(self.dir) + os.pathsep + env.get("PATH", "")
        proc, _ = self._run(5, 1, ["/bin/sh", "-c", "sleep 0.2"], env=env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("AEGL_TASK_CLEANUP=UNCONFIRMED", proc.stderr)
        self.assertNotIn("AEGL_TASK_CLEANUP=CONFIRMED", proc.stderr)
        self.assertEqual(self._markers(proc)["cleanup"], "UNCONFIRMED")

    def test_timeout_cleanup_returns_124(self):
        proc, elapsed = self._run(1, 1, ["/bin/sh", "-c", "sleep 10"])
        self.assertEqual(proc.returncode, 124, proc.stderr)
        self.assertIn("AEGL_TASK_CLEANUP=CONFIRMED", proc.stderr)
        self.assertLess(elapsed, 10)
        self._assert_no_group(proc)

    def test_ignore_term_child_is_killed(self):
        proc, elapsed = self._run(
            1, 1, ["/bin/sh", "-c", "trap '' TERM; while :; do sleep 0.2; done"]
        )
        self.assertEqual(proc.returncode, 124, proc.stderr)
        self.assertIn("phase=TERM", proc.stderr)
        self.assertIn("phase=KILL", proc.stderr)
        self.assertIn("AEGL_TASK_CLEANUP=CONFIRMED", proc.stderr)
        self.assertLess(elapsed, 10)
        self._assert_no_group(proc)

    def test_lingering_child_after_parent_exit_is_reaped(self):
        proc, elapsed = self._run(5, 1, ["/bin/sh", "-c", "sleep 10 & exit 0"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("AEGL_TASK_CHILDREN_LINGER", proc.stderr)
        self.assertIn("AEGL_TASK_CLEANUP=CONFIRMED", proc.stderr)
        self.assertEqual(self._markers(proc)["cleanup"], "CONFIRMED")
        self.assertLess(elapsed, 10)
        self._assert_no_group(proc)


if __name__ == "__main__":
    unittest.main(verbosity=2)
