#!/usr/bin/env python3
"""Focused tests for user-message extraction and exact confirmation (no browser)."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

BRIDGE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BRIDGE_DIR))

import chatgpt_adapter as adapter  # noqa: E402


def canonical_message() -> tuple[str, dict]:
    envelope = {
        "exit_code": 0,
        "in_reply_to": "a" * 64,
        "next_nonce": "b" * 64,
        "next_sequence": 4,
        "outcome": "SUCCESS",
        "protocol": "HERMES_RESULT_V1",
        "result_sha256": "c" * 64,
        "sequence": 3,
        "task_id": "BRIDGE-READONLY-001",
    }
    message = (
        "<<<HERMES_RESULT_V1>>>\n"
        + json.dumps(envelope, sort_keys=True, separators=(",", ":"))
        + "\n<<<END_HERMES_RESULT_V1>>>\n\nNEXT_CONTROL_CHALLENGE:\nsequence=4\nnonce="
        + "n" * 64
        + "\nin_reply_to="
        + "r" * 64
        + "\n"
    )
    return message, envelope


class Ops:
    def __init__(self, turns):
        self._turns = turns

    def find_control_tab(self):
        return {"url": adapter.CONTROL_URL}

    def user_turns(self):
        return list(self._turns)


class UserTurnExtractionTest(unittest.TestCase):
    def test_complete_user_receipt_confirms(self):
        message, _ = canonical_message()
        self.assertTrue(adapter.confirm_message_present(message, ops=Ops([message])))

    def test_assistant_only_receipt_not_confirmed(self):
        message, _ = canonical_message()
        self.assertFalse(adapter.confirm_message_present(message, ops=Ops([])))

    def test_same_hash_only_not_confirmed(self):
        message, envelope = canonical_message()
        turn = "result_sha256=" + envelope["result_sha256"]
        self.assertFalse(adapter.confirm_message_present(message, ops=Ops([turn])))

    def test_missing_not_confirmed(self):
        message, _ = canonical_message()
        self.assertFalse(adapter.confirm_message_present(message, ops=Ops(["nothing relevant"])))

    def test_tampered_challenge_not_confirmed(self):
        message, _ = canonical_message()
        tampered = message.replace("nonce=" + "n" * 64, "nonce=" + "z" * 64)
        self.assertFalse(adapter.confirm_message_present(message, ops=Ops([tampered])))

    def test_real_extraction_reads_per_message_body(self):
        ops = object.__new__(adapter.RealOps)
        ops.js = lambda expression: ["first body", "second body"]
        self.assertEqual(ops.user_turns(), ["first body", "second body"])
        self.assertEqual(ops.user_turn_text(), "first body\nsecond body")

    def test_node_miss_raises_and_never_uses_whole_page(self):
        message, _ = canonical_message()
        for bad in (None, [], [None]):
            ops = object.__new__(adapter.RealOps)
            ops.js = (lambda value: (lambda expression: value))(bad)
            with self.assertRaises(adapter.AdapterError):
                ops.user_turns()

            confirming = object.__new__(adapter.RealOps)
            confirming.js = (lambda value: (lambda expression: value))(bad)
            confirming.find_control_tab = lambda: {"url": adapter.CONTROL_URL}
            with self.assertRaises(adapter.AdapterError):
                adapter.confirm_message_present(message, ops=confirming)


if __name__ == "__main__":
    unittest.main()
