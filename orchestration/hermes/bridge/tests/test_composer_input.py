#!/usr/bin/env python3
"""Offline tests for newline-preserving composer input and the pre-Enter guard."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

BRIDGE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BRIDGE_DIR))

import chatgpt_adapter as adapter  # noqa: E402


def canonical_message() -> tuple[str, str]:
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
    return message, envelope["result_sha256"]


class HarnessRecorder:
    def __init__(self):
        self.fill_calls = []
        self.press = []

    def fill_input(self, selector, text, clear_first=False, timeout=0.0):
        self.fill_calls.append((selector, text, clear_first, timeout))

    def press_key(self, key, modifiers=0):
        self.press.append((key, modifiers))

    def js(self, expression):
        return None


class ComposerInputTest(unittest.TestCase):
    def test_keystroke_plan_preserves_line_breaks(self):
        self.assertEqual(
            adapter._keystroke_plan("a\nb"),
            [("a", 0), ("Enter", adapter.SHIFT_KEY), ("b", 0)],
        )
        self.assertEqual(
            adapter._keystroke_plan("a\r\nb\r\n"),
            [("a", 0), ("Enter", adapter.SHIFT_KEY), ("b", 0), ("Enter", adapter.SHIFT_KEY)],
        )
        self.assertEqual(adapter._keystroke_plan(""), [])

    def test_fill_input_uses_shift_enter_and_never_drops_newline(self):
        ops = object.__new__(adapter.RealOps)
        recorder = HarnessRecorder()
        ops.h = {"fill_input": recorder.fill_input, "press_key": recorder.press_key, "js": recorder.js}
        ops.fill_input("sel", "line1\nline2")
        self.assertEqual(recorder.fill_calls, [("sel", "", True, 3)])
        self.assertNotIn(("\n", 0), recorder.press)
        self.assertNotIn(("Enter", 0), recorder.press)  # a bare Enter would submit
        self.assertEqual(recorder.press.count(("Enter", adapter.SHIFT_KEY)), 1)
        typed = "".join(key for key, _mods in recorder.press if len(key) == 1)
        self.assertEqual(typed, "line1line2")


class SendOps:
    def __init__(self, *, composer, turns_before=(), turns_after=None, composer_error=False):
        self.composer = composer
        self.turns = list(turns_before)
        self.turns_after = turns_after
        self.composer_error = composer_error
        self.press_calls = 0
        self.fill_calls = 0

    def find_control_tab(self):
        return {"url": "fake"}

    def composer_selector(self):
        return "sel"

    def fill_input(self, selector, text):
        self.fill_calls += 1

    def composer_text(self, selector):
        if self.composer_error:
            raise adapter.AdapterError("composer read failed")
        return self.composer

    def press_key(self, key):
        self.press_calls += 1
        if self.turns_after is not None:
            self.turns = list(self.turns_after)

    def user_turns(self):
        return list(self.turns)


class PreEnterGuardTest(unittest.TestCase):
    def test_matching_composer_submits_at_most_once(self):
        message, identifier = canonical_message()
        ops = SendOps(composer=message, turns_after=[message])
        out = adapter.send_once(message, identifier, ops=ops, confirm_timeout_s=0, exact=True)
        self.assertEqual(out["status"], adapter.CONFIRMED_SENT)
        self.assertEqual(ops.press_calls, 1)
        self.assertEqual(ops.fill_calls, 1)

    def test_lost_newlines_blocks_before_enter(self):
        message, identifier = canonical_message()
        ops = SendOps(composer=message.replace("\n", ""), turns_after=[message])
        out = adapter.send_once(message, identifier, ops=ops, confirm_timeout_s=0, exact=True)
        self.assertEqual(out["status"], adapter.SEND_UNCERTAIN)
        self.assertFalse(out["sent"])
        self.assertEqual(ops.press_calls, 0)

    def test_truncated_composer_blocks_before_enter(self):
        message, identifier = canonical_message()
        ops = SendOps(composer=message[:50], turns_after=[message])
        out = adapter.send_once(message, identifier, ops=ops, confirm_timeout_s=0, exact=True)
        self.assertEqual(out["status"], adapter.SEND_UNCERTAIN)
        self.assertFalse(out["sent"])
        self.assertEqual(ops.press_calls, 0)

    def test_composer_read_failure_raises_before_enter(self):
        message, identifier = canonical_message()
        ops = SendOps(composer="", composer_error=True)
        with self.assertRaises(adapter.AdapterError):
            adapter.send_once(message, identifier, ops=ops, confirm_timeout_s=0, exact=True)
        self.assertEqual(ops.press_calls, 0)

    def test_post_send_missing_challenge_not_confirmed(self):
        message, identifier = canonical_message()
        head = message.split("NEXT_CONTROL_CHALLENGE:")[0]
        ops = SendOps(composer=message, turns_after=[head])
        out = adapter.send_once(message, identifier, ops=ops, confirm_timeout_s=0, exact=True)
        self.assertEqual(out["status"], adapter.SEND_UNCERTAIN)
        self.assertTrue(out["sent"])
        self.assertEqual(ops.press_calls, 1)

    def test_post_send_tampered_challenge_not_confirmed(self):
        message, identifier = canonical_message()
        tampered = message.replace("nonce=" + "n" * 64, "nonce=" + "z" * 64)
        ops = SendOps(composer=message, turns_after=[tampered])
        out = adapter.send_once(message, identifier, ops=ops, confirm_timeout_s=0, exact=True)
        self.assertEqual(out["status"], adapter.SEND_UNCERTAIN)
        self.assertTrue(out["sent"])
        self.assertEqual(ops.press_calls, 1)


class ComposerTextTest(unittest.TestCase):
    def test_joins_blocks_with_single_newline(self):
        message, _ = canonical_message()
        blocks = message.split("\n")
        ops = object.__new__(adapter.RealOps)
        ops.js = lambda expression: blocks
        self.assertEqual(ops.composer_text("sel"), message)

    def test_blank_middle_block_is_preserved(self):
        ops = object.__new__(adapter.RealOps)
        ops.js = lambda expression: ["<<<X>>>", "", "NEXT:"]
        self.assertEqual(ops.composer_text("sel"), "<<<X>>>\n\nNEXT:")

    def test_missing_composer_returns_empty(self):
        ops = object.__new__(adapter.RealOps)
        ops.js = lambda expression: None
        self.assertEqual(ops.composer_text("sel"), "")


if __name__ == "__main__":
    unittest.main()
