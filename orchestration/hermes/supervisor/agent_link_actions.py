"""Fixed actions for Agent Link; business execution reuses the real Bridge."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

try:
    from . import agent_link as link
except ImportError:
    import agent_link as link

BRIDGE = Path(__file__).resolve().parent.parent / "bridge"


def services():
    if str(BRIDGE) not in sys.path:
        sys.path.insert(0, str(BRIDGE))
    import bridge_cli, bridge_state, contract_executor, chatgpt_adapter, protocol
    from types import SimpleNamespace
    return SimpleNamespace(cli=bridge_cli, state=bridge_state, ce=contract_executor,
                           adapter=chatgpt_adapter, protocol=protocol)


def contract_gate(task, svc):
    try:
        return svc.ce.gate(task["contract_package"], task["contract_manifest_sha256"],
                           project=task["project"], task_id=task["task_id"])
    except Exception as exc:
        if not hasattr(exc, "code"):
            raise
        raise link.LinkError("CONTRACT_GATE_REJECTED:" + str(exc.code)) from exc


def preparation_ready(task, svc=None):
    svc = svc or services()
    registry = json.loads(Path(svc.ce.CONTROLLED_TASK_REGISTRY).read_text())
    if task["task_id"] not in registry:
        return False
    task_check(task, svc)
    return True


def configure_browser_env(adapter, environ=None):
    """Declare the existing formal adapter endpoint, never relax its checks."""
    env = os.environ if environ is None else environ
    expected = adapter.EXPECTED_CDP
    if env.get("BU_CDP_URL") not in (None, expected) or env.get("BU_CDP_WS"):
        raise link.LinkError("FORMAL_BROWSER_ENDPOINT_MISMATCH")
    env.setdefault("BU_CDP_URL", expected)


def task_check(task, svc=None):
    svc = svc or services()
    state_dir = svc.state.state_dir()
    state_file = state_dir / "state.json"
    if not state_file.is_file():
        raise link.LinkError("BRIDGE_STATE_ABSENT")
    state = link.strict_json(state_file.read_text())
    if (state.get("status") not in {"WAITING_FOR_GPT", "IDLE"}
            or (state_dir / "pending_result.json").exists()
            or svc.state.unresolved_accepted()):
        raise link.LinkError("BRIDGE_NOT_READY_NO_RECOVERY")
    consumed, _ = svc.state.consumed_identities()
    if task["task_id"] in consumed:
        raise link.LinkError("TASK_ALREADY_CONSUMED_NO_RETRY")
    contract_gate(task, svc)
    candidate = {"protocol": "HERMES_TASK_V1", **task, "action": "EXECUTE_CONTRACT", "risk": "LOW",
                 "sequence": state["expected_sequence"], "nonce": state["expected_nonce"],
                 "in_reply_to": state["expected_in_reply_to"]}
    verdict = svc.protocol.validate_task(candidate, state)
    if verdict.get("status") != "ACCEPTED":
        raise link.LinkError("TASK_PROTOCOL_REJECTED:" + str(verdict.get("code")))
    return candidate


def execute_contract(task, job_id, *, svc=None):
    svc = svc or services()
    authorized = {}

    def guard():
        authorized.update(task_check(task, svc))
        configure_browser_env(svc.adapter)

    def control():
        previous = svc.adapter.read_latest_assistant()["sha256"]
        request = ("这是已由用户限定授权且完成可信登记的单次执行请求。请只输出恰好一个 "
                   "HERMES_TASK_V1 控制块，其 JSON 必须逐字段等于下面对象；不要改身份、路径、预算或链值。\n"
                   "request_id=" + job_id + "\n" + link.json_text(authorized))
        sent = svc.adapter.send_once(request, job_id, exact=True)
        if sent.get("status") not in {"CONFIRMED_SENT", "ALREADY_PRESENT"}:
            raise link.LinkError("CONTROL_SEND_UNCERTAIN_NO_RESEND")
        response = svc.adapter.wait_for_new_assistant(previous, timeout=120)
        if response.get("status") != "NEW_ASSISTANT":
            raise link.LinkError("CONTROL_RESPONSE_TIMEOUT_NO_RETRY")
        extracted = svc.protocol.extract_control_message(response.get("text"))
        if extracted.get("status") != "ACCEPTED" or extracted.get("task") != authorized:
            raise link.LinkError("CONTROL_DIFFERS_FROM_AUTHORIZATION")
        return response

    result = svc.cli.run_round(entry_guard_fn=guard, read_fn=control)
    envelope = result.get("result", {})
    diag = result.get("diagnostic", {})
    ok = (envelope.get("outcome") == "SUCCESS" and envelope.get("exit_code") == 0
          and diag.get("cleanup") == "CONFIRMED"
          and result.get("send", {}).get("status") in {"CONFIRMED_SENT", "ALREADY_PRESENT"})
    return {"passed": ok, "bridge_result": result}


def parse_trx(path, minimum):
    root = ET.parse(path).getroot()
    counters = root.find(".//{*}Counters")
    if counters is None:
        raise link.LinkError("ACCEPTANCE_COUNTERS_MISSING")
    data = {k: int(counters.get(k, "0")) for k in
            ("total", "executed", "passed", "failed", "error", "timeout", "aborted", "notExecuted")}
    data["passed_acceptance"] = (data["executed"] >= minimum and data["passed"] == data["executed"]
                                 and not any(data[k] for k in ("failed", "error", "timeout", "aborted", "notExecuted")))
    return data


def accept_dotnet(task, spec, output, *, svc=None):
    svc = svc or services()
    registry = json.loads(Path(svc.ce.CONTROLLED_TASK_REGISTRY).read_text())
    entry = registry.get(task["task_id"], {})
    # Revalidate frozen package and repository relation even after execution.
    contract_gate(task, svc)
    worktree = Path(entry["worktree"]).resolve(strict=True)
    output = Path(output)
    if output.exists():
        raise link.LinkError("ACCEPTANCE_OUTPUT_ALREADY_EXISTS")
    project = output / "project"
    # No symlink from the execution tree can redirect host acceptance outside the copy.
    for path in worktree.rglob("*"):
        if path.is_symlink():
            raise link.LinkError("ACCEPTANCE_WORKTREE_SYMLINK")
    shutil.copytree(worktree, project, ignore=shutil.ignore_patterns(".git", "bin", "obj"))
    test_project = (project / spec["project"]).resolve(strict=True)
    if not test_project.is_relative_to(project.resolve()):
        raise link.LinkError("ACCEPTANCE_PROJECT_ESCAPE")
    results = output / "results"
    results.mkdir()
    sdk = Path(spec["dotnet"]).resolve(strict=True)
    if not sdk.is_file():
        raise link.LinkError("DOTNET_TOOLCHAIN_MISSING")
    argv = [str(sdk), "test", str(test_project), "--filter", spec["filter"],
            "--logger", "trx;LogFileName=acceptance.trx", "--results-directory", str(results)]
    # Host acceptance executes code from a writable AI worktree. Keep the host
    # filesystem read-only and allow writes only to this external acceptance copy.
    home = output / "home"
    home.mkdir()
    hidden = []
    # Business tests must not reach the reviewer's credentials/control sockets.
    for private in (Path.home()/".codex", Path.home()/".commandcode", Path("/run/user")/str(os.getuid())):
        if private.is_dir():
            hidden += ["--tmpfs", str(private)]
    argv = ["bwrap", "--die-with-parent", "--new-session", "--unshare-net", "--unshare-pid", "--unshare-ipc",
            "--ro-bind", "/", "/", "--bind", str(output.resolve()), str(output.resolve()),
            "--tmpfs", "/tmp", *hidden, "--proc", "/proc", "--dev", "/dev", "--clearenv",
            "--setenv", "PATH", "/usr/local/bin:/usr/bin:/bin",
            "--setenv", "HOME", str(home.resolve()), "--setenv", "DOTNET_CLI_HOME", str(home.resolve()),
            "--setenv", "DOTNET_ROOT", str(sdk.parent),
            "--setenv", "NUGET_PACKAGES", str(Path.home()/".nuget/packages"),
            "--setenv", "LANG", "C.UTF-8", "--chdir", str(project.resolve()), "--", *argv]
    proc = subprocess.Popen(argv, cwd=project, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, start_new_session=True)
    try:
        proc.communicate(timeout=120)
    except subprocess.TimeoutExpired as exc:
        link.terminate(proc)
        raise link.LinkError("ACCEPTANCE_TIMEOUT_NO_RETRY") from exc
    trx = results / "acceptance.trx"
    if not trx.is_file():
        return {"passed": False, "exit_code": proc.returncode, "reason": "ACCEPTANCE_TRX_MISSING"}
    counts = parse_trx(trx, spec["minimum_tests"])
    return {"passed": proc.returncode == 0 and counts["passed_acceptance"],
            "exit_code": proc.returncode, "counts": counts}
