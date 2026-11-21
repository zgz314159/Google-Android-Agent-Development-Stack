#!/usr/bin/env python3
"""Persistent Agent Link jobs: Hermes review/dispatch + advisor dual-link.

Corrected topology (2026-11-21):
1) Dev: Cursor decide + local gate -> Hermes / Command Code / terminal (no HERMES_TASK_V1).
2) Advisor: plain development report -> Chrome ChatGPT -> instructions reinjected into Hermes.
3) Review: Cursor inbox is post-facto reports only (not a Chrome control relay).

Chrome must never receive HERMES_TASK_V1 / EXECUTE_CONTRACT challenge-response.
No new daemon or deployment framework. Model text cannot introduce paths, budgets,
task identities, retries or promotion.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from . import agent_link as link, agent_link_actions as actions
except ImportError:
    import agent_link as link
    import agent_link_actions as actions

ACTIVE = {"WAITING_PREPARATION", "NEW", "READY", "WAITING_REVIEW", "WORKER_RUNNING", "ACTION_RUNNING"}
TERMINAL = {"COMPLETE", "HUMAN_REQUIRED", "STOP"}
DESKTOP_CODEX_BIN = Path('/usr/lib/chatgpt/resources/codex')
REVIEW_BINDING_NAME = 'review-binding.json'
CURSOR_INBOX_NAME = 'cursor-inbox'
CURSOR_REVIEW_ID = 'cursor-inbox'
CODEX_THREAD_RE = re.compile(r"[0-9a-f-]{36}")


class NotificationNotStarted(link.LinkError):
    """The queue executable was not started; no delivery attempt took place."""


def codex_executable(explicit=None):
    value=explicit or os.environ.get('CODEX_APP_RUNTIME_CLI_PATH') or shutil.which('codex') or DESKTOP_CODEX_BIN
    if not value or not Path(value).is_absolute() or not Path(value).is_file() or not os.access(value,os.X_OK):
        raise NotificationNotStarted('CODEX_QUEUE_EXECUTABLE_MISSING_NOT_SENT')
    return str(Path(value).resolve())


def codex_queue(thread_id, message, *, executable=None):
    binary=codex_executable(executable)
    try:
        p=subprocess.run([binary,'queue','--thread',thread_id,'--message',message],
                         capture_output=True,text=True,timeout=15)
    except FileNotFoundError as exc:
        raise NotificationNotStarted('CODEX_QUEUE_EXECUTABLE_MISSING_NOT_SENT') from exc
    return {'returncode':p.returncode}


def root():
    value = (link.cstate.state_root()/"agent-link/jobs").resolve()
    if any(value.is_relative_to(p.resolve()) for p in (link.HERE.parents[2], Path.home()/"Projects")):
        raise link.LinkError("STATE_IN_PROJECT")
    return value


def agent_link_root():
    return root().parent


def cursor_inbox_root():
    value = (agent_link_root()/CURSOR_INBOX_NAME).resolve()
    if any(value.is_relative_to(p.resolve()) for p in (link.HERE.parents[2], Path.home()/"Projects")):
        raise link.LinkError("STATE_IN_PROJECT")
    return value


def load_review_binding():
    """Optional dual-channel binding. Missing file keeps Codex-only behavior."""
    path = agent_link_root()/REVIEW_BINDING_NAME
    if not path.exists():
        return {"channels": ["codex"], "required": ["codex"]}
    data = link.strict_json(path.read_text())
    if not isinstance(data, dict):
        raise link.LinkError("REVIEW_BINDING_INVALID")
    channels = data.get("channels")
    if (not isinstance(channels, list) or not channels
            or any(c not in {"codex", "cursor_inbox"} for c in channels)
            or len(channels) != len(set(channels))):
        raise link.LinkError("REVIEW_BINDING_CHANNELS")
    required = data.get("required", channels)
    if (not isinstance(required, list) or not required
            or any(c not in channels for c in required)
            or len(required) != len(set(required))):
        raise link.LinkError("REVIEW_BINDING_REQUIRED")
    return {"channels": channels, "required": required}


def report_message(plan, state):
    return ("【Stack 自动汇报｜非新增授权｜事后审查｜cursor-inbox】job_id=" + plan["job_id"]
            + " report_sha256=" + state["report_sha256"]
            + "。开发在 Hermes+Command Code+终端完成本地受权执行；Chrome ChatGPT 只收开发汇报并回顾问指令（直注回流），"
            "禁止 HERMES_TASK_V1 控制块。本 cursor-inbox 仅事后汇报；用 pending/decide/ack 收口，不经网页中转控制协议。"
            "桌面审查不承担 sudo。模型回报不授予执行、重试、sudo或晋升；已消费任务不重放。")


def validate_review_thread_id(thread_id):
    """Link-1 reviewer identity: Codex terminal UUID or the Cursor inbox endpoint id."""
    if thread_id == CURSOR_REVIEW_ID or CODEX_THREAD_RE.fullmatch(thread_id):
        return thread_id
    raise link.LinkError("THREAD_ID")


def review_queue_for_binding(codex_bin=None):
    """Build the optional Codex terminal queue only when link-1 binding includes codex."""
    binding = load_review_binding()
    if "codex" not in binding["channels"]:
        def _cursor_only(_thread, _message):
            raise link.LinkError("CODEX_REVIEW_CHANNEL_DISABLED")
        return None, _cursor_only
    binary = codex_executable(codex_bin)
    return binary, (lambda thread, message: codex_queue(thread, message, executable=binary))


def write_cursor_inbox(plan, state, message):
    """Durable Cursor-facing drop. Does not grant decisions or execute actions."""
    inbox = cursor_inbox_root()
    inbox.mkdir(mode=0o700, parents=True, exist_ok=True)
    payload = {
        "job_id": plan["job_id"],
        "thread_id": plan["thread_id"],
        "report_sha256": state["report_sha256"],
        "plan_sha256": state["plan_sha256"],
        "status": state["status"],
        "report_number": state.get("report_number"),
        "message": message,
        "written_at": time.time(),
    }
    name = plan["job_id"] + "-" + state["report_sha256"][:16] + ".json"
    target = inbox/name
    latest = inbox/"LATEST.json"
    wake = inbox/"WAKE"
    text = link.json_text(payload) + "\n"
    tmp = target.with_suffix(target.suffix + ".tmp")
    link.cstate._atomic_write(tmp, text)
    os.replace(tmp, target)
    link.cstate._atomic_write(latest, text)
    link.cstate._atomic_write(wake, link.json_text({
        "job_id": plan["job_id"],
        "report_sha256": state["report_sha256"],
        "path": str(target),
        "written_at": payload["written_at"],
    }) + "\n")
    return target


def publish_cursor_inbox(job_id):
    """Re-publish an existing review/failure report into the Cursor inbox without resending Codex."""
    directory, plan, state = load(job_id)
    if (state["status"] not in {"WAITING_REVIEW", "HUMAN_REQUIRED"}
            or not state.get("report_sha256") or not state.get("report")):
        raise link.LinkError("NO_PUBLISHABLE_REPORT")
    message = report_message(plan, state)
    path = write_cursor_inbox(plan, state, message)
    return {
        "job_id": job_id,
        "status": "CURSOR_INBOX_WRITTEN",
        "job_status": state["status"],
        "report_sha256": state["report_sha256"],
        "path": str(path),
        "latest": str(cursor_inbox_root()/"LATEST.json"),
    }


def ident(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", value):
        raise link.LinkError("JOB_ID")
    return value


def validate_plan(p):
    if set(p) != {"job_id", "thread_id", "evidence", "evidence_sha256", "worker_model",
                  "max_wall_seconds", "max_actions", "task", "acceptance"}:
        raise link.LinkError("PLAN_FIELDS")
    ident(p["job_id"])
    validate_review_thread_id(p["thread_id"])
    if not Path(p["evidence"]).is_absolute() or not re.fullmatch(r"[0-9a-f]{64}", p["evidence_sha256"]):
        raise link.LinkError("EVIDENCE_BINDING")
    if (type(p["max_wall_seconds"]) is not int or not 60 <= p["max_wall_seconds"] <= 3600
            or type(p["max_actions"]) is not int or not 1 <= p["max_actions"] <= 3):
        raise link.LinkError("PLAN_LIMITS")
    if not isinstance(p["worker_model"], str) or not p["worker_model"].strip():
        raise link.LinkError("WORKER_MODEL_REQUIRED")
    task = p["task"]
    if task is not None:
        if set(task) != {"task_id", "project", "contract_package", "contract_manifest_sha256", "max_runtime_s"}:
            raise link.LinkError("TASK_FIELDS")
        # Bounded allowlist only; 300 is the user-authorized raise for write-first calendar work.
        if type(task["max_runtime_s"]) is not int or task["max_runtime_s"] not in {120, 300}:
            raise link.LinkError("TASK_BUDGET_NOT_ALLOWED")
        if (not isinstance(task["task_id"], str) or not isinstance(task["project"], str)
                or not Path(task["contract_package"]).is_absolute()
                or not re.fullmatch(r"[0-9a-f]{64}", task["contract_manifest_sha256"])):
            raise link.LinkError("TASK_BINDING")
        spec = p["acceptance"]
        if (not isinstance(spec, dict) or set(spec) != {"kind", "project", "filter", "minimum_tests", "dotnet"}
                or spec["kind"] != "dotnet-test" or not isinstance(spec["filter"], str) or not spec["filter"]
                or type(spec["minimum_tests"]) is not int or spec["minimum_tests"] < 1
                or not isinstance(spec["dotnet"], str) or not Path(spec["dotnet"]).is_absolute()):
            raise link.LinkError("SUPPORTED_HOST_ACCEPTANCE_REQUIRED")
        rel = Path(spec["project"])
        if rel.is_absolute() or ".." in rel.parts or rel.suffix != ".csproj":
            raise link.LinkError("ACCEPTANCE_PROJECT_ESCAPE")
    elif p["acceptance"] is not None:
        raise link.LinkError("ACCEPTANCE_WITHOUT_TASK")
    return p


def load(job_id):
    directory = root()/ident(job_id)
    plan_text = (directory/"plan.json").read_text()
    state = link.strict_json((directory/"state.json").read_text())
    if state["plan_sha256"] != link.digest(plan_text):
        raise link.LinkError("FROZEN_PLAN_CHANGED")
    return directory, validate_plan(link.strict_json(plan_text)), state


def save(directory, state):
    link.cstate._atomic_write(directory/"state.json", link.json_text(state)+"\n")


def submit(plan):
    validate_plan(plan)
    link.read_evidence(plan["evidence"], plan["evidence_sha256"])
    directory = root()/plan["job_id"]
    with link.cstate.campaign_lock(directory):
        if (directory/"state.json").exists() or (directory/"plan.json").exists():
            raise link.LinkError("JOB_ALREADY_EXISTS_NO_RESTART")
        frozen = link.json_text(plan)+"\n"
        link.cstate._atomic_write(directory/"plan.json", frozen)
        initial = "WAITING_PREPARATION" if plan["task"] is not None else "NEW"
        state = {"job_id": plan["job_id"], "plan_sha256": link.digest(frozen), "status": initial,
                 "expires_at": time.time()+plan["max_wall_seconds"], "actions_done": [],
                 "worker_session_id": None, "report_number": 0, "report": None,
                 "report_sha256": None, "notification": None, "decision": None, "results": {}}
        save(directory, state)
    return {"job_id": plan["job_id"], "status": initial, "state": str(directory/"state.json")}


def notify(directory, plan, state, queue=None):
    # Durable attempted flag precedes the potentially non-idempotent send.
    if state.get("notification") is not None:
        raise link.LinkError("NOTIFICATION_ALREADY_ATTEMPTED")
    state["notification"] = "ATTEMPTED"
    save(directory, state)
    message = report_message(plan, state)
    binding = load_review_binding()
    channels = binding["channels"]
    required = binding["required"]
    outcomes = {}

    if "cursor_inbox" in channels:
        try:
            path = write_cursor_inbox(plan, state, message)
            outcomes["cursor_inbox"] = {"ok": True, "path": str(path)}
        except (OSError, ValueError, link.LinkError) as exc:
            outcomes["cursor_inbox"] = {"ok": False, "error": str(exc)}

    if "codex" in channels:
        try:
            result = (queue or codex_queue)(plan["thread_id"], message)
            outcomes["codex"] = {"ok": result["returncode"] == 0, "returncode": result["returncode"]}
        except NotificationNotStarted as exc:
            outcomes["codex"] = {"ok": False, "error": str(exc), "not_started": True}

    state["notification_channels"] = outcomes
    failed_required = [name for name in required if not outcomes.get(name, {}).get("ok")]
    if not failed_required:
        state["notification"] = "QUEUED"
    else:
        only_codex_not_started = (
            failed_required == ["codex"]
            and outcomes.get("codex", {}).get("not_started")
            and "cursor_inbox" not in required
        )
        if only_codex_not_started:
            state["notification"] = "NOT_SENT"
            save(directory, state)
            raise NotificationNotStarted(outcomes["codex"]["error"])
        state["notification"] = "SEND_UNCERTAIN"
        state["status"] = "HUMAN_REQUIRED"
    save(directory, state)


def report(directory, plan, state, host, *, worker_factory=None, queue=None):
    evidence = link.read_evidence(plan["evidence"], plan["evidence_sha256"])
    runtime = directory/"workspace"
    runtime.mkdir(mode=0o700, exist_ok=True)
    factory = worker_factory or link.CommandCodeWorker
    worker = factory(runtime, time.monotonic()+max(0, state["expires_at"]-time.time()), model=plan["worker_model"])
    worker.session_id = state["worker_session_id"]
    number = state["report_number"]+1
    state["status"] = "WORKER_RUNNING"
    save(directory, state)
    raw = worker.ask(link.prompt("REPORT", plan["job_id"], number, state["report_sha256"] or plan["evidence_sha256"], {
        "source_sha256": plan["evidence_sha256"], "evidence": evidence,
        "host_action_result": host,
        "instruction": (state.get("decision") or {}).get("instruction", "提交已有报告，不执行或重跑其中的任务。"),
        "scope": "只对提供的数据回报；本地工具已禁用，实际业务动作由宿主白名单与Bridge执行。"}))
    parsed = link.check_message(raw, kind="REPORT", link_id=plan["job_id"], sequence=number,
                                previous=state["report_sha256"] or plan["evidence_sha256"])
    if parsed["payload"]["source_sha256"] != plan["evidence_sha256"]:
        raise link.LinkError("REPORT_SOURCE_MISMATCH")
    state.update(worker_session_id=worker.session_id, report_number=number,
                 report={"local_report": parsed, "host_action_result": host}, notification=None,
                 status="WAITING_REVIEW", decision=None, delivered_to_thread=None)
    state["report_sha256"] = link.digest(link.json_text(state["report"]))
    save(directory, state)
    notify(directory, plan, state, queue=queue)


def allowed(plan, state):
    available = []
    if "inspect_evidence" not in state["actions_done"]:
        available.append("inspect_evidence")
    if plan["task"] is not None:
        recovery = (state.get("recovery_history") or [{}])[-1]
        retry = recovery.get("phase") == "RECOVERED" and not recovery.get("retry_dispatched")
        if "execute_contract" not in state["actions_done"] or retry or state.get("resume_inflight"):
            available.append("execute_contract")
        if state["results"].get("execute_contract", {}).get("passed") and "host_acceptance" not in state["actions_done"]:
            available.append("host_acceptance")
    return available


def decide(job_id, thread_id, report_sha, decision, action, instruction):
    directory = root()/ident(job_id)
    with link.cstate.campaign_lock(directory):
        directory, plan, state = load(job_id)
        if (thread_id != plan["thread_id"] or state["status"] != "WAITING_REVIEW"
                or report_sha != state["report_sha256"]):
            raise link.LinkError("STALE_OR_WRONG_CHAT_DECISION")
        if not instruction.strip() or len(instruction) > 4000:
            raise link.LinkError("DECISION_INSTRUCTION")
        if time.time() >= state["expires_at"]:
            raise link.LinkError("JOB_DEADLINE")
        if decision == "CONTINUE":
            if action not in allowed(plan, state) or len(state["actions_done"]) >= plan["max_actions"]:
                raise link.LinkError("ACTION_NOT_AUTHORIZED")
            state["status"] = "READY"
        elif decision in TERMINAL:
            if action is not None:
                raise link.LinkError("TERMINAL_ACTION")
            if decision == "COMPLETE":
                ok = (state["results"].get("host_acceptance", {}).get("passed") if plan["task"]
                      else "inspect_evidence" in state["actions_done"])
                if not ok:
                    raise link.LinkError("BUSINESS_ACCEPTANCE_NOT_PASSED")
            state["status"] = decision
        else:
            raise link.LinkError("DECISION_VALUE")
        state["decision"] = {"decision": decision, "action": action, "instruction": instruction}
        state["delivered_to_thread"] = thread_id
        save(directory, state)
        return {"job_id": job_id, "status": state["status"]}


def step(job_id, *, worker_factory=None, queue=None, execute=None, acceptance=None, prepare=None):
    directory = root()/ident(job_id)
    with link.cstate.campaign_lock(directory):
        directory, plan, state = load(job_id)
        if state["status"] in TERMINAL:
            return {"job_id": job_id, "status": state["status"]}
        try:
            if (directory/"stop.request").exists():
                raise link.LinkError("USER_STOP_REQUESTED")
            if time.time() >= state["expires_at"]:
                raise link.LinkError("JOB_DEADLINE")
            if state["status"] in {"ACTION_RUNNING", "WORKER_RUNNING"}:
                raise link.LinkError("INTERRUPTED_NO_AUTO_RECOVERY")
            if state["status"] == "WAITING_REVIEW":
                return {"job_id": job_id, "status": state["status"]}
            if state["status"] == "WAITING_PREPARATION":
                if not (prepare or actions.preparation_ready)(plan["task"]):
                    return {"job_id": job_id, "status": "WAITING_PREPARATION"}
                state["status"] = "NEW"
                save(directory, state)
            if state["status"] == "NEW":
                report(directory, plan, state, {"action": "initial_report"}, worker_factory=worker_factory, queue=queue)
            elif state["status"] == "READY":
                action = state["decision"]["action"]
                if action not in allowed(plan, state) or len(state["actions_done"]) >= plan["max_actions"]:
                    raise link.LinkError("ACTION_NOT_AUTHORIZED")
                # Repeats require the one-shot audited recovery grant, persisted first.
                continuing = action == "execute_contract" and state.pop("resume_inflight", False)
                if action == "execute_contract" and "execute_contract" in state["actions_done"] and not continuing:
                    recovery = state["recovery_history"][-1]
                    recovery["retry_dispatched"] = True
                if not continuing:
                    state["actions_done"].append(action)
                state["status"] = "ACTION_RUNNING"
                save(directory, state)
                if action == "inspect_evidence":
                    link.read_evidence(plan["evidence"], plan["evidence_sha256"])
                    result = {"passed": True, "source_sha256": plan["evidence_sha256"]}
                elif action == "execute_contract":
                    if state["expires_at"]-time.time() < 300:
                        raise link.LinkError("INSUFFICIENT_TIME_FOR_CONTROL_AND_CLEANUP")
                    result = (execute or actions.execute_contract)(plan["task"], job_id)
                elif action == "host_acceptance":
                    if state["expires_at"]-time.time() < 130:
                        raise link.LinkError("INSUFFICIENT_TIME_FOR_ACCEPTANCE")
                    result = (acceptance or actions.accept_dotnet)(plan["task"], plan["acceptance"], directory/"acceptance")
                else:
                    raise link.LinkError("ACTION_NOT_AUTHORIZED")
                state["results"][action] = result
                save(directory, state)
                if (directory/"stop.request").exists():
                    raise link.LinkError("USER_STOP_REQUESTED")
                if not result.get("passed"):
                    raise link.LinkError("ACTION_FAILED_NO_RETRY:" + action)
                report(directory, plan, state, {"action": action, "result": result}, worker_factory=worker_factory, queue=queue)
            else:
                raise link.LinkError("UNKNOWN_JOB_STATE")
        except (link.LinkError, OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
            state.update(status="STOP" if str(exc) == "USER_STOP_REQUESTED" else "HUMAN_REQUIRED", error=str(exc))
            if isinstance(exc,NotificationNotStarted):
                state['notification']='NOT_SENT'
                save(directory,state)
                return {'job_id':job_id,'status':state['status'],'notification':'NOT_SENT','error':str(exc)}
            if state.get("notification") in {"ATTEMPTED", "SEND_UNCERTAIN"}:
                state["notification"] = "SEND_UNCERTAIN"
                save(directory, state)
                return {"job_id": job_id, "status": state["status"], "notification": state["notification"]}
            state["report"] = {"error": str(exc), "results": state["results"]}
            state["report_sha256"] = link.digest(link.json_text(state["report"]))
            state["notification"] = None
            state["delivered_to_thread"] = None
            save(directory, state)
            try:
                notify(directory, plan, state, queue=queue)
            except (OSError, subprocess.SubprocessError, link.LinkError):
                state["notification"] = "SEND_UNCERTAIN"
                save(directory, state)
        return {"job_id": job_id, "status": state["status"], "notification": state.get("notification")}


def pending():
    if not root().is_dir():
        return []
    result = []
    for directory in sorted(root().iterdir()):
        if not (directory/"state.json").is_file():
            continue
        _, plan, state = load(directory.name)
        if state["status"] in ACTIVE or state.get("notification") == "QUEUED" and not state.get("delivered_to_thread"):
            result.append({"plan": plan, "state": state, "allowed_actions": allowed(plan, state)})
    return result


def tick():
    results = []
    with link.cstate.campaign_lock(root()/"worker"):
        for item in pending():
            if item["state"]["status"] in ACTIVE:
                if (item['state']['status'] == 'READY'
                        and (item['state'].get('decision') or {}).get('action') == 'execute_contract'):
                    try:
                        actions.services().ce.require_launch_privilege()
                    except Exception as exc:
                        if not hasattr(exc,'code'):
                            raise
                        results.append({'job_id':item['plan']['job_id'],'status':'READY',
                                        'dispatch':'HOST_CONTEXT_REQUIRED','code':exc.code})
                        continue
                results.append(step(item["plan"]["job_id"]))
    return results


def collect_host_diagnostic(directory, task, svc):
    """Read existing fixed phase metadata once, in the user-started host context."""
    marker=directory/'phase-summary-attempt.json'
    if marker.exists():
        return
    link.cstate._atomic_write(marker,link.json_text({'attempted':True,'task_id':task['task_id']})+'\n')
    try:
        proc=subprocess.run(['sudo','-n','--',svc.ce.CONTROLLED_WRAPPER,'--diagnostic-summary',
            '--task-id',task['task_id']],capture_output=True,text=True,timeout=15)
        stdout,stderr,rc=proc.stdout,proc.stderr,proc.returncode
    except (OSError,subprocess.SubprocessError) as exc:
        stdout,stderr,rc='',type(exc).__name__,None
    link.cstate._atomic_write(directory/'phase-summary.txt',stdout)
    link.cstate._atomic_write(directory/'phase-summary.stderr.txt',stderr)
    link.cstate._atomic_write(marker,link.json_text({'attempted':True,'exit_code':rc,
        'sha256':link.digest(stdout),'task_id':task['task_id']})+'\n')


def host_run(job_id, thread_id, plan_sha256, *, check_only=False, codex_bin=None):
    """User-started, bounded operator process for ONE frozen job; no daemon/service."""
    if os.geteuid() == 0 or os.geteuid() != os.getuid():
        raise link.LinkError('HOST_RUN_REQUIRES_UNPRIVILEGED_OPERATOR')
    svc=actions.services()
    try:
        svc.ce.require_launch_privilege()
    except Exception as exc:
        if not hasattr(exc,'code'):
            raise
        raise link.LinkError('HOST_CONTEXT_REQUIRED:'+exc.code) from exc
    _, plan, state=load(job_id)
    if thread_id != plan['thread_id'] or plan_sha256 != state['plan_sha256']:
        raise link.LinkError('HOST_JOB_BINDING_MISMATCH')
    # Link-1 only: Codex CLI is optional unless review-binding includes the codex channel.
    _binary, queue = review_queue_for_binding(codex_bin)
    if not shutil.which('command-code'):
        raise link.LinkError('HOST_REPORT_WORKER_EXECUTABLE_MISSING')
    if check_only:
        return {'job_id':job_id,'status':state['status'],'host_context':'READY','execution_attempted':False,
                'review_channels': load_review_binding()['channels']}
    deadline=state['expires_at']
    while True:
        # Reuse the same serialization as tick; review decisions use the job lock
        # and remain writable while this operator process waits.
        with link.cstate.campaign_lock(root()/'worker'):
            directory, current_plan, state=load(job_id)
            if (thread_id != current_plan['thread_id'] or plan_sha256 != state['plan_sha256']
                    or state['expires_at'] != deadline):
                raise link.LinkError('HOST_JOB_BINDING_OR_DEADLINE_CHANGED')
            failed=state.get('results',{}).get('execute_contract',{}).get('bridge_result',{})
            waiting_repair=(state['status']=='HUMAN_REQUIRED' and not state.get('recovery_history')
                and failed.get('decision')=='READ_FAILED' and svc.cli.initial_read_failure_is_presend(failed)
                and deadline-time.time()>=430 and len(state['actions_done'])+2<=plan['max_actions']
                and not (directory/'stop.request').exists())
            waiting_notification=(state['status']=='HUMAN_REQUIRED' and not state.get('notification_recovery_history')
                and state.get('notification')=='NOT_SENT' and state.get('report_number')==1
                and state.get('error')=='CODEX_QUEUE_EXECUTABLE_MISSING_NOT_SENT'
                and not state.get('actions_done') and not state.get('results')
                and deadline-time.time()>=430 and not (directory/'stop.request').exists())
            waiting_repair=waiting_repair or waiting_notification
            if state['status'] in TERMINAL and not waiting_repair:
                return {'job_id':job_id,'status':state['status'],'host_context':'READY','error':state.get('error')}
            if not waiting_repair:
                action=(state.get('decision') or {}).get('action') if state['status']=='READY' else None
                result=step(job_id, queue=queue)
                if action=='execute_contract':
                    after=load(job_id)[2]
                    diagnostic=after.get('results',{}).get('execute_contract',{}).get('bridge_result',{}).get('diagnostic',{})
                    if diagnostic.get('stage')=='EXECUTED':
                        collect_host_diagnostic(directory,current_plan['task'],svc)
                if result.get('status') in {'COMPLETE','STOP'}:
                    return {**result,'host_context':'READY'}
        time.sleep(1)


def ack(job_id, thread_id, report_sha):
    directory = root()/ident(job_id)
    with link.cstate.campaign_lock(directory):
        directory, plan, state = load(job_id)
        if thread_id != plan["thread_id"] or report_sha != state["report_sha256"]:
            raise link.LinkError("STALE_OR_WRONG_CHAT_RECEIPT")
        state["delivered_to_thread"] = thread_id
        save(directory, state)
        return {"job_id": job_id, "status": state["status"], "receipt": "CONFIRMED"}


def recover_notification_start(job_id, thread_id, report_sha, authorization_id, *, codex_bin=None, queue=None):
    """Re-deliver only a proven pre-spawn failure, using the existing saved initial report."""
    binary=codex_executable(codex_bin)
    if not re.fullmatch(r'[A-Za-z0-9._:-]{1,128}',authorization_id):
        raise link.LinkError('RECOVERY_AUTHORIZATION_REQUIRED')
    with link.cstate.campaign_lock(root()/'worker'),link.cstate.campaign_lock(root()/ident(job_id)):
        directory,plan,state=load(job_id)
        legacy=(state.get('notification')=='SEND_UNCERTAIN'
            and state.get('error')=="[Errno 2] No such file or directory: 'codex'")
        known_not_sent=(state.get('notification')=='NOT_SENT'
            and state.get('error')=='CODEX_QUEUE_EXECUTABLE_MISSING_NOT_SENT')
        if (thread_id!=plan['thread_id'] or state['status']!='HUMAN_REQUIRED'
                or report_sha!=state.get('report_sha256') or state.get('actions_done') or state.get('results')
                or state.get('report_number')!=1 or not (legacy or known_not_sent)
                or state.get('notification_recovery_history') or state.get('delivered_to_thread')
                or (directory/'stop.request').exists() or state['expires_at']-time.time()<430):
            raise link.LinkError('NOTIFICATION_START_RECOVERY_NOT_ELIGIBLE')
        report=state.get('report',{})
        if report.get('host_action_result')!={'action':'initial_report'} or link.digest(link.json_text(report))!=report_sha:
            raise link.LinkError('SAVED_INITIAL_REPORT_MISMATCH')
        parsed=link.check_message(link.json_text(report.get('local_report')),kind='REPORT',link_id=job_id,
            sequence=1,previous=plan['evidence_sha256'])
        if parsed['payload']['source_sha256']!=plan['evidence_sha256']:
            raise link.LinkError('REPORT_SOURCE_MISMATCH')
        link.read_evidence(plan['evidence'],plan['evidence_sha256'])
        if plan['task'] is not None:
            actions.task_check(plan['task'])
        record={'authorization_id':authorization_id,'reason':'EXECUTABLE_NOT_FOUND_BEFORE_SPAWN',
            'previous':{k:state.get(k) for k in ['status','error','notification','report_sha256']},'phase':'AUTHORIZED'}
        state['notification_recovery_history']=[record]
        state.update(status='WAITING_REVIEW',notification=None,delivered_to_thread=None)
        state.pop('error',None)
        save(directory,state)
        try:
            notify(directory,plan,state,queue=queue or (lambda thread,message:codex_queue(thread,message,executable=binary)))
        except (link.LinkError,OSError,subprocess.SubprocessError) as exc:
            state.update(status='HUMAN_REQUIRED',error=str(exc))
            if state.get('notification')=='ATTEMPTED':state['notification']='SEND_UNCERTAIN'
            record['phase']='DELIVERY_FAILED';save(directory,state)
            raise link.LinkError('NOTIFICATION_RECOVERY_DELIVERY_FAILED') from exc
        record['phase']=state['notification'];save(directory,state)
        return {'job_id':job_id,'status':state['status'],'notification':state['notification'],
                'report_sha256':report_sha,'new_model_call':False}


def stop(job_id, thread_id):
    directory, plan, state = load(job_id)
    if thread_id != plan["thread_id"]:
        raise link.LinkError("WRONG_CHAT_STOP")
    link.cstate._atomic_write(directory/"stop.request", "USER_STOP_REQUESTED\n")
    return {"job_id": job_id, "status": "STOP_REQUESTED",
            "in_flight": state["status"] in {"ACTION_RUNNING", "WORKER_RUNNING"},
            "note": "No next action; an in-flight controlled task retains its existing bounded cleanup."}


def recover_initial_read(job_id, thread_id, report_sha, authorization_id, *, svc=None):
    """One authorized pre-send recovery; preserve the failed attempt and frozen plan."""
    svc = svc or actions.services()
    directory = root()/ident(job_id)
    with link.cstate.campaign_lock(root()/"worker"), link.cstate.campaign_lock(directory):
        directory, plan, state = load(job_id)
        failed = state.get("results", {}).get("execute_contract", {}).get("bridge_result", {})
        if (thread_id != plan["thread_id"] or state["status"] != "HUMAN_REQUIRED"
                or report_sha != state["report_sha256"] or plan["task"] is None
                or failed.get("decision") != "READ_FAILED" or not svc.cli.initial_read_failure_is_presend(failed)
                or "result" in failed or (directory/"stop.request").exists()):
            raise link.LinkError("RECOVERY_NOT_ELIGIBLE")
        if state.get("recovery_history"):
            raise link.LinkError("RECOVERY_LIMIT_REACHED")
        if len(state["actions_done"])+2 > plan["max_actions"] or state["expires_at"]-time.time() < 430:
            raise link.LinkError("RECOVERY_OUTSIDE_EXISTING_BUDGET")
        if not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", authorization_id):
            raise link.LinkError("RECOVERY_AUTHORIZATION_REQUIRED")
        actions.configure_browser_env(svc.adapter)
        bridge_state = link.strict_json((svc.state.state_dir()/"state.json").read_text())
        journal = svc.state.read_journal()
        record = {"authorization_id": authorization_id, "phase": "AUTHORIZED",
                  "failed_report_sha256": report_sha,
                  "failed_attempt": json.loads(link.json_text({k: state.get(k) for k in
                      ("report", "results", "decision", "actions_done", "error")})),
                  "retry_dispatched": False}
        state["recovery_history"] = [record]
        save(directory, state)
        try:
            result = svc.cli.recover_initial_read_failure(task=plan["task"],
                expected_state_sha256=link.digest(link.json_text(bridge_state)),
                rejection_sha256=link.digest(link.json_text(journal[-1] if journal else {})),
                authorization_id=authorization_id)
        except Exception as exc:
            record.update(phase="REJECTED", error=str(exc))
            save(directory, state)
            raise link.LinkError("RECOVERY_REJECTED:"+str(exc)) from exc
        record.update(phase="RECOVERED", bridge=result)
        state.update(status="READY", decision={"decision": "CONTINUE", "action": "execute_contract",
            "instruction": "用户已授权本次有审计的入口恢复；沿用原冻结任务、身份和120秒预算执行一次，再自动回报。"})
        state.pop("error", None)
        save(directory, state)
        return {"job_id": job_id, "status": "READY", "recovery": result}


def prepare_tick_runtime():
    """Use the installed Hermes runtime BEFORE acquiring locks/changing state."""
    proc = subprocess.run(["hermes", "--print-runtime-command"], capture_output=True, text=True, timeout=15)
    if proc.returncode != 0:
        raise link.LinkError("HERMES_RUNTIME_QUERY_FAILED")
    command = link.strict_json(proc.stdout)
    if not isinstance(command, list) or not command or not Path(command[0]).is_absolute() or not Path(command[0]).is_file():
        raise link.LinkError("HERMES_RUNTIME_INVALID")
    if Path(sys.executable).resolve() != Path(command[0]).resolve():
        os.execv(command[0], [command[0], "-B", str(Path(__file__).resolve()), *sys.argv[1:]])


def continue_bootstrap(job_id, thread_id, authorization_id, *, svc=None):
    """Continue one in-flight pre-send attempt after a proven bootstrap crash."""
    svc = svc or actions.services()
    directory = root()/ident(job_id)
    with link.cstate.campaign_lock(root()/"worker"), link.cstate.campaign_lock(directory):
        directory, plan, state = load(job_id)
        history = state.get("recovery_history", [])
        if (thread_id != plan["thread_id"] or state["status"] != "ACTION_RUNNING"
                or len(history) != 1 or not history[0].get("retry_dispatched")
                or history[0].get("bootstrap_continuation")
                or state["expires_at"]-time.time() < 430 or (directory/"stop.request").exists()):
            raise link.LinkError("BOOTSTRAP_CONTINUATION_NOT_ELIGIBLE")
        actions.configure_browser_env(svc.adapter)
        raw = link.strict_json((svc.state.state_dir()/"state.json").read_text())
        candidate = {"protocol": "HERMES_TASK_V1", **plan["task"], "action": "EXECUTE_CONTRACT", "risk": "LOW",
                     "sequence": raw["expected_sequence"], "nonce": raw["expected_nonce"],
                     "in_reply_to": raw["expected_in_reply_to"]}
        # Exact confirmation uses the existing formal adapter; never sends.
        if svc.adapter.confirm_message_present(actions.control_request(candidate, job_id)):
            raise link.LinkError("BOOTSTRAP_REQUEST_ALREADY_PRESENT_NO_RESEND")
        journal = svc.state.read_journal()
        witness = {"authorization_id": authorization_id, "phase": "CONFIRMED_ABSENT",
                   "cause": "Hermes bootstrap re-exec lost the project entrypoint import path"}
        history[0]["bootstrap_continuation"] = witness
        save(directory, state)
        result = svc.cli.recover_initial_read_failure(task=plan["task"],
            expected_state_sha256=link.digest(link.json_text(raw)),
            rejection_sha256=link.digest(link.json_text(journal[-1] if journal else {})),
            authorization_id=authorization_id, bootstrap_request_absent=True)
        witness.update(phase="AUDITED", bridge=result)
        state.update(status="READY", resume_inflight=True)
        save(directory, state)
        return {"job_id": job_id, "status": "READY", "continuation": result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("submit")
    p.add_argument("--plan", type=Path, required=True)
    sub.add_parser("pending")
    sub.add_parser("tick")
    p = sub.add_parser('host-run')
    p.add_argument('--job-id',required=True)
    p.add_argument('--thread-id',required=True)
    p.add_argument('--plan-sha256',required=True)
    p.add_argument('--check-only',action='store_true')
    p.add_argument('--codex-bin',type=Path,default=None)
    p = sub.add_parser("decide")
    p.add_argument("--job-id", required=True)
    p.add_argument("--thread-id", required=True)
    p.add_argument("--report-sha256", required=True)
    p.add_argument("--decision", choices=["CONTINUE", *TERMINAL], required=True)
    p.add_argument("--action", default=None)
    p.add_argument("--instruction", required=True)
    p = sub.add_parser("check-task")
    p.add_argument("--task-plan", type=Path, required=True)
    p = sub.add_parser("ack")
    p.add_argument("--job-id", required=True)
    p.add_argument("--thread-id", required=True)
    p.add_argument("--report-sha256", required=True)
    p = sub.add_parser('recover-notification-start')
    p.add_argument('--job-id',required=True)
    p.add_argument('--thread-id',required=True)
    p.add_argument('--report-sha256',required=True)
    p.add_argument('--authorization-id',required=True)
    p.add_argument('--codex-bin',type=Path,default=None)
    p = sub.add_parser("stop")
    p.add_argument("--job-id", required=True)
    p.add_argument("--thread-id", required=True)
    p = sub.add_parser("recover-initial-read")
    p.add_argument("--job-id", required=True)
    p.add_argument("--thread-id", required=True)
    p.add_argument("--report-sha256", required=True)
    p.add_argument("--authorization-id", required=True)
    p = sub.add_parser("continue-bootstrap")
    p.add_argument("--job-id", required=True)
    p.add_argument("--thread-id", required=True)
    p.add_argument("--authorization-id", required=True)
    p = sub.add_parser("publish-cursor-inbox")
    p.add_argument("--job-id", required=True)
    args = parser.parse_args()
    try:
        if args.command in {"tick", "continue-bootstrap", "host-run"}:
            prepare_tick_runtime()
        if args.command == "submit":
            result = submit(link.strict_json(args.plan.read_text()))
        elif args.command == "pending":
            result = pending()
        elif args.command == "tick":
            result = tick()
        elif args.command == 'host-run':
            result=host_run(args.job_id,args.thread_id,args.plan_sha256,check_only=args.check_only,
                            codex_bin=str(args.codex_bin) if args.codex_bin else None)
        elif args.command == "check-task":
            actions.task_check(link.strict_json(args.task_plan.read_text()))
            result = {"status": "TASK_PREFLIGHT_PASS_NO_EXECUTION"}
        elif args.command == "ack":
            result = ack(args.job_id, args.thread_id, args.report_sha256)
        elif args.command == 'recover-notification-start':
            result=recover_notification_start(args.job_id,args.thread_id,args.report_sha256,args.authorization_id,
                codex_bin=str(args.codex_bin) if args.codex_bin else None)
        elif args.command == "stop":
            result = stop(args.job_id, args.thread_id)
        elif args.command == "recover-initial-read":
            result = recover_initial_read(args.job_id, args.thread_id, args.report_sha256, args.authorization_id)
        elif args.command == "continue-bootstrap":
            result = continue_bootstrap(args.job_id, args.thread_id, args.authorization_id)
        elif args.command == "publish-cursor-inbox":
            result = publish_cursor_inbox(args.job_id)
        else:
            result = decide(args.job_id, args.thread_id, args.report_sha256, args.decision, args.action, args.instruction)
        print(link.json_text(result))
        return 0
    except (link.LinkError, link.cstate.CampaignLockBusy, OSError, ValueError, KeyError) as exc:
        print(link.json_text({"status": "HUMAN_REQUIRED", "error": str(exc)}))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
