#!/usr/bin/env python3
"""Normalize one benchmark run into benchmark-run.json + verification-result.json.

All wall times come from the harness's monotonic host timestamps or the in-process
SystemClock.elapsedRealtimeNanos event log -- never from log text or estimates. Where a
value cannot be proven it is written as null, never guessed.

Crash attribution is scoped to the app process (`com.keeplab.app`) so a FATAL in the
harness-side instrumentation (e.g. com.android.cli.interact.instrumentation) is never
misattributed to KeepLab. The detection functions are pure and unit-tested.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HARNESS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(HARNESS_DIR))
import schema  # noqa: E402

APP_PROCESS = r"com\.keeplab\.app"
_EXECUTOR_OK = re.compile(r"OK \(\d+ tests?\)")


def detect_app_crash(logcat: str) -> bool:
    """True only for a FATAL/ANR that belongs to the app process itself."""
    app_fatal = re.search(
        r"FATAL EXCEPTION[\s\S]{0,400}?Process: " + APP_PROCESS + r"(?![\w.])", logcat)
    app_anr = re.search(r"ANR in " + APP_PROCESS + r"(?![\w.])", logcat)
    return bool(app_fatal) or bool(app_anr)


def detect_raw_crash(logcat: str) -> bool:
    """Unqualified crash signal (any process) — kept for traceability only."""
    return bool(re.search(r"FATAL EXCEPTION", logcat)) or bool(re.search(r"ANR in ", logcat))


def detect_process_evidence(logcat: str) -> tuple[str, str]:
    """Return (process_evidence, process_evidence_raw)."""
    return ("CRASH" if detect_app_crash(logcat) else "no-crash",
            "CRASH" if detect_raw_crash(logcat) else "no-crash")


def executor_ok(executor: str) -> bool:
    return _EXECUTOR_OK.search(executor) is not None


STARTS = {"ACTION": "ACTION_START", "ASSERT": "ASSERT_START", "EVIDENCE": "EVIDENCE_START"}
ENDS = {"ACTION": "ACTION_END", "ASSERT": "ASSERT_END", "EVIDENCE": "EVIDENCE_END"}


def parse_spans(path: Path) -> list[dict]:
    spans: list[dict] = []
    open_: dict[tuple, int] = {}
    if not path.exists():
        return spans
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        e = json.loads(line)
        kind, name = e["kind"], e["name"]
        for k, start_kind in STARTS.items():
            if kind == start_kind:
                open_[(k, name)] = e["elapsed_realtime_ns"]
        for k, end_kind in ENDS.items():
            if kind == end_kind:
                key = (k, name)
                if key in open_:
                    ms = (e["elapsed_realtime_ns"] - open_.pop(key)) / 1_000_000.0
                    spans.append({"kind": k, "name": name, "ms": round(ms, 3)})
    return spans


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--run-id", required=True)
    p.add_argument("--engine", required=True)
    p.add_argument("--journey", required=True)
    p.add_argument("--iteration", type=int, default=1)
    p.add_argument("--bench-dir", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--setup-ms", type=int, required=True)
    p.add_argument("--total-ms", type=int, required=True)
    p.add_argument("--apk-sha256", required=True)
    p.add_argument("--test-apk-sha256", default=None)
    p.add_argument("--harness-version", default="unknown")
    p.add_argument("--runner-version", default="unknown")
    p.add_argument("--git-commit", default="NO_GIT")
    p.add_argument("--device-serial", default="87296ada")
    p.add_argument("--device-model", default="Redmi Note 7 Pro")
    p.add_argument("--api", default="36")
    p.add_argument("--model-requests", type=int, default=0)
    p.add_argument("--input-tokens", type=int, default=0)
    p.add_argument("--output-tokens", type=int, default=0)
    p.add_argument("--retries", type=int, default=0)
    p.add_argument("--human-interventions", type=int, default=0)
    p.add_argument("--outcome", default=None,
                   help="explicit outcome for engines whose result is not in executor.txt (Engine C)")
    p.add_argument("--launch-test", default=None,
                   help="FQ test class used to launch/verify (defaults per engine)")
    p.add_argument("--measurement-class", default=None,
                   help="explicit measurement_class for diagnostic/self-test runs")
    p.add_argument("--excluded-from-baseline", action="store_true",
                   help="mark a diagnostic run as excluded from the baseline")
    args = p.parse_args()

    bench = Path(args.bench_dir)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    events = bench / f"events-{args.run_id}.jsonl"
    spans = parse_spans(events)

    launch_test = args.launch_test or (
        "com.keeplab.app.benchmark.DbProbe" if args.engine.upper() == "C"
        else f"com.keeplab.app.benchmark.{args.journey}JourneyTest"
    )

    def span_ms(kind: str, name: str | None = None) -> float | None:
        sel = [s for s in spans if s["kind"] == kind and (name is None or s["name"] == name)]
        return round(sum(s["ms"] for s in sel), 3) if sel else None

    t7a = span_ms("ACTION", "launch")
    action_spans = [s for s in spans if s["kind"] == "ACTION" and s["name"] != "launch"]
    t7b = round(sum(s["ms"] for s in action_spans), 3) if action_spans else None
    t7c_spans = [s for s in spans if s["kind"] in ("EVIDENCE", "ASSERT")]
    t7c = round(sum(s["ms"] for s in t7c_spans), 3) if t7c_spans else None

    executor = (out / "executor.txt").read_text(errors="replace") if (out / "executor.txt").exists() else ""
    ok = executor_ok(executor)
    logcat = (out / "logcat.txt").read_text(errors="replace") if (out / "logcat.txt").exists() else ""
    proc_evidence, proc_raw = detect_process_evidence(logcat)
    crashed = proc_evidence == "CRASH"
    outcome = args.outcome or ("PASS" if (ok and not crashed) else "FAIL")

    verify_path = bench / "verify-part.json"
    verify = json.loads(verify_path.read_text()) if verify_path.exists() else None
    checks = verify["database"]["checks"] if verify else []

    failure_dir = bench / "failure"
    failure_files = sorted(f.name for f in failure_dir.glob("*")) if failure_dir.exists() else []

    ui_evidence = "maestro" if args.engine.upper() == "C" else "uiautomator"

    run = {
        "engine": args.engine,
        "journey": args.journey,
        "iteration": args.iteration,
        "run_id": args.run_id,
        "outcome": outcome,
        "apk_sha256": args.apk_sha256,
        "test_apk_sha256": args.test_apk_sha256,
        "harness_version": args.harness_version,
        "runner_version": args.runner_version,
        "git_commit": args.git_commit,
        "device_serial": args.device_serial,
        "device_model": args.device_model,
        "api": args.api,
        "setup_wall_ms": args.setup_ms,
        "t7a_ms": t7a,
        "t7b_ms": t7b if spans else None,
        "t7c_ms": t7c,
        "total_wall_ms": args.total_ms,
        "model_requests": args.model_requests,
        "input_tokens": args.input_tokens,
        "output_tokens": args.output_tokens,
        "assertions": len(checks),
        "screenshots": len(list(bench.glob("*.png"))) + len(list(failure_dir.glob("*.png"))),
        "layout_dumps": len(list(failure_dir.glob("layout*.json"))),
        "retries": args.retries,
        "human_interventions": args.human_interventions,
        "ui_evidence": ui_evidence,
        "database_evidence": (verify["outcome"] if verify else None),
        "process_evidence": proc_evidence,
        "process_evidence_raw": proc_raw,
        "visual_evidence": "failure-only",
        "spans": spans,
        "launch_test": launch_test,
    }
    if args.measurement_class:
        run["measurement_class"] = args.measurement_class
    if args.excluded_from_baseline:
        run["excluded_from_baseline"] = True

    errs = schema.validate_benchmark_run(run)
    if errs:
        print("SCHEMA_FAIL", file=sys.stderr)
        for e in errs:
            print(f"  - {e}", file=sys.stderr)
        return 2

    (out / "benchmark-run.json").write_text(json.dumps(run, indent=2))

    result = {
        "engine": args.engine,
        "journey": args.journey,
        "run_id": args.run_id,
        "outcome": outcome,
        "ui": {"evidence": ui_evidence, "reachable": ok},
        "database": verify["database"] if verify else {"checked": False},
        "process": {"crashed": crashed, "executor_ok": ok, "evidence": proc_evidence},
        "visual": {"screenshots": run["screenshots"], "mode": "failure-only"},
    }
    (out / "verification-result.json").write_text(json.dumps(result, indent=2))
    print(f"{args.run_id}: outcome={outcome} t7a={t7a} t7b={t7b} t7c={t7c} total={args.total_ms}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
