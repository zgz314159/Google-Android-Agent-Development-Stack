"""Exercise the actual status CLI without a browser, model, or host state."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager


CLI = Path(__file__).resolve().parents[1] / "bridge_cli.py"
MEMBERS = ("state.json", "journal.jsonl", "pending_result.json")


@contextmanager
def scene():
    base = Path(tempfile.mkdtemp(prefix="bridge-status-", dir="/var/tmp"))
    root = base / "bridge"
    try:
        yield root
    except BaseException:
        print("SCENE_KEPT=%s" % base, file=sys.stderr)
        raise
    else:
        # Only the exact fixture members; an unknown file makes rmdir fail.
        try:
            for name in MEMBERS:
                path = root / name
                if path.exists() or path.is_symlink():
                    path.unlink()
            if root.exists():
                root.rmdir()
            base.rmdir()
        except OSError:
            print("SCENE_KEPT=%s" % base, file=sys.stderr)
            raise


def run_status(root):
    env = dict(os.environ, HERMES_BRIDGE_STATE_DIR=str(root),
               PYTHONDONTWRITEBYTECODE="1")
    proc = subprocess.run([sys.executable, "-B", str(CLI), "status"],
                          env=env, text=True, capture_output=True, timeout=10)
    return proc.returncode, json.loads(proc.stdout)


class StatusReadonlyTests(unittest.TestCase):
    def test_absent_directory_is_reported_without_creating_chain(self):
        with scene() as root:
            rc, out = run_status(root)
            self.assertEqual(rc, 1)
            self.assertEqual(out["decision"], "STATE_ABSENT")
            self.assertFalse(root.exists())

    def test_empty_directory_keeps_its_mode_and_contents(self):
        with scene() as root:
            root.mkdir(mode=0o750)
            before = root.stat().st_mode
            rc, out = run_status(root)
            self.assertEqual((rc, out["decision"]), (1, "STATE_ABSENT"))
            self.assertEqual(root.stat().st_mode, before)
            self.assertEqual(list(root.iterdir()), [])

    def test_existing_state_journal_and_pending_are_unchanged(self):
        with scene() as root:
            root.mkdir(mode=0o750)
            state = {"status": "WAITING_FOR_GPT", "expected_sequence": 13,
                     "expected_nonce": "fixture", "expected_in_reply_to": "fixture"}
            (root / "state.json").write_text(json.dumps(state))
            (root / "journal.jsonl").write_text('{"event":"NOTE"}\n')
            (root / "pending_result.json").write_text('{}\n')
            before = {p.name: (p.read_bytes(), p.stat().st_mode)
                      for p in root.iterdir()}
            mode = root.stat().st_mode
            rc, out = run_status(root)
            self.assertEqual(rc, 0)
            self.assertEqual(out["state"], state)
            self.assertTrue(out["pending_result"])
            self.assertEqual(out["journal_entries"], 1)
            self.assertEqual(root.stat().st_mode, mode)
            self.assertEqual({p.name: (p.read_bytes(), p.stat().st_mode)
                              for p in root.iterdir()}, before)

    def test_corrupt_state_fails_without_repair(self):
        for content in ("{broken", "[]"):
            with self.subTest(content=content), scene() as root:
                root.mkdir()
                path = root / "state.json"
                path.write_text(content)
                before = path.read_bytes()
                rc, out = run_status(root)
                self.assertEqual((rc, out["decision"]), (1, "ERROR"))
                self.assertEqual(path.read_bytes(), before)
                self.assertEqual([p.name for p in root.iterdir()], ["state.json"])


if __name__ == "__main__":
    unittest.main()
