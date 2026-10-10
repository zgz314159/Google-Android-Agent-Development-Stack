#!/usr/bin/env python3
"""Offline hardening tests for the reference-replay runner (stdlib only).

S1.1 coverage:
  E. nested Maestro output layout -> screenshot_path + real screenshot_sha256
     (and: a flat layout still works; a run with no screenshots stays null and
     never fabricates a path)
  F. default FAIL-FAST: a planned 9-run batch stops after the first non-PASS run,
     still flushes result.json + failure evidence + index.json, and exits non-zero
  G. --continue-on-fail diagnostic mode: the whole planned batch runs

Uses the same fake-`maestro` technique as test_replay_offline.py. This does NOT
prove anything about a physical device or real selectors; it proves the runner's
discovery + batch semantics.
"""
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile

RR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPLAY = os.path.join(RR, "runner", "replay.py")
sys.path.insert(0, os.path.join(RR, "runner"))
import replay as replay_mod  # noqa: E402  (pure helpers; no side effects on import)

# The stub reproduces the REAL Maestro output layout:
#   <test-output-dir>/<timestamp>/<FLOWNAME>/takeScreenshot/<name>.png
# FLOWNAME is read from the flow YAML's `name:` header, exactly like Maestro does.
MAESTRO_STUB = r"""#!/usr/bin/env bash
xml=""; todir=""; yaml=""
while [ $# -gt 0 ]; do
  case "$1" in
    test) shift; yaml="$1"; shift;;
    --output) xml="$2"; shift 2;;
    --test-output-dir) todir="$2"; shift 2;;
    *) shift;;
  esac
done
flow="$(sed -n 's/^name:[[:space:]]*//p' "$yaml" | head -n 1)"
[ -n "$flow" ] || flow="FLOW"
ts="2026-10-05_010101"
if [ "${FAKE_MAESTRO_FLAT:-0}" = "1" ]; then
  shotdir="$todir/takeScreenshot"
else
  shotdir="$todir/$ts/$flow/takeScreenshot"
fi
mkdir -p "$shotdir"
printf 'PNG-A-%s' "$flow" > "$shotdir/${flow}-home.png"
printf 'PNG-B-%s' "$flow" > "$shotdir/${flow}-search.png"
if [ "${FAKE_MAESTRO_NO_SCREENSHOT:-0}" = "1" ]; then rm -rf "$shotdir"; fi

n=0
if [ -n "${FAKE_MAESTRO_COUNTER:-}" ]; then
  [ -f "$FAKE_MAESTRO_COUNTER" ] && n="$(cat "$FAKE_MAESTRO_COUNTER")"
  n=$((n + 1)); printf '%s' "$n" > "$FAKE_MAESTRO_COUNTER"
fi

fail=0
[ "${FAKE_MAESTRO_FAIL:-0}" = "1" ] && fail=1
if [ "${FAKE_MAESTRO_FAIL_FIRST:-0}" = "1" ] && [ "$n" = "1" ]; then fail=1; fi

if [ "$fail" = "1" ]; then
  printf '<?xml version="1.0"?><testsuites><testsuite name="%s" tests="1" failures="1" errors="0"></testsuite></testsuites>' "$flow" > "$xml"
  echo "Assertion failed: synthetic nested-layout failure" >&2
  exit 1
fi
printf '<?xml version="1.0"?><testsuites><testsuite name="%s" tests="1" failures="0" errors="0"></testsuite></testsuites>' "$flow" > "$xml"
echo "SUCCESS"
exit 0
"""

FAILS = []


def bad(msg: str) -> None:
    FAILS.append(msg)
    print("FAIL:", msg)


