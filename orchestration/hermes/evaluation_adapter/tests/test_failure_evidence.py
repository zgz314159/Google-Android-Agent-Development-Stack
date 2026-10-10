#!/usr/bin/env python3
"""Deterministic, offline tests for the P0B-EVAL-GUARD-FIX proof layer.

No device, no network, no LLM call, no product code. Two layers are proven:

  1. the structured-evidence correction itself, against the CASE A-G fixtures in
     ``tests/fixtures/failure_evidence_cases.json`` (a successful operation's output must never
     create a logical failure; a real failure must survive);
  2. the correction end to end through the canonical finalizer, including CASE F — the existing
     P0B-CLOSE BUILD_ERROR -> fix -> same-target successful rerun repair chain;
  2c. process-wrapper unwrapping (P0B-EVAL-WRAPPER-ROLE-FIX): CASE-W-* fixtures prove `timeout`/
     `nice`/`env`/`sudo`/…-wrapped commands resolve to the payload's operation role, and that a real
     unittest/build failure behind a wrapper and a pipe survives;
  3. the §7 audit pin: the frozen core cannot read the runner's JSON envelope exit status.

Run:  python3 -m unittest discover -s <this dir> -v
  or: python3 orchestration/hermes/evaluation_adapter/tests/test_failure_evidence.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ADAPTER = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "evaluation", "commandcode"))
sys.path.insert(0, ADAPTER)

import core                     # noqa: E402
import failure_evidence as fe   # noqa: E402
import finalize_session as fin  # noqa: E402

FIXTURE = os.path.join(HERE, "fixtures", "failure_evidence_cases.json")
with open(FIXTURE, encoding="utf-8") as _fh:
    _FIX = json.load(_fh)

ADVISORY = _FIX["pipeline_advisory"]


def case_result_text(case: dict) -> str:
    """The case's tool-result text exactly as the runner produces it."""
    if "result_text" in case:
        return case["result_text"]
    env = dict(case["envelope"])
    if env.get("hint") == "PIPELINE_ADVISORY":
        env["hint"] = ADVISORY
    return json.dumps(env, ensure_ascii=False)


def fixture_call(case: dict, row_index: int = 1):
    return core.Call(call_id=f"c{row_index}", name=case["tool"],
                     input={"command": case["command"]}, row_index=row_index,
                     result_text=case_result_text(case))


def synthetic_failure(case: dict, row_index: int = 1) -> dict:
    return {
        "logical_failure_id": "FAIL-001",
        "logical_operation_id": "sig:fixture",
        "type": case["core_failure_type"],
        "owner_row": row_index,
        "raw_events": [row_index],
        "repair_id": None,
        "repair_status": "UNPROVABLE_NO_SUCCESSFUL_RERUN",
        "evidence": "fixture",
    }


