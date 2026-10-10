#!/usr/bin/env python3
"""Emit a standardized verification-result.json from a run directory.

All wall times come from the harness's monotonic host timestamps or the in-process
`elapsed_realtime_ns` event log — never from log text or estimates. Where a value cannot be
proven it is written as null, never guessed.

Crash attribution is scoped to the target app package so a FATAL in harness-side
instrumentation is never misattributed to the app. The detection functions are pure.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema  # noqa: E402

_EXECUTOR_OK = re.compile(r"OK \(\d+ tests?\)")
STARTS = {"ACTION": "ACTION_START", "ASSERT": "ASSERT_START", "EVIDENCE": "EVIDENCE_START"}
ENDS = {"ACTION": "ACTION_END", "ASSERT": "ASSERT_END", "EVIDENCE": "EVIDENCE_END"}

# Fail-closed evidence gate (v1.0.1). A run that requires a terminal oracle can never be
# PASS without its verify-part.json. Markers are stable machine signals.
MISSING_EVIDENCE = "REQUIRED_VERIFICATION_EVIDENCE_MISSING"
INVALID_EVIDENCE = "VERIFICATION_EVIDENCE_SCHEMA_INVALID"
ORACLE_FAIL = "VERIFICATION_ORACLE_FAIL"


def require_verify_part(plan: dict, engine: str) -> bool:
    """Fail-closed default: a uiautomator journey, or any plan declaring an oracle, must
    produce verify-part.json. A plan may explicitly opt out with `require_verify_part:false`
    (e.g. a UI-only journey with no DB/domain ground truth)."""
    explicit = plan.get("require_verify_part")
    if explicit is not None:
        return bool(explicit)
    return engine == "uiautomator" or bool(plan.get("oracle"))


def required_evidence_failures(plan: dict, engine: str, verify_part, db_outcome,
                               verify_part_error: str | None = None) -> list[tuple[str, str]]:
    """Return [(marker, message)] for every required-evidence problem; [] == satisfied.

    Absence of required evidence is never PASS: a missing or incomplete oracle is a
    failure, not a default success.
    """
    if not require_verify_part(plan, engine):
        # Optional evidence: still never let an explicit oracle FAIL slip through.
        if isinstance(verify_part, dict) and verify_part.get("outcome") not in (None, "PASS"):
            return [(ORACLE_FAIL, f"verify-part outcome={verify_part.get('outcome')}")]
        return []
    if verify_part_error:
        return [(INVALID_EVIDENCE, verify_part_error)]
    if verify_part is None:
        return [(MISSING_EVIDENCE,
                 "verify-part.json was not produced (the journey's terminal oracle did not run)")]
    if not isinstance(verify_part, dict):
        return [(INVALID_EVIDENCE, "verify-part.json is not an object")]
    db = verify_part.get("database")
    if not isinstance(db, dict):
        return [(INVALID_EVIDENCE, "verify-part.json has no database object")]
    if db.get("checked") is not True:
        return [(MISSING_EVIDENCE, "verify-part.json database.checked is not true")]
    if verify_part.get("outcome") != "PASS":
        return [(ORACLE_FAIL, f"oracle outcome={verify_part.get('outcome')}")]
    if db_outcome != "PASS":
        return [(ORACLE_FAIL, f"database.outcome={db_outcome}")]
    return []


def write_evidence_failure(run: Path, plan: dict, engine: str, marker: str, message: str) -> None:
    """A mechanically-produced bundle for a host-gate failure so a missing oracle still
    yields a complete, inspectable failure bundle (no human inspection required)."""
    f = run / "failure"
    f.mkdir(parents=True, exist_ok=True)
    (f / "failed-assertion.json").write_text(json.dumps({
        "test": "host:required-evidence-gate",
        "run_id": plan["verification_id"],
        "journey": plan["journey"]["id"],
        "exception": "RequiredVerificationEvidence",
        "marker": marker,
        "stage": "evidence",
        "message": message,
        "timestamp_ms": int(time.time() * 1000),
    }, indent=2))
    (f / "gate.json").write_text(json.dumps({
        "verification_id": plan["verification_id"],
        "project": plan.get("project"),
        "engine": engine,
        "journey": plan["journey"]["id"],
        "marker": marker,
        "message": message,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }, indent=2))


def detect_app_crash(logcat: str, app_process: str) -> bool:
    """True only for a FATAL/ANR that belongs to the app process itself."""
    q = re.escape(app_process)
    app_fatal = re.search(r"FATAL EXCEPTION[\s\S]{0,400}?Process: " + q + r"(?![\w.])", logcat)
    app_anr = re.search(r"ANR in " + q + r"(?![\w.])", logcat)
    return bool(app_fatal) or bool(app_anr)


def executor_ok(executor: str) -> bool:
    return _EXECUTOR_OK.search(executor) is not None


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
    p.add_argument("--plan", required=True, help="verification-plan.json")
    p.add_argument("--run-dir", required=True)
    p.add_argument("--provenance", required=True, help="provenance.json from provenance.py")
    p.add_argument("--started-at", required=True)
    p.add_argument("--finished-at", required=True)
    p.add_argument("--setup-ms", type=int, default=None)
    p.add_argument("--total-ms", type=int, default=None)
    p.add_argument("--outcome", default=None, help="explicit PASS/FAIL; derived when omitted")
    p.add_argument("--failed-stage", default=None)
    p.add_argument("--marker", default=None)
    p.add_argument("--evidence-policy", default="failure-only")
    p.add_argument("--evidence-bundle", default=None)
    p.add_argument("--evidence-complete", default=None, choices=["true", "false"])
    p.add_argument("--verification-layer-version", default="unknown")
    p.add_argument("--dry-run", action="store_true",
                   help="no device artifacts; requires --outcome")
    args = p.parse_args()

    plan = json.loads(Path(args.plan).read_text())
    run = Path(args.run_dir)
    prov = json.loads(Path(args.provenance).read_text())

    android = plan["android"]
    engine = plan["engine"]
    app_process = android["package_name"]
    runner = android.get("runner", "androidx.test.runner.AndroidJUnitRunner")

    bench = run / "bench"
    run_id = plan["journey"]["id"]

    executor = ""
    if not args.dry_run and (run / "executor.txt").exists():
        executor = (run / "executor.txt").read_text(errors="replace")
    logcat = ""
    if not args.dry_run and (run / "logcat.txt").exists():
        logcat = (run / "logcat.txt").read_text(errors="replace")

    ok = executor_ok(executor)
    crashed = detect_app_crash(logcat, app_process)
    proc_evidence = "CRASH" if crashed else "no-crash"

    verify_part = None
    verify_part_error = None
    vp = bench / "verify-part.json"
    if vp.exists():
        try:
            verify_part = json.loads(vp.read_text())
        except Exception as e:  # noqa: BLE001
            verify_part_error = f"verify-part.json is not valid JSON: {e}"
    db_checks = ((verify_part or {}).get("database") or {}).get("checks", []) \
        if isinstance(verify_part, dict) else []
    db_outcome = verify_part.get("outcome") if isinstance(verify_part, dict) else None

    spans = []
    if not args.dry_run:
        events = bench / f"events-{plan['verification_id']}.jsonl"
        if not events.exists():
            cands = sorted(bench.glob("events-*.jsonl"),
                           key=lambda p: p.stat().st_mtime, reverse=True)
            events = cands[0] if cands else None
        if events is not None:
            spans = parse_spans(events)

    def span_ms(kind: str, name: str | None = None):
        sel = [s for s in spans if s["kind"] == kind and (name is None or s["name"] == name)]
        return round(sum(s["ms"] for s in sel), 3) if sel else None

    launch_ms = span_ms("ACTION", "launch")
    action_ms = [s for s in spans if s["kind"] == "ACTION" and s["name"] != "launch"]
    t7b = round(sum(s["ms"] for s in action_ms), 3) if action_ms else None
    t7c_spans = [s for s in spans if s["kind"] in ("EVIDENCE", "ASSERT")]
    t7c = round(sum(s["ms"] for s in t7c_spans), 3) if t7c_spans else None

    gate_failures: list[tuple[str, str]] = []
    if args.outcome:
        outcome = args.outcome
    else:
        derived = ok and not crashed
        if derived:
            gate_failures = required_evidence_failures(
                plan, engine, verify_part, db_outcome, verify_part_error)
            if gate_failures:
                derived = False
        outcome = "PASS" if derived else "FAIL"

    ui_evidence = "uiautomator" if engine == "uiautomator" else "maestro"
    measurement_class = plan.get("measurement_class") or "measured"

    result = {
        "verification_id": plan["verification_id"],
        "project": plan["project"],
        "engine": engine,
        "journey": run_id,
        "outcome": outcome,
        "started_at": args.started_at,
        "finished_at": args.finished_at,
        "app_apk_sha256": prov["apk_sha256"],
        "test_apk_sha256": prov.get("test_apk_sha256"),
        "verification_layer_version": args.verification_layer_version,
        "runner_version": runner,
        "device": {
            "serial": prov.get("device_serial") or plan.get("device", {}).get("serial") or "",
            "model": prov.get("device_model"),
            "api": prov.get("device_api"),
        },
        "measurements": {
            "class": measurement_class,
            "excluded_from_baseline": bool(plan.get("excluded_from_baseline", False)),
            "setup_wall_ms": args.setup_ms,
            "total_wall_ms": args.total_ms,
            "t7a_ms": launch_ms,
            "t7b_ms": t7b,
            "t7c_ms": t7c,
        },
        "checks": {
            "ui": {"evidence": ui_evidence, "reachable": ok},
            "database": {
                "checked": verify_part is not None,
                "outcome": db_outcome,
                "checks": db_checks,
            },
            "process": {"crashed": crashed, "executor_ok": ok, "evidence": proc_evidence},
            "visual": {
                "mode": args.evidence_policy,
                "screenshots": len(list((run / "failure").glob("*.png"))) if (run / "failure").is_dir() else 0,
            },
        },
        "evidence": {
            "policy": args.evidence_policy,
            "bundle": args.evidence_bundle,
            "complete": (args.evidence_complete == "true") if args.evidence_complete else None,
        },
    }
    fail_stage = args.failed_stage
    fail_marker = args.marker
    gate_message = None
    if outcome == "FAIL" and not fail_marker and gate_failures:
        fail_stage = "evidence"
        fail_marker = gate_failures[0][0]
        gate_message = "; ".join(f"{m}: {msg}" for m, msg in gate_failures)
        print(f"EVIDENCE_GATE=FAIL {fail_marker} {gate_message}", file=sys.stderr)
    if fail_stage or fail_marker:
        result["failure"] = {"stage": fail_stage, "marker": fail_marker}

    errs = schema.validate_result(result)
    if errs:
        print("SCHEMA_FAIL", file=sys.stderr)
        for e in errs:
            print(f"  - {e}", file=sys.stderr)
        return 2

    (run / "verification-result.json").write_text(json.dumps(result, indent=2))
    if gate_message:
        write_evidence_failure(run, plan, engine, fail_marker, gate_message)
    print(f"{plan['verification_id']}: outcome={outcome} "
          f"t7a={launch_ms} t7b={t7b} t7c={t7c} total={args.total_ms}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
