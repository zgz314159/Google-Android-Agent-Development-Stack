#!/usr/bin/env python3
"""Deterministic, offline tests for the P0B-CLOSE frozen-contract write guard.

No device, no network, no files written. Proves the ALLOW/BLOCK policy required by
AC-P0BC-003 (TASK-02):

  ALLOW: benchmark-source write, runtime lock creation, report/evidence output,
         read-only terminal commands
  BLOCK: app/src/main, app/src/test, app/src/androidTest, Testapp, PowerAi,
         governance files, the frozen P0B contract, the Evaluation Core,
         verification/core, any ambiguous write intent, and any write target
         outside every declared writable root (OUT_OF_CONTRACT_SCOPE, fail closed)

Run:  python3 -m unittest discover -s <this dir> -v
  or: python3 orchestration/hermes/evaluation_adapter/tests/test_contract_guard.py
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import contract_guard as guard  # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
# <repo>/orchestration/hermes/evaluation_adapter/tests -> <repo>
STACK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_HERE))))
PROJECTS = os.path.dirname(STACK)
RELAY = os.path.join(PROJECTS, "KeepLab-Relay")

# Frozen package under test: the real P0B-CLOSE contract, not a fixture.
PACKAGE = os.environ.get(
    "HERMES_CONTRACT_PACKAGE",
    os.path.join(RELAY, "specs", "p0b-close-benchmarkability"),
)


def load():
    return guard.load_contract(PACKAGE)


def decide(tool_name, tool_input, cwd=STACK, loaded=None):
    loaded = loaded or load()
    return guard.evaluate(tool_name=tool_name, tool_input=tool_input, cwd=cwd, loaded=loaded)


class ContractLoadTests(unittest.TestCase):
    def test_contract_loads_and_is_hash_verified(self):
        loaded = load()
        self.assertEqual(loaded["contract_id"], "KEEPLAB-P0B-CLOSE-001")
        self.assertIn(loaded["integrity"], ("MANIFEST_OK",))
        self.assertGreater(len(loaded["allowed"]), 5)
        self.assertGreater(len(loaded["forbidden"]), 20)

    def test_no_allowed_forbidden_overlap(self):
        loaded = load()
        for allowed in loaded["allowed"]:
            for forbidden in loaded["forbidden"]:
                self.assertFalse(
                    guard._inside(allowed.rstrip("/"), forbidden),
                    "allowed %r overlaps forbidden %r" % (allowed, forbidden),
                )
                self.assertFalse(
                    guard._inside(forbidden, allowed.rstrip("/")),
                    "forbidden %r overlaps allowed %r" % (forbidden, allowed),
                )

    def test_runtime_ephemeral_is_expressible(self):
        """The old P0B contradiction: verification/** forbidden while the device lock writes
        verification/.state/**. The new contract must classify the lock path as allowed."""
        v = decide("write_file", {"path": STACK + "/verification/.state/locks/device-87296ada.lock"})
        self.assertEqual(v["decision"], "ALLOW", v)
        self.assertEqual(v["class"], "RUNTIME_EPHEMERAL", v)
        # ...while the lock script itself stays frozen.
        b = decide("write_file", {"path": STACK + "/verification/core/device_lock.sh"})
        self.assertEqual(b["decision"], "BLOCK", b)


class AllowTests(unittest.TestCase):
    def setUp(self):
        self.loaded = load()

    def assert_allow(self, tool, args, expected_class=None, cwd=STACK):
        v = decide(tool, args, cwd=cwd, loaded=self.loaded)
        self.assertEqual(v["decision"], "ALLOW", v)
        if expected_class:
            self.assertEqual(v["class"], expected_class, v)
        return v

    def test_benchmark_source_write_is_allowed(self):
        self.assert_allow("write_file", {"path": RELAY + "/benchmark/lib/measure_close.py"},
                          "BENCHMARK_SOURCE")
        self.assert_allow("write_file",
                          {"path": RELAY + "/app/src/benchmark/java/com/keeplab/app/benchmark/BenchmarkSeeder.kt"},
                          "BENCHMARK_SOURCE")
        self.assert_allow("write_file", {"path": RELAY + "/app/src/benchmark/AndroidManifest.xml"},
                          "BENCHMARK_SOURCE")
        self.assert_allow("patch", {"path": RELAY + "/app/build.gradle.kts"}, "BENCHMARK_SOURCE")

    def test_runtime_lock_creation_is_allowed(self):
        self.assert_allow("write_file",
                          {"path": STACK + "/verification/.state/locks/device-87296ada.lock"},
                          "RUNTIME_EPHEMERAL")
        self.assert_allow("terminal",
                          {"command": "mkdir -p " + STACK + "/verification/.state/locks"},
                          "RUNTIME_EPHEMERAL")

    def test_evidence_and_report_output_is_allowed(self):
        self.assert_allow("write_file",
                          {"path": STACK + "/reports/P0B-CLOSE-BENCHMARKABILITY.md"},
                          "EVIDENCE_OUTPUT")
        self.assert_allow("write_file",
                          {"path": STACK + "/orchestration/hermes/evidence/p0b-close/audit.md"},
                          "EVIDENCE_OUTPUT")
        self.assert_allow("terminal",
                          {"command": "echo ok > " + STACK + "/reports/evidence/probe.txt"},
                          "EVIDENCE_OUTPUT")

    def test_read_only_terminal_commands_are_allowed(self):
        for cmd in (
            "find " + RELAY + " -type f | LC_ALL=C sort | xargs sha256sum",
            "adb shell dumpsys package com.keeplab.app",
            "python3 " + STACK + "/specification/compiler/validate_package.py /x --project-root " + PROJECTS,
            "grep -rn testTag " + RELAY + "/app/src/main/java --include=*.kt",
            "python3 " + STACK + "/orchestration/hermes/evidence/p0b-close/probe_sessions.py list",
            "echo hello",
        ):
            v = decide("terminal", {"command": cmd}, loaded=self.loaded)
            self.assertEqual(v["decision"], "ALLOW", (cmd, v))

    def test_out_of_contract_scope_write_fails_closed(self):
        """A write outside every declared writable root is now BLOCK, not ALLOW."""
        for tool, args in (
            ("write_file", {"path": "/tmp/p0b_close_probe.txt"}),
            ("write_file", {"path": os.path.join(os.path.expanduser("~"), ".hermes",
                                                 "profiles", "android-stack", "cache", "scratch", "x.json")}),
            ("terminal", {"command": "cp /etc/hosts /tmp/hosts.copy"}),
        ):
            v = decide(tool, args, loaded=self.loaded)
            self.assertEqual(v["decision"], "BLOCK", (tool, args, v))
            self.assertEqual(v["class"], "OUT_OF_CONTRACT_SCOPE", (tool, args, v))

    def test_relative_path_resolves_against_the_tool_workdir(self):
        v = decide("terminal", {"command": "mkdir -p benchmark/results/P0B-CLOSE",
                                "workdir": RELAY}, loaded=self.loaded)
        self.assertEqual(v["decision"], "ALLOW", v)

    def test_not_a_write_tool_is_allowed(self):
        v = decide("read_file", {"path": RELAY + "/app/src/main/java/com/keeplab/app/MainActivity.kt"},
                   loaded=self.loaded)
        self.assertEqual(v["decision"], "ALLOW", v)
        self.assertEqual(v["class"], "NOT_A_WRITE_TOOL", v)


class BlockTests(unittest.TestCase):
    def setUp(self):
        self.loaded = load()

    def assert_block(self, tool, args, cwd=STACK):
        v = decide(tool, args, cwd=cwd, loaded=self.loaded)
        self.assertEqual(v["decision"], "BLOCK", v)
        return v

    def test_app_src_main_is_blocked(self):
        v = self.assert_block("write_file",
                              {"path": RELAY + "/app/src/main/java/com/keeplab/app/MainActivity.kt"})
        self.assertEqual(v["class"], "PRODUCTION_IMMUTABLE", v)
        self.assert_block("patch", {"path": RELAY + "/app/src/main/res/values/strings.xml"})
        self.assert_block("terminal",
                          {"command": "sed -i 's/a/b/' " + RELAY + "/app/src/main/java/com/keeplab/app/MainActivity.kt"})

    def test_app_src_test_and_androidtest_are_blocked(self):
        self.assert_block("write_file",
                          {"path": RELAY + "/app/src/test/java/com/keeplab/app/HomeViewModelTest.kt"})
        self.assert_block("write_file",
                          {"path": RELAY + "/app/src/androidTest/java/com/keeplab/app/verify/FixtureSeeder.kt"})

    def test_testapp_and_powerai_are_blocked(self):
        v = self.assert_block("write_file", {"path": PROJECTS + "/Testapp/app/build.gradle.kts"})
        self.assertEqual(v["class"], "FORBIDDEN", v)
        self.assert_block("write_file", {"path": PROJECTS + "/PowerAi/anything.txt"})

    def test_governance_files_are_blocked(self):
        for path in (
            STACK + "/.hermes.md",
            RELAY + "/MISSION.md",
            RELAY + "/FACTORY_RULES.md",
            STACK + "/specification/compiler/build_contract.py",
        ):
            v = self.assert_block("write_file", {"path": path})
            self.assertEqual(v["class"], "PRODUCTION_IMMUTABLE", (path, v))

    def test_frozen_phase_surfaces_are_blocked(self):
        # PRODUCTION_IMMUTABLE class: governance, the compiler, the frozen Evaluation Core
        # semantics, the pinned Hermes identity and the frozen build inputs.
        for path in (
            RELAY + "/specs/p0b-performance-reliability/design.md",
            STACK + "/evaluation/commandcode/core.py",
            STACK + "/evaluation/commandcode/phase_rules.json",
            STACK + "/orchestration/hermes/HERMES-LOCK.json",
            RELAY + "/gradle.properties",
            RELAY + "/gradlew",
        ):
            v = self.assert_block("write_file", {"path": path})
            self.assertEqual(v["class"], "PRODUCTION_IMMUTABLE", (path, v))
        # FORBIDDEN class: frozen Stack subtrees that are invoked, never modified.
        for path in (
            STACK + "/verification/core/device_lock.sh",
            STACK + "/verification/reference-replay/runner/replay.py",
        ):
            v = self.assert_block("write_file", {"path": path})
            self.assertEqual(v["class"], "FORBIDDEN", (path, v))

    def test_unclassified_project_path_fails_closed(self):
        v = self.assert_block("write_file", {"path": RELAY + "/app/newfile.kt"})
        self.assertEqual(v["class"], "UNCLASSIFIED_FAIL_CLOSED", v)

    def test_terminal_destructive_commands_are_blocked(self):
        self.assert_block("terminal", {"command": "rm -rf " + RELAY + "/app/src/main"})
        self.assert_block("terminal",
                          {"command": "cd " + STACK + " && rm -f verification/core/device_lock.sh"})

    def test_ambiguous_write_intent_fails_closed(self):
        # A write verb with no resolvable target at all (here: an unset variable).
        v = decide("terminal", {"command": "rm -rf $TARGET_DIR", "workdir": ""}, cwd="", loaded=self.loaded)
        self.assertEqual(v["decision"], "BLOCK", v)
        self.assertEqual(v["class"], "AMBIGUOUS_WRITE_TARGET", v)
        # write_file without a path argument.
        self.assert_block("write_file", {})
        self.assert_block("patch", {"old_string": "a", "new_string": "b"})

    def test_false_positive_guards(self):
        """Legitimate commands whose argument shape must NOT be read as a protected write."""
        for cmd, cwd in (
            ("chmod +x " + RELAY + "/benchmark/run_p0b_close.sh", STACK),
            ("truncate -s 0 " + RELAY + "/benchmark/results/P0B-CLOSE/.keep", STACK),
            ("python3 -m unittest discover -s " + STACK + "/orchestration/hermes/evaluation_adapter/tests", STACK),
            ("unzip -l " + STACK + "/x.zip | grep -i com.android.test.properties", STACK),
        ):
            v = decide("terminal", {"command": cmd}, cwd=cwd, loaded=self.loaded)
            self.assertEqual(v["decision"], "ALLOW", (cmd, v))


class IntegrationTests(unittest.TestCase):
    def test_contract_hash_mismatch_fails_closed(self):
        loaded = load()
        loaded["integrity"] = "CONTRACT_HASH_MISMATCH:design.md"
        v = guard.evaluate(tool_name="write_file",
                           tool_input={"path": RELAY + "/benchmark/results/x.json"},
                           cwd=STACK, loaded=loaded)
        self.assertEqual(v["decision"], "BLOCK", v)
        self.assertEqual(v["class"], "CONTRACT_INTEGRITY_FAILURE", v)

    def test_missing_contract_fails_closed_via_cli_path(self):
        with self.assertRaises(RuntimeError):
            guard.load_contract("/nonexistent/package")

    def test_frozen_release_lane_is_derived_from_the_contract(self):
        """The guards must not hard-code a path list: removing an allowed path changes the verdict."""
        loaded = load()
        v = guard.evaluate(tool_name="write_file",
                           tool_input={"path": RELAY + "/benchmark/results/x.json"},
                           cwd=STACK, loaded=loaded)
        self.assertEqual(v["decision"], "ALLOW", v)
        loaded["allowed"] = [p for p in loaded["allowed"] if "KeepLab-Relay/benchmark" not in p]
        v2 = guard.evaluate(tool_name="write_file",
                            tool_input={"path": RELAY + "/benchmark/results/x.json"},
                            cwd=STACK, loaded=loaded)
        self.assertEqual(v2["decision"], "BLOCK", v2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
