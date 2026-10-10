#!/usr/bin/env python3
"""Deterministic, fake-driven tests for the Campaign Supervisor.

Every test drives the Supervisor exclusively through injected fakes for
``read_latest_assistant``, ``bridge_status``, ``bridge_round`` and the clock / sleep
seams, with a temporary private Supervisor state root. No real Chrome, no real
ChatGPT, no real Hermes, no live Bridge state and no device are ever touched.

Run from the Supervisor directory:

    python3 -m unittest discover -s tests -p "test_*.py"

Standard library only.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
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
import campaign_protocol as cproto  # noqa: E402
import campaign_state as cstate  # noqa: E402
import campaign_supervisor as csup  # noqa: E402

CAMPAIGN_ID = "CAMPAIGN-T1"
MILESTONE = "M5"
NONCE = "nonce-5"
PREV_LINK = "prev-link"
LAST_RESULT = "a" * 64


# --------------------------------------------------------------------------- #
# Fakes
# --------------------------------------------------------------------------- #

class FakeBridge:
    """A fake Bridge: exposes status + one round, advancing the chain."""

    def __init__(self, *, status="WAITING_FOR_GPT", sequence=5, nonce=NONCE,
                 in_reply_to=PREV_LINK, last_result_sha256=LAST_RESULT,
                 after_round_status=None, advance=True):
        self.status_name = status
        self.sequence = sequence
        self.nonce = nonce
        self.in_reply_to = in_reply_to
        self.last_result_sha256 = last_result_sha256
        self.after_round_status = after_round_status
        self.advance = advance
        self.round_calls = 0

    def status(self):
        return {
            "protocol_version": "HERMES_TASK_V1",
            "expected_sequence": self.sequence,
            "expected_nonce": self.nonce,
            "expected_in_reply_to": self.in_reply_to,
            "status": self.status_name,
            "last_task_id": None,
            "last_result_sha256": self.last_result_sha256,
        }

    def round(self):
        self.round_calls += 1
        if self.after_round_status is not None:
            self.status_name = self.after_round_status
        if self.advance:
            self.sequence += 1
            self.nonce = "nonce-%d" % self.sequence
            self.last_result_sha256 = "result-%d" % self.sequence
            self.in_reply_to = self.last_result_sha256
        return {"decision": self.status_name, "status": self.status_name}


class FixedReader:
    def __init__(self, text):
        self.text = text

    def __call__(self):
        return {"status": "OK", "text": self.text,
                "sha256": bridge_protocol.sha256_text(self.text)}


class SequenceReader:
    """Builds a fresh, chain-matching Bridge task from the current fake Bridge."""

    def __init__(self, bridge):
        self.bridge = bridge
        self.n = 0

    def __call__(self):
        self.n += 1
        st = self.bridge.status()
        task = make_task(task_id="T-%d" % self.n, sequence=st["expected_sequence"],
                         nonce=st["expected_nonce"], in_reply_to=st["expected_in_reply_to"])
        text = wrap_task(task)
        return {"status": "OK", "text": text, "sha256": bridge_protocol.sha256_text(text)}


class FakeClock:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t

    def advance(self, dt):
        self.t += dt


class FakeSleep:
    def __init__(self, clock):
        self.clock = clock
        self.calls = 0

    def __call__(self, seconds):
        self.calls += 1
        self.clock.advance(seconds)


# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #

def make_task(*, task_id="T-1", sequence=5, nonce=NONCE, in_reply_to=PREV_LINK,
              action="EXECUTE_CONTRACT", risk="LOW"):
    return {
        "protocol": "HERMES_TASK_V1",
        "task_id": task_id,
        "sequence": sequence,
        "nonce": nonce,
        "in_reply_to": in_reply_to,
        "project": "Google-Android-Agent-Development-Stack",
        "action": action,
        "contract_package": "/tmp/contract-pkg",
        "contract_manifest_sha256": "b" * 64,
        "risk": risk,
        "max_runtime_s": 60,
    }


def wrap_task(task):
    return "%s\n%s\n%s" % (bridge_protocol.TASK_OPEN,
                           json.dumps(task, sort_keys=True),
                           bridge_protocol.TASK_CLOSE)


def campaign_doc(*, campaign_id=CAMPAIGN_ID, milestone=MILESTONE, status="CLOSED",
                 outcome="PASS", in_reply_to=LAST_RESULT):
    return {
        "protocol": "HERMES_CAMPAIGN_V1",
        "campaign_id": campaign_id,
        "milestone": milestone,
        "status": status,
        "outcome": outcome,
        "in_reply_to": in_reply_to,
    }


def wrap_campaign(doc_or_payload):
    payload = doc_or_payload if isinstance(doc_or_payload, str) else json.dumps(doc_or_payload, sort_keys=True)
    return "%s\n%s\n%s" % (cproto.CAMPAIGN_OPEN, payload, cproto.CAMPAIGN_CLOSE)


class SupervisorTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="supervisor-test-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def build(self, *, bridge, reader, read_pending=None, max_rounds=1,
              max_wall_seconds=900.0, poll_seconds=5.0, clock=None, progress=None,
              root=None):
        clock = clock or FakeClock()
        sleep = FakeSleep(clock)
        store = cstate.CampaignStore(CAMPAIGN_ID, root=root or self.tmp)
        supervisor = csup.CampaignSupervisor(
            campaign_id=CAMPAIGN_ID,
            milestone=MILESTONE,
            start_sequence=None,
            start_nonce=None,
            start_in_reply_to=None,
            max_rounds=max_rounds,
            max_wall_seconds=max_wall_seconds,
            poll_seconds=poll_seconds,
            store=store,
            read_latest_assistant=reader,
            bridge_status=bridge.status,
            bridge_round=bridge.round,
            read_pending=read_pending or (lambda: None),
            clock=clock,
            sleep=sleep,
            progress=progress or (lambda line: None),
            lock_timeout=0.2,
        )
        return supervisor, store

    # -- 1/2: new-response guard + single dispatch -------------------------- #
    def test_same_response_never_dispatched_twice(self):
        bridge = FakeBridge()
        reader = FixedReader(wrap_task(make_task()))
        supervisor, store = self.build(bridge=bridge, reader=reader,
                                       max_rounds=2, max_wall_seconds=10.0, poll_seconds=5.0)
        result = supervisor.run()
        self.assertEqual(bridge.round_calls, 1)  # never twice on the same response
        self.assertEqual(result["status"], "PAUSED")
        state = store.load()
        self.assertEqual(state["round_count"], 1)

    def test_new_exact_task_invokes_bridge_exactly_once(self):
        bridge = FakeBridge()
        reader = FixedReader(wrap_task(make_task()))
        supervisor, store = self.build(bridge=bridge, reader=reader,
                                       max_rounds=2, max_wall_seconds=10.0, poll_seconds=5.0)
        supervisor.run()
        self.assertEqual(bridge.round_calls, 1)
        state = store.load()
        self.assertEqual(state["round_count"], 1)
        self.assertEqual(state["last_dispatched_task_id"], "T-1")
        self.assertEqual(state["last_bridge_result_sha256"], bridge.last_result_sha256)

    # -- 3: chain mismatch pauses ------------------------------------------- #
    def test_sequence_mismatch_pauses_without_bridge_call(self):
        self._mismatch(make_task(sequence=99))

    def test_nonce_mismatch_pauses_without_bridge_call(self):
        self._mismatch(make_task(nonce="wrong"))

    def test_in_reply_to_mismatch_pauses_without_bridge_call(self):
        self._mismatch(make_task(in_reply_to="stale"))

    def _mismatch(self, task):
        bridge = FakeBridge()
        reader = FixedReader(wrap_task(task))
        supervisor, store = self.build(bridge=bridge, reader=reader)
        result = supervisor.run()
        self.assertEqual(bridge.round_calls, 0)
        self.assertEqual(result["status"], "PAUSED")
        self.assertEqual(result["outcome"], "FAILED")
        self.assertEqual(store.load()["status"], "PAUSED")

    # -- 4: control-free marked seen ---------------------------------------- #
    def test_control_free_response_marked_seen_and_ignored(self):
        bridge = FakeBridge()
        reader = FixedReader("just assistant prose, no control envelope")
        supervisor, store = self.build(bridge=bridge, reader=reader,
                                       max_rounds=5, max_wall_seconds=1.0, poll_seconds=1.0)
        result = supervisor.run()
        self.assertEqual(bridge.round_calls, 0)
        self.assertEqual(result["status"], "PAUSED")
        self.assertEqual(result["outcome"], "LIMIT_REACHED")
        state = store.load()
        self.assertEqual(state["last_seen_assistant_sha256"],
                         bridge_protocol.sha256_text("just assistant prose, no control envelope"))

    # -- 5/6: malformed + ambiguous fail closed ----------------------------- #
    def test_malformed_task_pauses_fail_closed(self):
        bridge = FakeBridge()
        reader = FixedReader("%s\nnot json at all\n%s" % (bridge_protocol.TASK_OPEN,
                                                          bridge_protocol.TASK_CLOSE))
        supervisor, _ = self.build(bridge=bridge, reader=reader)
        result = supervisor.run()
        self.assertEqual(bridge.round_calls, 0)
        self.assertEqual(result["status"], "PAUSED")
        self.assertEqual(result["outcome"], "FAILED")

    def test_ambiguous_task_pauses_fail_closed(self):
        bridge = FakeBridge()
        text = wrap_task(make_task(task_id="A")) + "\n" + wrap_task(make_task(task_id="B"))
        supervisor, _ = self.build(bridge=bridge, reader=FixedReader(text))
        result = supervisor.run()
        self.assertEqual(bridge.round_calls, 0)
        self.assertEqual(result["status"], "PAUSED")
        self.assertEqual(result["outcome"], "FAILED")

    # -- 7: valid campaign PASS closes without a bridge call ---------------- #
    def test_valid_campaign_pass_closes_without_bridge_call(self):
        bridge = FakeBridge()
        reader = FixedReader(wrap_campaign(campaign_doc(status="CLOSED", outcome="PASS")))
        supervisor, store = self.build(bridge=bridge, reader=reader)
        result = supervisor.run()
        self.assertEqual(bridge.round_calls, 0)
        self.assertEqual(result["status"], "CLOSED")
        self.assertEqual(result["outcome"], "PASS")
        state = store.load()
        self.assertEqual(state["status"], "CLOSED")
        self.assertEqual(state["terminal_outcome"], "PASS")
        # the Bridge is left WAITING_FOR_GPT with its next sequence available
        self.assertEqual(bridge.status()["status"], "WAITING_FOR_GPT")
        self.assertEqual(bridge.status()["expected_sequence"], 5)

    def test_valid_campaign_paused_envelope_persists_paused(self):
        bridge = FakeBridge()
        reader = FixedReader(wrap_campaign(campaign_doc(status="PAUSED", outcome="BLOCKED")))
        supervisor, store = self.build(bridge=bridge, reader=reader)
        result = supervisor.run()
        self.assertEqual(bridge.round_calls, 0)
        self.assertEqual(result["status"], "PAUSED")
        self.assertEqual(result["outcome"], "BLOCKED")
        self.assertEqual(store.load()["status"], "PAUSED")

    # -- 8/9/10: wrong id / milestone / stale reply rejected ---------------- #
    def test_campaign_wrong_id_rejected(self):
        self._rejected_campaign(campaign_doc(campaign_id="OTHER-CAMPAIGN"))

    def test_campaign_wrong_milestone_rejected(self):
        self._rejected_campaign(campaign_doc(milestone="M6"))

    def test_campaign_stale_in_reply_to_rejected(self):
        self._rejected_campaign(campaign_doc(in_reply_to="0" * 64))

    def _rejected_campaign(self, doc):
        bridge = FakeBridge()
        supervisor, store = self.build(bridge=bridge, reader=FixedReader(wrap_campaign(doc)))
        result = supervisor.run()
        self.assertEqual(bridge.round_calls, 0)
        self.assertNotEqual(result["status"], "CLOSED")
        self.assertEqual(result["status"], "PAUSED")
        self.assertNotEqual(store.load()["status"], "CLOSED")

    # -- 11: task + campaign terminal rejected ------------------------------ #
    def test_response_with_both_task_and_campaign_rejected(self):
        bridge = FakeBridge()
        text = wrap_campaign(campaign_doc()) + "\n" + wrap_task(make_task())
        supervisor, _ = self.build(bridge=bridge, reader=FixedReader(text))
        result = supervisor.run()
        self.assertEqual(bridge.round_calls, 0)
        self.assertEqual(result["status"], "PAUSED")

    # -- 12: bridge safety states pause ------------------------------------- #
    def test_bridge_safety_states_pause(self):
        for status in ("AWAITING_APPROVAL", "RECOVERY_REQUIRED", "SEND_UNCERTAIN",
                       "STOPPED", "ERROR"):
            with self.subTest(status=status):
                bridge = FakeBridge(status=status)
                supervisor, store = self.build(bridge=bridge,
                                               reader=FixedReader("no control"),
                                               root=os.path.join(self.tmp, status))
                result = supervisor.run()
                self.assertEqual(bridge.round_calls, 0)
                self.assertEqual(result["status"], "PAUSED")
                self.assertEqual(result["outcome"], "SAFETY_STOP")
                self.assertNotEqual(result["exit_code"], 0)
                self.assertEqual(store.load()["status"], "PAUSED")

    # -- 13: max_rounds ------------------------------------------------------ #
    def test_max_rounds_pauses_with_limit_reached(self):
        bridge = FakeBridge()
        reader = SequenceReader(bridge)
        supervisor, store = self.build(bridge=bridge, reader=reader,
                                       max_rounds=2, max_wall_seconds=10000.0, poll_seconds=1.0)
        result = supervisor.run()
        self.assertEqual(bridge.round_calls, 2)
        self.assertEqual(result["status"], "PAUSED")
        self.assertEqual(result["outcome"], "LIMIT_REACHED")
        self.assertEqual(store.load()["round_count"], 2)

    # -- 14: wall deadline --------------------------------------------------- #
    def test_max_wall_seconds_pauses_with_limit_reached(self):
        bridge = FakeBridge()
        supervisor, store = self.build(bridge=bridge, reader=FixedReader("no control"),
                                       max_rounds=5, max_wall_seconds=3.0, poll_seconds=1.0)
        result = supervisor.run()
        self.assertEqual(bridge.round_calls, 0)
        self.assertEqual(result["status"], "PAUSED")
        self.assertEqual(result["outcome"], "LIMIT_REACHED")

    # -- 15: restart reuses seen hash --------------------------------------- #
    def test_restart_uses_persisted_seen_hash_and_does_not_duplicate(self):
        bridge = FakeBridge()
        text = wrap_task(make_task())
        first, store = self.build(bridge=bridge, reader=FixedReader(text),
                                  max_rounds=2, max_wall_seconds=1.0, poll_seconds=1.0)
        first.run()
        self.assertEqual(bridge.round_calls, 1)
        first_rounds = store.load()["round_count"]

        # A brand-new Supervisor over the same persisted state root.
        second, store2 = self.build(bridge=bridge, reader=FixedReader(text),
                                    max_rounds=2, max_wall_seconds=1.0, poll_seconds=1.0)
        second.run()
        self.assertEqual(bridge.round_calls, 1)  # no duplicate dispatch after restart
        self.assertEqual(store2.load()["round_count"], first_rounds)

    # -- 16/17: pending-result reconciliation -------------------------------- #
    def test_pending_reconciliation_calls_bridge_once_then_resumes_waiting(self):
        bridge = FakeBridge()
        pending = {"task_id": "PENDING-1", "result_sha256": "r" * 64, "message": "m"}
        calls = {"n": 0}

        def read_pending():
            calls["n"] += 1
            return pending if calls["n"] == 1 else None

        supervisor, store = self.build(bridge=bridge, reader=FixedReader("no control"),
                                       read_pending=read_pending,
                                       max_rounds=5, max_wall_seconds=1.0, poll_seconds=1.0)
        result = supervisor.run()
        self.assertEqual(bridge.round_calls, 1)          # the reconciliation round
        self.assertEqual(supervisor.round_calls, 1)
        self.assertEqual(result["status"], "PAUSED")      # resumed waiting until the wall limit
        self.assertEqual(result["outcome"], "LIMIT_REACHED")
        events = [entry.get("event") for entry in store.read_journal()]
        self.assertIn("CAMPAIGN_RECONCILE", events)

    def test_pending_reconciliation_safety_result_pauses(self):
        bridge = FakeBridge(after_round_status="RECOVERY_REQUIRED")
        supervisor, store = self.build(bridge=bridge, reader=FixedReader("no control"),
                                       read_pending=lambda: {"task_id": "P", "result_sha256": "r", "message": "m"})
        result = supervisor.run()
        self.assertEqual(bridge.round_calls, 1)
        self.assertEqual(result["status"], "PAUSED")
        self.assertEqual(result["outcome"], "SAFETY_STOP")
        self.assertNotEqual(result["exit_code"], 0)

    # -- 18: campaign lock --------------------------------------------------- #
    def test_campaign_lock_prevents_two_workers(self):
        bridge = FakeBridge()
        store = cstate.CampaignStore(CAMPAIGN_ID, root=self.tmp)
        with store.lock(timeout=0.1):
            supervisor, _ = self.build(bridge=bridge, reader=FixedReader(wrap_task(make_task())))
            result = supervisor.run()
        self.assertEqual(result["status"], "LOCK_BUSY")
        self.assertEqual(bridge.round_calls, 0)
        self.assertFalse(store.state_path.exists())  # no campaign state was touched

    # -- 19: persistence survives a restart ---------------------------------- #
    def test_state_and_journal_persist_across_restart(self):
        store = cstate.CampaignStore(CAMPAIGN_ID, root=self.tmp)
        state = cstate.initial_state(campaign_id=CAMPAIGN_ID, milestone=MILESTONE,
                                     started_at=1000.0, deadline=1900.0,
                                     max_rounds=3, initial_sequence=5)
        state["last_seen_assistant_sha256"] = "seen-sha"
        state["round_count"] = 1
        store.save(state)
        store.journal({"event": "CAMPAIGN_START", "campaign_id": CAMPAIGN_ID})

        reopened = cstate.CampaignStore(CAMPAIGN_ID, root=self.tmp)
        loaded = reopened.load()
        for field in cstate.STATE_FIELDS:
            self.assertIn(field, loaded)
        self.assertEqual(loaded["last_seen_assistant_sha256"], "seen-sha")
        self.assertEqual(loaded["round_count"], 1)
        events = [entry.get("event") for entry in reopened.read_journal()]
        self.assertIn("CAMPAIGN_START", events)

    def test_state_permissions_and_required_fields(self):
        store = cstate.CampaignStore(CAMPAIGN_ID, root=self.tmp)
        state = cstate.initial_state(campaign_id=CAMPAIGN_ID, milestone=MILESTONE,
                                     started_at=1.0, deadline=2.0, max_rounds=1,
                                     initial_sequence=5)
        store.save(state)
        store.journal({"event": "X"})
        self.assertEqual(set(cstate.STATE_FIELDS) - set(store.load()), set())
        if os.name == "posix":
            dir_mode = stat.S_IMODE(os.stat(store.root).st_mode)
            file_mode = stat.S_IMODE(os.stat(store.state_path).st_mode)
            journal_mode = stat.S_IMODE(os.stat(store.journal_path).st_mode)
            self.assertEqual(dir_mode, 0o700)
            self.assertEqual(file_mode, 0o600)
            self.assertEqual(journal_mode, 0o600)

    # -- 20: campaign protocol strictness ----------------------------------- #
    def test_campaign_protocol_marker_composition(self):
        self.assertEqual(cproto.CAMPAIGN_OPEN, "<" * 3 + "HERMES_CAMPAIGN_V1" + ">" * 3)
        self.assertEqual(cproto.CAMPAIGN_CLOSE, "<" * 3 + "END_HERMES_CAMPAIGN_V1" + ">" * 3)

    def test_campaign_protocol_accepts_valid_envelope(self):
        payload = json.dumps(campaign_doc(), sort_keys=True)
        parsed = cproto.parse_campaign_envelope(payload, campaign_id=CAMPAIGN_ID,
                                                milestone=MILESTONE, last_result_sha256=LAST_RESULT)
        self.assertEqual(parsed["status"], "ACCEPTED")
        self.assertEqual(parsed["campaign"]["outcome"], "PASS")

    def test_campaign_protocol_rejects_duplicate_key(self):
        payload = ('{"protocol":"HERMES_CAMPAIGN_V1","campaign_id":"CAMPAIGN-T1",'
                   '"campaign_id":"dup","milestone":"M5","status":"CLOSED",'
                   '"outcome":"PASS","in_reply_to":"%s"}' % LAST_RESULT)
        parsed = cproto.parse_campaign_envelope(payload, campaign_id=CAMPAIGN_ID,
                                                milestone=MILESTONE, last_result_sha256=LAST_RESULT)
        self.assertEqual(parsed["status"], "REJECTED")
        self.assertEqual(parsed["code"], "E_DUPLICATE_KEY")

    def test_campaign_protocol_rejects_unknown_and_missing_fields(self):
        unknown = campaign_doc()
        unknown["extra"] = "x"
        parsed = cproto.parse_campaign_envelope(json.dumps(unknown), campaign_id=CAMPAIGN_ID,
                                                milestone=MILESTONE, last_result_sha256=LAST_RESULT)
        self.assertEqual(parsed["code"], "E_UNKNOWN_FIELD")

        missing = campaign_doc()
        missing.pop("outcome")
        parsed = cproto.parse_campaign_envelope(json.dumps(missing), campaign_id=CAMPAIGN_ID,
                                                milestone=MILESTONE, last_result_sha256=LAST_RESULT)
        self.assertEqual(parsed["code"], "E_MISSING_FIELD")

    def test_campaign_protocol_rejects_bad_status_and_outcome(self):
        bad_status = campaign_doc(status="DONE")
        parsed = cproto.parse_campaign_envelope(json.dumps(bad_status), campaign_id=CAMPAIGN_ID,
                                                milestone=MILESTONE, last_result_sha256=LAST_RESULT)
        self.assertEqual(parsed["code"], "E_STATUS")

        bad_outcome = campaign_doc(outcome="MAYBE")
        parsed = cproto.parse_campaign_envelope(json.dumps(bad_outcome), campaign_id=CAMPAIGN_ID,
                                                milestone=MILESTONE, last_result_sha256=LAST_RESULT)
        self.assertEqual(parsed["code"], "E_OUTCOME")

    def test_classify_multiple_campaign_envelopes_is_ambiguous(self):
        text = wrap_campaign(campaign_doc()) + "\n" + wrap_campaign(campaign_doc())
        decision = cproto.classify_response(text, campaign_id=CAMPAIGN_ID,
                                            milestone=MILESTONE, last_result_sha256=LAST_RESULT)
        self.assertEqual(decision["status"], cproto.S_AMBIGUOUS)

    def test_classify_empty_response_is_no_control(self):
        decision = cproto.classify_response("", campaign_id=CAMPAIGN_ID,
                                            milestone=MILESTONE, last_result_sha256=LAST_RESULT)
        self.assertEqual(decision["status"], cproto.S_NO_CONTROL)

    # -- 21: CLI interface --------------------------------------------------- #
    def test_cli_help_exposes_interface(self):
        cli = str(_SUPERVISOR_DIR / "campaign_cli.py")
        top = subprocess.run([sys.executable, cli, "--help"], capture_output=True,
                             text=True, timeout=60)
        self.assertEqual(top.returncode, 0)
        self.assertIn("status", top.stdout)
        self.assertIn("run", top.stdout)

        run_help = subprocess.run([sys.executable, cli, "run", "--help"], capture_output=True,
                                  text=True, timeout=60)
        self.assertEqual(run_help.returncode, 0)
        for flag in ("--campaign-id", "--milestone", "--start-sequence", "--start-nonce",
                     "--start-in-reply-to", "--max-rounds", "--max-wall-seconds", "--poll-seconds"):
            self.assertIn(flag, run_help.stdout)

        status_help = subprocess.run([sys.executable, cli, "status", "--help"],
                                     capture_output=True, text=True, timeout=60)
        self.assertEqual(status_help.returncode, 0)
        self.assertIn("--campaign-id", status_help.stdout)

    # -- 22: no live transport is imported/constructed by the tests ---------- #
    def test_no_live_transport_constructed(self):
        # The Supervisor is driven exclusively through injected fakes above. Assert
        # the fakes are what carry the calls, not the live adapter.
        bridge = FakeBridge()
        reader = FixedReader(wrap_task(make_task()))
        supervisor, _ = self.build(bridge=bridge, reader=reader, max_rounds=1,
                                   max_wall_seconds=1.0, poll_seconds=1.0)
        self.assertIs(supervisor.read_latest_assistant, reader)
        self.assertEqual(supervisor.bridge_round, bridge.round)
        self.assertEqual(supervisor.bridge_status, bridge.status)


if __name__ == "__main__":
    unittest.main()
