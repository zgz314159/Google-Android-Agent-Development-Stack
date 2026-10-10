#!/usr/bin/env python3
"""WAVE1A phase-rule regression tests — device-evidence classification.

Contract: STACK-SIMPLIFICATION-S2-WAVE1A-001  (TASK-01 / TASK-02, AC-W1A-001..003)

These tests apply the DECLARED rule conditions of ``evaluation/commandcode/phase_rules.json``
directly to synthetic items, exactly as the frozen Evaluation Core does
(``core.py::PhaseMapper._match`` -> first rule whose declared conditions ALL match an item),
but WITHOUT importing ``core.py``. They are offline, deterministic, touch no device and write
nothing.

Covered:
  * section 2.1 — the three exact M4 false-positive commands (plus the other non-device classes)
    must NOT resolve to T7 / T7c / WAIT_DEVICE;
  * section 2.2 — genuine device/evidence commands must STILL resolve to T7 + WAIT_DEVICE;
  * the rule table stays valid ordered JSON with unique ids and no id removed.
"""

from __future__ import annotations

import json
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
RULE_FILE = os.path.join(os.path.dirname(HERE), "phase_rules.json")

# The 50 rule ids that existed before the WAVE1A edit. A deliberate WAVE1A edit may ADD ids
# (t2_scratch_tooling_cmd / t2_wrapper_tool_call / t9_evidence_write); removing any of these is a
# regression and fails the test.
BASELINE_RULE_IDS = [
    "t3_plan_mode_enter", "t3_plan_mode_exit", "t3_clarification", "t3_plan_review",
    "t2_agent_explore", "t3_agent_plan", "t2_agent_output",
    "t9_handoff_artifact", "t9_result_file", "t9_factory_record", "t9_report_cmd",
    "t9_git_commit", "t9_agent_review",
    "t6_gradle_test", "t6_harness_device", "t6_harness_ci", "t6_test_path", "t6_harness_path",
    "t6_maestro_def", "t6_test_runner",
    "t5_gradle_build", "t5_gradle_generic",
    "t7a_deploy", "t7a_device_props", "t7a_kill_shell", "t7_verification_run", "t7b_ui",
    "t7c_evidence_cmd", "t7c_image_read", "t7c_state_read",
    "t4_impl_code", "t4_impl_dir",
    "t3_plan_write", "t3_plan_mode_file", "t3_docs_write", "t3_plan_read", "t3_workflow_scripts",
    "t9_readme", "t6_verification_tree",
    "t1b_provider_probe", "t1b_provider_env", "t1b_bootstrap", "t1b_studio_check",
    "t1a_routing_read", "t1a_routing_cmd",
    "t2_tool_discovery", "t2_explore_cmd", "t2_scratch_tooling", "t3_todo", "t2_read_any",
]

# --------------------------------------------------------------------------- #
# sections 2.1 / 2.2 command sets (verbatim from acceptance.md)
# --------------------------------------------------------------------------- #
FP_TURN_0018 = (
    'cd /mnt/AndroidDev/Projects/KeepLab-Relay; wc -l app/build.gradle.kts '
    'gradle/libs.versions.toml app/src/main/AndroidManifest.xml app/src/test -R 2>/dev/null '
    '| tail -5; find app/src/test -name "*.kt" | xargs wc -l | sort -n'
)
FP_TURN_0110 = (
    'cd /mnt/AndroidDev/Projects/KeepLab-Relay && f=$(find app/build/intermediates -name '
    '"AndroidManifest.xml" -path "*merged*" | head -1); echo "MERGED: $f"; grep -o '
    "'android:name=\"android.permission[^\"]*\"' \"$f\" 2>/dev/null | sort -u; "
    'echo "--- FileProvider present? ---"; grep -c "provider" "$f" 2>/dev/null'
)
FP_TURN_0111 = (
    'cd /mnt/AndroidDev/Projects/KeepLab-Relay && f=app/build/intermediates/merged_manifests/'
    'debug/processDebugManifest/AndroidManifest.xml; grep -o '
    "'android:name=\"[^\"]*provider[^\"]*\"' \"$f\" | sort -u; "
    'echo "--- fileprovider mentions ---"; grep -ci "fileprovider" "$f"; '
    'echo "--- source manifest mtime/unchanged ---"; ls -l app/src/main/AndroidManifest.xml; '
    'find app/build/intermediates/merged_manifests -name "*.xml" | wc -l'
)

