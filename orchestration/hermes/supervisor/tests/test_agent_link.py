"""Boundary tests for automatic report/review handoff; no real model calls."""
import json
import contextlib
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import agent_link as link


class Endpoint:
    session_id = "worker-session"
    thread_id = "review-session"

    def __init__(self, decisions=None, fault=None, callback=None):
        self.decisions = iter(decisions or [])
        self.fault, self.callback = fault, callback
        self.calls = []

    def ask(self, prompt):
        self.calls.append(prompt)
        template, data = prompt.split("OUTPUT_TEMPLATE_JSON\n", 1)[1].split("\nINPUT_DATA_JSON\n", 1)
        body, d = json.loads(data), json.loads(template)
        if self.callback:
            self.callback(len(self.calls))
        if self.fault:
            raise link.LinkError(self.fault)
        if d["kind"] == "DECISION":
            decision = next(self.decisions)
            d["payload"] = {"decision": decision,
                            "action": "inspect_evidence" if decision == "CONTINUE" else None,
                            "instruction": "核对报告；不重跑失败任务。"}
        else:
            d["payload"] = {"source_sha256": body["source_sha256"], "summary": "业务失败。",
                            "facts": {"business_status": "FAILED", "task_exit_code": 124,
                                      "matched_tests": 0, "root_cause": "UNKNOWN", "windows_status": "UNKNOWN"}}
        return json.dumps(d, ensure_ascii=False)


class ExchangeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="stack-link-test-", dir="/var/tmp")
        self.addCleanup(self.temp.cleanup)
        self.evidence = Path(self.temp.name) / "report.md"
        self.evidence.write_text("BLOCKED / exit 124; 0 tests; root cause UNKNOWN\n")
        self.sha = link.digest(self.evidence.read_text())
        self.saved = []

    def run_exchange(self, worker=None, reviewer=None):
        return link.exchange(link_id="LINK-TEST", evidence_path=self.evidence,
                             evidence_sha=self.sha, worker=worker or Endpoint(),
                             reviewer=reviewer or Endpoint(["CONTINUE", "COMPLETE"]),
                             save=lambda s: self.saved.append(json.loads(json.dumps(s))))

    def test_two_way_exchange_uses_instruction_and_keeps_failure(self):
        worker, reviewer = Endpoint(), Endpoint(["CONTINUE", "COMPLETE"])
        result = self.run_exchange(worker, reviewer)
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(result["inspection_count"], 1)
        self.assertEqual(len(worker.calls), 2)
        self.assertEqual(len(reviewer.calls), 2)
        self.assertIn("核对报告", worker.calls[1])
        self.assertEqual(result["messages"][2]["payload"]["facts"]["task_exit_code"], 124)
        self.assertEqual(self.saved[-1]["stage"], "TERMINAL")

    def test_worker_failure_never_retries_or_calls_reviewer(self):
        worker, reviewer = Endpoint(fault="WORKER_DEADLINE"), Endpoint()
        with self.assertRaisesRegex(link.LinkError, "WORKER_DEADLINE"):
            self.run_exchange(worker, reviewer)
        self.assertEqual(len(worker.calls), 1)
        self.assertFalse(reviewer.calls)
        self.assertEqual(self.saved[-1]["stage"], "WORKER_IN_FLIGHT")

    def test_changed_evidence_stops_before_local_followup(self):
        worker = Endpoint()
        reviewer = Endpoint(["CONTINUE"], callback=lambda _: self.evidence.write_text("changed"))
        with self.assertRaisesRegex(link.LinkError, "EVIDENCE_CHANGED"):
            self.run_exchange(worker, reviewer)
        self.assertEqual(len(worker.calls), 1)

    def test_human_required_is_terminal(self):
        worker, reviewer = Endpoint(), Endpoint(["HUMAN_REQUIRED"])
        result = self.run_exchange(worker, reviewer)
        self.assertEqual(result["status"], "HUMAN_REQUIRED")
        self.assertEqual(len(worker.calls), 1)

    def test_repeated_continue_stops_without_third_worker_call(self):
        worker, reviewer = Endpoint(), Endpoint(["CONTINUE", "CONTINUE"])
        with self.assertRaisesRegex(link.LinkError, "LINK_LIMIT_REACHED"):
            self.run_exchange(worker, reviewer)
        self.assertEqual(len(worker.calls), 2)

    def test_complete_without_roundtrip_rejected(self):
        with self.assertRaisesRegex(link.LinkError, "ROUNDTRIP_INCOMPLETE"):
            self.run_exchange(reviewer=Endpoint(["COMPLETE"]))

    def test_no_shell_dispatch_even_with_valid_message_binding(self):
        d = {"protocol": link.PROTOCOL, "link_id": "L", "sequence": 2, "in_reply_to": "hash",
             "kind": "DECISION", "payload": {"decision": "CONTINUE", "action": "shell",
                                             "instruction": "sudo run something"}}
        with self.assertRaisesRegex(link.LinkError, "ACTION_NOT_AUTHORIZED"):
            link.check_message(json.dumps(d), kind="DECISION", link_id="L", sequence=2, previous="hash")

    def test_duplicate_keys_stale_sequence_and_wrong_link_rejected(self):
        with self.assertRaisesRegex(link.LinkError, "DUPLICATE_JSON_KEY"):
            link.strict_json('{"action":"inspect_evidence","action":"shell"}')
        d = {"protocol": link.PROTOCOL, "link_id": "OLD", "sequence": 2, "in_reply_to": "hash",
             "kind": "DECISION", "payload": {}}
        with self.assertRaisesRegex(link.LinkError, "MESSAGE_BINDING"):
            link.check_message(json.dumps(d), kind="DECISION", link_id="L", sequence=3, previous="hash")

    def test_symlink_report_rejected(self):
        alias = self.evidence.with_name("alias.md")
        alias.symlink_to(self.evidence)
        with self.assertRaises(OSError):
            link.read_evidence(alias, self.sha)

    def test_worker_mod_disables_and_blocks_tools(self):
        mod = (link.HERE / "agent_link_worker.mjs").as_uri()
        code = """
import policy from MOD;
let names = ['shell_command', 'write_file', 'task', 'mcp'];
let start, hooks;
policy({on: (event, fn) => {start = fn},
        setActiveTools: n => {names = n}, getActiveTools: () => names,
        hooks: h => {hooks = h}});
start();
if (names.length || !hooks.beforeToolCall().block || !hooks.beforeToolCall().terminate)
  process.exit(1);
""".replace("MOD", json.dumps(mod))
        p = subprocess.run(["node", "--input-type=module", "-e", code], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("STACK_AGENT_LINK_TOOLS_NONE", p.stderr)

    def fake_reviewer(self, status="completed", approval=False):
        exe = Path(self.temp.name) / "fake-codex"
        exe.write_text('''#!/usr/bin/python3
import json,sys
def send(d): print(json.dumps(d),flush=True)
for line in sys.stdin:
 d=json.loads(line); m=d.get('method')
 if m=='initialize': send({'id':d['id'],'result':{}})
 if m=='thread/start': send({'id':d['id'],'result':{'thread':{'id':'review'}}})
 if m=='turn/start':
  send({'id':d['id'],'result':{'turn':{'id':'turn'}}})
  if APPROVAL:
   send({'id':100,'method':'item/commandExecution/requestApproval','params':{}})
  else:
   for i in range(250): send({'method':'item/agentMessage/delta','params':{'threadId':'review','turnId':'turn','delta':'ignored'}})
   send({'method':'item/completed','params':{'threadId':'review','turnId':'turn','item':{'type':'agentMessage','id':'answer','text':'final-only'}}})
   send({'method':'turn/completed','params':{'threadId':'review','turn':{'id':'turn','status':STATUS}}})
'''.replace('APPROVAL', repr(approval)).replace('STATUS', repr(status)))
        exe.chmod(0o700)
        reviewer = link.CodexReviewer(self.temp.name, time.monotonic()+3, "no tools", executable=str(exe))
        self.addCleanup(reviewer.close)
        return reviewer

    def test_appserver_burst_stream_uses_completed_final_message(self):
        reviewer = self.fake_reviewer()
        self.assertEqual(reviewer.ask("report"), "final-only")

    def test_appserver_failed_turn_never_uses_partial_answer(self):
        reviewer = self.fake_reviewer(status="failed")
        with self.assertRaisesRegex(link.LinkError, "REVIEW_TURN_failed"):
            reviewer.ask("report")

    def test_appserver_approval_is_not_auto_approved(self):
        reviewer = self.fake_reviewer(approval=True)
        with self.assertRaisesRegex(link.LinkError, "REVIEW_REQUESTS_HUMAN"):
            reviewer.ask("report")

    def test_persisted_attempt_cannot_be_silently_restarted(self):
        reviewer, worker = Endpoint(["CONTINUE", "COMPLETE"]), Endpoint()
        reviewer.close = lambda: None
        args = SimpleNamespace(link_id="SAVED", evidence=self.evidence, evidence_sha256=self.sha,
                               max_wall_seconds=60, codex="unused", command_code="unused", worker_model=None)
        with patch.object(link.cstate, "state_root", return_value=Path(self.temp.name)), \
                patch.object(link, "CodexReviewer", return_value=reviewer) as make_reviewer, \
                patch.object(link, "CommandCodeWorker", return_value=worker), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(link.run(args), 0)
            saved = json.loads((Path(self.temp.name)/"agent-link/SAVED/state.json").read_text())
            self.assertEqual(saved["worker_session_id"], "worker-session")
            self.assertEqual(saved["status"], "COMPLETE")
            self.assertNotIn("last_unvalidated_response", saved)
            with self.assertRaisesRegex(link.LinkError, "LINK_ALREADY_ATTEMPTED"):
                link.run(args)
            self.assertEqual(make_reviewer.call_count, 1)


if __name__ == "__main__":
    unittest.main()
