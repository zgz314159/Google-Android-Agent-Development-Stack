#!/usr/bin/env python3
"""Focused checks for zhong -> narrow sudo wrapper -> installed sandbox wiring."""
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
        (self.pkg / "manifest.json").write_text('{"entries":[]}', encoding="utf-8")
        (self.pkg / "EXECUTOR-PROMPT.md").write_text("prompt", encoding="utf-8")
        self.wrapper = self.root / "run_registered_task"
        self.wrapper.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        self.wrapper.chmod(0o755)

    def tearDown(self):
        self.tmp.cleanup()

    def _registry(self, task_id="task-1", contract=None):
        path = self.root / "registry.json"
        path.write_text(json.dumps({
            task_id: {"contract_package": str(contract or self.pkg)}
        }), encoding="utf-8")
        return path

    def _manifest(self):
        return ce.manifest_sha256(self.pkg)

    def test_missing_task_id_rejected(self):
        registry = self._registry()
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(ce.CONTROLLED_TASK_ID_ENV, None)
            with self.assertRaises(ce.ControlledLaunchError) as ctx:
                ce.controlled_task_check(self.pkg, task_id=None,
                                         registry_path=str(registry),
                                         wrapper=str(self.wrapper),
                                         require_root_owner=False)
        self.assertEqual(ctx.exception.code, "E_CONTROLLED_TASK_ID_MISSING")

    def test_missing_task_rejected(self):
        registry = self._registry(task_id="other-task")
        with self.assertRaises(ce.ControlledLaunchError) as ctx:
            ce.controlled_task_check(self.pkg, task_id="task-1",
                                     registry_path=str(registry),
                                     wrapper=str(self.wrapper),
                                     require_root_owner=False)
        self.assertEqual(ctx.exception.code, "E_CONTROLLED_TASK_NOT_REGISTERED")

    def test_contract_mismatch_rejected(self):
        other = self.root / "other-pkg"
        other.mkdir()
        registry = self._registry(contract=other)
        with self.assertRaises(ce.ControlledLaunchError) as ctx:
            ce.controlled_task_check(self.pkg, task_id="task-1",
                                     registry_path=str(registry),
                                     wrapper=str(self.wrapper),
                                     require_root_owner=False)
        self.assertEqual(ctx.exception.code, "E_CONTROLLED_TASK_CONTRACT_MISMATCH")

    def test_missing_wrapper_rejected(self):
        registry = self._registry()
        with self.assertRaises(ce.ControlledLaunchError) as ctx:
            ce.controlled_task_check(self.pkg, task_id="task-1",
                                     registry_path=str(registry),
                                     wrapper=str(self.root / "missing-wrapper"),
                                     require_root_owner=False)
        self.assertEqual(ctx.exception.code, "E_CONTROLLED_WRAPPER_MISSING")

    def test_non_root_owned_wrapper_rejected(self):
        registry = self._registry()
        with self.assertRaises(ce.ControlledLaunchError) as ctx:
            ce.controlled_task_check(self.pkg, task_id="task-1",
                                     registry_path=str(registry),
                                     wrapper=str(self.wrapper),
                                     require_root_owner=True)
        self.assertEqual(ctx.exception.code, "E_CONTROLLED_WRAPPER_NOT_ROOT")

    def test_argv_uses_narrow_sudo_wrapper(self):
        argv = ce.hermes_argv(self.pkg / "EXECUTOR-PROMPT.md", task_id="task-1",
                              wrapper=str(self.wrapper),
                              manifest_sha256=self._manifest(),
                              require_root_owner=False)
        self.assertEqual(argv[:4], ["sudo", "-n", "--", str(self.wrapper)])
        self.assertEqual(argv[4:6], ["--task-id", "task-1"])
        self.assertEqual(argv[6:8], ["--prompt-file", str(self.pkg / "EXECUTOR-PROMPT.md")])
        self.assertEqual(argv[8:10], ["--expected-manifest-sha256", self._manifest()])

    def test_execute_uses_wrapper_and_manifest_hash(self):
        registry = self._registry()
        captured = {}

        def runner(argv, **kwargs):
            captured["argv"] = argv
            captured["env"] = kwargs.get("env")
            return subprocess.CompletedProcess(argv, 0, "ok", "")

        result = ce.execute(str(self.pkg), self.pkg / "EXECUTOR-PROMPT.md", 5,
                            task_id="task-1", task_registry=str(registry),
                            wrapper=str(self.wrapper),
                            require_root_owner=False, runner=runner)
        self.assertEqual(result["outcome"], ce.O_SUCCESS)
        self.assertEqual(captured["argv"][:4], ["sudo", "-n", "--", str(self.wrapper)])
        self.assertEqual(captured["argv"][4:6], ["--task-id", "task-1"])
        self.assertEqual(captured["argv"][8], "--expected-manifest-sha256")
        self.assertEqual(captured["argv"][9], self._manifest())
        self.assertEqual(captured["env"]["HERMES_CONTRACT_PACKAGE"], str(self.pkg))

    def test_execute_rejects_non_root_owned_wrapper_without_runner(self):
        registry = self._registry()
        called = []
        result = ce.execute(str(self.pkg), self.pkg / "EXECUTOR-PROMPT.md", 5,
                            task_id="task-1", task_registry=str(registry),
                            wrapper=str(self.wrapper), require_root_owner=True,
                            runner=lambda *a, **k: called.append(a))
        self.assertEqual(result["outcome"], ce.O_BLOCKED)
        self.assertEqual(result["reason"], "E_CONTROLLED_WRAPPER_NOT_ROOT")
        self.assertEqual(called, [])

    def test_execute_passes_supervisor_limits_and_outer_wait(self):
        registry = self._registry()
        captured = {}

        def runner(argv, **kwargs):
            captured["argv"] = argv
            captured["timeout"] = kwargs.get("timeout")
            return subprocess.CompletedProcess(argv, 0, "ok", "")

        result = ce.execute(str(self.pkg), self.pkg / "EXECUTOR-PROMPT.md", 5,
                            task_id="task-1", task_registry=str(registry),
                            wrapper=str(self.wrapper), require_root_owner=False,
                            runner=runner)
        self.assertEqual(result["outcome"], ce.O_SUCCESS)
        self.assertEqual(captured["argv"][-4:], [
            "--max-runtime", "5", "--grace", str(ce.WRAPPER_GRACE_S)])
        self.assertEqual(captured["timeout"],
                         5 + ce.WRAPPER_GRACE_S + ce.WRAPPER_SLACK_S)

    def test_execute_timeout_reports_cleanup_unconfirmed(self):
        registry = self._registry()

        def runner(argv, **kwargs):
            raise subprocess.TimeoutExpired(argv, kwargs.get("timeout"))

        result = ce.execute(str(self.pkg), self.pkg / "EXECUTOR-PROMPT.md", 5,
                            task_id="task-1", task_registry=str(registry),
                            wrapper=str(self.wrapper), require_root_owner=False,
                            runner=runner)
        self.assertEqual(result["outcome"], ce.O_BLOCKED)
        self.assertEqual(result["exit_code"], 125)
        self.assertIn("cleanup not confirmed", result["stderr_tail"])

    def test_execute_supervisor_timeout_codes_are_blocked(self):
        registry = self._registry()
        for code in (124, 125):
            def runner(argv, **kwargs):
                return subprocess.CompletedProcess(argv, code, "", "AEGL_TASK_CLEANUP")

            result = ce.execute(str(self.pkg), self.pkg / "EXECUTOR-PROMPT.md", 5,
                                task_id="task-1", task_registry=str(registry),
                                wrapper=str(self.wrapper), require_root_owner=False,
                                runner=runner)
            self.assertEqual(result["outcome"], ce.O_BLOCKED)
            self.assertEqual(result["exit_code"], code)
            self.assertIn("AEGL_TASK_CLEANUP", result["stderr_tail"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
