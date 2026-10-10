#!/usr/bin/env python3
"""Tests for the hardened host-state export/import tools (round-2)."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EXPORT = REPO / "scripts" / "export-host-state.sh"
IMPORT = REPO / "scripts" / "import-host-state.sh"


class ArchiveCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="host-state-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.state = self.tmp / "state"
        self.data = self.tmp / "data"
        self.cache = self.tmp / "cache"
        self.config = self.tmp / "config"
        self.hermes = self.tmp / "hermes"
        for d in (self.state, self.data, self.cache, self.config, self.hermes):
            d.mkdir(parents=True)
        self.env = dict(os.environ)
        self.env.update({
            "ANDROID_AGENT_STACK_STATE_ROOT": str(self.state),
            "ANDROID_AGENT_STACK_DATA_ROOT": str(self.data),
            "ANDROID_AGENT_STACK_CACHE_ROOT": str(self.cache),
            "ANDROID_AGENT_STACK_CONFIG_ROOT": str(self.config),
            "HERMES_HOME": str(self.hermes),
        })

    def export(self, dest: Path, *extra):
        return subprocess.run(["bash", str(EXPORT), "--dest", str(dest), *extra],
                              env=self.env, capture_output=True, text=True, timeout=120)

    def import_(self, archive: Path, *extra):
        return subprocess.run(["bash", str(IMPORT), str(archive), *extra],
                              env=self.env, capture_output=True, text=True, timeout=120)

    def seed_bridge(self, text='{"expected_sequence": 7}\n'):
        b = self.state / "bridge"
        b.mkdir(parents=True, exist_ok=True)
        (b / "state.json").write_text(text, encoding="utf-8")


class TestRoundTrip(ArchiveCase):
    def test_export_then_import_round_trip(self):
        self.seed_bridge()
        archive = self.tmp / "archive"
        p = self.export(archive)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertTrue((archive / "manifest.sha256").is_file())
        shutil.rmtree(self.state / "bridge")
        p = self.import_(archive)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("expected_sequence", (self.state / "bridge" / "state.json").read_text())

    def test_secrets_excluded_by_default(self):
        (self.hermes / ".env").write_text("COMMANDCODE_API_KEY=SECRETVALUE\n", encoding="utf-8")
        archive = self.tmp / "archive"
        self.assertEqual(self.export(archive).returncode, 0)
        blob = b""
        for root, _d, files in os.walk(archive):
            for f in files:
                blob += (Path(root) / f).read_bytes()
        self.assertNotIn(b"SECRETVALUE", blob)


class TestDestinationSafety(ArchiveCase):
    def test_destination_inside_project_rejected(self):
        p = self.export(REPO / "_should_not_exist")
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("inside the project", (p.stdout + p.stderr).lower())

    def test_non_empty_destination_rejected(self):
        archive = self.tmp / "archive"
        archive.mkdir()
        (archive / "stale.txt").write_text("stale\n", encoding="utf-8")
        p = self.export(archive)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("not empty", (p.stdout + p.stderr).lower())

    def test_export_skips_symlinks(self):
        self.seed_bridge()
        (self.state / "bridge" / "link").symlink_to("/etc/hostname")
        archive = self.tmp / "archive"
        p = self.export(archive)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        man = (archive / "manifest.sha256").read_text()
        self.assertNotIn("link", man)
        self.assertIn("symlinks", p.stdout)  # skip count recorded


class TestMaliciousArchives(ArchiveCase):
    def _export_ok(self):
        self.seed_bridge()
        archive = self.tmp / "archive"
        self.assertEqual(self.export(archive).returncode, 0)
        return archive

    def test_path_traversal_rejected(self):
        archive = self._export_ok()
        with open(archive / "manifest.sha256", "a", encoding="utf-8") as fh:
            fh.write("00  ../../escape.txt\n")
        p = self.import_(archive)
        self.assertNotEqual(p.returncode, 0)

    def test_duplicate_manifest_path_rejected(self):
        archive = self._export_ok()
        line = (archive / "manifest.sha256").read_text().splitlines()[0]
        with open(archive / "manifest.sha256", "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
        p = self.import_(archive)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("duplicate", (p.stdout + p.stderr).lower())

    def test_malformed_digest_rejected(self):
        archive = self._export_ok()
        lines = (archive / "manifest.sha256").read_text().splitlines()
        lines[0] = "nothexdigest  state/bridge/state.json"
        (archive / "manifest.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.assertNotEqual(self.import_(archive).returncode, 0)

    def test_checksum_mismatch_rejected(self):
        archive = self._export_ok()
        (archive / "state" / "bridge" / "state.json").write_text('{"a": 2}\n', encoding="utf-8")
        p = self.import_(archive)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("checksum", (p.stdout + p.stderr).lower())

    def test_symlink_inside_archive_rejected(self):
        archive = self._export_ok()
        (archive / "state" / "bridge" / "evil").symlink_to("/etc/passwd")
        p = self.import_(archive)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("symlink", (p.stdout + p.stderr).lower())

    def test_symlinked_destination_parent_rejected(self):
        archive = self._export_ok()
        # Replace the destination bridge dir with a symlink escaping the mapped root.
        shutil.rmtree(self.state / "bridge")
        outside = self.tmp / "outside"
        outside.mkdir()
        (self.state / "bridge").symlink_to(outside)
        p = self.import_(archive)
        self.assertNotEqual(p.returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
