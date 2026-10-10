#!/usr/bin/env python3
"""Offline harness test for the reference-replay runner (stdlib only).

Uses a fake `maestro` stub so the runner's wiring, result schema, and
fail-closed evidence path can be validated WITHOUT a physical device. This does
NOT prove anything about a real device or real selectors; it only proves the
harness emits conformant results and fails closed.
"""
import json
import os
import stat
import subprocess
import sys
import tempfile

RR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPLAY = os.path.join(RR, "runner", "replay.py")

MAESTRO_STUB = r"""#!/usr/bin/env bash
xml=""; todir=""
while [ $# -gt 0 ]; do
  case "$1" in
    --output) xml="$2"; shift 2;;
    --test-output-dir) todir="$2"; shift 2;;
    *) shift;;
  esac
done
mkdir -p "$todir/takeScreenshot"
printf 'PNG' > "$todir/takeScreenshot/R1-home.png"
if [ "${FAKE_MAESTRO_FAIL:-0}" = "1" ]; then
  printf '[{"command":"assertVisible","status":"FAILED"},{"command":"assertVisible","status":"COMPLETED"}]' > "$todir/commands.json"
  printf '<?xml version="1.0"?><testsuites><testsuite name="R1" tests="1" failures="1" errors="0"></testsuite></testsuites>' > "$xml"
  echo "Assertion failed: Search not visible" >&2
  exit 1
fi
printf '[{"command":"assertVisible","status":"COMPLETED"},{"command":"assertVisible","status":"COMPLETED"}]' > "$todir/commands.json"
printf '<?xml version="1.0"?><testsuites><testsuite name="R1" tests="1" failures="0" errors="0"></testsuite></testsuites>' > "$xml"
echo "SUCCESS"
exit 0
"""

REQUIRED = ["flow_id", "device_serial", "app_package", "start_time", "end_time", "wall_ms",
            "exit_code", "assertions_total", "assertions_passed", "screenshot_path",
            "screenshot_sha256", "visual_llm_calls", "model_requests_during_device_steps",
            "direct_adb_ui_inputs", "result"]


def make_exec(path: str, body: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(body)
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def check_schema(r: dict) -> list[str]:
    errs = [f"missing {k}" for k in REQUIRED if k not in r]
    if r.get("result") not in ("PASS", "FAIL", "BLOCKED"):
        errs.append("bad result enum")
    if r.get("result") == "PASS":
        if r.get("assertions_total", 0) <= 0 or r.get("assertions_passed") != r.get("assertions_total"):
            errs.append("PASS with no/unmet assertions")
        if not (isinstance(r.get("screenshot_sha256"), str) and len(r["screenshot_sha256"]) == 64):
            errs.append("PASS without screenshot sha256")
    for k in ("visual_llm_calls", "model_requests_during_device_steps", "direct_adb_ui_inputs"):
        if r.get(k) != 0:
            errs.append(f"{k} != 0")
    return errs


def run(env_extra: dict, out: str, locks: str, maestro: str, adb: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["REPLAY_ALLOW_NO_DEVICE"] = "1"
    env.update(env_extra)
    return subprocess.run(
        [sys.executable, REPLAY, "--flows", "R1", "--runs", "1", "--out", out,
         "--maestro", maestro, "--adb", adb, "--lock-dir", locks, "--skip-device-check"],
        capture_output=True, text=True, env=env, cwd=RR,
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as d:
        maestro = os.path.join(d, "maestro")
        adb = os.path.join(d, "adb")
        make_exec(maestro, MAESTRO_STUB)
        make_exec(adb, "#!/usr/bin/env bash\necho device\n")
        locks = os.path.join(d, "locks")

        # --- PASS path ----------------------------------------------------
        out = os.path.join(d, "out_pass")
        p = run({}, out, locks, maestro, adb)
        if p.returncode != 0:
            print("FAIL: pass run exit", p.returncode, p.stdout, p.stderr)
            return 1
        idx = json.load(open(os.path.join(out, "index.json")))
        r = idx["results"][0]
        errs = check_schema(r)
        if errs:
            print("FAIL schema (pass):", errs)
            return 1
        if r["result"] != "PASS":
            print("FAIL: expected PASS, got", r["result"])
            return 1
        if r["assertions_total"] != 2 or r["assertions_passed"] != 2:
            print("FAIL: assertion counts", r["assertions_total"], r["assertions_passed"])
            return 1
        print("ok: PASS path -> result=PASS, assertions=2/2, screenshot sha256 present")

        # --- controlled FAIL path ----------------------------------------
        out = os.path.join(d, "out_fail")
        p = run({"FAKE_MAESTRO_FAIL": "1"}, out, locks, maestro, adb)
        if p.returncode == 0:
            print("FAIL: controlled-fail run exited 0 (should fail closed)")
            return 1
        idx = json.load(open(os.path.join(out, "index.json")))
        r = idx["results"][0]
        errs = check_schema(r)
        if errs:
            print("FAIL schema (fail):", errs)
            return 1
        if r["result"] != "FAIL":
            print("FAIL: expected FAIL, got", r["result"])
            return 1
        ev = (r.get("failure") or {}).get("evidence_dir")
        if not ev or not os.path.isdir(ev):
            print("FAIL: no evidence dir on controlled fail")
            return 1
        if not os.path.isfile(os.path.join(ev, "metadata.json")):
            print("FAIL: evidence metadata.json missing")
            return 1
        print("ok: controlled FAIL -> result=FAIL, fail-closed, evidence bundle written")

    print("REPLAY_OFFLINE_TEST=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