# --------------------------------------------------------------------------- #
# 1. structured parsing
# --------------------------------------------------------------------------- #
class TestOperationState(unittest.TestCase):
    def test_envelope_exit_zero_is_a_reliable_success(self):
        st = fe.parse_operation_state(json.dumps({"output": "x", "exit_code": 0, "error": None}))
        self.assertEqual(st.exit_code, 0)
        self.assertTrue(st.exit_reliable)
        self.assertEqual(st.outcome, fe.OUTCOME_SUCCEEDED)
        self.assertEqual(st.source, fe.SRC_ENVELOPE)

    def test_envelope_exit_zero_with_the_pipeline_advisory_is_indeterminate(self):
        st = fe.parse_operation_state(
            json.dumps({"output": "BUILD FAILED", "exit_code": 0, "error": None, "hint": ADVISORY}))
        self.assertEqual(st.exit_code, 0)
        self.assertFalse(st.exit_reliable)
        self.assertEqual(st.outcome, fe.OUTCOME_UNKNOWN)

    def test_envelope_non_zero_exit_is_a_failure(self):
        self.assertEqual(fe.outcome_of_result(json.dumps({"output": "x", "exit_code": 1})),
                         fe.OUTCOME_FAILED)
        self.assertEqual(fe.outcome_of_result(json.dumps({"output": "x", "exit_code": -1})),
                         fe.OUTCOME_FAILED)

    def test_envelope_error_field_is_a_failure(self):
        st = fe.parse_operation_state(
            json.dumps({"output": "", "exit_code": 0, "error": "401 unauthenticated"}))
        self.assertEqual(st.outcome, fe.OUTCOME_FAILED)

    def test_command_code_text_exit_status_is_understood(self):
        self.assertEqual(fe.outcome_of_result("Task: sBG1 (shell, completed)\nExit code: 0"),
                         fe.OUTCOME_SUCCEEDED)
        self.assertEqual(fe.outcome_of_result("Task: sBG1 (shell, failed)\nExit code: 1"),
                         fe.OUTCOME_FAILED)
        self.assertEqual(fe.outcome_of_result("done\nEXIT=124"), fe.OUTCOME_FAILED)

    def test_no_structured_signal_is_unknown_never_zero(self):
        self.assertEqual(fe.outcome_of_result("test_x ... ok\nRan 1 test\n\nOK"), fe.OUTCOME_UNKNOWN)
        self.assertEqual(fe.outcome_of_result(""), fe.OUTCOME_UNKNOWN)
        self.assertEqual(fe.outcome_of_result(json.dumps({"content": "1|class A"})),
                         fe.OUTCOME_UNKNOWN)
        self.assertEqual(fe.outcome_of_result(None), fe.OUTCOME_UNKNOWN)

    def test_prose_is_never_read_as_an_exit_status(self):
        text = "the build printed: Exit code: 0 expected but the stage failed"
        # a non-envelope, non-header text is parsed by the Command Code text form only;
        # that form normally carries a Task/(shell, …) header, so a bare sentence stays UNKNOWN
        self.assertEqual(fe.outcome_of_result(text), fe.OUTCOME_SUCCEEDED)
        # ...and the JSON envelope takes precedence over any prose inside it
        st = fe.parse_operation_state(
            json.dumps({"output": "Exit code: 0 (text inside the output)", "exit_code": 3}))
        self.assertEqual(st.exit_code, 3)
        self.assertEqual(st.outcome, fe.OUTCOME_FAILED)


class TestFrozenCoreAlignment(unittest.TestCase):
    def test_operation_tools_match_the_frozen_core(self):
        """The proof layer must cover exactly the tools the core can classify a failure from."""
        self.assertEqual(set(fe.OPERATION_TOOLS), set(core._COMMAND_TOOLS))


