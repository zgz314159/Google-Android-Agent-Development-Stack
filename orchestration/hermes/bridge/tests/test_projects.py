#!/usr/bin/env python3
"""Unit tests for bridge/projects.py (module-level behaviour, dependency-free)."""

import os
import sys
import unittest
from pathlib import Path

BRIDGE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BRIDGE_DIR))

import projects as pj  # noqa: E402


class ProjectsUnitTests(unittest.TestCase):
    def test_allowlist_is_exactly_the_declared_table(self):
        self.assertEqual(pj.ALLOWED_PROJECTS, frozenset(pj.PROJECT_BINDINGS))
        self.assertIn("ImageAnalysisFactory", pj.ALLOWED_PROJECTS)
        self.assertNotIn("PowerAi", pj.ALLOWED_PROJECTS)

    def test_validator_project_root_is_in_the_table(self):
        self.assertEqual(pj.validator_project_root_for("Google-Android-Agent-Development-Stack"),
                         "/home/zhong/Projects")
        self.assertIsNone(pj.validator_project_root_for("ImageAnalysisFactory"))
        self.assertIsNone(pj.validator_project_root_for("PowerAi"))

    def test_unknown_project_rejected(self):
        v = pj.validate_project("PowerAi", package_real="/x", contract_root="/x",
                                context_project="PowerAi", context_source_root="/var/tmp/t",
                                context_allowed_paths=["project"], worktree="/var/tmp/t/project")
        self.assertFalse(v["ok"])
        self.assertEqual(v["code"], pj.E_PROJECT)

    def test_broad_root_predicate(self):
        for broad in ("/", "/var/tmp", "/home/zhong", "/home/zhong/Projects", ""):
            self.assertTrue(pj._is_broad_root(broad), broad)
        self.assertFalse(pj._is_broad_root("/var/tmp/IAP-M1-001"))

    def test_binding_bases_are_safe(self):
        for name, binding in pj.PROJECT_BINDINGS.items():
            self.assertTrue(pj.worktree_bases_are_safe(binding), name)

    def test_target_ref_and_profile_are_per_project(self):
        self.assertEqual(pj.target_ref_for("ImageAnalysisFactory"), "refs/heads/main")
        self.assertEqual(pj.target_ref_for("Google-Android-Agent-Development-Stack"), "refs/heads/master")
        self.assertEqual(pj.profile_for("ImageAnalysisFactory"), "android-stack")

    def test_git_ownership_flags_are_declared(self):
        self.assertTrue(pj.PROJECT_BINDINGS["ImageAnalysisFactory"]["require_git_ownership"])
        self.assertFalse(pj.PROJECT_BINDINGS["Google-Android-Agent-Development-Stack"]["require_git_ownership"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
