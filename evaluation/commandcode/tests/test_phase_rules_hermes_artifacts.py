#!/usr/bin/env python3
"""WAVE1A phase-rule regression tests — Hermes-native artifact classification.

Contract: STACK-SIMPLIFICATION-S2-WAVE1A-001  (TASK-02, AC-W1A-005 / AC-W1A-006)

Pins the deterministic classification of the seven M4 spans that were UNKNOWN because they were
Hermes-native artifacts (scratch tooling, the ``tool_call`` / ``process_manage`` wrapper, and an
``orchestration/hermes/evidence/**`` result write). Like the sibling device-classification test,
this applies the DECLARED rule conditions directly, imports no ``core.py``, runs offline and
touches no device.

The evidence strings below are the exact frozen M4 transcript strings (acceptance.md section 3).
"""

from __future__ import annotations

import json
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
RULE_FILE = os.path.join(os.path.dirname(HERE), "phase_rules.json")


def load_rules() -> list:
    with open(RULE_FILE, "r", encoding="utf-8") as fh:
        return json.load(fh)["rules"]


def _match(rule: dict, item: dict) -> bool:
    tools = rule.get("tools")
    if tools and item["name"] not in tools:
        return False
    for field_name, probe in (
        ("tool_regex", item["name"]),
        ("subagent_regex", item.get("subagent", "")),
        ("command_regex", item.get("command", "")),
        ("path_regex", item.get("path", "")),
        ("result_regex", item.get("result", "")),
    ):
        rx = rule.get(field_name)
        if rx and not re.search(rx, probe or ""):
            return False
    return True


def classify(rules: list, item: dict) -> dict:
    for rule in rules:
        if _match(rule, item):
            return {"phase": rule["phase"], "subphase": rule.get("subphase"),
                    "time_class": rule.get("time_class"), "wait_tag": rule.get("wait_tag"),
                    "rule_id": rule["id"]}
    return {"phase": "UNKNOWN", "subphase": None, "time_class": None,
            "wait_tag": None, "rule_id": "no_rule_match"}


def shell_item(command: str) -> dict:
    return {"name": "shell_command", "command": command, "path": "", "result": "", "subagent": ""}


def write_item(path: str, name: str = "write_file") -> dict:
    return {"name": name, "command": "", "path": path, "result": "", "subagent": ""}


# --------------------------------------------------------------------------- #
# exact frozen M4 evidence strings (acceptance.md section 3)
# --------------------------------------------------------------------------- #
SCRATCH_ROOT = "/home/zhong/.hermes/profiles/android-stack/cache/scratch"
EVIDENCE_WRITE = ("/mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack/"
                  "orchestration/hermes/evidence/keeplab-m4-attachments/post-run-proof.json")

SCRATCH_SPANS = {
    "TURN-0010 (shell_command)": shell_item(
        "cd %s && python3 m4_verify_frozen.py" % SCRATCH_ROOT),
    "TURN-0097 (write_file)": write_item("%s/m4_postrun_proof.py" % SCRATCH_ROOT, "write_file"),
    "TURN-0099 (edit_file)": write_item("%s/m4_postrun_proof.py" % SCRATCH_ROOT, "edit_file"),
    "TURN-0101 (write_file)": write_item("%s/m4_secret_scan.py" % SCRATCH_ROOT, "write_file"),
}

# The Hermes wrapper tool: name tool_call, its input nests process_manage. The core's effective
# item carries name='tool_call', command='' (no 'command'/'description' key) and path=''.
WRAPPER_SPANS = {
    "TURN-0052 (tool_call/process_manage)": {
        "name": "tool_call", "command": "", "path": "",
        "result": json.dumps({"calls": [{"arguments": {"session_id": "proc_5e7ec6f68cde"},
                                         "name": "process_manage"}]}), "subagent": ""},
    "TURN-0053 (tool_call/process_manage)": {
        "name": "tool_call", "command": "", "path": "",
        "result": json.dumps({"calls": [{"arguments": {"action": "wait",
                                                      "session_id": "proc_5e7ec6f68cde",
                                                      "timeout": 420},
                                        "name": "process_manage"}]}), "subagent": ""},
}


