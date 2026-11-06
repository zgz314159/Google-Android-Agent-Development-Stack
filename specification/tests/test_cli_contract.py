"""Focused tests for the non-UI `cli` verification engine."""

import json
import os
import tempfile
import unittest

import support


def _write_design(pkg, **changes):
    path = os.path.join(pkg, "design.md")
    text = support.read(path)
    design = support.spec_lib.find_json_block(text)
    design.update(changes)
    block = "```json\n" + json.dumps(design, indent=2) + "\n```"
    support.write(path, support.spec_lib.JSON_BLOCK.sub(lambda _m: block, text, count=1))


def _write_intent(pkg, **changes):
    path = os.path.join(pkg, "verification-intent.json")
    data = json.loads(support.read(path))
    data.update(changes)
    support.write(path, json.dumps(data, indent=2) + "\n")


def make_cli_package(tmp_dir):
    pkg = support.fresh_package(tmp_dir)
    _write_design(
        pkg,
        ui_change={"surfaces": [], "selectors_added": []},
        selector_contract=[],
    )
    _write_intent(
        pkg,
        engine="cli",
        required_selectors=[],
        cli_checks=[
            {
                "step": "identity",
                "command": "id -un",
                "expected": "a non-empty user name; record the actual value",
                "on_failure": "stop; record the actual command, exit code and output",
            },
            {
                "step": "worktree",
                "command": "pwd",
                "expected": "the disposable task worktree path",
                "on_failure": "stop; record the actual value",
            },
            {
                "step": "revision",
                "command": "git rev-parse HEAD",
                "expected": "a 40-character lowercase hexadecimal commit id; record the actual value",
                "on_failure": "stop; record the actual command, exit code and output",
            },
            {
                "step": "evidence",
                "command": "test -s EVIDENCE.txt && cat EVIDENCE.txt",
                "expected": "EVIDENCE.txt exists and contains the actual command outputs",
                "on_failure": "stop; do not synthesize or repair EVIDENCE.txt",
            },
        ],
    )
    return pkg


class CliContractTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_cli_contract_is_ready_and_prompt_has_no_ui_requirements(self):
        pkg = make_cli_package(self.tmp.name)
        report = support.run_pipeline(pkg)
        self.assertEqual(report["status"], "READY", report["errors"])
        self.assertTrue(os.path.exists(os.path.join(pkg, "READY.json")))

        contract = json.loads(support.read(os.path.join(pkg, "implementation-contract.json")))
        self.assertEqual(contract["verification_intent"]["engine"], "cli")
        self.assertEqual(contract["selector_contract"], [])
        self.assertEqual(contract["verification_intent"]["required_selectors"], [])
        self.assertTrue(contract["verification_intent"]["cli_checks"])

        prompt = support.build_contract.render_prompt(contract)
        self.assertIn("CLI checks:", prompt)
        self.assertIn("A zero process exit alone is NOT a PASS", prompt)
        for forbidden in (
            "Build the Verification Plan",
            "Verification Layer",
            "Maestro",
            "uiautomator",
            "selector",
        ):
            self.assertNotIn(forbidden, prompt)

    def _prompt(self, pkg):
        report = support.run_pipeline(pkg)
        self.assertEqual(report["status"], "READY", report["errors"])
        contract = json.loads(support.read(os.path.join(pkg, "implementation-contract.json")))
        return support.build_contract.render_prompt(contract)

    def test_prompt_is_contract_first_for_evidence(self):
        pkg = make_cli_package(self.tmp.name)
        prompt = self._prompt(pkg)
        self.assertIn(
            "Record evidence only in the files and format required by the frozen contract.",
            prompt,
        )
        self.assertIn(
            "Put expected results, failure conditions, and supplemental reporting in the FINAL ASSISTANT RESPONSE",
            prompt,
        )
        self.assertNotIn(
            "Record the actual command, actual output, expected result and failure condition in `EVIDENCE.txt`",
            prompt,
        )
        self.assertNotIn("four labeled lines", prompt)
        self.assertIn("EVIDENCE.txt exists and contains the actual command outputs", prompt)
        self.assertNotIn("IAP", prompt)
        self.assertNotIn("PREP-BINDING", prompt)

    def test_contract_defined_evidence_format_survives(self):
        pkg = make_cli_package(self.tmp.name)
        path = os.path.join(pkg, "verification-intent.json")
        data = json.loads(support.read(path))
        data["cli_checks"][-1]["command"] = "test -s REPORT.json && cat REPORT.json"
        data["cli_checks"][-1]["expected"] = (
            "REPORT.json contains one JSON object with keys user, path, head, python"
        )
        support.write(path, json.dumps(data, indent=2) + "\n")
        prompt = self._prompt(pkg)
        self.assertIn("REPORT.json contains one JSON object with keys user, path, head, python", prompt)
        self.assertNotIn("four labeled lines", prompt)
        self.assertNotIn(
            "Record the actual command, actual output, expected result and failure condition in `EVIDENCE.txt`",
            prompt,
        )

    def test_contract_four_line_evidence_is_preserved(self):
        pkg = make_cli_package(self.tmp.name)
        path = os.path.join(pkg, "verification-intent.json")
        data = json.loads(support.read(path))
        data["cli_checks"][-1]["expected"] = (
            "exactly four labeled lines in this order, with no extra lines: a, b, c, d"
        )
        support.write(path, json.dumps(data, indent=2) + "\n")
        prompt = self._prompt(pkg)
        self.assertIn("exactly four labeled lines in this order, with no extra lines: a, b, c, d", prompt)
        self.assertIn(
            "Put expected results, failure conditions, and supplemental reporting in the FINAL ASSISTANT RESPONSE",
            prompt,
        )

    def test_ui_contract_without_selector_is_rejected(self):
        pkg = make_cli_package(self.tmp.name)
        _write_intent(pkg, engine="uiautomator", required_selectors=[])
        report = support.run_pipeline(pkg)
        self.assertEqual(report["status"], "NOT_READY")
        self.assertTrue(
            {"E_UI_SELECTOR_REQUIRED", "E_SCHEMA_INVALID"} & support.rule_ids(report),
            report["errors"],
        )

    def test_unknown_engine_is_rejected(self):
        pkg = make_cli_package(self.tmp.name)
        _write_intent(pkg, engine="playwright")
        report = support.run_pipeline(pkg)
        self.assertEqual(report["status"], "NOT_READY")
        self.assertIn("E_UNKNOWN_ENGINE", support.rule_ids(report))
        self.assertIn("E_SCHEMA_INVALID", support.rule_ids(report))

    def test_missing_cli_checks_is_rejected(self):
        pkg = make_cli_package(self.tmp.name)
        path = os.path.join(pkg, "verification-intent.json")
        data = json.loads(support.read(path))
        data.pop("cli_checks")
        support.write(path, json.dumps(data, indent=2) + "\n")
        report = support.run_pipeline(pkg)
        self.assertEqual(report["status"], "NOT_READY")
        self.assertTrue(
            {"E_CLI_CHECKS_MISSING", "E_SCHEMA_INVALID"} & support.rule_ids(report),
            report["errors"],
        )

    def test_incomplete_cli_check_is_rejected(self):
        pkg = make_cli_package(self.tmp.name)
        path = os.path.join(pkg, "verification-intent.json")
        data = json.loads(support.read(path))
        data["cli_checks"][0].pop("on_failure")
        support.write(path, json.dumps(data, indent=2) + "\n")
        report = support.run_pipeline(pkg)
        self.assertEqual(report["status"], "NOT_READY")
        self.assertIn("E_CLI_CHECK_INCOMPLETE", support.rule_ids(report))


if __name__ == "__main__":
    unittest.main()
