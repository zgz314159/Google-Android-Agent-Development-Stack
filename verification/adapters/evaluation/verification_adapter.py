#!/usr/bin/env python3
"""Evaluation Layer adapter: Verification Layer result -> normalized handoff.

ADD-ON only. It does NOT modify or re-implement the Evaluation Core (`core.py`,
`phase_rules.json`, the JSONL v3 parser, T0-T9, T7a/T7b/T7c, repair or token accounting).
It only *reads* a Verification Layer `verification-result.json` and normalizes it into one
document the Evaluation Layer can attribute to the Verification (T7) phase.

Honesty rule: a value the layer cannot prove stays null; the adapter never estimates and
never forces external timing into the JSONL v3 parser.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def normalize(result: dict) -> dict:
    def prov(key, source):
        val = (result.get("measurements") or {}).get(key)
        return source if val is not None else "NOT_AVAILABLE"

    m = result.get("measurements") or {}
    checks = result.get("checks") or {}
    ev = result.get("evidence") or {}
    return {
        "verification_id": result.get("verification_id"),
        "project": result.get("project"),
        "engine": result.get("engine"),
        "journey": result.get("journey"),
        "outcome": result.get("outcome"),
        "identity": {
            "app_apk_sha256": result.get("app_apk_sha256"),
            "test_apk_sha256": result.get("test_apk_sha256"),
            "verification_layer_version": result.get("verification_layer_version"),
            "runner_version": result.get("runner_version"),
            "device": result.get("device"),
        },
        "clocks": {
            "setup_wall_ms": m.get("setup_wall_ms"),
            "total_wall_ms": m.get("total_wall_ms"),
        },
        "phases": {
            "T7": {
                "T7a_deploy_ms": m.get("t7a_ms"),
                "T7b_ui_driving_ms": m.get("t7b_ms"),
                "T7c_evidence_state_ms": m.get("t7c_ms"),
            }
        },
        "measurement_class": m.get("class"),
        "excluded_from_baseline": m.get("excluded_from_baseline", False),
        "evidence": {
            "ui": (checks.get("ui") or {}).get("evidence"),
            "database": (checks.get("database") or {}).get("outcome"),
            "process": (checks.get("process") or {}).get("evidence"),
            "policy": ev.get("policy"),
            "bundle": ev.get("bundle"),
            "complete": ev.get("complete"),
        },
        "human_interventions": 0,
        "provenance": {
            "T7a": prov("t7a_ms", "verification-monotonic"),
            "T7b": prov("t7b_ms", "verification-events"),
            "T7c": prov("t7c_ms", "verification-events"),
        },
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--result", required=True, help="verification-result.json")
    p.add_argument("--output", required=True)
    p.add_argument("--evaluation-run-json", default=None,
                   help="optional Evaluation Core run.json to fold in (T7 wall/tokens)")
    args = p.parse_args()

    result = json.loads(Path(args.result).read_text())
    doc = {
        "adapter": "verification_adapter.py",
        "version": "1.0",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": "Add-on only. Evaluation Core (core.py / phase_rules.json / JSONL v3) is unchanged.",
        "verification": normalize(result),
    }
    if args.evaluation_run_json:
        core = json.loads(Path(args.evaluation_run_json).read_text())
        sub = (core.get("subphase_totals") or {})
        doc["evaluation_core"] = {
            "run_id": core.get("run_id"),
            "T7_wall_seconds": ((core.get("phase_totals") or {}).get("T7") or {}).get("wall_seconds"),
            "T7a_seconds": (sub.get("T7a") or {}).get("wall_seconds"),
            "T7b_seconds": (sub.get("T7b") or {}).get("wall_seconds"),
            "T7c_seconds": (sub.get("T7c") or {}).get("wall_seconds"),
        }
    Path(args.output).write_text(json.dumps(doc, indent=2))
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
