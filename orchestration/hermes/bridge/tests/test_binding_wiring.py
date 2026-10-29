#!/usr/bin/env python3
"""Offline regression over the REAL production entrypoint (contract_executor.gate).

Local, model-free, no root, no network. Uses a temp (never real) registry, temp wrapper,
real temp git repos and a compiler-validated package, so a helper-only unit test cannot
stand in for the actual call path.

Covers: normal IAP binding; wrong repo association; missing/inconsistent approval info;
legacy Stack compatibility.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

BRIDGE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BRIDGE_DIR))

import contract_executor as ce  # noqa: E402
import projects as pj  # noqa: E402
from protocol import sha256_file  # noqa: E402

TEMPLATE = BRIDGE_DIR.parents[2] / "reports" / "contracts" / "BRIDGE-READONLY-001"
AUTHORED = ("PRODUCT.md", "requirements.md", "design.md", "tasks.md", "DESIGN.md",
            "acceptance.md", "verification-intent.json")


def _run(argv, cwd=None):
    return subprocess.run(argv, capture_output=True, text=True, cwd=cwd)


class GateWiringTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="iap-wiring-", dir="/var/tmp"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

        self.formal = self.tmp / "ImageAnalysisFactory"
        self._init_repo(self.formal)
        self.task_root = self.tmp / "IAP-M1-001"
        self.worktree = self.task_root / "project"
        r = _run(["git", "worktree", "add", "-q", "--detach", str(self.worktree), "HEAD"], self.formal)
        self.assertEqual(r.returncode, 0, r.stderr)

        self.contract_root = self.tmp / "trusted" / "contracts"
        self.pkg = self.contract_root / "IAP-M1-001"
        self._make_package("ImageAnalysisFactory", str(self.task_root))

        self.registry = self.tmp / "registry.json"
        self.wrapper = self.tmp / "run_registered_task"
        self.wrapper.write_text("#!/bin/sh\nexit 0\n")
        self.wrapper.chmod(0o755)

        self.saved = pj.PROJECT_BINDINGS["ImageAnalysisFactory"]
        pj.PROJECT_BINDINGS["ImageAnalysisFactory"] = {
            **self.saved,
            "formal_source_root": str(self.formal),
            "contract_root": str(self.contract_root),
            "worktree_bases": (str(self.tmp) + "/",),
        }
        self.addCleanup(self._restore)

    def _restore(self):
        pj.PROJECT_BINDINGS["ImageAnalysisFactory"] = self.saved

    def _init_repo(self, root):
        root.mkdir(parents=True, exist_ok=True)
        _run(["git", "init", "-q", "-b", "main"], root)
        _run(["git", "config", "user.email", "c@local"], root)
        _run(["git", "config", "user.name", "c"], root)
        (root / "README.md").write_text("baseline\n")
        _run(["git", "add", "-A"], root)
        _run(["git", "commit", "-q", "-m", "baseline"], root)

    def _make_package(self, project, source_root):
        self.pkg.mkdir(parents=True, exist_ok=True)
        for name in AUTHORED:
            shutil.copy(TEMPLATE / name, self.pkg / name)
        (Path(source_root) / "project").mkdir(parents=True, exist_ok=True)
        (Path(source_root) / "project" / "PLAN.md").write_text("task plan\n")
        (self.pkg / "project-context.json").write_text(json.dumps({
            "project": project,
            "project_type": "greenfield",
            "source_root": source_root,
            "read_first": [{"path": "project/PLAN.md", "why": "task-scoped input"}],
            "allowed_paths": ["project"],
            "forbidden_paths": [],
            "path_classes": {"EVIDENCE_OUTPUT": ["project/EVIDENCE.txt"]},
        }, indent=2) + "\n")
        self._recompile()

    def _set_context(self, project, source_root, allowed_paths, read_first):
        (self.pkg / "project-context.json").write_text(json.dumps({
            "project": project,
            "project_type": "greenfield",
            "source_root": source_root,
            "read_first": [{"path": read_first, "why": "task-scoped input"}],
            "allowed_paths": allowed_paths,
            "forbidden_paths": [],
        }, indent=2) + "\n")

    def _recompile(self):
        cmp = ce.PROJECT_ROOT / "specification" / "compiler"
        for step in ("hash_manifest.py", "build_contract.py"):
            r = _run([sys.executable, str(cmp / step), str(self.pkg)])
            self.assertEqual(r.returncode, 0, (step, r.stdout, r.stderr))
        # mirror production: the validator resolves read_first against the package's own
        # source_root (no --project-root override for IAP)
        r = _run([sys.executable, str(cmp / "validate_package.py"), str(self.pkg)])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def _entry(self, **over):
        base = {
            "worktree": str(self.worktree),
            "scratch": str(self.task_root / "scratch"),
            "project": str(self.formal),
            "contract_package": str(self.pkg),
        }
        base.update(over)
        return {"IAP-M1-001": base}

    def _gate(self, entry=None, package=None, project="ImageAnalysisFactory"):
        self.registry.write_text(json.dumps(entry or self._entry(), indent=2) + "\n")
        pkg = package or str(self.pkg)
        return ce.gate(pkg, sha256_file(str(Path(pkg) / "manifest.json")), project=project,
                       task_id="IAP-M1-001", task_registry=self.registry, wrapper=self.wrapper,
                       require_root_owner=False)

    # --- 1. normal IAP binding ------------------------------------------------
    def test_normal_iap_binding_accepted(self):
        result = self._gate()
        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["project"], "ImageAnalysisFactory")

    # --- 2. wrong repo association -------------------------------------------
    def test_registry_project_not_formal_root_rejected(self):
        other = self.tmp / "OtherProject"
        self._init_repo(other)
        with self.assertRaises(ce.GateError) as ctx:
            self._gate(self._entry(project=str(other)))
        self.assertEqual(ctx.exception.code, "E_EXT_REGISTRY_PROJECT")

    def test_forged_worktree_not_a_git_worktree_rejected(self):
        forged = self.task_root / "forged"
        forged.mkdir()
        # inside source_root and authorized, so the git proof is the failing gate
        self._set_context("ImageAnalysisFactory", str(self.task_root), ["project", "forged"],
                          "project/PLAN.md")
        self._recompile()
        with self.assertRaises(ce.GateError) as ctx:
            self._gate(self._entry(worktree=str(forged)))
        self.assertEqual(ctx.exception.code, "E_EXT_WORKTREE_GIT")

    def test_worktree_of_other_repo_rejected_at_gate(self):
        other = self.tmp / "OtherRepo"
        self._init_repo(other)
        foreign = self.tmp / "foreign-wt"
        r = _run(["git", "worktree", "add", "-q", "--detach", str(foreign), "HEAD"], other)
        self.assertEqual(r.returncode, 0, r.stderr)
        (foreign / "PLAN.md").write_text("x\n")
        # keep it inside source_root + allowed_paths so the git proof is the failing gate
        self._set_context("ImageAnalysisFactory", str(self.tmp), ["foreign-wt"], "foreign-wt/PLAN.md")
        self._recompile()
        with self.assertRaises(ce.GateError) as ctx:
            self._gate(self._entry(worktree=str(foreign)))
        self.assertEqual(ctx.exception.code, "E_EXT_WORKTREE_GIT")

    # --- 3. missing / inconsistent approval info ------------------------------
    def test_contract_source_root_broad_rejected(self):
        # absolute read_first so the package still compiles; the gate must reject the root
        self._set_context("ImageAnalysisFactory", "/var/tmp", ["IAP-M1-001"],
                          str(self.pkg / "PRODUCT.md"))
        self._recompile()
        with self.assertRaises(ce.GateError) as ctx:
            self._gate()
        self.assertEqual(ctx.exception.code, "E_EXT_SOURCE_ROOT_BROAD")

    def test_worktree_not_authorized_by_allowed_paths_rejected(self):
        self._set_context("ImageAnalysisFactory", str(self.task_root), ["elsewhere"],
                          "project/PLAN.md")
        self._recompile()
        with self.assertRaises(ce.GateError) as ctx:
            self._gate()
        self.assertEqual(ctx.exception.code, "E_EXT_WORKTREE_NOT_ALLOWED")

    def test_contract_project_mismatch_rejected(self):
        self._set_context("SomethingElse", str(self.task_root), ["project"], "project/PLAN.md")
        self._recompile()
        with self.assertRaises(ce.GateError) as ctx:
            self._gate()
        self.assertEqual(ctx.exception.code, "E_EXT_CONTRACT_PROJECT")

    def test_unknown_project_rejected(self):
        with self.assertRaises(ce.GateError) as ctx:
            self._gate(project="PowerAi")
        self.assertEqual(ctx.exception.code, "E_PROJECT")

    # --- 4. legacy Stack compatibility ---------------------------------------
    def test_stack_binding_values_preserved(self):
        b = pj.PROJECT_BINDINGS["Google-Android-Agent-Development-Stack"]
        self.assertEqual(b["formal_source_root"],
                         "/home/zhong/Projects/Google-Android-Agent-Development-Stack")
        self.assertEqual(b["contract_root"],
                         "/home/zhong/Projects/Google-Android-Agent-Development-Stack/reports/contracts")
        self.assertEqual(b["validator_project_root"], "/home/zhong/Projects")
        self.assertFalse(b["require_git_ownership"])

    def test_stack_legacy_path_gate_unchanged(self):
        # a relative package still fails the very first path check, for the Stack project
        with self.assertRaises(ce.GateError) as ctx:
            ce.gate("reports/contracts/X", "b" * 64, project="Google-Android-Agent-Development-Stack")
        self.assertEqual(ctx.exception.code, "E_PACKAGE_NOT_ABSOLUTE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