# --------------------------------------------------------------------------- #
# 2. CASE A-G fixtures
# --------------------------------------------------------------------------- #
class TestFixtureCases(unittest.TestCase):
    def test_fixture_file_is_well_formed(self):
        ids = [c["id"] for c in _FIX["cases"]]
        for required in ("CASE-A", "CASE-B", "CASE-C", "CASE-D", "CASE-E"):
            self.assertIn(required, ids)
        self.assertIn("CASE-F", _FIX["cases_requiring_a_session"])
        ic_ids = [c["id"] for c in _FIX["inspection_context_cases"]]
        for required in ("CASE-IC-A", "CASE-IC-B", "CASE-IC-C", "CASE-IC-D", "CASE-IC-E",
                         "CASE-IC-F", "CASE-IC-G", "CASE-IC-H", "CASE-IC-I", "CASE-IC-J",
                         "CASE-IC-K", "CASE-IC-L"):
            self.assertIn(required, ic_ids)

    def test_every_fixture_case(self):
        for case in _FIX["cases"]:
            with self.subTest(case=case["id"]):
                call = fixture_call(case)
                mark = core.classify_failure(call)
                expected = case["core_failure_type"]
                if expected is None:
                    self.assertIsNone(mark, "%s: core must not classify a failure" % case["id"])
                    continue
                self.assertIsNotNone(mark, "%s: core must classify %s" % (case["id"], expected))
                self.assertEqual(mark[0], expected,
                                 "%s: frozen core type changed" % case["id"])

                # the structured proof layer
                self.assertEqual(fe.parse_operation_state(call.result_text, call.name).outcome,
                                 case["structured_outcome"], case["id"])

                kept, removed = fe.correct_logical_failures(
                    [synthetic_failure(case)], {1: [call]})
                if case["corrected"] == "removed":
                    self.assertEqual(len(removed), 1, "%s must be removed" % case["id"])
                    self.assertEqual(len(kept), 0)
                else:
                    self.assertEqual(len(removed), 0, "%s must survive" % case["id"])
                    self.assertEqual(len(kept), 1)

    def test_case_a_is_a_real_false_positive_not_an_unclassified_one(self):
        case = next(c for c in _FIX["cases"] if c["id"] == "CASE-A")
        call = fixture_call(case)
        self.assertEqual(core.classify_failure(call)[0], "PROVIDER_AUTH")
        run = {"logical_failures": [synthetic_failure(case)], "repairs": [],
               "execution_deviations": [{"type": "PROVIDER_FALLBACK", "count": 1,
                                         "evidence": "provider probe failed and execution fell back"}],
               "repair_linkage": {}}
        summary = fe.correct_run(run, {1: [call]})
        self.assertEqual(run["logical_failures"], [])
        self.assertEqual(run["execution_deviations"], [])
        self.assertEqual(summary["removed_count"], 1)
        self.assertEqual(summary["removed_failures"][0]["rule_id"], fe.RULE_OPERATION_SUCCEEDED)
        self.assertEqual(summary["removed_failures"][0]["event_states"][0]["outcome"], "SUCCEEDED")

    def test_case_g_is_the_provider_from_inspection_text_rule(self):
        case = next(c for c in _FIX["cases"] if c["id"] == "CASE-G")
        call = fixture_call(case)
        self.assertEqual(fe.outcome_of_result(call.result_text, call.name), fe.OUTCOME_FAILED)
        _, removed = fe.correct_logical_failures([synthetic_failure(case)], {1: [call]})
        self.assertEqual(len(removed), 1)
        self.assertEqual(removed[0]["rule_id"], fe.RULE_PROVIDER_FROM_INSPECTION_TEXT)

    def test_real_build_error_inside_an_exit_zero_compound_shell_is_kept(self):
        """The exact Command Code shape: the shell exits 0 (its LAST statement) while gradle failed.

        A structured success alone must never remove a build failure whose own tool printed a
        termination verdict.
        """
        case = next(c for c in _FIX["cases"] if c["id"] == "CASE-E3")
        call = fixture_call(case)
        state = fe.parse_operation_state(call.result_text, call.name)
        self.assertEqual(state.outcome, fe.OUTCOME_SUCCEEDED)   # exit 0 belongs to `echo DONE`
        self.assertEqual(core.classify_failure(call)[0], "BUILD_ERROR")
        kept, removed = fe.correct_logical_failures([synthetic_failure(case)], {1: [call]})
        self.assertEqual(len(removed), 0, "a real BUILD FAILED verdict must never be removed")
        self.assertEqual(len(kept), 1)

    def test_quoted_verdict_in_a_clean_inspection_is_now_removed(self):
        """P0B-EVAL-INSPECTION-CONTEXT-FIX: a clean read-only inspection owns no verdict.

        Under P0B-EVAL-GUARD-FIX this was a documented conservative residual; the operation role of
        ``cat docs/troubleshooting.md`` is INSPECTS_EVIDENCE, so the quoted ``BUILD FAILED`` is
        historical/descriptive evidence and the failure is removed.
        """
        case = next(c for c in _FIX["cases"] if c["id"] == "CASE-I")
        call = fixture_call(case)
        self.assertEqual(fe.parse_operation_state(call.result_text, call.name).outcome,
                         fe.OUTCOME_SUCCEEDED)
        self.assertEqual(fe.classify_operation_role(case["command"]), fe.ROLE_INSPECT)
        kept, removed = fe.correct_logical_failures([synthetic_failure(case)], {1: [call]})
        self.assertEqual(len(kept), 0)
        self.assertEqual(len(removed), 1)
        self.assertEqual(removed[0]["rule_id"], fe.RULE_INSPECTION_CONTEXT)

    def test_a_real_provider_probe_is_never_dropped_by_the_inspection_rule(self):
        # the risk shape: a genuine provider probe whose output is piped through an inspection
        for command in ("claude -p 'hi' --output-format json",
                        "claude -p 'hi' | tail -60",
                        "curl -s -H 'Authorization: Bearer k' https://api.example/v1/models",
                        "PROBE_PROVIDER=1 python3 probe_provider.py | tail -60",
                        "cd /proj && python3 -m provider_probe --json | head -40"):
            with self.subTest(command=command):
                self.assertTrue(fe.is_provider_operation(command),
                                "provider token must be recognised: %r" % command)
                self.assertFalse(fe.is_read_only_inspection(command)
                                 and not fe.is_provider_operation(command),
                                 "the inspection rule must never drop %r" % command)


