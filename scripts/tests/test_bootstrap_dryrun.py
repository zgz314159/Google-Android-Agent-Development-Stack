#!/usr/bin/env python3
"""Bootstrap dry-run test: resolves the pinned Hermes revision and changes nothing."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BOOTSTRAP = REPO / "scripts" / "bootstrap-host.sh"
LOCK = json.loads((REPO / "orchestration" / "hermes" / "HERMES-LOCK.json").read_text())


class TestBootstrapDryRun(unittest.TestCase):
    def test_dry_run_resolves_pin_and_makes_no_changes(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            hermes = d / "hermes"
            env = dict(os.environ)
            env.update({
                "ANDROID_AGENT_STACK_STATE_ROOT": str(d / "state"),
                "ANDROID_AGENT_STACK_DATA_ROOT": str(d / "data"),
                "ANDROID_AGENT_STACK_CACHE_ROOT": str(d / "cache"),
                "ANDROID_AGENT_STACK_CONFIG_ROOT": str(d / "config"),
                "HERMES_HOME": str(hermes),
            })
            p = subprocess.run(["bash", str(BOOTSTRAP), "--dry-run"],
                               env=env, capture_output=True, text=True, timeout=120)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertIn(LOCK["commit_sha"], p.stdout)
            self.assertIn("DRY RUN complete", p.stdout)
            # nothing was created
            self.assertFalse(hermes.exists())
            for name in ("state", "data", "cache", "config"):
                self.assertFalse((d / name).exists(), name)

    def test_bootstrap_script_has_no_credentials(self):
        text = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertNotIn("sk-", text)
        self.assertNotIn("COMMANDCODE_API_KEY=", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
