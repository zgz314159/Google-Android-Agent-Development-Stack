#!/usr/bin/env python3
"""WAVE1A tests for the shadow-only transient observer hook.

Contract: STACK-SIMPLIFICATION-S2-WAVE1A-001  (TASK-03, AC-W1A-008 / AC-W1A-009 / AC-W1A-010)

Deterministic and offline: the hook is driven as a subprocess with synthetic fixtures and an
isolated ``HERMES_OBSERVER_LOG``. No device, no network, no live Hermes profile change.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(HERE, os.pardir, "hooks", "hermes-transient-observer.py")

ALLOWED_KEYS = {
    "hook_event_name", "captured_at", "payload_keys",
    "session_id", "profile", "cwd", "tool_name",
    "tool_call_id", "task_id", "turn_id", "api_request_id",
    "status", "error_type", "duration_ms", "api_call_count", "model", "provider",
}

SECRET_SENTINELS = ("SUPERSECRET", "correct-horse-battery", "sk-live-xxxxxxxx")


def run_hook(payload_text: str, log_path: str):
    env = dict(os.environ)
    env["HERMES_OBSERVER_LOG"] = log_path
    return subprocess.run(
        [sys.executable, HOOK],
        input=payload_text, env=env, capture_output=True, text=True, timeout=30,
    )


def read_lines(path: str):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as fh:
        return [ln for ln in fh.read().splitlines() if ln.strip()]


POST_TOOL_CALL = {
    "hook_event_name": "post_tool_call",
    "tool_name": "write_file",
    "tool_input": {"path": "/repo/x.py", "content": "SUPERSECRET_TOKEN", "api_key": "sk-live-xxxxxxxx"},
    "session_id": "sess-1",
    "cwd": "/repo",
    "profile": "android-stack",
    "extra": {"tool_call_id": "call_1", "task_id": "task-1", "turn_id": "TURN-0007",
              "duration_ms": 123, "status": "ok", "result": "correct-horse-battery"},
}

API_EVENTS = {
    "pre_api_request": {"api_request_id": "req-9", "model": "deepseek/deepseek-v4.1-flash",
                        "provider": "commandcode", "api_call_count": 4},
    "post_api_request": {"api_request_id": "req-9", "status": "ok", "duration_ms": 812,
                         "model": "deepseek/deepseek-v4.1-flash"},
    "api_request_error": {"api_request_id": "req-10", "error_type": "PROVIDER_TIMEOUT",
                          "status": "error", "duration_ms": 30000},
}


class ObserverBehaviourTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.log = os.path.join(self.tmp.name, "transient-hook-events.jsonl")

    def tearDown(self):
        self.tmp.cleanup()

    def test_post_tool_call_writes_one_metadata_only_line(self):
        payload = dict(POST_TOOL_CALL)
        r = run_hook(json.dumps(payload), self.log)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, "", "observer must print nothing to stdout")

        lines = read_lines(self.log)
        self.assertEqual(len(lines), 1, lines)
        rec = json.loads(lines[0])
        self.assertEqual(rec["hook_event_name"], "post_tool_call")
        self.assertEqual(rec["tool_name"], "write_file")
        self.assertEqual(rec["session_id"], "sess-1")
        self.assertEqual(rec["tool_call_id"], "call_1")
        self.assertEqual(rec["turn_id"], "TURN-0007")
        self.assertEqual(rec["duration_ms"], 123)
        self.assertIn("captured_at", rec)
        self.assertTrue(rec["payload_keys"])
        self.assertEqual(rec["payload_keys"], sorted(rec["payload_keys"]))
        self.assertEqual(set(rec) - ALLOWED_KEYS, set(), "unexpected keys: %r" % (set(rec) - ALLOWED_KEYS))

    def test_tool_input_values_and_secrets_never_appear(self):
        r = run_hook(json.dumps(dict(POST_TOOL_CALL)), self.log)
        self.assertEqual(r.returncode, 0)
        blob = "\n".join(read_lines(self.log))
        for sentinel in SECRET_SENTINELS:
            self.assertNotIn(sentinel, blob, "secret value leaked: %s" % sentinel)
        rec = json.loads(read_lines(self.log)[0])
        for forbidden in ("tool_input", "content", "result", "prompt", "messages", "response"):
            self.assertNotIn(forbidden, rec, "field %r must not be captured" % forbidden)
        # only the KEY NAMES of the payload are recorded, never their values
        self.assertIn("tool_input", rec["payload_keys"])
        self.assertNotIn("api_key", blob)  # a nested tool_input key name is not captured either

    def test_second_invocation_appends_and_preserves_earlier_lines(self):
        first = run_hook(json.dumps(dict(POST_TOOL_CALL)), self.log)
        self.assertEqual(first.returncode, 0)
        before = read_lines(self.log)
        self.assertEqual(len(before), 1)

        second = run_hook(json.dumps({
            "hook_event_name": "post_tool_call", "tool_name": "read_file", "session_id": "sess-1",
            "extra": {"tool_call_id": "call_2"},
        }), self.log)
        self.assertEqual(second.returncode, 0)
        after = read_lines(self.log)
        self.assertEqual(len(after), 2)
        self.assertEqual(after[0], before[0], "an existing line was rewritten")

    def test_api_events_capture_status_model_provider_timing(self):
        for event, extra in API_EVENTS.items():
            with self.subTest(event=event):
                payload = {"hook_event_name": event, "session_id": "sess-1",
                           "profile": "android-stack", "cwd": "/repo", "extra": dict(extra)}
                r = run_hook(json.dumps(payload), self.log)
                self.assertEqual(r.returncode, 0)
        lines = [json.loads(ln) for ln in read_lines(self.log)]
        self.assertEqual(len(lines), 3)
        self.assertEqual([ln["hook_event_name"] for ln in lines], list(API_EVENTS))
        by_event = {ln["hook_event_name"]: ln for ln in lines}
        self.assertEqual(by_event["pre_api_request"]["api_call_count"], 4)
        self.assertEqual(by_event["post_api_request"]["status"], "ok")
        self.assertEqual(by_event["api_request_error"]["error_type"], "PROVIDER_TIMEOUT")
        self.assertEqual(by_event["api_request_error"]["duration_ms"], 30000)

    def test_malformed_payloads_write_nothing_and_exit_zero(self):
        for bad in ("", "   ", "not json", "[1,2,3]", "null", '"a string"', "42", "{invalid"):
            with self.subTest(payload=bad):
                r = run_hook(bad, self.log)
                self.assertEqual(r.returncode, 0, "must always exit 0")
                self.assertEqual(r.stdout, "", "must print nothing")
        self.assertEqual(read_lines(self.log), [], "malformed input must write nothing")

    def test_unhandled_event_writes_nothing(self):
        r = run_hook(json.dumps({"hook_event_name": "pre_tool_call", "tool_name": "write_file"}),
                     self.log)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, "")
        self.assertEqual(read_lines(self.log), [])

    def test_bad_log_path_fails_safe(self):
        # an unwritable target (here: a directory) must not raise, print, or exit non-zero
        r = run_hook(json.dumps(dict(POST_TOOL_CALL)), self.tmp.name)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, "")


class ObserverShadowOnlyTests(unittest.TestCase):
    def test_hook_header_declares_shadow_only(self):
        with open(HOOK, "r", encoding="utf-8") as fh:
            head = fh.read(1500)
        self.assertIn("SHADOW_ONLY", head)

    def test_hook_is_not_registered_in_the_live_profile(self):
        hermes_home = os.path.expanduser(os.environ.get("HERMES_HOME", "~/.hermes"))
        config = os.path.join(hermes_home, "profiles", "android-stack", "config.yaml")
        if not os.path.exists(config):
            self.skipTest("live profile config not present in this environment")
        with open(config, "r", encoding="utf-8") as fh:
            text = fh.read()
        self.assertNotIn("hermes-transient-observer", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