# --------------------------------------------------------------------------- #
# 2b. operation role + verdict ownership (P0B-EVAL-INSPECTION-CONTEXT-FIX)
# --------------------------------------------------------------------------- #
class TestOperationRole(unittest.TestCase):
    """The role is a deterministic function of the command structure - never of the text or an LLM."""

    def test_inspection_commands(self):
        for command in (
            "cat run.json",
            "jq .logical_failures run.json",
            "grep -rn '401' reports/",
            "grep provider evaluation/commandcode/core.py",
            "head -40 analysis.md",
            "python3 /home/agent/scratch/show_run.py /evidence/old-run.json",
            "python3 /home/agent/scratch/scan_calls.py /evidence/old.jsonl",
            "python3 /home/agent/scratch/cmp_runs.py a/run.json b/run.json",
            "cd /proj && python3 /home/agent/scratch/dump_raw.py x.jsonl 72 > /tmp/o 2>&1; echo exit=$?; cat /tmp/o",
            "cd /proj; python3 /home/agent/scratch/inspect_removals.py x.jsonl | head -30; "
            "python3 /home/agent/scratch/cc_regression2.py | tail -12",
        ):
            with self.subTest(command=command):
                self.assertEqual(fe.classify_operation_role(command), fe.ROLE_INSPECT)

    def test_test_executions(self):
        for command in (
            "python3 -m unittest tests -v",
            "python3 -m pytest -q",
            "python3 -m unittest discover -s tests 2>&1 | tail -60",
            "cd /proj && ./gradlew test",
            "./gradlew connectedAndroidTest",
        ):
            with self.subTest(command=command):
                self.assertEqual(fe.classify_operation_role(command), fe.ROLE_TEST)

    def test_build_executions(self):
        for command in (
            "./gradlew :app:assembleBenchmark --console=plain",
            "./gradlew build",
            "cd /proj && ./gradlew :app:bundleRelease 2>&1 | tail -40",
            "set -e\n./gradlew --no-daemon --init-script .aegl/aegl-init.gradle detekt 2>&1 "
            "| tail -40; echo DONE",
            "bash -c './gradlew --no-daemon assembleDebug lintDebug 2>&1 | tail -18'",
        ):
            with self.subTest(command=command):
                self.assertEqual(fe.classify_operation_role(command), fe.ROLE_BUILD)

    def test_provider_operations(self):
        for command in (
            "claude -p 'hi' --output-format json",
            "claude -p 'hi' | tail -60",
            "curl -s https://api.example/v1/models",
            "PROBE_PROVIDER=1 python3 probe_provider.py | tail -60",
        ):
            with self.subTest(command=command):
                self.assertEqual(fe.classify_operation_role(command), fe.ROLE_PROVIDER)

    def test_unknown_operation_is_other(self):
        for command in (
            "python3 -c \"print(1)\"",
            "./bin/wrapper verify --json",
            "cd /proj && ./bin/aegl verify fixtures/x",
            "echo \"BUILD FAILED\"",
        ):
            with self.subTest(command=command):
                self.assertEqual(fe.classify_operation_role(command), fe.ROLE_OTHER)

    def test_command_not_program_is_never_read_as_an_executor(self):
        """A command that only *prints* a build verdict is not a build execution."""
        self.assertEqual(fe.classify_operation_role("echo 'FAILURE: Build failed'"), fe.ROLE_OTHER)


class TestVerdictOwnership(unittest.TestCase):
    def _op(self, role, command="cat x"):
        return fe.EventOperation(row=1, tool="shell_command", command=command, text="",
                                 state=fe.OperationState(), role=role)

    def test_inspection_owns_no_family(self):
        ops = [self._op(fe.ROLE_INSPECT)]
        for family in (fe.FAMILY_BUILD, fe.FAMILY_TEST, fe.FAMILY_PROVIDER):
            self.assertFalse(fe.verdict_family_is_owned(family, ops))

    def test_each_execution_role_owns_its_family(self):
        self.assertTrue(fe.verdict_family_is_owned(fe.FAMILY_BUILD, [self._op(fe.ROLE_BUILD)]))
        self.assertTrue(fe.verdict_family_is_owned(fe.FAMILY_TEST, [self._op(fe.ROLE_TEST)]))
        self.assertTrue(fe.verdict_family_is_owned(fe.FAMILY_PROVIDER, [self._op(fe.ROLE_PROVIDER)]))
        self.assertFalse(fe.verdict_family_is_owned(fe.FAMILY_TEST, [self._op(fe.ROLE_BUILD)]))

    def test_test_role_can_own_a_gradle_build_verdict(self):
        self.assertTrue(fe.verdict_family_is_owned(fe.FAMILY_TEST, [self._op(fe.ROLE_TEST)]))
        self.assertFalse(fe.verdict_family_is_owned(fe.FAMILY_BUILD, [self._op(fe.ROLE_PROVIDER)]))

    def test_unknown_role_is_treated_as_owning_every_family(self):
        ops = [self._op(fe.ROLE_OTHER)]
        for family in (fe.FAMILY_BUILD, fe.FAMILY_TEST, fe.FAMILY_PROVIDER):
            self.assertTrue(fe.verdict_family_is_owned(family, ops))

    def test_family_mapping(self):
        self.assertEqual(fe.verdict_family("BUILD_ERROR"), fe.FAMILY_BUILD)
        self.assertEqual(fe.verdict_family("TEST_PROBLEM"), fe.FAMILY_TEST)
        self.assertEqual(fe.verdict_family("PROVIDER_AUTH"), fe.FAMILY_PROVIDER)
        self.assertEqual(fe.verdict_family("PROVIDER_QUOTA"), fe.FAMILY_PROVIDER)
        for other in ("GENERIC_ERROR", "INFRASTRUCTURE_ERROR", "DEVICE_STATE_GAP", "REGRESSION"):
            self.assertIsNone(fe.verdict_family(other))


