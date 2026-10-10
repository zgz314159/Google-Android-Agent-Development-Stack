#!/usr/bin/env python3
"""Evidence bundle completeness tests for evidence_completeness.py."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HARNESS))
import evidence_completeness as ec  # noqa: E402


def write(p: Path, text: str):
    p.write_text(text)


def make_bundle(tmp: Path, *, layout="json", db=True, meta_extra=None) -> Path:
    f = tmp / "failure"
    f.mkdir(parents=True, exist_ok=True)
    write(f / "executor-output.txt", "executor")
    write(f / "failed-assertion.json", '{"exception":"java.lang.AssertionError"}')
    write(f / "logcat.txt", "logcat")
    write(f / "screenshot.png", "\x89PNG\r\n")
    if db:
        write(f / "db-state.json", '{"outcome":"FAIL"}')
    if layout == "json":
        write(f / "layout.json", '[]')
    elif layout == "xml":
        write(f / "layout.xml", "<?xml version='1.0'?><hierarchy rotation=\"0\"></hierarchy>")
    meta = {"layout_provider": layout == "xml" and "uiautomator_xml" or "android_cli"}
    if meta_extra:
        meta.update(meta_extra)
    write(f / "metadata.json", json.dumps(meta))
    return f


class TestCompleteness(unittest.TestCase):
    def test_complete_json_layout(self):
        f = make_bundle(Path(tempfile.mkdtemp()))
        r = ec.check_bundle(f)
        self.assertTrue(r["complete"], r)
        self.assertEqual(r["missing"], [])
        self.assertEqual(r["errors"], [])

    def test_complete_xml_layout(self):
        f = make_bundle(Path(tempfile.mkdtemp()), layout="xml")
        r = ec.check_bundle(f)
        self.assertTrue(r["complete"], r)
        self.assertIn("layout.xml", r["present"])

    def test_missing_logcat_is_incomplete(self):
        f = make_bundle(Path(tempfile.mkdtemp()))
        (f / "logcat.txt").unlink()
        r = ec.check_bundle(f)
        self.assertFalse(r["complete"])
        self.assertIn("logcat", r["missing"])

    def test_db_state_explicitly_unavailable_is_complete(self):
        f = make_bundle(Path(tempfile.mkdtemp()), db=False)
        (f / "metadata.json").write_text(json.dumps({
            "layout_provider": "android_cli",
            "artifacts": [{"name": "db-state", "available": False, "reason": "app did not start"}],
        }))
        r = ec.check_bundle(f)
        self.assertTrue(r["complete"], r)
        self.assertTrue(any("db-state" in u for u in r["unavailable"]))

    def test_db_state_silently_missing_is_incomplete(self):
        f = make_bundle(Path(tempfile.mkdtemp()), db=False)
        r = ec.check_bundle(f)
        self.assertFalse(r["complete"])
        self.assertIn("db-state", r["missing"])

    def test_xml_relabelled_as_json_fails(self):
        f = make_bundle(Path(tempfile.mkdtemp()))
        (f / "layout.json").write_text("<?xml version='1.0'?><hierarchy/>")
        r = ec.check_bundle(f)
        self.assertFalse(r["complete"])
        self.assertTrue(any("not valid JSON" in e for e in r["errors"]))

    def test_bad_layout_provider(self):
        f = make_bundle(Path(tempfile.mkdtemp()))
        (f / "metadata.json").write_text(json.dumps({"layout_provider": "magic"}))
        r = ec.check_bundle(f)
        self.assertFalse(r["complete"])
        self.assertTrue(any("layout_provider" in e for e in r["errors"]))

    def test_layout_unavailable_explicit_is_complete(self):
        f = make_bundle(Path(tempfile.mkdtemp()), layout="none")
        (f / "metadata.json").write_text(json.dumps({
            "layout_provider": "unavailable",
            "artifacts": [{"name": "layout", "available": False, "reason": "no window"}],
        }))
        r = ec.check_bundle(f)
        self.assertTrue(r["complete"], r)


if __name__ == "__main__":
    unittest.main(verbosity=2)
