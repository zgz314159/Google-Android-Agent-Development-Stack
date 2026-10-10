"""P0 self-tests for build_contract: deterministic assembly and fail-fast on missing input."""

import os
import tempfile
import unittest

import support


class BuildContractTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_build_is_deterministic_and_complete(self):
        pkg = support.fresh_package(self.tmp.name)
        manifest, missing = support.hash_manifest.build_manifest(pkg)
        self.assertFalse(missing)
        support.spec_lib.write_json(os.path.join(pkg, "manifest.json"), manifest)

        first = support.build_contract.build(pkg)
        second = support.build_contract.build(pkg)
        self.assertEqual(first, second)
        self.assertEqual(first["contract_id"], "FIXTURE-B1-CONTRACT")
        self.assertEqual(first["mode"], "brownfield")
        self.assertEqual(len(first["requirements"]), 1)
        self.assertEqual(len(first["tasks"]), 1)
        self.assertEqual(first["acceptance_ids"], ["AC-FIX-001"])
        self.assertEqual(first["artifact_hashes"], {e["path"]: e["sha256"] for e in manifest["entries"]})

    def test_build_fails_fast_when_input_missing(self):
        pkg = support.fresh_package(self.tmp.name)
        manifest, _ = support.hash_manifest.build_manifest(pkg)
        support.spec_lib.write_json(os.path.join(pkg, "manifest.json"), manifest)
        os.remove(os.path.join(pkg, "design.md"))
        with self.assertRaises(support.build_contract.BuildError):
            support.build_contract.build(pkg)

    def test_prompt_is_generated(self):
        pkg = support.fresh_package(self.tmp.name)
        manifest, _ = support.hash_manifest.build_manifest(pkg)
        support.spec_lib.write_json(os.path.join(pkg, "manifest.json"), manifest)
        contract = support.build_contract.build(pkg)
        prompt = support.build_contract.render_prompt(contract)
        self.assertIn("CONTRACT_DEVIATION", prompt)
        self.assertIn("broad repo scan = forbidden", prompt)
        self.assertIn("read_first", prompt)


if __name__ == "__main__":
    unittest.main()