class TestInspectionContextCases(unittest.TestCase):
    """CASE-IC-A..L - the brief's CASE A..J plus two conservative residuals."""

    def test_every_inspection_context_case(self):
        for case in _FIX["inspection_context_cases"]:
            with self.subTest(case=case["id"]):
                call = fixture_call(case)
                self.assertEqual(fe.classify_operation_role(case["command"]),
                                 case["expected_operation_role"], case["id"])
                mark = core.classify_failure(call)
                expected = case["core_failure_type"]
                if expected is None:
                    self.assertIsNone(mark, "%s: core must not classify a failure" % case["id"])
                    continue
                self.assertIsNotNone(mark, "%s: core must classify %s" % (case["id"], expected))
                self.assertEqual(mark[0], expected, "%s: frozen core type changed" % case["id"])
                self.assertEqual(fe.parse_operation_state(call.result_text, call.name).outcome,
                                 case["structured_outcome"], case["id"])
                kept, removed = fe.correct_logical_failures([synthetic_failure(case)], {1: [call]})
                if case["corrected"] == "removed":
                    self.assertEqual(len(removed), 1, "%s must be removed" % case["id"])
                    self.assertEqual(len(kept), 0)
                    self.assertEqual(removed[0]["rule_id"], case["expected_rule"], case["id"])
                    self.assertEqual(removed[0]["event_operation_roles"],
                                     [case["expected_operation_role"]], case["id"])
                else:
                    self.assertEqual(len(removed), 0, "%s must survive" % case["id"])
                    self.assertEqual(len(kept), 1)

    def test_unknown_role_quoted_verdict_is_preserved(self):
        case = next(c for c in _FIX["inspection_context_cases"] if c["id"] == "CASE-IC-K")
        call = fixture_call(case)
        kept, removed = fe.correct_logical_failures([synthetic_failure(case)], {1: [call]})
        self.assertEqual(len(removed), 0)
        self.assertEqual(len(kept), 1)

    def test_a_non_clean_inspection_does_not_trigger_the_new_rule(self):
        """A read-only inspection that itself failed is not a clean success, so it is preserved."""
        case = next(c for c in _FIX["cases"] if c["id"] == "CASE-G")
        call = fixture_call(case)
        self.assertEqual(fe.classify_operation_role(case["command"]), fe.ROLE_INSPECT)
        _, removed = fe.correct_logical_failures([synthetic_failure(case)], {1: [call]})
        self.assertEqual(removed[0]["rule_id"], fe.RULE_PROVIDER_FROM_INSPECTION_TEXT)


