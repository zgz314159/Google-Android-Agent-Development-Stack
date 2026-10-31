#!/usr/bin/env python3
"""Offline CLI regression for ``bridge_cli.py recover-preconsume``.

Isolated and model-free: a temp bridge state dir, an injected READ seam, no browser,
no root, no execution. Proves the scoped recovery clears EXACTLY one retryable
PRE-CONSUME rejection, preserves chain values + journal history, does not send,
write a pending result or start execution, and refuses every other shape.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

BRIDGE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BRIDGE_DIR))

import bridge_cli  # noqa: E402
import bridge_state as bs  # noqa: E402
import protocol as proto  # noqa: E402

TASK_ID = "IAP-SMOKE-001"
SEQ = 5
NONCE = "ff44d13a3993f62236ab001628dab61aa03436f5ec78f51892b9c0298aa2f626"
IN_REPLY = "d96049d4ccf7e3be6d17d7cec5941768791493422ebc5c0c5c9e7b132f1c8d83"
CODE = "E_EXT_WORKTREE_GIT"
CHAIN_KEYS = ("expected_sequence", "expected_nonce", "expected_in_reply_to",
              "last_task_id", "last_result_sha256")


def make_task(**overrides) -> dict:
    task = {
        "protocol": "HERMES_TASK_V1",
        "task_id": TASK_ID,
        "sequence": SEQ,
        "nonce": NONCE,
        "in_reply_to": IN_REPLY,
        "project": "ImageAnalysisFactory",
        "action": "EXECUTE_CONTRACT",
        "contract_package": "/x",
        "contract_manifest_sha256": "b" * 64,
        "risk": "LOW",
        "max_runtime_s": 120,
    }
    task.update(overrides)
    return task


def envelope_text(task: dict) -> str:
    return "prose before\n%s\n%s\n%s\nprose after" % (
        proto.TASK_OPEN, json.dumps(task), proto.TASK_CLOSE)


class Base(unittest.TestCase):
    def setUp(self) -> None:
        self._prev = os.environ.get("HERMES_BRIDGE_STATE_DIR")
        self.tmp = tempfile.TemporaryDirectory(prefix="hermes-preconsume-test-")
        os.environ["HERMES_BRIDGE_STATE_DIR"] = self.tmp.name
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        if self._prev is None:
            os.environ.pop("HERMES_BRIDGE_STATE_DIR", None)
        else:
            os.environ["HERMES_BRIDGE_STATE_DIR"] = self._prev
        self.tmp.cleanup()

    def write_state(self, **overrides) -> dict:
        state = {
            "protocol_version": bs.PROTOCOL_VERSION,
            "expected_sequence": SEQ,
            "expected_nonce": NONCE,
            "expected_in_reply_to": IN_REPLY,
            "status": "ERROR",
            "last_task_id": "BRIDGE-READONLY-002",
            "last_result_sha256": IN_REPLY,
        }
        state.update(overrides)
        bs._atomic_write(self.root / "state.json", bs.canonical_json(state) + "\n")
        return state

    def write_journal(self, entries) -> None:
        for entry in entries:
            bs.journal_append(entry, self.root)

    def reject(self, code: str = CODE, **overrides) -> dict:
        entry = {"event": "CONTRACT_REJECTED", "task_id": TASK_ID, "sequence": SEQ, "code": code}
        entry.update(overrides)
        return entry

    @staticmethod
    def read(text: str):
        return lambda: {"sha256": "0" * 64, "text": text}

    @staticmethod
    def boom():
        raise AssertionError("READ seam must not be reached")

    def run_it(self, **overrides) -> dict:
        kwargs = dict(root=self.root, task_id=TASK_ID, sequence=SEQ, nonce=NONCE,
                      in_reply_to=IN_REPLY, envelope_sha256=proto.task_envelope_sha256(make_task()),
                      reason_code=CODE)
        kwargs.update(overrides)
        return bridge_cli.run_recover_preconsume(**kwargs)


class LegitRecovery(Base):
    def test_recovers_unconsumed_rejection(self) -> None:
        self.write_state()
        self.write_journal([self.reject()])
        before = bs.load_state(self.root).as_dict()

        result = self.run_it(read_fn=self.read(envelope_text(make_task())))

        self.assertEqual(result["decision"], "PRECONSUME_RECOVERED")
        self.assertEqual(result["exit_code"], 0)
        after = bs.load_state(self.root).as_dict()
        self.assertEqual(after["status"], "WAITING_FOR_GPT")
        for key in CHAIN_KEYS:
            self.assertEqual(after[key], before[key], key)

        journal = bs.read_journal(self.root)
        self.assertEqual(journal[0]["event"], "CONTRACT_REJECTED", "history is preserved")
        audit = [e for e in journal if e.get("event") == "PRECONSUME_RECOVERY"]
        self.assertEqual(len(audit), 1, "exactly one append-only audit event")
        self.assertEqual(audit[0]["code"], CODE)
        self.assertEqual(audit[0]["from_status"], "ERROR")
        self.assertEqual(audit[0]["to_status"], "WAITING_FOR_GPT")

        self.assertIsNone(bs.read_pending(self.root), "no pending result is written")
        self.assertFalse([e for e in journal if e.get("event") in ("ACCEPTED", "RESULT")],
                         "no consumption and no result — execution never started")

    def test_cli_wires_the_subcommand(self) -> None:
        parser = bridge_cli.build_parser()
        args = parser.parse_args(["recover-preconsume", "--task-id", TASK_ID,
                                  "--sequence", str(SEQ), "--nonce", NONCE,
                                  "--in-reply-to", IN_REPLY, "--envelope-sha256", "c" * 64])
        self.assertEqual(args.func, bridge_cli._cmd_recover_preconsume)
        self.assertEqual(args.reason_code, CODE)


class Refusals(Base):
    def test_reject_when_not_in_error(self) -> None:
        self.write_state(status="WAITING_FOR_GPT")
        self.write_journal([self.reject()])
        self.assertEqual(self.run_it(read_fn=self.boom)["reason"], "NOT_IN_ERROR")

    def test_reject_when_pending_present(self) -> None:
        self.write_state()
        self.write_journal([self.reject()])
        bs.write_pending({"task_id": TASK_ID, "sequence": SEQ, "result": {},
                          "result_sha256": "z" * 64}, self.root)
        self.assertEqual(self.run_it(read_fn=self.boom)["reason"], "PENDING_RESULT_PRESENT")

    def test_reject_when_task_consumed(self) -> None:
        self.write_state()
        self.write_journal([{"event": "ACCEPTED", "task_id": TASK_ID, "sequence": SEQ,
                             "nonce": NONCE, "task_envelope_sha256": "y" * 64}])
        self.assertEqual(self.run_it(read_fn=self.boom)["reason"], "TASK_ALREADY_CONSUMED")

    def test_reject_when_task_resolved(self) -> None:
        self.write_state()
        self.write_journal([self.reject(),
                            {"event": "RESULT", "task_id": TASK_ID, "sequence": SEQ,
                             "outcome": "SUCCESS", "exit_code": 0, "result_sha256": "z" * 64}])
        self.assertEqual(self.run_it(read_fn=self.boom)["reason"], "TASK_ALREADY_RESOLVED")

    def test_reject_on_chain_mismatch(self) -> None:
        self.write_state(expected_sequence=SEQ + 1)
        self.write_journal([self.reject()])
        self.assertEqual(self.run_it(read_fn=self.boom)["reason"], "CHAIN_MISMATCH")

    def test_reject_without_matching_rejection(self) -> None:
        self.write_state()
        self.write_journal([self.reject(code="E_SELF_MODIFY_CONTROL_PLANE")])
        self.assertEqual(self.run_it(read_fn=self.boom)["reason"], "NO_MATCHING_REJECTION")

    def test_reject_on_envelope_mismatch(self) -> None:
        self.write_state()
        self.write_journal([self.reject()])
        other = envelope_text(make_task(nonce="f" * 64))
        self.assertEqual(self.run_it(read_fn=self.read(other))["reason"], "ENVELOPE_MISMATCH")

    def test_reject_when_read_fails(self) -> None:
        self.write_state()
        self.write_journal([self.reject()])
        result = self.run_it(read_fn=self.boom)
        self.assertEqual(result["reason"], "READ_FAILED")
        self.assertEqual(result["exit_code"], 1)

    def test_refusal_leaves_state_untouched(self) -> None:
        self.write_state(expected_sequence=SEQ + 1)
        self.write_journal([self.reject()])
        before = bs.load_state(self.root).as_dict()
        self.run_it(read_fn=self.boom)
        after = bs.load_state(self.root).as_dict()
        self.assertEqual(after, before, "a refusal must not mutate the chain state")
        self.assertEqual(len(bs.read_journal(self.root)), 1, "no audit event on refusal")


if __name__ == "__main__":
    unittest.main(verbosity=2)