def make_exec(path: str, body: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(body)
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def run(env_extra: dict, out: str, locks: str, maestro: str, adb: str,
        flows: str = "R1", runs: int = 1, extra_args=None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["REPLAY_ALLOW_NO_DEVICE"] = "1"
    env.update(env_extra)
    cmd = [sys.executable, REPLAY, "--flows", flows, "--runs", str(runs), "--out", out,
           "--maestro", maestro, "--adb", adb, "--lock-dir", locks, "--skip-device-check"]
    cmd += list(extra_args or [])
    return subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=RR)


def load(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    with tempfile.TemporaryDirectory() as d:
        maestro = os.path.join(d, "maestro")
        adb = os.path.join(d, "adb")
        make_exec(maestro, MAESTRO_STUB)
        make_exec(adb, "#!/usr/bin/env bash\necho device\n")
        locks = os.path.join(d, "locks")

        # ---------------- E. nested screenshot discovery ---------------------
        out = os.path.join(d, "out_nested")
        p = run({}, out, locks, maestro, adb)
        if p.returncode != 0:
            bad(f"nested PASS run exited {p.returncode}: {p.stdout} {p.stderr}")
        r = load(os.path.join(out, "runs", "R1-1", "result.json"))
        sp = r.get("screenshot_path")
        if not sp:
            bad(f"nested layout: screenshot_path is {sp!r} (expected a real PNG path)")
        elif not os.path.isfile(sp):
            bad(f"nested layout: screenshot_path does not exist: {sp}")
        elif "2026-10-05_010101" not in sp or f"{os.sep}takeScreenshot{os.sep}" not in sp:
            bad(f"nested layout: unexpected path shape: {sp}")
        elif not sp.endswith(f"{os.sep}R1-HOME-SEARCH-search.png"):
            bad(f"nested layout: selection semantics changed (expected lexicographically-last): {sp}")
        else:
            want = sha256_of(sp)
            got = r.get("screenshot_sha256")
            if got != want:
                bad(f"nested layout: screenshot_sha256 {got!r} != real sha256 {want!r}")
            elif len(got) != 64:
                bad(f"nested layout: screenshot_sha256 not 64 hex chars: {got!r}")
            else:
                print(f"ok: nested layout -> screenshot_path set, sha256 verifies ({want[:12]}…)")

        # ---------------- E2. flat layout still supported --------------------
        out = os.path.join(d, "out_flat")
        p = run({"FAKE_MAESTRO_FLAT": "1"}, out, locks, maestro, adb)
        r = load(os.path.join(out, "runs", "R1-1", "result.json"))
        sp = r.get("screenshot_path")
        if p.returncode != 0 or not sp or not os.path.isfile(sp) or r.get("screenshot_sha256") is None:
            bad(f"flat layout regression: rc={p.returncode} path={sp!r}")
        else:
            print("ok: flat layout still discovered (backward compatible)")

        # ---------------- E3. no screenshot -> null, never fabricated --------
        out = os.path.join(d, "out_shotless")
        p = run({"FAKE_MAESTRO_NO_SCREENSHOT": "1", "FAKE_MAESTRO_FAIL": "1"}, out, locks, maestro, adb)
        r = load(os.path.join(out, "runs", "R1-1", "result.json"))
        if r.get("screenshot_path") is not None or r.get("screenshot_sha256") is not None:
            bad(f"missing screenshot fabricated a path: {r.get('screenshot_path')!r}")
        elif replay_mod.find_screenshots(os.path.join(d, "does-not-exist")):
            bad("find_screenshots returned results for a non-existent directory")
        else:
            print("ok: missing screenshot -> screenshot_path/sha256 null, no fabrication")

        # ---------------- F. default FAIL-FAST -------------------------------
        n0 = len(FAILS)
        out = os.path.join(d, "out_failfast")
        counter = os.path.join(d, "counter_ff")
        p = run({"FAKE_MAESTRO_FAIL_FIRST": "1", "FAKE_MAESTRO_COUNTER": counter},
                out, locks, maestro, adb, flows="R1,R2,R3", runs=3)
        if p.returncode == 0:
            bad("fail-fast: batch exited 0 despite a FAIL")
        idx = load(os.path.join(out, "index.json"))
        if idx.get("planned_runs") != 9:
            bad(f"fail-fast: planned_runs={idx.get('planned_runs')!r} (expected 9)")
        if idx.get("executed_runs") != 1:
            bad(f"fail-fast: executed_runs={idx.get('executed_runs')!r} (expected 1)")
        if idx.get("stopped_early") is not True:
            bad(f"fail-fast: stopped_early={idx.get('stopped_early')!r} (expected True)")
        if not idx.get("stop_reason"):
            bad("fail-fast: stop_reason is empty")
        ff = idx.get("first_failure") or {}
        if ff.get("flow_id") != "R1" or ff.get("run_index") != 1 or ff.get("result") != "FAIL":
            bad(f"fail-fast: first_failure={ff!r}")
        if len(idx.get("results") or []) != 1 or idx.get("totals", {}).get("runs") != 1:
            bad("fail-fast: index results/totals.runs do not reflect the single executed run")
        if idx.get("totals", {}).get("fail") != 1:
            bad("fail-fast: totals.fail != 1")
        if os.path.exists(os.path.join(out, "runs", "R1-2")):
            bad("fail-fast: R1-2 was executed after the first failure")
        ev = os.path.join(out, "runs", "R1-1", "evidence", "metadata.json")
        if not os.path.isfile(ev):
            bad(f"fail-fast: failure evidence not flushed ({ev})")
        per_run = load(os.path.join(out, "runs", "R1-1", "result.json"))
        for leak in ("planned_runs", "executed_runs", "stopped_early", "stop_reason", "first_failure"):
            if leak in per_run:
                bad(f"fail-fast: batch field {leak!r} leaked into the per-run result.json")
        if len(FAILS) == n0:
            print("ok: fail-fast -> planned=9 executed=1 stopped_early=True, evidence flushed, exit!=0")

        # ---------------- G. --continue-on-fail ------------------------------
        n0 = len(FAILS)
        out = os.path.join(d, "out_continue")
        counter = os.path.join(d, "counter_cof")
        p = run({"FAKE_MAESTRO_FAIL_FIRST": "1", "FAKE_MAESTRO_COUNTER": counter},
                out, locks, maestro, adb, flows="R1,R2,R3", runs=3,
                extra_args=["--continue-on-fail"])
        if p.returncode == 0:
            bad("continue-on-fail: batch exited 0 despite a FAIL")
        idx = load(os.path.join(out, "index.json"))
        if idx.get("executed_runs") != 9 or len(idx.get("results") or []) != 9:
            bad(f"continue-on-fail: executed={idx.get('executed_runs')!r}/results={len(idx.get('results') or [])} (expected 9)")
        if idx.get("planned_runs") != 9:
            bad(f"continue-on-fail: planned_runs={idx.get('planned_runs')!r}")
        if idx.get("stopped_early") is not False:
            bad(f"continue-on-fail: stopped_early={idx.get('stopped_early')!r} (expected False)")
        if idx.get("totals", {}).get("fail") != 1 or idx.get("totals", {}).get("pass") != 8:
            bad(f"continue-on-fail: totals={idx.get('totals')!r}")
        if not os.path.exists(os.path.join(out, "runs", "R3-3")):
            bad("continue-on-fail: the final planned run R3-3 was not executed")
        if len(FAILS) == n0:
            print("ok: continue-on-fail -> all 9 planned runs executed (diagnostic mode)")

    if FAILS:
        print(f"REPLAY_HARDENING_TEST=FAIL ({len(FAILS)} problem(s))")
        return 1
    print("REPLAY_HARDENING_TEST=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
