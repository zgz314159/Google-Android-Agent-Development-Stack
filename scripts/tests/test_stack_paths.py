#!/usr/bin/env python3
"""Tests for the canonical filesystem path contract (scripts/lib/stack_paths.py)."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "lib"))
import stack_paths  # noqa: E402

ROOT_ENV = ["ANDROID_AGENT_STACK_ROOT", "ANDROID_AGENT_STACK_STATE_ROOT",
            "ANDROID_AGENT_STACK_DATA_ROOT", "ANDROID_AGENT_STACK_CACHE_ROOT",
            "ANDROID_AGENT_STACK_CONFIG_ROOT", "XDG_STATE_HOME", "XDG_DATA_HOME",
            "XDG_CACHE_HOME", "XDG_CONFIG_HOME", "HERMES_HOME"]


class ContractBase(unittest.TestCase):
    def setUp(self):
        self._saved = {k: os.environ.get(k) for k in ROOT_ENV}
        for k in ROOT_ENV:
            os.environ.pop(k, None)

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


class TestDefaults(ContractBase):
    def test_project_root_is_this_checkout(self):
        self.assertEqual(stack_paths.project_root(), REPO)

    def test_roots_are_xdg_shaped_and_outside_project(self):
        for name in ("STACK_STATE_ROOT", "STACK_DATA_ROOT", "STACK_CACHE_ROOT", "STACK_CONFIG_ROOT"):
            path = stack_paths.resolve(name)
            self.assertTrue(str(path).endswith("google-android-agent-stack"), name)
            self.assertFalse(str(path).startswith(str(REPO) + os.sep), name)

    def test_no_hard_coded_username(self):
        # The resolver must not embed any literal home path; roots derive from $HOME / XDG vars.
        source = (REPO / "scripts" / "lib" / "stack_paths.py").read_text(encoding="utf-8")
        self.assertNotIn("/home/", source)
        self.assertNotIn("/mnt/AndroidDev", source)

    def test_evaluation_output_is_under_data_artifacts(self):
        self.assertEqual(stack_paths.evaluation_output_root(),
                         stack_paths.data_root() / "artifacts" / "evaluation")

    def test_hermes_home_default(self):
        self.assertEqual(stack_paths.hermes_home(), Path.home() / ".hermes")


class TestOverrides(ContractBase):
    def test_state_override(self):
        os.environ["ANDROID_AGENT_STACK_STATE_ROOT"] = "/tmp/sx/state"
        self.assertEqual(stack_paths.state_root(), Path("/tmp/sx/state"))

    def test_data_override_via_xdg(self):
        os.environ["XDG_DATA_HOME"] = "/tmp/sx/data"
        self.assertEqual(stack_paths.data_root(), Path("/tmp/sx/data/google-android-agent-stack"))

    def test_explicit_data_override_beats_xdg(self):
        os.environ["XDG_DATA_HOME"] = "/tmp/ignored"
        os.environ["ANDROID_AGENT_STACK_DATA_ROOT"] = "/tmp/win"
        self.assertEqual(stack_paths.data_root(), Path("/tmp/win"))

    def test_hermes_home_override(self):
        os.environ["HERMES_HOME"] = "/tmp/hermes"
        self.assertEqual(stack_paths.hermes_home(), Path("/tmp/hermes"))

    def test_project_root_override(self):
        os.environ["ANDROID_AGENT_STACK_ROOT"] = "/tmp/proj"
        self.assertEqual(stack_paths.project_root(), Path("/tmp/proj"))


class TestCli(ContractBase):
    def test_query_and_export_and_ensure(self):
        with tempfile.TemporaryDirectory() as d:
            os.environ["ANDROID_AGENT_STACK_DATA_ROOT"] = d
            self.assertEqual(stack_paths.main(["query", "STACK_DATA_ROOT"]), 0)
            self.assertEqual(stack_paths.main(["export"]), 0)
            created = stack_paths.ensure(["STACK_DATA_ROOT"])
            self.assertTrue(os.path.isdir(created[0]))
            self.assertEqual(os.stat(created[0]).st_mode & 0o777, 0o700)

    def test_unknown_name_fails(self):
        self.assertEqual(stack_paths.main(["query", "NOPE"]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
