#!/usr/bin/env python3
"""Focused tests for latest-assistant selection and old-response rejection."""
from __future__ import annotations

import hashlib
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

BRIDGE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BRIDGE_DIR))

import chatgpt_adapter as adapter  # noqa: E402


def candidate(index, *, visible=True, user=False, assistant=False):
    return {"index": index, "visible": visible, "user": user, "assistant": assistant}


class FakeOps(adapter.RealOps):
    """Minimal adapter surface: inherited snapshot/text path, fake JS transport."""

    def __init__(self, snapshot, selected_text):
        self.snapshot = snapshot
        self.selected_text = selected_text
        self.js_calls = 0

    def js(self, expression):
        self.js_calls += 1
        if "const candidates" in expression:
            return self.snapshot
        if re.search(r"nodes\[(\d+)\]", expression):
            return self.selected_text
        return None


class FakeWaitOps:
    def __init__(self, texts):
        self.texts = texts
        self.reads = 0

    def find_control_tab(self):
        return {"url": adapter.CONTROL_URL, "title": "test"}

    def latest_assistant_text(self):
        value = self.texts[min(self.reads, len(self.texts) - 1)]
        self.reads += 1
        return value


class SelectLatestAssistantTests(unittest.TestCase):
    def test_hidden_empty_nodes_are_ignored(self):
        snapshot = {
            "streaming": False,
            "candidates": [
                candidate(0),
                candidate(1),
                candidate(2, visible=False),
                candidate(3, visible=False),
            ],
        }
        self.assertEqual(adapter.select_latest_assistant(snapshot)["index"], 1)

    def test_latest_visible_candidate_wins(self):
        snapshot = {
            "streaming": False,
            "candidates": [candidate(0), candidate(1)],
        }
        self.assertEqual(adapter.select_latest_assistant(snapshot)["index"], 1)

    def test_explicit_assistant_role_is_preferred(self):
        snapshot = {
            "streaming": False,
            "candidates": [
                candidate(0),
                candidate(1, assistant=True),
                candidate(2),
            ],
        }
        chosen = adapter.select_latest_assistant(snapshot)
        self.assertEqual(chosen["index"], 1)
        self.assertTrue(chosen["assistant"])

    def test_user_only_is_rejected(self):
        snapshot = {
            "streaming": False,
            "candidates": [candidate(0, user=True), candidate(1, user=True)],
        }
        with self.assertRaisesRegex(adapter.AdapterError, "no assistant message container"):
            adapter.select_latest_assistant(snapshot)

    def test_no_candidates_is_rejected(self):
        with self.assertRaisesRegex(adapter.AdapterError, "no assistant message container"):
            adapter.select_latest_assistant({"streaming": False, "candidates": []})

    def test_streaming_is_rejected(self):
        snapshot = {
            "streaming": True,
            "candidates": [candidate(0)],
        }
        with self.assertRaisesRegex(adapter.AdapterError, "still streaming"):
            adapter.select_latest_assistant(snapshot)

    def test_latest_assistant_text_does_not_read_user_text(self):
        snapshot = {
            "streaming": False,
            "candidates": [candidate(0, user=True)],
        }
        ops = FakeOps(snapshot, "USER_TEXT_MUST_NOT_BE_READ")
        with self.assertRaisesRegex(adapter.AdapterError, "no assistant message container"):
            adapter.RealOps.latest_assistant_text(ops)
        self.assertEqual(ops.js_calls, 1)

    def test_latest_assistant_text_selects_visible_latest(self):
        snapshot = {
            "streaming": False,
            "candidates": [candidate(0), candidate(1), candidate(2, visible=False)],
        }
        ops = FakeOps(snapshot, "ASSISTANT_TEXT")
        self.assertEqual(adapter.RealOps.latest_assistant_text(ops), "ASSISTANT_TEXT")
        self.assertEqual(ops.js_calls, 2)


class OldAssistantRejectionTests(unittest.TestCase):
    def test_same_old_assistant_is_not_accepted_as_new(self):
        old = "OLD_ASSISTANT"
        old_sha = hashlib.sha256(old.encode()).hexdigest()
        ops = FakeWaitOps([old, old, old, old])
        with mock.patch.object(adapter.time, "monotonic", side_effect=[0.0, 0.4, 0.8, 1.2]), \
                mock.patch.object(adapter.time, "sleep"):
            result = adapter.wait_for_new_assistant(old_sha, timeout=1, ops=ops)
        self.assertEqual(result["status"], "TIMEOUT")
        self.assertGreaterEqual(ops.reads, 1)


if __name__ == "__main__":
    unittest.main()
