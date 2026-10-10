#!/usr/bin/env python3
"""Tests for scripts/verify-layout.sh (layout enforcement)."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "verify-layout.sh"


def run_verify(root: Path, allowlist: Path | None = None) -> subprocess.CompletedProcess:
    cmd = ["bash", str(SCRIPT), "--root", str(root)]
    if allowlist is not None:
        cmd += ["--allowlist", str(allowlist)]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120)


class TestVerifyLayout(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="verify-layout-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (self.tmp / "scripts" / "lib").mkdir(parents=True)
        (self.tmp / "src").mkdir()
        # an authored, clean source file
        (self.tmp / "src" / "ok.py").write_text("print('clean')\n", encoding="utf-8")

    def test_clean_tree_passes(self):
        p = run_verify(self.tmp)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_generated_dir_is_a_violation(self):
        (self.tmp / "src" / "__pycache__").mkdir()
        (self.tmp / "src" / "__pycache__" / "x.pyc").write_bytes(b"x")
        p = run_verify(self.tmp)
        self.assertEqual(p.returncode, 1)
        self.assertIn("GENERATED", p.stdout)

    def test_absolute_host_path_is_a_violation(self):
        (self.tmp / "src" / "bad.py").write_text('P = "/home/someone/proj/x"\n', encoding="utf-8")
        p = run_verify(self.tmp)
        self.assertEqual(p.returncode, 1)
        self.assertIn("HOST_PATH", p.stdout)

    def test_allowlisted_fixture_is_ignored(self):
        allow = self.tmp / "allowlist.txt"
        allow.write_text("src/fixture.py\n", encoding="utf-8")
        (self.tmp / "src" / "fixture.py").write_text('P = "/mnt/AndroidDev/x"\n', encoding="utf-8")
        p = run_verify(self.tmp, allowlist=allow)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