class ScratchToolingTests(unittest.TestCase):
    def test_hermes_scratch_spans_are_T2_necessary_overhead(self):
        rules = load_rules()
        for label, item in SCRATCH_SPANS.items():
            with self.subTest(span=label):
                got = classify(rules, item)
                self.assertEqual(got["phase"], "T2", "%s -> %s" % (label, got))
                self.assertEqual(got["time_class"], "NECESSARY_OVERHEAD", "%s -> %s" % (label, got))

    def test_scratch_signatures_are_token_bounded(self):
        rules = load_rules()
        # a token-bounded '.hermes/<profile>/cache/scratch' signature classifies as scratch ...
        self.assertEqual(classify(rules, shell_item(
            "cd %s && python3 proof.py" % SCRATCH_ROOT))["phase"], "T2")
        self.assertEqual(classify(rules, write_item(
            "%s/proof.py" % SCRATCH_ROOT))["phase"], "T2")
        # ... but an unrelated path that merely contains the word 'scratch' does not have to.
        got = classify(rules, write_item("/mnt/AndroidDev/Projects/KeepLab-Relay/"
                                         "docs/scratching_notes.md"))
        self.assertNotEqual(got["rule_id"], "t2_scratch_tooling")


class WrapperToolCallTests(unittest.TestCase):
    def test_wrapper_spans_use_the_dedicated_rule(self):
        rules = load_rules()
        for label, item in WRAPPER_SPANS.items():
            with self.subTest(span=label):
                got = classify(rules, item)
                self.assertEqual(got["phase"], "T2", "%s -> %s" % (label, got))
                self.assertEqual(got["time_class"], "NECESSARY_OVERHEAD", "%s -> %s" % (label, got))
                self.assertEqual(got["wait_tag"], "WAIT_TOOL", "%s -> %s" % (label, got))
                self.assertEqual(got["rule_id"], "t2_wrapper_tool_call", "%s -> %s" % (label, got))

    def test_wrapper_rule_is_its_own_rule_not_an_alias(self):
        rules = load_rules()
        rule = next(r for r in rules if r["id"] == "t2_wrapper_tool_call")
        self.assertEqual(sorted(rule["tools"]), ["process_manage", "tool_call"])


class EvidenceWriteTests(unittest.TestCase):
    def test_evidence_path_write_is_T9_productive(self):
        rules = load_rules()
        got = classify(rules, write_item(EVIDENCE_WRITE))
        self.assertEqual(got["phase"], "T9", got)
        self.assertEqual(got["time_class"], "PRODUCTIVE", got)

    def test_evidence_rule_covers_the_declared_extensions(self):
        rules = load_rules()
        for suffix in ("json", "jsonl", "md", "csv", "txt"):
            with self.subTest(suffix=suffix):
                got = classify(rules, write_item(
                    "/mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack/"
                    "orchestration/hermes/evidence/stack-simplification-s2-wave1a/x.%s" % suffix))
                self.assertEqual(got["phase"], "T9", "%s -> %s" % (suffix, got))

    def test_evidence_rule_also_covers_the_external_live_destination(self):
        # The live evidence destination is now outside the project (STACK_DATA_ROOT/artifacts).
        rules = load_rules()
        external = ("/home/operator/.local/share/google-android-agent-stack/artifacts/"
                    "evaluation/Proj/RUN-ID/run.json")
        got = classify(rules, write_item(external))
        self.assertEqual(got["phase"], "T9", got)
        self.assertEqual(got["time_class"], "PRODUCTIVE", got)


class AliasPreservationTests(unittest.TestCase):
    """The fix must not have forced tool_call onto a Command Code tool name."""

    def test_wrapper_tool_is_never_aliased(self):
        import importlib.util
        src = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))),
                           "orchestration", "hermes", "evaluation_adapter",
                           "hermes_session_source.py")
        spec = importlib.util.spec_from_file_location("hermes_session_source_under_test", src)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertNotIn("tool_call", mod.HERMES_TOOL_ALIAS)
        self.assertNotIn("process_manage", mod.HERMES_TOOL_ALIAS)
        self.assertEqual(mod.canonical_tool_name("tool_call"), "tool_call")
        self.assertEqual(mod.canonical_tool_name("process_manage"), "process_manage")
        # the pre-existing successful mappings must be preserved
        self.assertEqual(mod.HERMES_TOOL_ALIAS["terminal"], "shell_command")
        self.assertEqual(mod.HERMES_TOOL_ALIAS["patch"], "edit_file")
        self.assertEqual(mod.HERMES_TOOL_ALIAS["search_files"], "grep")


if __name__ == "__main__":
    unittest.main(verbosity=2)
