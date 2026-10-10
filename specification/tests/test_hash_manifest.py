"""P0 self-tests for hash_manifest: stable hashes and tamper detection."""

import os
import tempfile
import unittest

import support


class HashManifestTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pkg = support.fresh_package(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_hashes_are_stable(self):
        first, missing = support.hash_manifest.build_manifest(self.pkg)
        second, _ = support.hash_manifest.build_manifest(self.pkg)
        self.assertFalse(missing)
        self.assertEqual(first, second)
        self.assertEqual(len(first["entries"]), 8)

    def test_verify_passes_on_untouched_package(self):
        manifest, _ = support.hash_manifest.build_manifest(self.pkg)
        support.spec_lib.write_json(os.path.join(self.pkg, "manifest.json"), manifest)
        self.assertEqual(support.hash_manifest.verify_manifest(self.pkg, manifest), [])

    def test_verify_detects_tampering(self):
        manifest, _ = support.hash_manifest.build_manifest(self.pkg)
        support.spec_lib.write_json(os.path.join(self.pkg, "manifest.json"), manifest)
        support.append(os.path.join(self.pkg, "requirements.md"), "\n<!-- tamper -->\n")
        problems = support.hash_manifest.verify_manifest(self.pkg, manifest)
        self.assertTrue(any("requirements.md" in problem for problem in problems), problems)


if __name__ == "__main__":
    unittest.main()
