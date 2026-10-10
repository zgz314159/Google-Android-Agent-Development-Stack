#!/usr/bin/env python3
"""Failure-bundle completeness + format-rule tests for core/evidence_completeness.py."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

VERIFY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(VERIFY / "core"))
import evidence_completeness as ec  # noqa: E402


def complete_bundle(root: Path) -> Path:
    (root / "metadata.json").write_text(json.dumps({
        "layout_provider": "android_cli",
        "artifacts": [{"name": "screenshot", "file": "screenshot.png", "available": True}],
    }))
    for f, content in (("executor-output.txt", "OK (1 test)"),
                       ("failed-assertion.json", "{}"),
                       ("logcat.txt", "log"),
                       ("screenshot.png", "png"),
                       ("db-state.json", "{}")):
        (root / f).write_text(content)
    (root / "layout.json").write_text("{}")
    return root


class TestEvidenceCompleteness(unittest.TestCase):
    def test_complete(self):
        d = complete_bundle(Path(tempfile.mkdtemp()))
        rep = ec.check_bundle(d)
        self.assertTrue(rep["complete"], rep)
        self.assertEqual(rep["missing"], [])

    def test_missing_executor(self):
        d = complete_bundle(Path(tempfile.mkdtemp()))
        (d / "executor-output.txt").unlink()
        rep = ec.check_bundle(d)
        self.assertFalse(rep["complete"])
        self.assertIn("executor-output", rep["missing"])

    def test_unavailable_with_reason_is_ok(self):
        d = complete_bundle(Path(tempfile.mkdtemp()))
        (d / "screenshot.png").unlink()
        meta = json.loads((d / "metadata.json").read_text())
        meta["artifacts"] = [{"name": "screenshot", "file": "screenshot.png",
                              "available": False, "reason": "no device"}]
        (d / "metadata.json").write_text(json.dumps(meta))
        rep = ec.check_bundle(d)
        self.assertTrue(rep["complete"], rep)

    def test_xml_not_relabelled(self):
        d = complete_bundle(Path(tempfile.mkdtemp()))
        (d / "layout.json").unlink()
        (d / "layout.xml").write_text("<?xml version=\"1.0\"?><hierarchy/>")
        meta = json.loads((d / "metadata.json").read_text())
        meta["layout_provider"] = "uiautomator_xml"
        (d / "metadata.json").write_text(json.dumps(meta))
        rep = ec.check_bundle(d)
        self.assertTrue(rep["complete"], rep)
        # a .json file holding XML must fail the JSON parse rule
        (d / "layout.json").write_text("<hierarchy/>")
        rep = ec.check_bundle(d)
        self.assertFalse(rep["complete"])

    def test_bad_layout_provider(self):
        d = complete_bundle(Path(tempfile.mkdtemp()))
        meta = json.loads((d / "metadata.json").read_text())
        meta["layout_provider"] = "magic"
        (d / "metadata.json").write_text(json.dumps(meta))
        rep = ec.check_bundle(d)
        self.assertFalse(rep["complete"])

    def test_resolve_bundle_run_dir(self):
        root = Path(tempfile.mkdtemp())
        (root / "failure").mkdir()
        self.assertEqual(ec.resolve_bundle(str(root)), root / "failure")


if __name__ == "__main__":
    unittest.main(verbosity=2)
