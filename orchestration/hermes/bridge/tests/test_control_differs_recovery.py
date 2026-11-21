#!/usr/bin/env python3
"""Offline tests for recover_control_differs (ERROR -> WAITING_FOR_GPT, no send)."""

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

SEQ = 23
NONCE = "a" * 64
IN_REPLY = "b" * 64
AUTH = "USER-TEST-CONTROL-DIFFERS"


class ControlDiffersRecoveryTest(unittest.TestCase):
    def setUp(self):
        self._prev = os.environ.get("HERMES_BRIDGE_STATE_DIR")
        self.tmp = tempfile.TemporaryDirectory(prefix="hermes-control-differs-")
        os.environ["HERMES_BRIDGE_STATE_DIR"] = self.tmp.name
        self.root = Path(self.tmp.name)

    def tearDown(self):
        if self._prev is None:
            os.environ.pop("HERMES_BRIDGE_STATE_DIR", None)
        else:
            os.environ["HERMES_BRIDGE_STATE_DIR"] = self._prev
        self.tmp.cleanup()

    def _write(self, *, status="ERROR", journal=None):
        state = {
            "protocol_version": bs.PROTOCOL_VERSION,
            "expected_sequence": SEQ,
            "expected_nonce": NONCE,
            "expected_in_reply_to": IN_REPLY,
            "status": status,
            "last_task_id": "CAL-WORD-PARAGRAPH-ABS-001",
            "last_result_sha256": IN_REPLY,
        }
        (self.root / bs.STATE_FILE).write_text(json.dumps(state) + "\n")
        lines = journal or [
            {"event": "CONTROL_REQUEST_SEND_ATTEMPTED", "sequence": SEQ, "task_id": "T"},
            {"event": "READ_FAILED", "error": "LinkError",
             "message": "CONTROL_DIFFERS_FROM_AUTHORIZATION"},
        ]
        with open(self.root / bs.JOURNAL_FILE, "w", encoding="utf-8") as handle:
            for entry in lines:
                handle.write(json.dumps(entry) + "\n")
        return state, lines[-1]

    def test_recovers_exact_control_differs(self):
        state, last = self._write()
        result = bridge_cli.recover_control_differs(
            authorization_id=AUTH,
            expected_state_sha256=proto.canonical_sha256(state),
            rejection_sha256=proto.canonical_sha256(last),
            root=self.root,
        )
        self.assertEqual(result["decision"], "CONTROL_DIFFERS_RECOVERED")
        after = json.loads((self.root / bs.STATE_FILE).read_text())
        self.assertEqual(after["status"], "WAITING_FOR_GPT")
        self.assertEqual(after["expected_sequence"], SEQ)
        self.assertEqual(after["expected_nonce"], NONCE)
        journal = bs.read_journal(self.root)
        self.assertEqual(journal[-1]["event"], "CONTROL_DIFFERS_RECOVERY")
        self.assertFalse((self.root / bs.PENDING_FILE).exists())

    def test_refuses_without_send_attempt_or_with_accepted(self):
        state, last = self._write(journal=[
            {"event": "READ_FAILED", "error": "LinkError",
             "message": "CONTROL_DIFFERS_FROM_AUTHORIZATION"},
        ])
        with self.assertRaisesRegex(ValueError, "SEND_ATTEMPT_MISSING"):
            bridge_cli.recover_control_differs(
                authorization_id=AUTH,
                expected_state_sha256=proto.canonical_sha256(state),
                rejection_sha256=proto.canonical_sha256(last),
                root=self.root,
            )
        # ACCEPTED without RESULT makes unresolved_accepted fail-closed first.
        state, last = self._write(journal=[
            {"event": "CONTROL_REQUEST_SEND_ATTEMPTED", "sequence": SEQ, "task_id": "T"},
            {"event": "ACCEPTED", "sequence": SEQ, "task_id": "T"},
            {"event": "READ_FAILED", "error": "LinkError",
             "message": "CONTROL_DIFFERS_FROM_AUTHORIZATION"},
        ])
        with self.assertRaisesRegex(ValueError, "UNRESOLVED_OR_PENDING"):
            bridge_cli.recover_control_differs(
                authorization_id=AUTH,
                expected_state_sha256=proto.canonical_sha256(state),
                rejection_sha256=proto.canonical_sha256(last),
                root=self.root,
            )
        # Terminal RESULT still blocks via SEQUENCE_ALREADY_TERMINAL.
        state, last = self._write(journal=[
            {"event": "CONTROL_REQUEST_SEND_ATTEMPTED", "sequence": SEQ, "task_id": "T"},
            {"event": "ACCEPTED", "sequence": SEQ, "task_id": "T"},
            {"event": "RESULT", "sequence": SEQ, "task_id": "T", "outcome": "BLOCKED"},
            {"event": "READ_FAILED", "error": "LinkError",
             "message": "CONTROL_DIFFERS_FROM_AUTHORIZATION"},
        ])
        with self.assertRaisesRegex(ValueError, "SEQUENCE_ALREADY_TERMINAL"):
            bridge_cli.recover_control_differs(
                authorization_id=AUTH,
                expected_state_sha256=proto.canonical_sha256(state),
                rejection_sha256=proto.canonical_sha256(last),
                root=self.root,
            )


if __name__ == "__main__":
    unittest.main()
