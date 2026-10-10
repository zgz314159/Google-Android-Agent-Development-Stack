#!/usr/bin/env python3
"""Thin adapter: external benchmark results -> normalized benchmark JSON.

ADD-ON to the Evaluation Core. It does NOT modify or re-implement anything in
`core.py`, `phase_rules.json`, the taxonomy, the JSONL v3 schema, the T0-T9 mapper,
T7a/T7b/T7c, repair detection, token accounting or WAIT. It only *reads* the harness
artifacts (benchmark-run.json per run) and, optionally, an Evaluation Core `run.json`
for Engine A, then normalizes them into one document.

Honesty rule: a value the Evaluation Core cannot prove stays null; the adapter never
estimates and never forces external timing into the JSONL v3 parser.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

SKIP = ("WARMUP", "TEST")


def load_runs(results_dir: Path) -> list[dict]:
    runs = []
    for d in sorted(results_dir.iterdir()):
        f = d / "benchmark-run.json"
        if not f.exists():
            continue
        r = json.loads(f.read_text())
        if any(s in r.get("run_id", "") for s in SKIP):
            continue
        runs.append(r)
    return runs


def normalize(run: dict) -> dict:
    def prov(key, source):
        return source if run.get(key) is not None else "NOT_AVAILABLE"

    return {
        "run_id": run["run_id"],
        "engine": run["engine"],
        "journey": run["journey"],
        "iteration": run.get("iteration"),
        "outcome": run.get("outcome"),
        "identity": {
            "apk_sha256": run.get("apk_sha256"),
            "git_commit": run.get("git_commit"),
            "device_serial": run.get("device_serial"),
            "device_model": run.get("device_model"),
            "api": run.get("api"),
        },
        "clocks": {
            "setup_wall_ms": run.get("setup_wall_ms"),
            "total_wall_ms": run.get("total_wall_ms"),
        },
        "phases": {
            "T7": {
                "T7a_deploy_ms": run.get("t7a_ms"),
                "T7b_ui_driving_ms": run.get("t7b_ms"),
                "T7c_evidence_state_ms": run.get("t7c_ms"),
            }
        },
        "tokens": {
            "model_requests": run.get("model_requests", 0),
            "input_tokens": run.get("input_tokens", 0),
            "output_tokens": run.get("output_tokens", 0),
        },
        "evidence": {
            "ui": run.get("ui_evidence"),
            "database": run.get("database_evidence"),
            "process": run.get("process_evidence"),
            "visual": run.get("visual_evidence"),
            "screenshots": run.get("screenshots", 0),
            "layout_dumps": run.get("layout_dumps", 0),
        },
        "human_interventions": run.get("human_interventions", 0),
        "provenance": {
            "T7a": prov("t7a_ms", "harness-monotonic"),
            "T7b": prov("t7b_ms", "harness-monotonic-events"),
            "T7c": prov("t7c_ms", "harness-monotonic-events"),
        },
    }


def fm_core(core_run: dict) -> dict | None:
    """Fold an Evaluation Core run.json (observer output) without altering its schema."""
    phase_totals = core_run.get("phase_totals") or {}
    subphase_totals = core_run.get("subphase_totals") or {}
    if not phase_totals and not subphase_totals:
        return None

    def secs(bucket: dict, key: str):
        v = (bucket.get(key) or {}).get("wall_seconds")
        return round(v, 3) if isinstance(v, (int, float)) else None

    return {
        "source": "evaluation-core run.json",
        "run_id": core_run.get("run_id"),
        "T7_wall_seconds": secs(phase_totals, "T7"),
        "T7a_seconds": secs(subphase_totals, "T7a"),
        "T7b_seconds": secs(subphase_totals, "T7b"),
        "T7c_seconds": secs(subphase_totals, "T7c"),
        "tokens_raw": core_run.get("tokens_raw"),
        "note": "values exactly as reported by the observer; null when the core could not prove them",
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--results", required=True, help="verification-benchmark/results dir")
    p.add_argument("--output", required=True)
    p.add_argument("--core-run-json", default=None, help="optional Evaluation Core run.json (Engine A)")
    p.add_argument("--engine-a-core", default=None, help="Engine A label to attach core numbers to")
    args = p.parse_args()

    runs = [normalize(r) for r in load_runs(Path(args.results))]

    doc = {
        "adapter": "external_adapter.py",
        "version": "1.0",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": "Add-on only. Evaluation Core (core.py / phase_rules.json / JSONL v3) is unchanged.",
        "runs": runs,
    }

    if args.core_run_json:
        core = json.loads(Path(args.core_run_json).read_text())
        folded = fm_core(core)
        if folded:
            doc["evaluation_core_engine_a"] = {
                "engine": args.engine_a_core or "A",
                **folded,
            }

    Path(args.output).write_text(json.dumps(doc, indent=2))
    print(f"wrote {args.output} ({len(runs)} runs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
