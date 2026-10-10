#!/usr/bin/env python3
"""Verification Layer runner: a bounded, fail-fast stage machine.

  run_verification.sh <verification-plan.json> [--run-root DIR] [--dry-run]
                      [--skip-input-smoke] [--skip-cleanup] [--out DIR]

Implements the production flow:

  load plan -> validate -> preflight -> APK provenance -> snapshot device state
  -> cleanup -> install -> deterministic IME -> input smoke -> fixture seed
  -> journey -> oracle -> collect -> emit result
     PASS -> compact result
     FAIL -> failure bundle + completeness
  -> cleanup + restore device state -> evaluation handoff

Every stage is timeout-bounded and writes run-state.json; the first unexpected FAIL stops
the run and still emits a standardized failed result (fail-fast). Host owns install/
lifecycle/IME/logcat/am-instrument/cleanup; instrumentation owns UI/assertions/oracle.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

RUNNER_DIR = Path(__file__).resolve().parent
VERIFY_ROOT = RUNNER_DIR.parent
CORE = VERIFY_ROOT / "core"
ANDROID = VERIFY_ROOT / "android"
sys.path.insert(0, str(CORE))
import plan_validate  # noqa: E402


def _stack_paths():
    _lib = VERIFY_ROOT.parent / "scripts" / "lib"
    if str(_lib) not in sys.path:
        sys.path.insert(0, str(_lib))
    import stack_paths  # noqa: PLC0415

    return stack_paths

DEFAULT_TIMEOUTS = {
    "preflight": 30, "install": 300, "instrumentation": 600,
    "oracle": 120, "evidence": 120, "cleanup": 60, "shell": 30,
}
LAYER_VERSION = (VERIFY_ROOT / "VERSION").read_text().strip() if (VERIFY_ROOT / "VERSION").exists() else "unknown"
RUNNER_VERSION = "androidx.test.runner.AndroidJUnitRunner"


class StageError(Exception):
    def __init__(self, stage: str, marker: str, message: str):
        super().__init__(message)
        self.stage = stage
        self.marker = marker
        self.message = message


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%SZ')}] {msg}", file=sys.stderr, flush=True)


class RunState:
    def __init__(self, run_dir: Path, plan: dict):
        self.path = run_dir / "run-state.json"
        self.started = utcnow()
        self.data = {
            "verification_id": plan.get("verification_id"),
            "project": plan.get("project"),
            "engine": plan.get("engine"),
            "journey": plan.get("journey", {}).get("id"),
            "run_id": plan.get("verification_id"),
            "stage": "start",
            "started_at": self.started,
            "last_progress_at": self.started,
        }
        self.write()

    def write(self) -> None:
        self.data["last_progress_at"] = utcnow()
        self.path.write_text(json.dumps(self.data, indent=2))

    def stage(self, name: str) -> None:
        self.data["stage"] = name
        self.write()
        log(f"stage={name}")

    def cleanup(self) -> None:
        self.data["cleanup_at"] = utcnow()
        self.write()


def build_env(plan: dict, run_dir: Path, serial: str | None) -> dict:
    android = plan["android"]
    runner_class = android.get("runner", RUNNER_VERSION)
    test_pkg = android.get("test_apk") and android["package_name"] + ".test" or ""
    env = dict(os.environ)
    env.update({
        "VERIFICATION_ID": plan["verification_id"],
        "PROJECT": plan["project"],
        "ENGINE": plan["engine"],
        "JOURNEY": plan["journey"]["id"],
        "RUN_ID": plan["verification_id"],
        "PKG": android["package_name"],
        "TEST_PKG": test_pkg,
        "OUT": str(run_dir),
        "VERIFY_STATE_DIR": str(run_dir / "state"),
        "ANDROID_CLI": env.get("ANDROID_CLI", str(Path.home() / ".local/bin/android")),
        # am instrument requires <TEST_PACKAGE>/<RUNNER_CLASS>
        "RUNNER": f"{test_pkg}/{runner_class}" if test_pkg else runner_class,
    })
    to = {**DEFAULT_TIMEOUTS, **plan.get("timeouts", {})}
    env.update({
        "PREFLIGHT_TO": str(to["preflight"]),
        "INSTALL_TO": str(to["install"]),
        "INSTR_TO": str(to["instrumentation"]),
        "ORACLE_TO": str(to["oracle"]),
        "EVIDENCE_TO": str(to["evidence"]),
        "CLEANUP_TO": str(to["cleanup"]),
        "SHELL_TO": str(to["shell"]),
    })
    dev = plan.get("device", {})
    if serial:
        env["SERIAL"] = serial
    if dev.get("expected_model"):
        env["EXPECTED_DEVICE"] = dev["expected_model"]
    if dev.get("expected_api"):
        env["EXPECTED_API"] = dev["expected_api"]
    smoke = plan.get("input_smoke", {})
    if smoke.get("class"):
        env["INPUT_SMOKE_CLASS"] = smoke["class"]
    if smoke.get("flow"):
        env["INPUT_SMOKE_FLOW"] = smoke["flow"]
    return env


def extract_marker(text: str) -> str | None:
    for line in text.splitlines():
        for key in ("TIMEOUT_STAGE=", "STAGE_FAIL=", "APK_SHA_MISMATCH=", "TEST_APK_SHA_MISMATCH=",
                    "HARNESS_ERROR=", "PREFLIGHT_FAIL", "IME_UNAVAILABLE", "IME_SET_FAILED=",
                    "INPUT_SMOKE_FAIL", "CLEANUP_INCOMPLETE", "UIAUTOMATION_CONFLICT_SUSPECTED",
                    "DEVICE_LOCKED_REQUIRES_OWNER_UNLOCK", "APK_MISSING=", "TEST_APK_MISSING=",
                    "LIFECYCLE_RESTORE=", "REQUIRED_VERIFICATION_EVIDENCE_MISSING",
                    "VERIFICATION_EVIDENCE_SCHEMA_INVALID", "VERIFICATION_ORACLE_FAIL"):
            if key in line:
                return line.strip()
    return None


def run_stage(stage: str, cmd: list[str], env: dict, timeout: int, run_dir: Path) -> str:
    """Run one bounded stage command, returning combined output. Raises StageError on failure."""
    log(f"exec: {' '.join(cmd)}")
    try:
        proc = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or "") + (e.stderr or "")
        raise StageError(stage, f"TIMEOUT_STAGE={stage}", f"stage {stage} timed out after {timeout}s")
    combined = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    (run_dir / f"stage-{stage}.log").write_text(combined)
    if proc.returncode != 0:
        raise StageError(stage, extract_marker(combined) or f"STAGE_FAIL={stage}",
                         f"stage {stage} failed (rc={proc.returncode})")
    return combined


def adb_shell(serial: str, args: list[str]) -> list[str]:
    return ["adb", "-s", serial, "shell", *args]


def resolve_serial(plan: dict, env: dict) -> str:
    explicit = plan.get("device", {}).get("serial") or os.environ.get("SERIAL")
    if explicit:
        return explicit
    out = subprocess.run(["adb", "devices"], capture_output=True, text=True).stdout
    ids = [l.split()[0] for l in out.splitlines()[1:] if l.split()[1:2] == ["device"]]
    if len(ids) != 1:
        raise StageError("resolve_serial", "ADB_DEVICE_COUNT", f"expected exactly 1 device, found {len(ids)}")
    return ids[0]


def read_device_identity(serial: str) -> dict:
    def prop(name: str) -> str | None:
        try:
            r = subprocess.run(["adb", "-s", serial, "shell", "getprop", name],
                               capture_output=True, text=True, timeout=10)
            return r.stdout.strip() or None
        except Exception:  # noqa: BLE001
            return None
    return {"device_serial": serial, "device_model": prop("ro.product.model"),
            "device_api": prop("ro.build.version.sdk")}


def am_instrument(serial: str, runner: str, pairs: list[tuple[str, str]]) -> list[str]:
    cmd = ["adb", "-s", serial, "shell", "am", "instrument", "-w"]
    for k, v in pairs:
        cmd += ["-e", k, v]
    cmd.append(runner)
    return cmd


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main() -> int:
    p = argparse.ArgumentParser(description="Verification Layer runner")
    p.add_argument("plan")
    p.add_argument("--run-root", default=str(Path(_stack_paths().artifacts_root()) / "verification" / "runs"))
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--skip-input-smoke", action="store_true")
    p.add_argument("--skip-cleanup", action="store_true")
    args = p.parse_args()

    plan = plan_validate.load_plan(args.plan)
    errs = plan_validate.validate_plan(plan)
    if errs:
        print("PLAN_VALID=false", file=sys.stderr)
        for e in errs:
            print(f"  - {e}", file=sys.stderr)
        return 2

    run_dir = Path(args.run_root) / plan["verification_id"]
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "plan.json").write_text(json.dumps(plan, indent=2))
    state = RunState(run_dir, plan)

    to = {**DEFAULT_TIMEOUTS, **plan.get("timeouts", {})}
    engine = plan["engine"]
    android = plan["android"]
    policy = plan.get("evidence_policy", "failure-only")
    started_at = utcnow()
    serial: str | None = None
    prov_path = run_dir / "provenance.json"

    try:
        if args.dry_run:
            # Schema/plan-side only: real provenance, synthetic outcome, no device.
            state.stage("provenance")
            env = build_env(plan, run_dir, serial=None)
            state.stage("emit")
            emit = ["python3", str(CORE / "result_emit.py"), "--plan", args.plan,
                    "--run-dir", str(run_dir), "--provenance", str(prov_path),
                    "--started-at", started_at, "--finished-at", utcnow(),
                    "--outcome", "PASS", "--evidence-policy", policy,
                    "--verification-layer-version", LAYER_VERSION, "--dry-run"]
            # provenance first (no device)
            run_stage("provenance", ["python3", str(CORE / "provenance.py"),
                                     "--app", android["apk"],
                                     *(("--test", android["test_apk"]) if android.get("test_apk") else ()),
                                     *(("--expected-app", android["expected_app_sha256"]) if android.get("expected_app_sha256") else ()),
                                     *(("--expected-test", android["expected_test_sha256"]) if android.get("expected_test_sha256") else ()),
                                     *(("--require-test",) if android.get("test_apk") else ()),
                                     "--verification-layer-version", LAYER_VERSION,
                                     "--runner-version", android.get("runner", RUNNER_VERSION),
                                     "--json", str(prov_path)], env, to["shell"], run_dir)
            run_stage("emit", emit, env, to["shell"], run_dir)
            state.cleanup()
            print(f"DRY_RUN=OK result={run_dir / 'verification-result.json'}")
            return 0

        serial = resolve_serial(plan, {})
        env = build_env(plan, run_dir, serial)

        # 1. preflight
        state.stage("preflight")
        run_stage("preflight", ["bash", str(ANDROID / "preflight.sh"), engine], env, to["preflight"], run_dir)

        # 2. APK provenance (STOP on mismatch)
        state.stage("provenance")
        run_stage("provenance", ["python3", str(CORE / "provenance.py"),
                                 "--app", android["apk"],
                                 *(("--test", android["test_apk"]) if android.get("test_apk") else ()),
                                 *(("--expected-app", android["expected_app_sha256"]) if android.get("expected_app_sha256") else ()),
                                 *(("--expected-test", android["expected_test_sha256"]) if android.get("expected_test_sha256") else ()),
                                 *(("--require-test",) if android.get("test_apk") else ()),
                                 "--verification-layer-version", LAYER_VERSION,
                                 "--runner-version", android.get("runner", RUNNER_VERSION),
                                 "--json", str(prov_path)], env, to["shell"], run_dir)
        # enrich provenance with device identity
        prov = json.loads(prov_path.read_text())
        prov.update({k: v for k, v in read_device_identity(serial).items() if v})
        prov_path.write_text(json.dumps(prov, indent=2))

        # 3. device state (setup timing starts here; not part of T7)
        setup_t0 = time.time()
        state.stage("snapshot")
        run_stage("snapshot", ["bash", str(ANDROID / "lifecycle.sh"), "snapshot"], env, to["shell"], run_dir)
        state.stage("apply")
        run_stage("apply", ["bash", str(ANDROID / "lifecycle.sh"), "apply"], env, to["shell"], run_dir)

        # 4. cleanup + install
        if not args.skip_cleanup:
            state.stage("cleanup")
            run_stage("cleanup", ["bash", str(ANDROID / "cleanup_engine.sh"), engine], env, to["cleanup"], run_dir)
        state.stage("ime")
        run_stage("ime", ["bash", str(ANDROID / "ime.sh"), engine], env, to["shell"], run_dir)
        state.stage("install")
        run_stage("install", ["bash", str(ANDROID / "install.sh"), android["apk"], android["package_name"]],
                  env, to["install"], run_dir)
        if android.get("test_apk"):
            run_stage("install", ["bash", str(ANDROID / "install.sh"), android["test_apk"],
                                  android["package_name"] + ".test"], env, to["install"], run_dir)

        # 5. reset any stale on-device bench evidence, then force-stop the app
        state.stage("reset")
        subprocess.run(adb_shell(serial, ["rm", "-rf", f"/sdcard/Android/data/{android['package_name']}/files/bench"]),
                       capture_output=True, text=True, timeout=to["shell"])
        subprocess.run(adb_shell(serial, ["am", "force-stop", android["package_name"]]),
                       capture_output=True, text=True, timeout=to["cleanup"])

        # 6. input smoke (optional)
        smoke = plan.get("input_smoke", {})
        if smoke.get("enabled", True) and not args.skip_input_smoke and (
                smoke.get("class") or smoke.get("flow")):
            state.stage("input_smoke")
            run_stage("input_smoke", ["bash", str(ANDROID / "input_smoke.sh"), engine], env, to["instrumentation"], run_dir)

        # 7. fixture seed
        fixture = plan.get("fixture")
        if fixture:
            state.stage("seed")
            run_stage("seed", am_instrument(serial, env["RUNNER"],
                      [("class", f"{fixture['class']}#{fixture['method']}")]), env, to["instrumentation"], run_dir)

        setup_ms = int((time.time() - setup_t0) * 1000)

        # 8. journey (measured) — clear logcat first so the retained log is run-scoped
        subprocess.run(adb_shell(serial, ["logcat", "-c"]), capture_output=True, text=True, timeout=to["shell"])
        state.stage("journey")
        t0 = time.time()
        if engine == "maestro":
            flow = plan["journey"]["flow"]
            out_txt = run_stage("journey", ["bash", str(VERIFY_ROOT / "challengers/maestro/run_maestro.sh"),
                                            flow], env, to["instrumentation"], run_dir)
            (run_dir / "executor.txt").write_text(out_txt)
        else:
            jpairs = [("class", plan["journey"]["test_class"]),
                      ("runId", plan["verification_id"]), ("journey", plan["journey"]["id"])]
            jpairs += [(k, v) for k, v in plan["journey"].get("args", {}).items()]
            out_txt = run_stage("journey", am_instrument(serial, env["RUNNER"], jpairs),
                                env, to["instrumentation"], run_dir)
            (run_dir / "executor.txt").write_text(out_txt)
        total_ms = int((time.time() - t0) * 1000)

        # 9. separate oracle
        oracle = plan.get("oracle")
        if oracle:
            state.stage("oracle")
            run_stage("oracle", am_instrument(serial, env["RUNNER"],
                      [("class", oracle["class"]), ("journey", plan["journey"]["id"])]),
                      env, to["oracle"], run_dir)

        # 10. collect artifacts
        state.stage("collect")
        _collect(run_dir, serial, android["package_name"], env, to)

        # 11. emit the compact result
        state.stage("emit")
        run_stage("emit", ["python3", str(CORE / "result_emit.py"),
                           "--plan", args.plan, "--run-dir", str(run_dir),
                           "--provenance", str(prov_path),
                           "--started-at", started_at, "--finished-at", utcnow(),
                           "--total-ms", str(total_ms), "--setup-ms", str(setup_ms),
                           "--evidence-policy", policy,
                           "--verification-layer-version", LAYER_VERSION],
                  env, to["shell"], run_dir)

        outcome = json.loads((run_dir / "verification-result.json").read_text())["outcome"]

        if outcome == "PASS":
            # keep the PASS path compact: drop the large run-scoped logcat, keep the result
            (run_dir / "logcat.txt").unlink(missing_ok=True)
        else:
            _collect_failure(run_dir, env, to, args.plan, started_at, policy)

        _finalize(run_dir, env, engine, to, args, state)
        result = json.loads((run_dir / "verification-result.json").read_text())
        print(f"VERIFICATION={result['outcome']} id={plan['verification_id']} "
              f"total_ms={total_ms} result={run_dir / 'verification-result.json'}")
        return 0 if result["outcome"] == "PASS" else 1

    except StageError as e:
        state.stage(e.stage)
        log(f"FAIL {e.marker}: {e.message}")
        _fail_result(run_dir, args.plan, prov_path, started_at, policy, e, serial)
        if not args.dry_run:
            try:
                _collect_failure(run_dir, build_env(plan, run_dir, serial), to, args.plan, started_at, policy)
            except Exception:  # noqa: BLE001
                pass
            try:
                _finalize(run_dir, build_env(plan, run_dir, serial), engine, to, args, state)
            except Exception:  # noqa: BLE001
                pass
        print(f"VERIFICATION=FAIL id={plan['verification_id']} stage={e.stage} marker={e.marker}")
        return 1


def _collect(run_dir: Path, serial: str, pkg: str, env: dict, to: dict) -> None:
    # logcat snapshot
    try:
        r = subprocess.run(["adb", "-s", serial, "logcat", "-d"], capture_output=True, text=True,
                           timeout=to["evidence"])
        (run_dir / "logcat.txt").write_text(r.stdout)
    except Exception:  # noqa: BLE001
        (run_dir / "logcat.txt").write_text("")
    # host-side force-stop + pull the bench dir
    subprocess.run(adb_shell(serial, ["am", "force-stop", pkg]), capture_output=True, text=True, timeout=to["cleanup"])
    bench = run_dir / "bench"
    if bench.exists():
        shutil.rmtree(bench)
    bench.mkdir(parents=True, exist_ok=True)
    subprocess.run(["adb", "-s", serial, "pull",
                    f"/sdcard/Android/data/{pkg}/files/bench/.", str(bench)],
                   capture_output=True, text=True, timeout=to["evidence"])


def _collect_failure(run_dir: Path, env: dict, to: dict, plan_path: str, started_at: str, policy: str) -> None:
    try:
        run_stage("failure_bundle", ["bash", str(ANDROID / "collect_failure.sh"), str(run_dir)],
                  env, to["evidence"] + 60, run_dir)
    except StageError as e:
        log(f"evidence bundle incomplete: {e.message}")
    # re-emit with evidence info
    bundle = run_dir / "failure"
    complete = None
    comp = bundle / "completeness.json"
    if comp.exists():
        complete = "true" if json.loads(comp.read_text()).get("complete") else "false"
    res_path = run_dir / "verification-result.json"
    if res_path.exists():
        result = json.loads(res_path.read_text())
        result["evidence"] = {"policy": policy, "bundle": str(bundle) if bundle.exists() else None,
                              "complete": (complete == "true") if complete else None}
        res_path.write_text(json.dumps(result, indent=2))


def _finalize(run_dir: Path, env: dict, engine: str, to: dict, args, state: RunState) -> None:
    try:
        if not args.skip_cleanup:
            b = run_dir / "bench"
            subprocess.run(["bash", str(ANDROID / "cleanup_engine.sh"), engine, "--check-only"],
                           env=env, capture_output=True, text=True, timeout=to["cleanup"])
        run_stage("restore", ["bash", str(ANDROID / "lifecycle.sh"), "restore"], env, to["shell"], run_dir)
    except StageError as e:
        log(f"finalize note: {e.message}")
    except Exception as e:  # noqa: BLE001
        log(f"finalize note: {e}")
    state.cleanup()


def _fail_result(run_dir: Path, plan_path: str, prov_path: Path, started_at: str, policy: str,
                 err: StageError, serial: str | None) -> None:
    if not prov_path.exists():
        # synthesize a minimal provenance so the result schema is satisfied
        plan = json.loads(Path(plan_path).read_text())
        prov_path.write_text(json.dumps({"apk_sha256": "0" * 64}, indent=2))
    try:
        subprocess.run(["python3", str(CORE / "result_emit.py"),
                        "--plan", plan_path, "--run-dir", str(run_dir),
                        "--provenance", str(prov_path),
                        "--started-at", started_at, "--finished-at", utcnow(),
                        "--outcome", "FAIL", "--failed-stage", err.stage, "--marker", err.marker,
                        "--evidence-policy", policy,
                        "--verification-layer-version", LAYER_VERSION],
                       capture_output=True, text=True, timeout=60)
    except Exception:  # noqa: BLE001
        pass


if __name__ == "__main__":
    raise SystemExit(main())
