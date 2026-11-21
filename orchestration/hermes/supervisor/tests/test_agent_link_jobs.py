"""Dispatch, current-chat receipts and stop-on-failure boundaries, without models."""
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import agent_link as link
import agent_link_jobs as jobs
import agent_link_actions as actions

THREAD = "01a1fb52-6dac-7f61-b200-1f8169e7a605"


class Worker:
    calls = 0
    def __init__(self, *args, **kwargs):
        self.session_id = None
    def ask(self, prompt):
        Worker.calls += 1
        a, b = prompt.split("OUTPUT_TEMPLATE_JSON\n")[1].split("\nINPUT_DATA_JSON\n")
        d, body = json.loads(a), json.loads(b)
        d["payload"] = {"source_sha256": body["source_sha256"], "summary": "failed business stays failed",
                        "facts": {"business_status": "FAILED", "task_exit_code": 124,
                                  "matched_tests": 0, "root_cause": "UNKNOWN", "windows_status": "NOT_RUN"}}
        self.session_id = "fixed-worker"
        return json.dumps(d)


class JobTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="stack-link-jobs-", dir="/var/tmp")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        p = patch.object(link.cstate, "state_root", return_value=self.base)
        p.start(); self.addCleanup(p.stop)
        self.evidence = self.base/"failure.md"
        self.evidence.write_text("FAILED exit 124, 0 tests")
        self.plan = {"job_id": "J", "thread_id": THREAD, "evidence": str(self.evidence),
                     "evidence_sha256": link.digest(self.evidence.read_text()), "worker_model": "configured-worker",
                     "max_wall_seconds": 900, "max_actions": 3, "task": None, "acceptance": None}
        self.sends = []
        Worker.calls = 0

    def queue(self, thread, message):
        self.sends.append((thread, message))
        return {"returncode": 0}

    def step(self, **kwargs):
        return jobs.step("J", worker_factory=Worker, queue=self.queue, prepare=lambda _: True, **kwargs)

    def decision(self, action=None, decision="CONTINUE", sha=None, thread=THREAD):
        _, _, s = jobs.load("J")
        return jobs.decide("J", thread, sha or s["report_sha256"], decision, action, "fixed scoped instruction")

    def business_plan(self):
        self.plan["task"] = {"task_id": "FRESH", "project": "DeclaredProject", "contract_package": "/var/lib/trusted/FRESH",
                             "contract_manifest_sha256": "a"*64, "max_runtime_s": 120}
        self.plan["acceptance"] = {"kind": "dotnet-test", "project": "tests/Tests.csproj",
                                   "filter": "ImportTests", "minimum_tests": 1, "dotnet": "/usr/bin/dotnet"}

    def test_current_chat_roundtrip_and_receipt_without_business_execution(self):
        jobs.submit(self.plan); self.step()
        self.assertEqual(self.sends[0][0], THREAD)
        old_sha = jobs.load("J")[2]["report_sha256"]
        self.decision("inspect_evidence"); self.step()
        self.assertEqual(Worker.calls, 2)
        self.assertEqual(len(self.sends), 2)
        self.assertIsNone(jobs.load("J")[2]["delivered_to_thread"])
        with self.assertRaisesRegex(link.LinkError, "STALE"):
            self.decision(decision="COMPLETE", sha=old_sha)
        self.decision(decision="COMPLETE")
        self.assertEqual(jobs.load("J")[2]["status"], "COMPLETE")
        self.assertFalse(jobs.pending())

    def test_report_cannot_grant_business_action_or_shell(self):
        jobs.submit(self.plan); self.step()
        for action in ("execute_contract", "shell", "sudo", "promote"):
            with self.assertRaisesRegex(link.LinkError, "ACTION_NOT_AUTHORIZED"):
                self.decision(action)

    def test_wrong_chat_and_early_complete_are_refused(self):
        jobs.submit(self.plan); self.step()
        with self.assertRaisesRegex(link.LinkError, "WRONG_CHAT"):
            self.decision("inspect_evidence", thread="0"*36)
        with self.assertRaisesRegex(link.LinkError, "ACCEPTANCE_NOT_PASSED"):
            self.decision(decision="COMPLETE")

    def test_unregistered_task_waits_without_models_sends_or_execution(self):
        self.business_plan();jobs.submit(self.plan)
        result = jobs.step("J", worker_factory=Worker, queue=self.queue, prepare=lambda _: False)
        self.assertEqual(result["status"], "WAITING_PREPARATION")
        self.assertEqual(Worker.calls, 0)
        self.assertFalse(self.sends)
        self.assertFalse(jobs.load("J")[2]["actions_done"])

    def test_execution_failure_stops_without_retries_or_extra_model_calls(self):
        self.business_plan(); jobs.submit(self.plan); self.step()
        self.decision("execute_contract")
        calls = []
        def fail(*args):
            calls.append(args); return {"passed": False, "exit_code": 124}
        result = self.step(execute=fail)
        self.assertEqual(result["status"], "HUMAN_REQUIRED")
        self.step(execute=fail)
        self.assertEqual(len(calls), 1)
        self.assertEqual(Worker.calls, 1)
        state = jobs.load("J")[2]
        jobs.ack("J", THREAD, state["report_sha256"])
        self.assertFalse(jobs.pending())

    def test_business_completion_requires_host_acceptance(self):
        self.business_plan(); jobs.submit(self.plan); self.step()
        self.decision("execute_contract")
        self.step(execute=lambda *_: {"passed": True})
        with self.assertRaisesRegex(link.LinkError, "ACCEPTANCE_NOT_PASSED"):
            self.decision(decision="COMPLETE")
        self.decision("host_acceptance")
        self.step(acceptance=lambda *_: {"passed": True, "executed_tests": 1})
        self.decision(decision="COMPLETE")

    def test_interrupted_action_is_not_recovered(self):
        jobs.submit(self.plan)
        d, _, s = jobs.load("J");s["status"] = "ACTION_RUNNING";jobs.save(d, s)
        self.step()
        self.assertEqual(jobs.load("J")[2]["error"], "INTERRUPTED_NO_AUTO_RECOVERY")
        self.assertEqual(Worker.calls, 0)

    def test_queued_send_timeout_is_not_resent(self):
        jobs.submit(self.plan)
        sends = []
        def uncertain(*args):
            import subprocess
            sends.append(args);raise subprocess.TimeoutExpired("codex queue", 15)
        jobs.step("J", worker_factory=Worker, queue=uncertain)
        self.step()
        self.assertEqual(len(sends), 1)
        self.assertEqual(jobs.load("J")[2]["notification"], "SEND_UNCERTAIN")

    def test_frozen_plan_change_rejected(self):
        jobs.submit(self.plan)
        d, _, _ = jobs.load("J")
        (d/"plan.json").write_text('{}')
        with self.assertRaisesRegex(link.LinkError, "FROZEN_PLAN_CHANGED"):
            jobs.load("J")

    def test_stop_request_prevents_next_worker_or_business_action(self):
        jobs.submit(self.plan)
        jobs.stop("J", THREAD)
        self.step()
        self.assertEqual(jobs.load("J")[2]["status"], "STOP")
        self.assertEqual(Worker.calls, 0)

    def test_zero_test_trx_is_never_acceptance(self):
        f = self.base/"result.trx"
        for executed, passed, expected in [(0, 0, False), (4, 4, True), (4, 3, False)]:
            f.write_text(f'<TestRun><ResultSummary><Counters executed="{executed}" passed="{passed}" total="{executed}"/></ResultSummary></TestRun>')
            self.assertEqual(actions.parse_trx(f, 1)["passed_acceptance"], expected)

    def fake_services(self, consumed=False):
        bridge = self.base/"bridge";bridge.mkdir(exist_ok=True)
        (bridge/"state.json").write_text(json.dumps({"status": "WAITING_FOR_GPT", "expected_sequence": 20,
                                                     "expected_nonce": "nonce", "expected_in_reply_to": "hash"}))
        calls = []
        state = SimpleNamespace(state_dir=lambda: bridge, unresolved_accepted=lambda: [],
                                journal_append=lambda event: calls.append(event['event']),
                                consumed_identities=lambda: ({"FRESH"} if consumed else set(), set()))
        def run_round(entry_guard_fn, read_fn):
            entry_guard_fn();calls.append("guard");read_fn();calls.append("round")
            return {"result": {"outcome": "SUCCESS", "exit_code": 0}, "diagnostic": {"cleanup": "CONFIRMED"},
                    "send": {"status": "CONFIRMED_SENT"}}
        svc = SimpleNamespace(state=state, ce=SimpleNamespace(gate=lambda *a, **k: calls.append("gate")),
                              cli=SimpleNamespace(run_round=run_round))
        svc.protocol = SimpleNamespace(validate_task=lambda *a: {"status": "ACCEPTED"},
            extract_control_message=lambda text: {"status": "ACCEPTED", "task": json.loads(text)})
        svc.adapter = SimpleNamespace(EXPECTED_CDP="http://127.0.0.1:9333", read_latest_assistant=lambda: {"sha256": "old"},
            send_once=lambda text, *a, **k: (calls.append("send") or {"status": "CONFIRMED_SENT"}),
            wait_for_new_assistant=lambda *a, **k: {"status": "NEW_ASSISTANT", "text": json.dumps(actions.task_check(self.plan["task"], svc))})
        return svc, calls

    def test_consumed_business_identity_stops_before_gate_send_or_round(self):
        self.business_plan();svc, calls = self.fake_services(consumed=True)
        with self.assertRaisesRegex(link.LinkError, "ALREADY_CONSUMED"):
            actions.execute_contract(self.plan["task"], "J", svc=svc)
        self.assertFalse(calls)

    def test_real_bridge_adapter_seam_keeps_all_existing_gates(self):
        self.business_plan();svc, calls = self.fake_services()
        result = actions.execute_contract(self.plan["task"], "J", svc=svc)
        self.assertTrue(result["passed"])
        self.assertLess(calls.index("gate"), calls.index("send"))
        self.assertEqual(calls.count("round"), 1)

    def test_formal_browser_environment_is_declared_but_never_redirected(self):
        adapter = SimpleNamespace(EXPECTED_CDP="http://127.0.0.1:9333")
        env = {}
        actions.configure_browser_env(adapter, env)
        self.assertEqual(env, {"BU_CDP_URL": "http://127.0.0.1:9333"})
        for bad in ({"BU_CDP_URL": "http://127.0.0.1:9222"}, {"BU_CDP_WS": "ws://other"}):
            before = dict(bad)
            with self.assertRaisesRegex(link.LinkError, "ENDPOINT_MISMATCH"):
                actions.configure_browser_env(adapter, bad)
            self.assertEqual(bad, before)

    def test_bridge_entry_guard_runs_before_state_or_startup_reconciliation(self):
        svc = actions.services()
        d = self.base/"guard-probe"
        def deny():
            raise link.LinkError("DENIED_BEFORE_STARTUP")
        with self.assertRaisesRegex(link.LinkError, "DENIED_BEFORE_STARTUP"):
            svc.cli.run_round(root=d, entry_guard_fn=deny)
        self.assertFalse((d/"state.json").exists())

    def recovery_fixture(self):
        svc = actions.services()
        d = self.base/"read-recovery";d.mkdir()
        state = svc.state.initial_state();state["status"] = "ERROR"
        (d/"state.json").write_text(link.json_text(state))
        rejection = {"event": "READ_FAILED", "error": "AdapterError",
                     "message": "BU_CDP_URL must equal http://127.0.0.1:9333"}
        svc.state.journal_append(rejection, d)
        last = svc.state.read_journal(d)[-1]
        self.business_plan();task = dict(self.plan["task"]);task["project"] = "OfflineTaskCalendar_WPF"
        kwargs = {"task": task, "expected_state_sha256": link.digest(link.json_text(state)),
                  "rejection_sha256": link.digest(link.json_text(last)), "authorization_id": "USER-READ-ONCE",
                  "root": d, "gate_fn": lambda *a, **k: None}
        return svc, d, state, kwargs

    def test_recovery_changes_only_status_and_appends_audit(self):
        svc, d, state, kwargs = self.recovery_fixture()
        result = svc.cli.recover_initial_read_failure(**kwargs)
        after = json.loads((d/"state.json").read_text())
        expected = dict(state);expected["status"] = "WAITING_FOR_GPT"
        self.assertEqual(after, expected)
        self.assertEqual(result["decision"], "INITIAL_READ_RECOVERED")
        self.assertEqual([e["event"] for e in svc.state.read_journal(d)], ["READ_FAILED", "INITIAL_READ_RECOVERY"])
        self.assertEqual(svc.state.consumed_identities(d), (set(), set()))
        with self.assertRaises(ValueError):
            svc.cli.recover_initial_read_failure(**kwargs)

    def test_recovery_refuses_uncertain_other_read_errors_and_pending(self):
        svc, d, state, kwargs = self.recovery_fixture()
        (d/"pending_result.json").write_text('{}')
        with self.assertRaisesRegex(ValueError, "PENDING"):
            svc.cli.recover_initial_read_failure(**kwargs)
        (d/"pending_result.json").unlink()
        svc.state.journal_append({"event": "READ_FAILED", "error": "AdapterError", "message": "response timed out after send"}, d)
        kwargs["rejection_sha256"] = link.digest(link.json_text(svc.state.read_journal(d)[-1]))
        with self.assertRaisesRegex(ValueError, "NOT_INITIAL_CDP"):
            svc.cli.recover_initial_read_failure(**kwargs)
        self.assertEqual(json.loads((d/"state.json").read_text()), state)

    def test_recovery_refuses_consumed_identity_and_wrong_snapshot(self):
        svc, d, state, kwargs = self.recovery_fixture()
        bad = dict(kwargs);bad["expected_state_sha256"] = '0'*64
        with self.assertRaisesRegex(ValueError, "STATE_MISMATCH"):
            svc.cli.recover_initial_read_failure(**bad)
        with patch.object(svc.state, "is_consumed", return_value=True):
            with self.assertRaisesRegex(ValueError, "ALREADY_CONSUMED"):
                svc.cli.recover_initial_read_failure(**kwargs)

    def test_job_recovery_retains_failed_attempt_and_grants_only_one_repeat(self):
        self.business_plan();jobs.submit(self.plan);self.step()
        self.decision("execute_contract")
        failure = {"decision": "READ_FAILED", "error": "AdapterError",
                   "message": "BU_CDP_URL must equal http://127.0.0.1:9333"}
        self.step(execute=lambda *_: {"passed": False, "bridge_result": failure})
        _, _, state = jobs.load('J');sha = state['report_sha256']
        svc, _, _, _ = self.recovery_fixture()
        bridge = self.base/'read-recovery'
        fake = SimpleNamespace(adapter=svc.adapter,
            state=SimpleNamespace(state_dir=lambda: bridge, read_journal=lambda: svc.state.read_journal(bridge)),
            cli=SimpleNamespace(initial_read_failure_is_presend=svc.cli.initial_read_failure_is_presend,
                recover_initial_read_failure=lambda **k: {"decision":"INITIAL_READ_RECOVERED"}))
        jobs.recover_initial_read('J', THREAD, sha, 'USER-ONCE', svc=fake)
        _, _, restored = jobs.load('J')
        self.assertEqual(restored['actions_done'], ['execute_contract'])
        self.assertEqual(restored['recovery_history'][0]['failed_attempt']['results']['execute_contract']['bridge_result'], failure)
        self.step(execute=lambda *_: {"passed":True})
        _, _, after = jobs.load('J')
        self.assertTrue(after['recovery_history'][0]['retry_dispatched'])
        self.assertEqual(after['actions_done'], ['execute_contract','execute_contract'])
        self.assertNotIn('execute_contract', jobs.allowed(self.plan,after))

    def test_bootstrap_continuation_requires_original_recovery_and_no_later_send(self):
        svc, d, state, kwargs = self.recovery_fixture()
        svc.cli.recover_initial_read_failure(**kwargs)
        raw = json.loads((d/'state.json').read_text());raw['status'] = 'VALIDATING'
        (d/'state.json').write_text(link.json_text(raw))
        kwargs.update(expected_state_sha256=link.digest(link.json_text(raw)),
                      rejection_sha256=link.digest(link.json_text(svc.state.read_journal(d)[-1])),
                      authorization_id='USER-BOOTSTRAP', bootstrap_request_absent=True)
        svc.state.journal_append({'event':'CONTROL_REQUEST_SEND_ATTEMPTED'}, d)
        kwargs['rejection_sha256'] = link.digest(link.json_text(svc.state.read_journal(d)[-1]))
        with self.assertRaisesRegex(ValueError, 'NOT_INITIAL_CDP'):
            svc.cli.recover_initial_read_failure(**kwargs)
        self.assertEqual(json.loads((d/'state.json').read_text()), raw)

    def test_connection_refused_recovery_preserves_chain(self):
        svc,d,state,kwargs=self.recovery_fixture()
        failure={'event':'READ_FAILED','error':'RuntimeError','message':
            'fatal: BU_CDP_URL=http://127.0.0.1:9333 unreachable after 30s: <urlopen error [Errno 111] Connection refused> -- '
            'is the dedicated automation Chrome running? Launch it with --remote-debugging-port=<port> --user-data-dir=<dedicated dir>'}
        svc.state.journal_append(failure,d)
        kwargs['rejection_sha256']=link.digest(link.json_text(svc.state.read_journal(d)[-1]))
        svc.cli.recover_initial_read_failure(**kwargs)
        expected=dict(state);expected['status']='WAITING_FOR_GPT'
        self.assertEqual(json.loads((d/'state.json').read_text()),expected)

    def test_even_known_failure_cannot_recover_after_send_attempt(self):
        svc,d,state,kwargs=self.recovery_fixture()
        failure=svc.state.read_journal(d)[-1]
        svc.state.journal_append({'event':'CONTROL_REQUEST_SEND_ATTEMPTED','sequence':state['expected_sequence']},d)
        svc.state.journal_append(failure,d)
        kwargs['rejection_sha256']=link.digest(link.json_text(svc.state.read_journal(d)[-1]))
        with self.assertRaisesRegex(ValueError,'SEND_ATTEMPT_PRESENT'):
            svc.cli.recover_initial_read_failure(**kwargs)
        self.assertEqual(json.loads((d/'state.json').read_text()),state)

    def test_bootstrap_continuation_preserves_chain_and_consumption(self):
        svc, d, state, kwargs = self.recovery_fixture()
        svc.cli.recover_initial_read_failure(**kwargs)
        raw = json.loads((d/'state.json').read_text());raw['status'] = 'VALIDATING'
        (d/'state.json').write_text(link.json_text(raw))
        kwargs.update(expected_state_sha256=link.digest(link.json_text(raw)),
                      rejection_sha256=link.digest(link.json_text(svc.state.read_journal(d)[-1])),
                      authorization_id='USER-BOOTSTRAP', bootstrap_request_absent=True)
        svc.cli.recover_initial_read_failure(**kwargs)
        expected = dict(raw);expected['status'] = 'WAITING_FOR_GPT'
        self.assertEqual(json.loads((d/'state.json').read_text()), expected)
        self.assertEqual(svc.state.read_journal(d)[-1]['event'], 'BOOTSTRAP_READ_CONTINUATION')
        self.assertEqual(svc.state.consumed_identities(d), (set(),set()))

    def test_inflight_continuation_does_not_consume_third_action(self):
        self.business_plan();jobs.submit(self.plan);self.step()
        self.decision('execute_contract')
        d, _, state = jobs.load('J')
        state.update(status='ACTION_RUNNING', actions_done=['execute_contract','execute_contract'],
                     recovery_history=[{'phase':'RECOVERED','retry_dispatched':True}])
        jobs.save(d,state)
        bridge=self.base/'bootstrap';bridge.mkdir()
        (bridge/'state.json').write_text(link.json_text({'expected_sequence':20,'expected_nonce':'n','expected_in_reply_to':'h'}))
        seen=[]
        svc=SimpleNamespace(adapter=SimpleNamespace(EXPECTED_CDP='http://127.0.0.1:9333',
            confirm_message_present=lambda request: (seen.append(request) or True)),
            state=SimpleNamespace(state_dir=lambda:bridge, read_journal=lambda:[{}]),
            cli=SimpleNamespace(recover_initial_read_failure=lambda **k: {'decision':'INITIAL_READ_RECOVERED'}))
        with self.assertRaisesRegex(link.LinkError,'ALREADY_PRESENT'):
            jobs.continue_bootstrap('J',THREAD,'USER-BOOTSTRAP',svc=svc)
        self.assertEqual(jobs.load('J')[2]['status'],'ACTION_RUNNING')
        svc.adapter.confirm_message_present=lambda request: False
        jobs.continue_bootstrap('J',THREAD,'USER-BOOTSTRAP',svc=svc)
        self.step(execute=lambda *_: {'passed':True})
        self.assertEqual(jobs.load('J')[2]['actions_done'],['execute_contract','execute_contract'])
        self.decision('host_acceptance')
        self.step(acceptance=lambda *_: {'passed':True,'executed_tests':4})
        self.decision(decision='COMPLETE')

    def test_host_acceptance_sandbox_writes_only_external_copy(self):
        worktree = self.base/"business"
        (worktree/"tests").mkdir(parents=True)
        (worktree/"tests/Tests.csproj").write_text('<Project/>')
        registry = self.base/"registry.json"
        registry.write_text(json.dumps({"FRESH": {"worktree": str(worktree)}}))
        sdk = self.base/"test-sdk"
        sdk.write_text('''#!/usr/bin/python3
from pathlib import Path
import errno,sys
if Path(REVIEW_AUTH).exists(): raise SystemExit(10)
if Path('/proc/' + HOST_PID + '/root').exists(): raise SystemExit(11)
try:
 Path(HOST).write_text('must not write host')
 raise SystemExit(9)
except OSError as e:
 if e.errno not in (errno.EROFS,errno.EACCES): raise
results=Path(sys.argv[sys.argv.index('--results-directory')+1])
(results/'acceptance.trx').write_text('<TestRun><ResultSummary><Counters total="1" executed="1" passed="1"/></ResultSummary></TestRun>')
'''.replace('HOST_PID', repr(str(os.getpid()))).replace('HOST', repr(str(worktree/"forbidden"))).replace('REVIEW_AUTH', repr(str(Path.home()/'.codex/auth.json'))))
        sdk.chmod(0o700)
        self.business_plan()
        self.plan["acceptance"]["dotnet"] = str(sdk)
        svc = SimpleNamespace(ce=SimpleNamespace(CONTROLLED_TASK_REGISTRY=str(registry), gate=lambda *a, **k: None))
        result = actions.accept_dotnet(self.plan["task"], self.plan["acceptance"], self.base/"acceptance", svc=svc)
        self.assertTrue(result["passed"])
        self.assertEqual(result["counts"]["executed"], 1)
        self.assertFalse((worktree/"forbidden").exists())

    def test_host_check_is_readonly_and_bound_to_frozen_job(self):
        jobs.submit(self.plan)
        _,_,state=jobs.load('J')
        before=(jobs.root()/'J/state.json').read_bytes()
        svc=actions.services()
        with patch.object(svc.ce,'require_launch_privilege'):
            r=jobs.host_run('J',THREAD,state['plan_sha256'],check_only=True)
            self.assertFalse(r['execution_attempted'])
            for thread,sha in [('0'*36,state['plan_sha256']),(THREAD,'0'*64)]:
                with self.assertRaisesRegex(link.LinkError,'BINDING_MISMATCH'):
                    jobs.host_run('J',thread,sha,check_only=True)
        self.assertEqual(before,(jobs.root()/'J/state.json').read_bytes())
        self.assertEqual(Worker.calls,0)

    def test_host_context_refusal_never_runs_step(self):
        jobs.submit(self.plan);svc=actions.services()
        error=svc.ce.ControlledLaunchError('E_LAUNCH_NO_NEW_PRIVS','blocked')
        with patch.object(svc.ce,'require_launch_privilege',side_effect=error),patch.object(jobs,'step') as run:
            with self.assertRaisesRegex(link.LinkError,'HOST_CONTEXT_REQUIRED'):
                jobs.host_run('J',THREAD,jobs.load('J')[2]['plan_sha256'])
        run.assert_not_called()

    def test_host_runner_never_replays_terminal_job(self):
        jobs.submit(self.plan);directory,_,state=jobs.load('J')
        state['status']='HUMAN_REQUIRED';jobs.save(directory,state)
        svc=actions.services()
        with patch.object(svc.ce,'require_launch_privilege'),patch.object(jobs,'step') as run:
            result=jobs.host_run('J',THREAD,state['plan_sha256'])
        self.assertEqual(result['status'],'HUMAN_REQUIRED')
        run.assert_not_called()

    def test_host_runner_waits_for_review_and_uses_existing_step_only(self):
        jobs.submit(self.plan);svc=actions.services()
        sha=jobs.load('J')[2]['plan_sha256']
        sleeps=[]
        def review(_):
            sleeps.append(1)
            state=jobs.load('J')[2]
            if state['status']=='WAITING_REVIEW':
                self.decision('inspect_evidence') if not state['actions_done'] else self.decision(decision='COMPLETE')
        real_step=jobs.step
        with patch.object(svc.ce,'require_launch_privilege'),patch.object(jobs.time,'sleep',side_effect=review), \
                patch.object(jobs,'step',side_effect=lambda job,**kw: real_step(job,worker_factory=Worker,queue=self.queue)):
            result=jobs.host_run('J',THREAD,sha)
        self.assertEqual(result['status'],'COMPLETE')
        self.assertEqual(jobs.load('J')[2]['actions_done'],['inspect_evidence'])
        self.assertEqual(Worker.calls,2)

    def test_desktop_tick_cannot_consume_ready_action_when_nnp_blocks(self):
        self.business_plan();jobs.submit(self.plan);self.step();self.decision('execute_contract')
        before=(jobs.root()/'J/state.json').read_bytes();svc=actions.services()
        with patch.object(svc.ce,'require_launch_privilege',side_effect=svc.ce.ControlledLaunchError('E_LAUNCH_NO_NEW_PRIVS','blocked')):
            result=jobs.tick()
        self.assertEqual(result[0]['dispatch'],'HOST_CONTEXT_REQUIRED')
        self.assertEqual(before,(jobs.root()/'J/state.json').read_bytes())

    def test_host_diagnostic_is_fixed_readonly_and_never_retried(self):
        self.business_plan();jobs.submit(self.plan)
        directory,_,_=jobs.load('J');svc=actions.services()
        proc=SimpleNamespace(stdout='DIAG phase=sandbox_prep_begin task=FRESH\n',stderr='',returncode=0)
        with patch.object(jobs.subprocess,'run',return_value=proc) as run:
            jobs.collect_host_diagnostic(directory,self.plan['task'],svc)
            jobs.collect_host_diagnostic(directory,self.plan['task'],svc)
        self.assertEqual(run.call_count,1)
        argv=run.call_args.args[0]
        self.assertEqual(argv,['sudo','-n','--',svc.ce.CONTROLLED_WRAPPER,'--diagnostic-summary','--task-id','FRESH'])
        self.assertEqual((directory/'phase-summary.txt').read_text(),proc.stdout)
        self.assertEqual(json.loads((directory/'phase-summary-attempt.json').read_text())['exit_code'],0)

    def test_desktop_cli_resolution_works_without_terminal_path(self):
        binary=self.base/'codex';binary.write_text('#!/bin/sh\nexit 0\n');binary.chmod(0o755)
        with patch.dict(os.environ,{},clear=True),patch.object(jobs.shutil,'which',return_value=None),patch.object(jobs,'DESKTOP_CODEX_BIN',binary):
            self.assertEqual(jobs.codex_executable(),str(binary.resolve()))
            with self.assertRaises(jobs.NotificationNotStarted):
                jobs.codex_executable('/missing/explicit-codex')

    def test_missing_queue_entry_preserves_initial_report_and_never_repeats_worker(self):
        jobs.submit(self.plan)
        def missing(*args): raise jobs.NotificationNotStarted('CODEX_QUEUE_EXECUTABLE_MISSING_NOT_SENT')
        result=jobs.step('J',worker_factory=Worker,queue=missing)
        state=jobs.load('J')[2]
        self.assertEqual(result['notification'],'NOT_SENT')
        self.assertIn('local_report',state['report'])
        self.assertEqual(state['report_number'],1)
        self.step()
        self.assertEqual(Worker.calls,1)

    def test_initial_notification_recovery_reuses_saved_report_and_preserves_failure(self):
        jobs.submit(self.plan);self.step()
        d,_,state=jobs.load('J');sha=state['report_sha256'];report=state['report']
        state.update(status='HUMAN_REQUIRED',notification='SEND_UNCERTAIN',error="[Errno 2] No such file or directory: 'codex'")
        jobs.save(d,state)
        r=jobs.recover_notification_start('J',THREAD,sha,'USER-PRESEND',queue=self.queue)
        after=jobs.load('J')[2]
        self.assertEqual(r['status'],'WAITING_REVIEW')
        self.assertFalse(r['new_model_call'])
        self.assertEqual(after['report'],report)
        self.assertEqual(after['report_sha256'],sha)
        self.assertEqual(Worker.calls,1)
        self.assertEqual(after['notification_recovery_history'][0]['previous']['error'],state['error'])
        with self.assertRaisesRegex(link.LinkError,'NOT_ELIGIBLE'):
            jobs.recover_notification_start('J',THREAD,sha,'USER-AGAIN',queue=self.queue)

    def test_uncertain_started_queue_is_not_notification_start_recovery(self):
        jobs.submit(self.plan);self.step()
        d,_,state=jobs.load('J');sha=state['report_sha256']
        state.update(status='HUMAN_REQUIRED',notification='SEND_UNCERTAIN',error='queue timed out after process started')
        jobs.save(d,state)
        with self.assertRaisesRegex(link.LinkError,'NOT_ELIGIBLE'):
            jobs.recover_notification_start('J',THREAD,sha,'USER-PRESEND',queue=self.queue)
        self.assertFalse(jobs.load('J')[2].get('notification_recovery_history'))

    def test_host_waits_for_proven_notification_repair_without_repeating_initial_model(self):
        jobs.submit(self.plan);svc=actions.services();sha=jobs.load('J')[2]['plan_sha256']
        real_step=jobs.step
        def queue(thread,message):
            if not jobs.load('J')[2].get('notification_recovery_history'):
                raise jobs.NotificationNotStarted('CODEX_QUEUE_EXECUTABLE_MISSING_NOT_SENT')
            return self.queue(thread,message)
        def review(_):
            state=jobs.load('J')[2]
            if state['status']=='HUMAN_REQUIRED':
                jobs.recover_notification_start('J',THREAD,state['report_sha256'],'USER-NOTIFY',queue=self.queue)
            elif state['status']=='WAITING_REVIEW':
                self.decision('inspect_evidence') if not state['actions_done'] else self.decision(decision='COMPLETE')
        with patch.object(svc.ce,'require_launch_privilege'),patch.object(jobs.time,'sleep',side_effect=review), \
                patch.object(jobs,'step',side_effect=lambda job,**kw:real_step(job,worker_factory=Worker,queue=queue)):
            result=jobs.host_run('J',THREAD,sha)
        self.assertEqual(result['status'],'COMPLETE')
        self.assertEqual(Worker.calls,2)
        self.assertEqual(jobs.load('J')[2]['notification_recovery_history'][0]['phase'],'QUEUED')

    def _write_binding(self, channels, required):
        directory = self.base/"agent-link"
        directory.mkdir(parents=True, exist_ok=True)
        (directory/"review-binding.json").write_text(
            json.dumps({"channels": channels, "required": required}) + "\n")

    def test_cursor_inbox_required_succeeds_even_if_codex_fails(self):
        self._write_binding(["cursor_inbox", "codex"], ["cursor_inbox"])
        jobs.submit(self.plan)
        def fail_codex(thread, message):
            self.sends.append((thread, message))
            return {"returncode": 1}
        jobs.step("J", worker_factory=Worker, queue=fail_codex, prepare=lambda _: True)
        state = jobs.load("J")[2]
        self.assertEqual(state["status"], "WAITING_REVIEW")
        self.assertEqual(state["notification"], "QUEUED")
        self.assertTrue(state["notification_channels"]["cursor_inbox"]["ok"])
        self.assertFalse(state["notification_channels"]["codex"]["ok"])
        latest = self.base/"agent-link"/"cursor-inbox"/"LATEST.json"
        self.assertTrue(latest.is_file())
        payload = json.loads(latest.read_text())
        self.assertEqual(payload["job_id"], "J")
        self.assertEqual(payload["report_sha256"], state["report_sha256"])
        self.assertIn("cursor-inbox", payload["message"])

    def test_publish_cursor_inbox_redelivers_waiting_review_without_codex(self):
        jobs.submit(self.plan); self.step()
        before = jobs.load("J")[2]["notification"]
        result = jobs.publish_cursor_inbox("J")
        self.assertEqual(result["status"], "CURSOR_INBOX_WRITTEN")
        self.assertEqual(jobs.load("J")[2]["notification"], before)
        self.assertTrue(Path(result["path"]).is_file())
        self.assertTrue(Path(result["latest"]).is_file())


if __name__ == "__main__":
    unittest.main()
