#!/usr/bin/env python3
"""APK provenance tests for core/provenance.py."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

VERIFY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(VERIFY / "core"))
import provenance  # noqa: E402


class TestProvenance(unittest.TestCase):
    def test_sha256_stable(self):
        p = Path(tempfile.mkdtemp()) / "x"
        p.write_text("hello")
        self.assertEqual(
            provenance.sha256(p),
            "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824")

    def test_expected_match(self):
        d = Path(tempfile.mkdtemp())
        apk = d / "app.apk"; apk.write_text("apk")
        sha = provenance.sha256(apk)
        out = d / "prov.json"
        rc = subprocess.run([sys.executable, str(VERIFY / "core/provenance.py"),
                             "--app", str(apk), "--expected-app", sha, "--json", str(out)],
                            capture_output=True, text=True).returncode
        self.assertEqual(rc, 0)
        self.assertEqual(__import__("json").loads(out.read_text())["apk_sha256"], sha)

    def test_expected_mismatch_stops(self):
        d = Path(tempfile.mkdtemp())
        apk = d / "app.apk"; apk.write_text("apk")
        r = subprocess.run([sys.executable, str(VERIFY / "core/provenance.py"),
                            "--app", str(apk), "--expected-app", "0" * 64],
                           capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("APK_SHA_MISMATCH", r.stderr)

    def test_require_test_missing(self):
        d = Path(tempfile.mkdtemp())
        apk = d / "app.apk"; apk.write_text("apk")
        r = subprocess.run([sys.executable, str(VERIFY / "core/provenance.py"),
                            "--app", str(apk), "--require-test"],
                           capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("TEST_APK_MISSING", r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