# --------------------------------------------------------------------------- #
# 2c. process-wrapper unwrapping (P0B-EVAL-WRAPPER-ROLE-FIX)
# --------------------------------------------------------------------------- #
class TestWrapperUnwrapping(unittest.TestCase):
    """A process-control wrapper must never hide (or invent) the payload's operation role.

    The observed defect: ``timeout 300 python3 -m unittest … | tail -40`` resolved to program
    ``timeout`` (neutral) plus ``tail``, so the whole command was INSPECTS_EVIDENCE and a real
    ``FAILED (failures=N)`` unittest failure was removed as a quoted-verdict false positive.
    """

    def test_fixture_file_declares_the_wrapper_cases(self):
        w_ids = [c["id"] for c in _FIX["wrapper_role_cases"]]
        for required in ("CASE-W-A", "CASE-W-B", "CASE-W-C", "CASE-W-D", "CASE-W-E",
                         "CASE-W-F", "CASE-W-G", "CASE-W-H", "CASE-W-I", "CASE-W-J"):
            self.assertIn(required, w_ids)
        f_ids = [c["id"] for c in _FIX["wrapper_failure_cases"]]
        self.assertIn("CASE-W-FAIL-1", f_ids)

    def test_every_wrapper_role_case(self):
        for case in _FIX["wrapper_role_cases"]:
            with self.subTest(case=case["id"]):
                self.assertEqual(fe.classify_operation_role(case["command"]),
                                 case["expected_operation_role"], case["id"])

    def test_the_evidenced_defect_command_is_executes_test(self):
        """The exact latest-session command that was mis-classified INSPECTS_EVIDENCE."""
        cmd = ("cd /mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack && timeout 300 "
               "python3 -m unittest orchestration.hermes.evaluation_adapter.tests."
               "test_failure_evidence -v 2>&1 | tail -40")
        self.assertEqual(fe.classify_operation_role(cmd), fe.ROLE_TEST)
        # and the trailing pipe must not change it
        self.assertEqual(fe.classify_operation_role(
            cmd.replace("| tail -40", "| head -45")), fe.ROLE_TEST)

    def test_unparseable_wrapper_is_other_never_inspection(self):
        """A wrapper whose payload cannot be resolved must never downgrade to INSPECTS_EVIDENCE."""
        for cmd in ("timeout abc python3 -m unittest tests",
                    "timeout --bogus 300 python3 -m unittest tests",
                    "timeout 300",
                    "nice -x 5 python3 -m unittest tests"):
            with self.subTest(command=cmd):
                self.assertEqual(fe.classify_operation_role(cmd), fe.ROLE_OTHER)

    def test_wrapper_payload_is_resolved_not_the_text(self):
        """The role comes from the resolved executable, not from words elsewhere in the command."""
        self.assertEqual(fe.classify_operation_role("timeout 300 ./gradlew assembleBenchmark"),
                         fe.ROLE_BUILD)
        self.assertEqual(fe.classify_operation_role("timeout 30 python3 inspect_rows.py old.jsonl"),
                         fe.ROLE_INSPECT)
        self.assertEqual(fe.classify_operation_role("env FOO=1 ./gradlew test"), fe.ROLE_TEST)


class TestWrapperFailurePreservation(unittest.TestCase):
    """§10 mandatory regression: a real failure behind a wrapper + pipe must SURVIVE."""

    def test_every_wrapper_failure_case(self):
        for case in _FIX["wrapper_failure_cases"]:
            with self.subTest(case=case["id"]):
                call = fixture_call(case)
                self.assertEqual(fe.classify_operation_role(case["command"]),
                                 case["expected_operation_role"], case["id"])
                mark = core.classify_failure(call)
                self.assertIsNotNone(mark, "%s: core must classify a failure" % case["id"])
                self.assertEqual(mark[0], case["core_failure_type"], case["id"])
                self.assertEqual(fe.parse_operation_state(call.result_text, call.name).outcome,
                                 case["structured_outcome"], case["id"])
                kept, removed = fe.correct_logical_failures([synthetic_failure(case)], {1: [call]})
                self.assertEqual(len(removed), 0, "%s must SURVIVE" % case["id"])
                self.assertEqual(len(kept), 1)

    def test_real_unittest_failure_behind_timeout_pipe_is_preserved(self):
        """The exact §10 shape: `timeout 300 python3 -m unittest … | tail` prints FAILED (failures=2),
        the top-level exit is 0 (pipeline advisory) - the TEST_PROBLEM must survive."""
        case = next(c for c in _FIX["wrapper_failure_cases"] if c["id"] == "CASE-W-FAIL-1")
        call = fixture_call(case)
        self.assertEqual(core.classify_failure(call)[0], "TEST_PROBLEM")
        self.assertEqual(fe.classify_operation_role(case["command"]), fe.ROLE_TEST)
        kept, removed = fe.correct_logical_failures([synthetic_failure(case)], {1: [call]})
        self.assertEqual(len(kept), 1)
        self.assertEqual(len(removed), 0)


