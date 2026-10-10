"""P0 self-tests for the deterministic validator.

Positive case: a valid package is READY with all gates PASS.
Negative cases: each deliberately breaks exactly one capability and must fail for the
SPECIFIC intended rule id (not just any non-zero result).
"""

import json
import os
import tempfile
import unittest

import support


class ValidatePackageTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, before=None, after=None):
        pkg = support.fresh_package(self.tmp.name)
        if before:
            before(pkg)
        report = support.run_pipeline(pkg)
        if after:
            after(pkg)
            # Validate only: do NOT rebuild, so a tamper stays tampered.
            report = support.validate_package.validate(pkg, project_root=os.path.join(pkg, "project"))
        return pkg, report

    def test_valid_package_is_ready(self):
        pkg, report = self._run()
        self.assertEqual(report["status"], "READY", report["errors"])
        for gate in ("schema", "traceability", "boundaries", "acceptance", "hashes"):
            self.assertEqual(report["gates"][gate], "PASS", (gate, report["errors"]))
        self.assertTrue(os.path.exists(os.path.join(pkg, "READY.json")))
        self.assertEqual(report["traceability"][0]["requirement"], "REQ-FIX-001")
        self.assertEqual(report["traceability"][0]["pc1_steps"], ["PC1-01"])

    def test_missing_requirements_is_not_ready(self):
        def after(pkg):
            os.remove(os.path.join(pkg, "requirements.md"))

        _pkg, report = self._run(after=after)
        self.assertEqual(report["status"], "NOT_READY")
        self.assertIn("E_ARTIFACT_MISSING", support.rule_ids(report))

    def test_duplicate_acceptance_id_is_not_ready(self):
        def before(pkg):
            support.append(
                os.path.join(pkg, "acceptance.md"),
                "\n### AC-FIX-001 — Duplicate\n- Given: x\n- When: y\n- Then: z\n"
                "- Verification: v\n- PC1 Step: PC1-02\n",
            )

        _pkg, report = self._run(before=before)
        self.assertEqual(report["status"], "NOT_READY")
        self.assertIn("E_DUP_AC_ID", support.rule_ids(report))

    def test_bad_dependency_is_not_ready(self):
        def before(pkg):
            path = os.path.join(pkg, "tasks.md")
            support.write(path, support.read(path).replace("_Depends:_ none", "_Depends:_ TASK-99"))

        _pkg, report = self._run(before=before)
        self.assertEqual(report["status"], "NOT_READY")
        self.assertIn("E_MISSING_DEPENDENCY", support.rule_ids(report))

    def test_allowed_forbidden_conflict_is_not_ready(self):
        def before(pkg):
            path = os.path.join(pkg, "project-context.json")
            data = json.loads(support.read(path))
            data["forbidden_paths"] = ["app/Main.kt"]
            support.write(path, json.dumps(data, indent=2) + "\n")

        _pkg, report = self._run(before=before)
        self.assertEqual(report["status"], "NOT_READY")
        self.assertIn("E_PATH_CONFLICT", support.rule_ids(report))

    def test_missing_read_first_file_is_not_ready(self):
        def after(pkg):
            os.remove(os.path.join(pkg, "project", "app", "Main.kt"))

        _pkg, report = self._run(after=after)
        self.assertEqual(report["status"], "NOT_READY")
        self.assertIn("E_READ_FIRST_MISSING", support.rule_ids(report))

    def test_unresolved_question_is_not_ready(self):
        def before(pkg):
            path = os.path.join(pkg, "PRODUCT.md")
            support.write(
                path,
                support.read(path).replace(
                    '"unresolved_questions": []',
                    '"unresolved_questions": [{"id": "Q1", "question": "Still open?"}]',
                ),
            )

        _pkg, report = self._run(before=before)
        self.assertEqual(report["status"], "NOT_READY")
        self.assertIn("E_UNRESOLVED_QUESTIONS", support.rule_ids(report))

    def test_hash_mismatch_is_not_ready(self):
        def after(pkg):
            support.append(os.path.join(pkg, "tasks.md"), "\n<!-- tampered after hashing -->\n")

        _pkg, report = self._run(after=after)
        self.assertEqual(report["status"], "NOT_READY")
        self.assertIn("E_HASH_MISMATCH", support.rule_ids(report))


if __name__ == "__main__":
    unittest.main()
