#!/usr/bin/env python3
"""Focused checks for the controlled Hermes launch wiring (no network, no sandbox run)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

BRIDGE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BRIDGE_DIR))

import contract_executor as ce  # noqa: E402


class ControlledLaunchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="controlled-launch-test-")
        self.root = Path(self.tmp.name)
        self.pkg = self.root / "pkg"
        self.pkg.mkdir()
        (self.pkg / "EXECUTOR-PROMPT.md").write_text("prompt", encoding="utf-8")
        self.sandbox = self.root / "sandbox"
        self.sandbox.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        self.sandbox.chmod(0o755)

    def tearDown(self):
        self.tmp.cleanup()

    def _registry(self, task_id="task-1", contract=None):
        path = self.root / "registry.json"
        path.write_text(json.dumps({
            task_id: {"contract_package": str(contract or self.pkg)}
        }), encoding="utf-8")
        return path

    def test_missing_task_id_rejected(self):
        registry = self._registry()
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(ce.CONTROLLED_TASK_ID_ENV, None)
            with self.assertRaises(ce.ControlledLaunchError) as ctx:
                ce.controlled_task_check(self.pkg, task_id=None,
                                         registry_path=str(registry),
                                         sandbox=str(self.sandbox),
                                         require_root=False)
        self.assertEqual(ctx.exception.code, "E_CONTROLLED_TASK_ID_MISSING")

    def test_missing_task_rejected(self):
        registry = self._registry(task_id="other-task")
        with self.assertRaises(ce.ControlledLaunchError) as ctx:
            ce.controlled_task_check(self.pkg, task_id="task-1",
                                     registry_path=str(registry),
                                     sandbox=str(self.sandbox),
                                     require_root=False)
        self.assertEqual(ctx.exception.code, "E_CONTROLLED_TASK_NOT_REGISTERED")

    def test_contract_mismatch_rejected(self):
        other = self.root / "other-pkg"
        other.mkdir()
        registry = self._registry(contract=other)
        with self.assertRaises(ce.ControlledLaunchError) as ctx:
            ce.controlled_task_check(self.pkg, task_id="task-1",
                                     registry_path=str(registry),
                                     sandbox=str(self.sandbox),
                                     require_root=False)
        self.assertEqual(ctx.exception.code, "E_CONTROLLED_TASK_CONTRACT_MISMATCH")

    def test_missing_sandbox_rejected(self):
        registry = self._registry()
        with self.assertRaises(ce.ControlledLaunchError) as ctx:
            ce.controlled_task_check(self.pkg, task_id="task-1",
                                     registry_path=str(registry),
                                     sandbox=str(self.root / "missing-sandbox"),
                                     require_root=False)
        self.assertEqual(ctx.exception.code, "E_CONTROLLED_SANDBOX_MISSING")

    def test_non_root_rejected(self):
        registry = self._registry()
        with mock.patch.object(ce.os, "geteuid", return_value=1000):
            with self.assertRaises(ce.ControlledLaunchError) as ctx:
                ce.controlled_task_check(self.pkg, task_id="task-1",
                                         registry_path=str(registry),
                                         sandbox=str(self.sandbox),
                                         require_root=True)
        self.assertEqual(ctx.exception.code, "E_CONTROLLED_LAUNCH_REQUIRES_ROOT")

    def test_argv_wraps_installed_sandbox(self):
        argv = ce.hermes_argv(self.pkg / "EXECUTOR-PROMPT.md",
                              task_id="task-1", sandbox=str(self.sandbox))
        self.assertEqual(argv[0], str(self.sandbox))
        self.assertEqual(argv[1:3], ["--task", "task-1"])
        self.assertEqual(argv[3], "--")
        self.assertEqual(argv[4], "hermes")
        self.assertEqual(argv[5:7], ["-p", "android-stack"])
        self.assertNotEqual(argv[0], "hermes")

    def test_execute_uses_sandbox_and_registered_task(self):
        registry = self._registry()
        captured = {}

        def runner(argv, **kwargs):
            captured["argv"] = argv
            captured["env"] = kwargs.get("env")
            return subprocess.CompletedProcess(argv, 0, "ok", "")

        with mock.patch.object(ce.os, "geteuid", return_value=0):
            result = ce.execute(str(self.pkg), self.pkg / "EXECUTOR-PROMPT.md", 5,
                                task_id="task-1", task_registry=str(registry),
                                sandbox=str(self.sandbox), runner=runner)
        self.assertEqual(result["outcome"], ce.O_SUCCESS)
        self.assertEqual(captured["argv"][0], str(self.sandbox))
        self.assertEqual(captured["argv"][1:3], ["--task", "task-1"])
        self.assertEqual(captured["argv"][3], "--")
        self.assertEqual(captured["argv"][4], "hermes")
        self.assertEqual(captured["env"]["HERMES_CONTRACT_PACKAGE"], str(self.pkg))

    def test_execute_non_root_blocks_without_runner(self):
        registry = self._registry()
        called = []
        with mock.patch.object(ce.os, "geteuid", return_value=1000):
            result = ce.execute(str(self.pkg), self.pkg / "EXECUTOR-PROMPT.md", 5,
                                task_id="task-1", task_registry=str(registry),
                                sandbox=str(self.sandbox),
                                runner=lambda *a, **k: called.append(a))
        self.assertEqual(result["outcome"], ce.O_BLOCKED)
        self.assertEqual(result["reason"], "E_CONTROLLED_LAUNCH_REQUIRES_ROOT")
        self.assertEqual(called, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
