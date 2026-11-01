#!/usr/bin/env python3
"""One isolated flow check: the round diagnostic must reach the campaign output.

Fake-driven (no Chrome, no Bridge state, no Hermes, no model). Drives the REAL
CampaignSupervisor.run() -> _dispatch -> bridge_round seam and asserts the whitelisted
CAMPAIGN_ROUND_DIAG line. A wrapper timeout with a cleanup record must surface
timed_out/cleanup/send status; an UNKNOWN cleanup must never print CONFIRMED, and a
missing diagnostic must report UNKNOWN for every field.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SUPERVISOR_DIR = _HERE.parent
_BRIDGE_DIR = _SUPERVISOR_DIR.parent / "bridge"
for _p in (str(_SUPERVISOR_DIR), str(_BRIDGE_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import protocol as bridge_protocol  # noqa: E402
import campaign_state as cstate  # noqa: E402
import campaign_supervisor as csup  # noqa: E402

CAMPAIGN_ID = "CAMPAIGN-DIAG"
MILESTONE = "S0"
NONCE = "nonce-5"
IN_REPLY = "in-reply-to-5"
RESULT_SHA = "r" * 64


def make_task(*, task_id, sequence, nonce, in_reply_to):
    return {
        "protocol": "HERMES_TASK_V1", "task_id": task_id, "sequence": sequence,
        "nonce": nonce, "in_reply_to": in_reply_to,
        "project": "Google-Android-Agent-Development-Stack", "action": "EXECUTE_CONTRACT",
        "contract_package": "/tmp/contract-pkg", "contract_manifest_sha256": "b" * 64,
        "risk": "LOW", "max_runtime_s": 60,
    }


class Bridge:
    def __init__(self, round_result):
        self.round_result = round_result
        self.sequence = 5
        self.nonce = NONCE
        self.in_reply_to = IN_REPLY
        self.result_sha = RESULT_SHA
        self.round_calls = 0

    def status(self):
        return {"protocol_version": "HERMES_TASK_V1", "expected_sequence": self.sequence,
                "expected_nonce": self.nonce, "expected_in_reply_to": self.in_reply_to,
                "status": "WAITING_FOR_GPT", "last_task_id": None,
                "last_result_sha256": self.result_sha}

    def round(self):
        self.round_calls += 1
        self.sequence += 1
        self.nonce = "nonce-%d" % self.sequence
        self.result_sha = "result-%d" % self.sequence
        self.in_reply_to = self.result_sha
        return dict(self.round_result)


class Reader:
    def __init__(self, bridge):
        self.bridge = bridge
        self.n = 0

    def __call__(self):
        self.n += 1
        st = self.bridge.status()
        task = make_task(task_id="T-%d" % self.n, sequence=st["expected_sequence"],
                         nonce=st["expected_nonce"], in_reply_to=st["expected_in_reply_to"])
        text = "%s\n%s\n%s" % (bridge_protocol.TASK_OPEN,
                               json.dumps(task, sort_keys=True), bridge_protocol.TASK_CLOSE)
        return {"status": "OK", "text": text, "sha256": bridge_protocol.sha256_text(text)}


class Clock:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t


class Sleep:
    def __init__(self, clock):
        self.clock = clock

    def __call__(self, seconds):
        self.clock.t += seconds


class RoundDiagnosticFlow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="round-diag-test-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def run_campaign(self, round_result):
        clock = Clock()
        store = cstate.CampaignStore(CAMPAIGN_ID, root=self.tmp)
        lines = []
        bridge = Bridge(round_result)
        supervisor = csup.CampaignSupervisor(
            campaign_id=CAMPAIGN_ID, milestone=MILESTONE, start_sequence=None,
            start_nonce=None, start_in_reply_to=None, max_rounds=1,
            max_wall_seconds=900.0, poll_seconds=5.0, store=store,
            read_latest_assistant=Reader(bridge), bridge_status=bridge.status,
            bridge_round=bridge.round, read_pending=lambda: None,
            clock=clock, sleep=Sleep(clock), progress=lines.append)
        supervisor.run()
        return [line for line in lines if line.startswith("CAMPAIGN_ROUND_DIAG ")]

    def test_timeout_with_cleanup_reaches_campaign_output(self):
        diag = {"task_id": "T-1", "stage": "EXECUTED", "exit_code": 124,
                "timed_out": True, "timeout_phases": ["TERM", "KILL"],
                "cleanup": "CONFIRMED", "send_status": "CONFIRMED_SENT",
                "result_sha256": RESULT_SHA}
        lines = self.run_campaign({"decision": "WAITING_FOR_GPT", "diagnostic": diag})
        self.assertEqual(len(lines), 1, lines)
        line = lines[0]
        for expected in ("task_id=T-1", "stage=EXECUTED", "exit_code=124",
                         "timed_out=True", "cleanup=CONFIRMED",
                         "send_status=CONFIRMED_SENT", "result_sha256=" + RESULT_SHA):
            self.assertIn(expected, line)

    def test_unknown_cleanup_never_reports_confirmed(self):
        diag = {"task_id": "T-1", "stage": "SEND_UNCERTAIN", "exit_code": 125,
                "timed_out": True, "timeout_phases": [],
                "cleanup": "UNKNOWN", "send_status": "SEND_UNCERTAIN",
                "result_sha256": RESULT_SHA}
        lines = self.run_campaign({"decision": "SEND_UNCERTAIN", "diagnostic": diag})
        self.assertEqual(len(lines), 1, lines)
        self.assertIn("cleanup=UNKNOWN", lines[0])
        self.assertNotIn("cleanup=CONFIRMED", lines[0])

    def test_missing_diagnostic_reports_unknown(self):
        lines = self.run_campaign({})
        self.assertEqual(len(lines), 1, lines)
        for expected in ("task_id=UNKNOWN", "stage=UNKNOWN", "exit_code=UNKNOWN",
                         "timed_out=UNKNOWN", "cleanup=UNKNOWN",
                         "send_status=UNKNOWN", "result_sha256=UNKNOWN"):
            self.assertIn(expected, lines[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
