#!/usr/bin/env python3
"""One isolated, end-to-end diagnostic check for the real execution chain.

Traverses contract_executor.execute -> bridge_cli.run_round -> CampaignSupervisor.run.
Only the external seams are replaced: the subprocess runner, the browser READ/WRITE
(read_latest_assistant / send) and the isolated state dirs. The runner returns REAL
wrapper-format stderr; the final diagnostic is produced by the production parsers — it is
never injected by the test.

Covers: wrapper timeout with a cleanup record; UNKNOWN when the timeout marker is absent;
UNCONFIRMED never misreported as CONFIRMED (incl. conflicting records); unstructured body
text never reaching the campaign output; and an execution-entry rejection reported as
ENTRY_REJECTED (never "started").
"""

from __future__ import annotations

import json
import shutil
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
import bridge_state as bs  # noqa: E402
import bridge_cli  # noqa: E402
import contract_executor as ce  # noqa: E402
import campaign_state as cstate  # noqa: E402
import campaign_supervisor as csup  # noqa: E402

TASK_ID = "T-DIAG"
CAMPAIGN_ID = "CAMPAIGN-DIAG"
MILESTONE = "S0"
NONCE = "nonce-5"
IN_REPLY = "in-reply-to-5"
PREV_RESULT = "a" * 64
MANIFEST = "b" * 64
SECRET_BODY = "PROMPT-BODY-SHOULD-NOT-LEAK"


def make_task(*, package):
    return {
        "protocol": "HERMES_TASK_V1", "task_id": TASK_ID, "sequence": 5,
        "nonce": NONCE, "in_reply_to": IN_REPLY,
        "project": "Google-Android-Agent-Development-Stack", "action": "EXECUTE_CONTRACT",
        "contract_package": package, "contract_manifest_sha256": MANIFEST,
        "risk": "LOW", "max_runtime_s": 120,
    }


class Reader:
    def __init__(self, package):
        self.package = package

    def __call__(self):
        text = "%s\n%s\n%s" % (bridge_protocol.TASK_OPEN,
                               json.dumps(make_task(package=str(self.package)), sort_keys=True),
                               bridge_protocol.TASK_CLOSE)
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


class ChainTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="round-diag-e2e-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.pkg = self.root / "pkg"
        self.pkg.mkdir()
        (self.pkg / "manifest.json").write_text("{}\n", encoding="utf-8")
        self.prompt = self.root / "EXECUTOR-PROMPT.md"
        self.prompt.write_text("task body\n", encoding="utf-8")
        self.wrapper = self.root / "run_registered_task"
        self.wrapper.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        self.wrapper.chmod(0o755)
        self.registry = self.root / "registry.json"
        self.bridge_root = self.root / "bridge"
        self.supervisor_root = self.root / "supervisor"

    def _write_registry(self, *, registered=True):
        data = {TASK_ID: {"contract_package": str(self.pkg)}} if registered else {}
        self.registry.write_text(json.dumps(data), encoding="utf-8")

    def _seed_bridge(self):
        state = bs.load_state(self.bridge_root)
        state.chain(next_sequence=5, next_nonce=NONCE, next_in_reply_to=IN_REPLY,
                    status="WAITING_FOR_GPT", last_task_id="PREV",
                    last_result_sha256=PREV_RESULT)

    def _run(self, *, stderr, returncode, registered=True):
        self._write_registry(registered=registered)
        self._seed_bridge()
        reader = Reader(self.pkg)
        captured = {}

        def fake_runner(argv, **kwargs):
            captured["argv"] = list(argv)
            return subprocess.CompletedProcess(argv, returncode, "body\n" + SECRET_BODY + "\n", stderr)

        def fake_execute(package, prompt, max_runtime_s, **kw):
            return ce.execute(package, str(prompt), max_runtime_s,
                              task_id=kw.get("task_id"), runner=fake_runner,
                              task_registry=str(self.registry), wrapper=str(self.wrapper),
                              require_root_owner=False)

        def fake_gate(package, manifest_sha, **_kw):
            return {"package": str(self.pkg), "prompt": str(self.prompt), "allowed_paths": []}

        def fake_send(text, identifier):
            return {"status": bridge_protocol.S_ALREADY_PRESENT if False else "CONFIRMED_SENT"}

        def bridge_round():
            return bridge_cli.run_round(root=self.bridge_root, read_fn=reader,
                                        gate_fn=fake_gate, execute_fn=fake_execute,
                                        send_fn=fake_send)

        lines = []
        clock = Clock()
        supervisor = csup.CampaignSupervisor(
            campaign_id=CAMPAIGN_ID, milestone=MILESTONE, start_sequence=None,
            start_nonce=None, start_in_reply_to=None, max_rounds=1,
            max_wall_seconds=900.0, poll_seconds=5.0,
            store=cstate.CampaignStore(CAMPAIGN_ID, root=str(self.supervisor_root)),
            read_latest_assistant=reader,
            bridge_status=lambda: bs.load_state(self.bridge_root).as_dict(),
            bridge_round=bridge_round,
            read_pending=lambda: bs.read_pending(self.bridge_root),
            clock=clock, sleep=Sleep(clock), progress=lines.append)
        supervisor.run()
        return [line for line in lines if line.startswith("CAMPAIGN_ROUND_DIAG ")], captured, lines

    def _fields(self, line):
        return dict(part.split("=", 1) for part in line.split(" ")[1:])

    def test_timeout_unconfirmed_not_misreported_and_body_absent(self):
        stderr = (
            "AEGL_TASK_TIMEOUT task=%s pgid=42 max_runtime=120s phase=TERM\n"
            "AEGL_TASK_TIMEOUT task=%s pgid=42 phase=KILL\n"
            "AEGL_TASK_CLEANUP=UNCONFIRMED task=%s pgid=42\n"
            "%s\n" % (TASK_ID, TASK_ID, TASK_ID, SECRET_BODY)
        )
        rows, captured, _ = self._run(stderr=stderr, returncode=124)
        self.assertEqual(len(rows), 1, rows)
        self.assertIn("--task-id", captured["argv"])
        self.assertIn(TASK_ID, captured["argv"])
        fields = self._fields(rows[0])
        self.assertEqual(fields["task_id"], TASK_ID)
        self.assertEqual(fields["stage"], "EXECUTED")
        self.assertEqual(fields["exit_code"], "124")
        self.assertEqual(fields["timed_out"], "True")
        self.assertEqual(fields["timeout_phases"], "KILL,TERM")
        self.assertEqual(fields["cleanup"], "UNCONFIRMED")
        self.assertEqual(fields["send_status"], "CONFIRMED_SENT")
        self.assertRegex(fields["result_sha256"], r"^[0-9a-f]{64}$")
        self.assertNotIn(SECRET_BODY, rows[0])

    def test_no_timeout_marker_is_unknown_not_false(self):
        stderr = "AEGL_TASK_CLEANUP=UNCONFIRMED task=%s pgid=42\n%s\n" % (TASK_ID, SECRET_BODY)
        rows, _, _ = self._run(stderr=stderr, returncode=124)
        fields = self._fields(rows[0])
        self.assertEqual(fields["timed_out"], "UNKNOWN")
        self.assertEqual(fields["cleanup"], "UNCONFIRMED")
        self.assertEqual(fields["timeout_phases"], "UNKNOWN")
        self.assertNotIn(SECRET_BODY, rows[0])

    def test_conflicting_cleanup_never_confirmed(self):
        stderr = (
            "AEGL_TASK_CLEANUP=CONFIRMED task=%s pgid=42\n"
            "AEGL_TASK_CLEANUP=UNCONFIRMED task=%s pgid=42\n"
            "AEGL_TASK_TIMEOUT task=%s pgid=42 phase=KILL\n"
        ) % (TASK_ID, TASK_ID, TASK_ID)
        rows, _, _ = self._run(stderr=stderr, returncode=124)
        fields = self._fields(rows[0])
        self.assertEqual(fields["cleanup"], "UNCONFIRMED")
        self.assertNotEqual(fields["cleanup"], "CONFIRMED")

    def test_marker_for_other_task_is_ignored(self):
        stderr = (
            "AEGL_TASK_TIMEOUT task=OTHER pgid=42 phase=TERM\n"
            "AEGL_TASK_CLEANUP=CONFIRMED task=OTHER pgid=42\n"
        )
        rows, _, _ = self._run(stderr=stderr, returncode=124)
        fields = self._fields(rows[0])
        self.assertEqual(fields["timed_out"], "UNKNOWN")
        self.assertEqual(fields["cleanup"], "UNKNOWN")

    def test_entry_rejection_is_not_reported_as_started(self):
        rows, _, _ = self._run(stderr="", returncode=1, registered=False)
        self.assertEqual(len(rows), 1, rows)
        fields = self._fields(rows[0])
        self.assertEqual(fields["stage"], "ENTRY_REJECTED")
        self.assertNotEqual(fields["stage"], "EXECUTED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