FALSE_POSITIVE_COMMANDS = {
    "TURN-0018 (h000061)": FP_TURN_0018,
    "TURN-0110 (h000351)": FP_TURN_0110,
    "TURN-0111 (h000353)": FP_TURN_0111,
    "build/intermediates manifest inspection": (
        'cd /mnt/AndroidDev/Projects/KeepLab-Relay && ls app/build/intermediates/merged_manifests'
        '/debug/processDebugManifest/AndroidManifest.xml'
    ),
    "test-results.xml inspection": (
        'cd /mnt/AndroidDev/Projects/KeepLab-Relay && cat backend/build/test-results/test/'
        'TEST-com.keeplab.backend.SyncRoutesTest.xml | head -40'
    ),
    "androidTest-results inspection": (
        'cd /mnt/AndroidDev/Projects/KeepLab-Relay && find app/build/outputs/androidTest-results '
        '-name "*.xml" | wc -l'
    ),
    "rebuild dir listing": (
        'cd /mnt/AndroidDev/Projects/KeepLab-Relay && ls -la app/rebuild/AndroidManifest.xml'
    ),
    "pure wc/find/grep over source": (
        'cd /mnt/AndroidDev/Projects/KeepLab-Relay/app/src/main && find . -name "*.kt" | '
        'xargs wc -l | sort -n'
    ),
    "buildDir path reference": (
        'cd /mnt/AndroidDev/Projects/KeepLab-Relay && ls "$buildDir"/intermediates/'
        'AndroidManifest.xml'
    ),
}

DEVICE_COMMANDS = {
    "uiautomator dump": "adb shell uiautomator dump /sdcard/window_dump.xml",
    "screencap": "adb exec-out screencap -p > /tmp/screen.png",
    "dumpsys window": "adb shell dumpsys window windows",
    "dumpsys activity": "adb shell dumpsys activity",
    "getprop": "adb shell getprop ro.product.model",
    "logcat": "adb logcat -d > logcat.txt",
    "input tap": "adb shell input tap 540 1200",
    "input text": "adb shell input text 'hello'",
    "input keyevent": "adb shell input keyevent 4",
}

DEVICE_EVIDENCE_READS = {
    "window_dump xml": "/mnt/AndroidDev/Projects/KeepLab-Relay/.evidence/window_dump_1.xml",
    "layout json": "/mnt/AndroidDev/Projects/KeepLab-Relay/.evidence/layout_1.json",
    "final_state json": "/mnt/AndroidDev/Projects/KeepLab-Relay/.evidence/final_state_1.json",
    "logcat txt": "/mnt/AndroidDev/Projects/KeepLab-Relay/.evidence/logcat_1.txt",
}


# --------------------------------------------------------------------------- #
# minimal, dependency-free re-implementation of core.PhaseMapper rule matching
# (conditions: tools exact list, tool_regex, subagent_regex, command_regex,
#  path_regex, result_regex — matched with re.search, case flags inside the regex)
# --------------------------------------------------------------------------- #
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


def load_rules() -> list:
    with open(RULE_FILE, "r", encoding="utf-8") as fh:
        return json.load(fh)["rules"]


def classify(rules: list, item: dict) -> dict:
    """First rule whose declared conditions all match -> its assignment; else UNKNOWN."""
    for rule in rules:
        if _match(rule, item):
            return {
                "phase": rule["phase"],
                "subphase": rule.get("subphase"),
                "wait_tag": rule.get("wait_tag"),
                "rule_id": rule["id"],
            }
    return {"phase": "UNKNOWN", "subphase": None, "wait_tag": None, "rule_id": "no_rule_match"}


def shell_item(command: str) -> dict:
    return {"name": "shell_command", "command": command, "path": "", "result": "", "subagent": ""}