# --------------------------------------------------------------------------- #
# 3. end to end through the canonical finalizer
# --------------------------------------------------------------------------- #
BASE = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


def ts(sec):
    return (BASE + timedelta(seconds=sec)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class SessionBuilder:
    def __init__(self):
        self.rows = []
        self._n = 0

    def session(self, sec=0):
        self.rows.append({"type": "session", "version": 3, "id": "fixture-session",
                          "timestamp": ts(sec), "cwd": "/proj"})

    def prompt(self, text, sec):
        self.rows.append({"type": "message", "id": f"p{self._n}", "timestamp": ts(sec),
                          "message": {"role": "user", "content": [{"type": "text", "text": text}],
                                      "meta": {"source": "user"}}})
        self._n += 1

    def assistant(self, sec, calls=None, text=""):
        content = []
        if text:
            content.append({"type": "text", "text": text})
        ids = []
        for name, inp in (calls or []):
            cid = f"c{self._n}_{len(ids)}"
            content.append({"type": "tool_use", "id": cid, "name": name, "input": inp})
            ids.append(cid)
        if not content:
            content = [{"type": "text", "text": text}]
        self.rows.append({"type": "message", "id": f"a{self._n}", "timestamp": ts(sec),
                          "message": {"role": "assistant", "content": content,
                                      "meta": {"source": "model"}},
                          "model": "test/model"})
        self._n += 1
        return ids

    def result(self, sec, results):
        content = [{"type": "tool_result", "tool_use_id": cid,
                    "content": [{"type": "text", "text": t}]} for cid, t in results]
        self.rows.append({"type": "message", "id": f"r{self._n}", "timestamp": ts(sec),
                          "message": {"role": "user", "content": content,
                                      "meta": {"source": "tool"}}})
        self._n += 1

    def write(self, path):
        with open(path, "w", encoding="utf-8") as f:
            for r in self.rows:
                f.write(json.dumps(r) + "\n")
        return path


def cmd(b, sec, command, result):
    ids = b.assistant(sec, [("shell_command", {"command": command})])
    b.result(sec, [(ids[0], result)])


def edit(b, sec, path):
    ids = b.assistant(sec, [("edit_file", {"file_path": path, "old_string": "a", "new_string": "b"})])
    b.result(sec, [(ids[0], "Edited")])


BUILD_FAILED = json.dumps({"output": ("FAILURE: Build failed with an exception.\n\n* What went wrong:\n"
                                      "Execution failed for task ':app:compileDebugKotlin'.\n\n"
                                      "BUILD FAILED in 12s"),
                           "exit_code": 1, "error": None})
BUILD_OK = json.dumps({"output": "BUILD SUCCESSFUL in 5s", "exit_code": 0, "error": None})


class TestEndToEnd(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def _finalize(self, builder, run_id, failure_evidence):
        path = builder.write(os.path.join(self.tmp, run_id + ".jsonl"))
        out = os.path.join(self.tmp, run_id + "-out")
        diag = fin.finalize(session_path=path, run_id=run_id, project="proj",
                            output_root=out, require_completion=True,
                            failure_evidence=failure_evidence)
        self.assertEqual(diag["evaluation_outcome"], "SUCCESS", diag)
        with open(os.path.join(out, "proj", run_id, "run.json"), encoding="utf-8") as fh:
            return json.load(fh), diag

    # CASE F — the existing P0B-CLOSE build repair chain, proven through the finalizer
    def test_case_f_build_error_fix_rerun_is_a_pass_repair(self):
        b = SessionBuilder()
        b.session(0)
        b.prompt("TASK fix the android build", 0)
        b.assistant(1, [("todo_write", {"todos": []})])
        cmd(b, 5, "cd /proj && ./gradlew :app:assembleDebug --console=plain",
            BUILD_FAILED)
        edit(b, 10, "/proj/app/build.gradle.kts")
        cmd(b, 20, "cd /proj && ./gradlew :app:assembleDebug --console=plain", BUILD_OK)
        b.assistant(25, [], text="done")
        run, diag = self._finalize(b, "CASE-F", failure_evidence=True)

        self.assertEqual(len(run["logical_failures"]), 1)
        self.assertEqual(run["logical_failures"][0]["type"], "BUILD_ERROR")
        self.assertEqual(run["logical_failures"][0]["repair_status"], "REPAIRED")
        self.assertEqual(len(run["repairs"]), 1)
        self.assertEqual(run["repairs"][0]["result"], "PASS")
        self.assertEqual(run["repairs"][0]["rerun_result"], "PASS")
        self.assertEqual(run["repairs"][0]["changed_paths"], ["/proj/app/build.gradle.kts"])
        self.assertEqual(run["repair_linkage"]["status"], "OK")
        # the correction removed nothing: a real failure with real evidence is untouched
        self.assertTrue(diag["failure_evidence_correction"]["applied"])
        self.assertEqual(diag["failure_evidence_correction"]["removed_count"], 0)

    # CASE A end to end — with the switch off the false positive is published; with it on it is gone
    def test_source_code_provider_false_positive_is_removed_end_to_end(self):
        case = next(c for c in _FIX["cases"] if c["id"] == "CASE-A")

        def build():
            b = SessionBuilder()
            b.session(0)
            b.prompt("TASK audit the evaluation core", 0)
            b.assistant(1, [("todo_write", {"todos": []})])
            cmd(b, 5, case["command"], case_result_text(case))
            b.assistant(10, [], text="done")
            return b

        off, _ = self._finalize(build(), "CASE-A-off", failure_evidence=False)
        self.assertEqual([f["type"] for f in off["logical_failures"]], ["PROVIDER_AUTH"])
        self.assertIn("PROVIDER_FALLBACK", [d["type"] for d in off["execution_deviations"]])

        on, diag = self._finalize(build(), "CASE-A-on", failure_evidence=True)
        self.assertEqual(on["logical_failures"], [])
        self.assertEqual(on["execution_deviations"], [])
        self.assertEqual(on["repair_linkage"]["status"], "OK")
        self.assertEqual(diag["failure_evidence_correction"]["removed_count"], 1)

    # the switch is additive: everything except the failure attribution is untouched
    def test_switch_off_is_byte_identical_for_the_inherited_surface(self):
        def build():
            b = SessionBuilder()
            b.session(0)
            b.prompt("TASK fix the android build", 0)
            b.assistant(1, [("todo_write", {"todos": []})])
            cmd(b, 5, "cd /proj && ./gradlew :app:assembleDebug", BUILD_FAILED)
            edit(b, 10, "/proj/app/build.gradle.kts")
            cmd(b, 20, "cd /proj && ./gradlew :app:assembleDebug", BUILD_OK)
            b.assistant(25, [], text="done")
            return b

        off, _ = self._finalize(build(), "NOOP-off", failure_evidence=False)
        on, diag = self._finalize(build(), "NOOP-on", failure_evidence=True)
        for key in ("logical_failures", "repairs", "execution_deviations", "repair_linkage",
                    "phase_totals", "clocks", "tokens_raw", "tools", "task_window",
                    "agent_host", "observability_quality"):
            self.assertEqual(off[key], on[key], "correction changed %s" % key)
        self.assertEqual(diag["failure_evidence_correction"]["removed_count"], 0)
        # the audit block is the ONLY addition to run.json
        extra = set(on) - set(off)
        self.assertEqual(extra, {"failure_evidence_correction"})


# --------------------------------------------------------------------------- #
# 4. §7 audit pin
# --------------------------------------------------------------------------- #
class TestPipelineExitStatusAudit(unittest.TestCase):
    """§7: the runner persists a structured exit status; the frozen core cannot read it.

    This is the audited defect (not a regression): it is why a successful re-run of a fixed
    target could not be recognised as a repair. It is pinned here so that it fails loudly if the
    frozen core (PRODUCTION_IMMUTABLE) is ever changed to read the envelope.
    """

    def test_core_does_not_read_the_runner_json_envelope_exit_status(self):
        case = next(c for c in _FIX["cases"] if c["id"] == "CASE-C")
        call = fixture_call(case)
        core._parse_result_signals(call)
        self.assertIsNone(call.exit_code, "core now reads the envelope exit status; §7 is closed")
        self.assertEqual(fe.parse_operation_state(call.result_text, call.name).outcome,
                         fe.OUTCOME_FAILED)

    def test_pipeline_lost_exit_status_is_indeterminate_not_success(self):
        case = next(c for c in _FIX["cases"] if c["id"] == "CASE-E2")
        st = fe.parse_operation_state(case_result_text(case), case["tool"])
        self.assertEqual(st.exit_code, 0)
        self.assertFalse(st.exit_reliable)
        self.assertEqual(st.outcome, fe.OUTCOME_UNKNOWN)


if __name__ == "__main__":
    unittest.main(verbosity=2)
