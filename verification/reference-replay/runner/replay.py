#!/usr/bin/env python3
"""Reference Replay engine (stdlib only).

Deterministic external-app replay: run a frozen Maestro flow against a physical
device, emit one compact machine-readable result per run. Zero per-step LLM calls,
zero vision in the PASS path, no direct adb UI input.

Execution policy: the official verification gate is FAIL-FAST. The first non-PASS
deterministic run stops the batch immediately (evidence, result.json and
index.json are still flushed, exit code non-zero). `--continue-on-fail` is an
explicit diagnostic opt-in that runs the whole planned batch.

See ../README.md, ../contracts/replay-result.schema.json and
../../orchestration/hermes/DEVICE-EXECUTION-POLICY.md.
"""
from __future__ import annotations

import argparse
import fcntl
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
RR_HOME = os.path.dirname(HERE)


def _stack_paths():
    _lib = os.path.join(os.path.dirname(os.path.dirname(RR_HOME)), "scripts", "lib")
    if _lib not in sys.path:
        sys.path.insert(0, _lib)
    import stack_paths  # noqa: PLC0415

    return stack_paths

ASSERT_CMD_RE = re.compile(r"^\s*-\s*(assert[A-Za-z]*)\b", re.MULTILINE)
ASSERT_CMDS = ("assertVisible", "assertNotVisible", "assertTrue", "assertWithAI")
FORBIDDEN_FOR_VISUAL = ("assertWithAI",)
DIRECT_ADB_UI = ("input tap", "input swipe", "input text")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: str) -> str | None:
    if not path or not os.path.isfile(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def find_screenshots(maestro_out: str) -> list:
    """Deterministic discovery of Maestro screenshots across real output layouts.

    Real Maestro nests every capture under a per-invocation timestamp directory and
    the flow name:  <maestro_out>/<timestamp>/<FLOWNAME>/takeScreenshot/<name>.png
    A flat <maestro_out>/takeScreenshot/*.png layout is also accepted (older
    Maestro / hand-made fixtures). Both patterns are globbed recursively; a
    recursive `**` also matches zero directories, so the first pattern is kept only
    for explicitness. Results are deduplicated and sorted, preserving the original
    runner semantics: the caller takes the lexicographically-last path.
    """
    if not maestro_out or not os.path.isdir(maestro_out):
        return []
    patterns = (
        os.path.join(maestro_out, "takeScreenshot", "*.png"),
        os.path.join(maestro_out, "**", "takeScreenshot", "*.png"),
    )
    found = set()
    for pat in patterns:
        for p in glob.glob(pat, recursive=True):
            if os.path.isfile(p):
                found.add(p)
    return sorted(found)


def count_yaml_assertions(yaml_path: str) -> int:
    try:
        with open(yaml_path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return 0
    total = 0
    for line in text.splitlines():
        m = re.match(r"^\s*-\s*(assert[A-Za-z]*)\b", line)
        if m and m.group(1) in ASSERT_CMDS:
            total += 1
    return total


def parse_commands(commands_path: str) -> tuple[int, int] | None:
    """Best-effort parse of Maestro commands.json -> (total_assertions, passed).

    Returns None when the shape is not recognizable, so the caller can fall back
    to a conservative JUnit/YAML derivation. Never guesses a PASS.
    """
    try:
        with open(commands_path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    items = data if isinstance(data, list) else data.get("commands") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return None
    total = passed = 0
    for it in items:
        if not isinstance(it, dict):
            continue
        name = str(it.get("command") or it.get("name") or it.get("type") or "")
        if not name.lower().startswith("assert"):
            continue
        total += 1
        status = str(it.get("status") or it.get("result") or "").lower()
        if status in ("", "success", "completed", "passed", "ok", "true"):
            passed += 1
    if total == 0:
        return None
    return total, passed


def parse_junit(xml_path: str) -> tuple[int, int] | None:
    """(tests, failures+errors) from a JUnit report, or None."""
    try:
        root = ET.parse(xml_path).getroot()
    except (OSError, ET.ParseError):
        return None
    if root.tag == "testsuites":
        suites = root.findall("testsuite")
        tests = sum(int(s.get("tests", "0")) for s in suites)
        bad = sum(int(s.get("failures", "0")) + int(s.get("errors", "0")) for s in suites)
        return tests, bad
    if root.tag == "testsuite":
        return int(root.get("tests", "0")), int(root.get("failures", "0")) + int(root.get("errors", "0"))
    return None


def device_state(adb_bin: str, serial: str) -> str:
    try:
        out = subprocess.run(
            [adb_bin, "-s", serial, "get-state"],
            capture_output=True, text=True, timeout=15,
        )
        return (out.stdout or "").strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def acquire_lock(lock_dir: str, serial: str, wait: int):
    """Advisory flock on device:<serial>. Returns an open fd or None (busy)."""
    os.makedirs(lock_dir, exist_ok=True)
    path = os.path.join(lock_dir, f"device-{serial}.lock")
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o644)
    flags = fcntl.LOCK_EX | (0 if wait > 0 else fcntl.LOCK_NB)
    deadline = time.monotonic() + max(wait, 0)
    while True:
        try:
            fcntl.flock(fd, flags)
            os.ftruncate(fd, 0)
            os.write(fd, f"{os.getpid()}\n".encode())
            return fd
        except OSError:
            if wait <= 0 or time.monotonic() >= deadline:
                os.close(fd)
                return None
            time.sleep(0.5)


def collect_evidence(run_dir: str, adb_bin: str, serial: str, app_package: str) -> str:
    ev = os.path.join(run_dir, "evidence")
    os.makedirs(ev, exist_ok=True)
    try:
        logcat = subprocess.run(
            [adb_bin, "-s", serial, "logcat", "-d", "-t", "400"],
            capture_output=True, text=True, timeout=30,
        )
        with open(os.path.join(ev, "logcat-slice.txt"), "w", encoding="utf-8") as fh:
            fh.write(logcat.stdout or "")
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        act = subprocess.run(
            [adb_bin, "-s", serial, "shell", "dumpsys", "activity", "activities"],
            capture_output=True, text=True, timeout=30,
        )
        with open(os.path.join(ev, "dumpsys-activity.txt"), "w", encoding="utf-8") as fh:
            fh.write(act.stdout or "")
    except (OSError, subprocess.SubprocessError):
        pass
    with open(os.path.join(ev, "metadata.json"), "w", encoding="utf-8") as fh:
        json.dump({
            "device_serial": serial,
            "app_package": app_package,
            "captured_at": utc_now(),
            "note": "reference-replay failure evidence (fail-closed)",
        }, fh, indent=2)
    return ev


def run_one(flow: dict, run_index: int, args, adb_bin: str) -> dict:
    yaml_path = os.path.join(RR_HOME, "flows", flow["yaml"])
    run_dir = os.path.join(args.out, "runs", f"{flow['flow_id']}-{run_index}")
    os.makedirs(run_dir, exist_ok=True)
    maestro_out = os.path.join(run_dir, "maestro")
    xml_path = os.path.join(run_dir, "maestro.xml")
    txt_path = os.path.join(run_dir, "maestro.txt")

    cmd = [
        args.maestro, "test", yaml_path,
        "--udid", args.serial, "--no-ansi",
        "--format", "JUNIT", "--output", xml_path,
        "--test-output-dir", maestro_out,
    ]
    if args.no_reinstall_driver:
        cmd.append("--no-reinstall-driver")

    start = utc_now()
    t0 = time.monotonic()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=args.timeout)
        out, rc = (proc.stdout or "") + (proc.stderr or ""), proc.returncode
    except subprocess.TimeoutExpired as exc:
        out = f"TIMEOUT after {args.timeout}s\n{exc}"
        rc = 124
    except OSError as exc:
        out = f"MAESTRO_LAUNCH_FAILED: {exc}"
        rc = 127
    wall_ms = int((time.monotonic() - t0) * 1000)
    end = utc_now()
    with open(txt_path, "w", encoding="utf-8") as fh:
        fh.write(out)

    yaml_asserts = count_yaml_assertions(yaml_path)
    a_total, a_passed, a_src = yaml_asserts, 0, "yaml"
    parsed = parse_commands(os.path.join(maestro_out, "commands.json"))
    if parsed is not None:
        a_total, a_passed, a_src = parsed[0], parsed[1], "maestro_commands"
    else:
        junit = parse_junit(xml_path)
        if junit is not None:
            tests, bad = junit
            if tests == 1 and bad == 0:
                a_total, a_passed, a_src = yaml_asserts, yaml_asserts, "junit"
            else:
                a_total, a_passed, a_src = yaml_asserts, 0, "junit"

    # Real Maestro nests captures under <out>/<timestamp>/<FLOW>/takeScreenshot/.
    shots = find_screenshots(maestro_out)
    shot = shots[-1] if shots else None
    passed = rc == 0 and a_total > 0 and a_passed == a_total

    result = {
        "flow_id": flow["flow_id"],
        "device_serial": args.serial,
        "app_package": flow.get("app_package", args.app_package),
        "start_time": start,
        "end_time": end,
        "wall_ms": wall_ms,
        "exit_code": rc,
        "assertions_total": a_total,
        "assertions_passed": a_passed,
        "screenshot_path": shot,
        "screenshot_sha256": sha256_file(shot) if shot else None,
        "visual_llm_calls": 0,
        "model_requests_during_device_steps": 0,
        "direct_adb_ui_inputs": 0,
        "result": "PASS" if passed else "FAIL",
        "run_index": run_index,
        "assertions_source": a_src,
        "failure": None,
    }
    if not passed:
        ev = collect_evidence(run_dir, adb_bin, args.serial, result["app_package"])
        result["failure"] = {
            "reason": "FLOW_ASSERTION_OR_STEP_FAILED" if rc != 0 and rc != 127 else "MAESTRO_ERROR",
            "marker": f"MAESTRO_EXIT_{rc}",
            "step": None,
            "evidence_dir": ev,
        }
    with open(os.path.join(run_dir, "result.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
    return result


def blocked_result(flow: dict, run_index: int, args, reason: str) -> dict:
    return {
        "flow_id": flow["flow_id"],
        "device_serial": args.serial,
        "app_package": flow.get("app_package", args.app_package),
        "start_time": utc_now(),
        "end_time": utc_now(),
        "wall_ms": None,
        "exit_code": None,
        "assertions_total": 0,
        "assertions_passed": 0,
        "screenshot_path": None,
        "screenshot_sha256": None,
        "visual_llm_calls": 0,
        "model_requests_during_device_steps": 0,
        "direct_adb_ui_inputs": 0,
        "result": "BLOCKED",
        "run_index": run_index,
        "assertions_source": "yaml",
        "failure": {"reason": reason, "marker": reason, "step": None, "evidence_dir": None},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Reference replay runner")
    ap.add_argument("--flows", default="R1,R2,R3")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--serial", default="87296ada")
    ap.add_argument("--out", default=os.path.join(str(_stack_paths().artifacts_root()), "verification",
                                                  "reference-replay", utc_now().replace(":", "")))
    ap.add_argument("--maestro", default=shutil.which("maestro") or os.path.expanduser("~/.maestro/bin/maestro"))
    ap.add_argument("--adb", default=shutil.which("adb") or "adb")
    ap.add_argument("--lock-dir", default=str(_stack_paths().state_root() / "verification" / "locks"))
    ap.add_argument("--lock-wait", type=int, default=0)
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--no-reinstall-driver", action="store_true")
    ap.add_argument("--skip-device-check", action="store_true",
                    help="offline harness tests ONLY (requires REPLAY_ALLOW_NO_DEVICE=1); never a device PASS")
    ap.add_argument("--continue-on-fail", action="store_true",
                    help="diagnostic ONLY: run the whole planned batch even after a non-PASS run. "
                         "The official verification gate defaults to FAIL-FAST (stop at the first failure)")
    args = ap.parse_args()

    with open(os.path.join(RR_HOME, "flows", "flows.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)
    args.app_package = manifest["app_package"]
    by_id = {f["flow_id"]: f for f in manifest["flows"]}
    wanted = [s.strip() for s in args.flows.split(",") if s.strip()]
    unknown = [w for w in wanted if w not in by_id]
    if unknown:
        print(f"UNKNOWN_FLOW {unknown}", file=sys.stderr)
        return 2

    planned_runs = len(wanted) * args.runs
    os.makedirs(os.path.join(args.out, "runs"), exist_ok=True)
    results: list[dict] = []

    # --- device availability -------------------------------------------------
    if not args.skip_device_check:
        state = device_state(args.adb, args.serial)
        if state != "device":
            for fid in wanted:
                for i in range(1, args.runs + 1):
                    r = blocked_result(by_id[fid], i, args, "DEVICE_UNAVAILABLE")
                    r["failure"]["reason"] = f"DEVICE_UNAVAILABLE:{state}"
                    results.append(r)
            _write_index(args, results, manifest, planned_runs=planned_runs)
            print(f"DEVICE_UNAVAILABLE serial={args.serial} state={state}", file=sys.stderr)
            return 3
    elif os.environ.get("REPLAY_ALLOW_NO_DEVICE") != "1":
        print("REFUSING: --skip-device-check requires REPLAY_ALLOW_NO_DEVICE=1", file=sys.stderr)
        return 2

    # --- exclusive device lock ----------------------------------------------
    fd = acquire_lock(args.lock_dir, args.serial, args.lock_wait)
    if fd is None:
        for fid in wanted:
            for i in range(1, args.runs + 1):
                results.append(blocked_result(by_id[fid], i, args, "DEVICE_BUSY"))
        _write_index(args, results, manifest, planned_runs=planned_runs)
        print(f"DEVICE_BUSY serial={args.serial}", file=sys.stderr)
        return 4

    # --- deterministic batch (fail-fast by default) --------------------------
    stopped_early = False
    stop_reason = None
    first_failure = None
    try:
        for fid in wanted:
            for i in range(1, args.runs + 1):
                r = run_one(by_id[fid], i, args, args.adb)
                results.append(r)
                print(f"[{fid} run {i}] {r['result']} wall_ms={r['wall_ms']} "
                      f"assert {r['assertions_passed']}/{r['assertions_total']}")
                if r["result"] != "PASS":
                    if first_failure is None:
                        first_failure = {
                            "flow_id": fid,
                            "run_index": i,
                            "result": r["result"],
                            "exit_code": r.get("exit_code"),
                            "assertions_passed": r.get("assertions_passed"),
                            "assertions_total": r.get("assertions_total"),
                            "failure": r.get("failure"),
                        }
                    if not args.continue_on_fail:
                        stopped_early = True
                        stop_reason = (
                            f"FAIL_FAST: first non-PASS run ({fid} run {i} -> {r['result']}) "
                            f"stopped the deterministic batch"
                        )
                        print(f"FAIL_FAST stop={fid} run={i} result={r['result']} "
                              f"executed={len(results)}/{planned_runs}", file=sys.stderr)
                        break
            if stopped_early:
                break
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
        except OSError:
            pass

    _write_index(args, results, manifest, planned_runs=planned_runs,
                 stopped_early=stopped_early, stop_reason=stop_reason,
                 first_failure=first_failure)
    bad = [r for r in results if r["result"] != "PASS"]
    print(f"REPLAY_TOTAL={len(results)} PASS={len(results) - len(bad)} NOT_PASS={len(bad)}"
          f"{' STOPPED_EARLY' if stopped_early else ''}")
    if stopped_early:
        print(f"REPLAY_PLANNED={planned_runs} REPLAY_EXECUTED={len(results)} STOP_REASON={stop_reason}")
    return 0 if not bad else 5


def _write_index(args, results, manifest, planned_runs=None, stopped_early=False,
                 stop_reason=None, first_failure=None) -> None:
    idx = {
        "schema_version": 1,
        "app_package": args.app_package,
        "device_serial": args.serial,
        "flows_requested": args.flows.split(","),
        "runs_per_flow": args.runs,
        # --- additive (S1.1): fail-fast batch metadata; old consumers ignore it ---
        "planned_runs": planned_runs if planned_runs is not None else len(results),
        "executed_runs": len(results),
        "stopped_early": bool(stopped_early),
        "stop_reason": stop_reason,
        "first_failure": first_failure,
        "generated_at": utc_now(),
        "flows_manifest": manifest,
        "totals": {
            "runs": len(results),
            "pass": sum(1 for r in results if r["result"] == "PASS"),
            "fail": sum(1 for r in results if r["result"] == "FAIL"),
            "blocked": sum(1 for r in results if r["result"] == "BLOCKED"),
            "visual_llm_calls": sum(r["visual_llm_calls"] for r in results),
            "model_requests_during_device_steps": sum(r["model_requests_during_device_steps"] for r in results),
            "direct_adb_ui_inputs": sum(r["direct_adb_ui_inputs"] for r in results),
        },
        "results": results,
    }
    with open(os.path.join(args.out, "index.json"), "w", encoding="utf-8") as fh:
        json.dump(idx, fh, indent=2)


if __name__ == "__main__":
    sys.exit(main())