def read_item(path: str) -> dict:
    return {"name": "read_file", "command": "", "path": path, "result": "", "subagent": ""}


class RuleTableIntegrityTests(unittest.TestCase):
    def test_table_is_valid_ordered_json_with_unique_ids(self):
        rules = load_rules()
        self.assertIsInstance(rules, list)
        self.assertTrue(rules, "rule table must not be empty")
        ids = [r["id"] for r in rules]
        self.assertEqual(len(ids), len(set(ids)), "duplicate rule ids: %r" % ids)

    def test_no_baseline_rule_id_was_removed(self):
        ids = set(r["id"] for r in load_rules())
        missing = [rid for rid in BASELINE_RULE_IDS if rid not in ids]
        self.assertEqual(missing, [], "rule ids removed: %r" % missing)

    def test_offending_unbounded_alternative_is_gone(self):
        rule = next(r for r in load_rules() if r["id"] == "t7c_evidence_cmd")
        rx = rule["command_regex"]
        # the old alternative let 'ui' match inside 'build'
        self.assertNotIn("(layout|ui|window_dump)", rx)
        # 'ui' must now be bounded by a non-word boundary and an evidence-file suffix
        self.assertIn("(?<![A-Za-z0-9_])(layout|window_dump|ui)", rx)


class FalsePositiveTests(unittest.TestCase):
    """AC-W1A-001 / AC-W1A-003 — section 2.1 commands must not be device evidence."""

    def test_false_positive_commands_are_not_device(self):
        rules = load_rules()
        for label, command in FALSE_POSITIVE_COMMANDS.items():
            with self.subTest(command=label):
                got = classify(rules, shell_item(command))
                self.assertNotEqual(got["phase"], "T7",
                                    "%s classified %s via %s" % (label, got, got["rule_id"]))
                self.assertNotEqual(got["subphase"], "T7c",
                                    "%s classified %s" % (label, got))
                self.assertNotEqual(got["wait_tag"], "WAIT_DEVICE",
                                    "%s classified %s" % (label, got))

    def test_ui_inside_build_never_matches_device_rule(self):
        rule = next(r for r in load_rules() if r["id"] == "t7c_evidence_cmd")
        rx = rule["command_regex"]
        for probe in (
            'ls app/build/AndroidManifest.xml',
            'ls app/buildDir/AndroidManifest.xml',
            'ls app/rebuild/AndroidManifest.xml',
            'find app/build/intermediates -name "AndroidManifest.xml"',
        ):
            with self.subTest(probe=probe):
                self.assertIsNone(re.search(rx, probe), probe)


class DeviceCoverageTests(unittest.TestCase):
    """AC-W1A-002 — section 2.2 device evidence must still be T7 / WAIT_DEVICE."""

    def test_device_commands_still_classify_as_device(self):
        rules = load_rules()
        for label, command in DEVICE_COMMANDS.items():
            with self.subTest(command=label):
                got = classify(rules, shell_item(command))
                self.assertEqual(got["phase"], "T7", "%s -> %s" % (label, got))
                self.assertEqual(got["wait_tag"], "WAIT_DEVICE", "%s -> %s" % (label, got))

    def test_saved_device_evidence_reads_still_classify_as_device(self):
        rules = load_rules()
        for label, path in DEVICE_EVIDENCE_READS.items():
            with self.subTest(read=label):
                got = classify(rules, read_item(path))
                self.assertEqual(got["phase"], "T7", "%s -> %s" % (label, got))
                self.assertEqual(got["subphase"], "T7c", "%s -> %s" % (label, got))
                self.assertEqual(got["wait_tag"], "WAIT_DEVICE", "%s -> %s" % (label, got))

    def test_t7c_evidence_cmd_still_matches_a_saved_window_dump_reference(self):
        rules = load_rules()
        got = classify(rules, shell_item("cat /sdcard/window_dump.xml"))
        self.assertEqual(got["phase"], "T7")
        self.assertEqual(got["wait_tag"], "WAIT_DEVICE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
