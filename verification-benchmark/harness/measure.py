#!/usr/bin/env python3
"""Aggregate per-run benchmark-run.json files into results/summary.json + summary.csv.

Aggregation is driven by the explicit, machine-readable baseline manifest
(`results/baseline-manifest.json`), NOT by substring matching on run ids. A run is
counted in the headline summary only when its `measurement_class == "measured"`.
Engine A control runs (`measurement_class == "control"`) are aggregated separately.

Classes: measured | control | warmup | diagnostic | failed-pre-fix
Runs absent from the manifest are excluded by default (deny-by-default allowlist).
"""
from __future__ import annotations

import csv
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
RESULTS = BASE / "results"
MANIFEST = RESULTS / "baseline-manifest.json"


def stat(values: list[float]):
    if not values:
        return {"median": None, "min": None, "max": None, "n": 0, "variation_pct": None}
    med = statistics.median(values)
    variation = None
    if med:
        variation = round((max(values) - min(values)) / med * 100, 1)
    return {
        "median": round(med, 1),
        "min": round(min(values), 1),
        "max": round(max(values), 1),
        "n": len(values),
        "variation_pct": variation,
    }


def reduction_pct(baseline: float | None, value: float | None):
    if baseline is None or value is None or baseline == 0:
        return None
    return round((baseline - value) / baseline * 100, 1)


def load_manifest() -> dict:
    if not MANIFEST.exists():
        raise SystemExit(
            f"missing baseline manifest {MANIFEST}; the aggregator requires an explicit "
            "allowlist (run the inventory builder or restore results/baseline-manifest.json)")
    return json.loads(MANIFEST.read_text())


def load_runs() -> tuple[list[dict], list[dict]]:
    """Return (included runs, excluded records)."""
    manifest = load_manifest()
    by_id = {r["run_id"]: r for r in manifest["runs"]}
    included: list[dict] = []
    excluded: list[dict] = []
    for d in sorted(RESULTS.iterdir()):
        f = d / "benchmark-run.json"
        if not f.exists():
            if d.name in by_id and by_id[d.name]["excluded_from_baseline"]:
                excluded.append({
                    "run_id": d.name, "engine": by_id[d.name].get("engine"),
                    "journey": by_id[d.name].get("journey"),
                    "measurement_class": by_id[d.name]["measurement_class"],
                    "reason": by_id[d.name].get("exclusion_reason") or "excluded",
                })
            continue
        r = json.loads(f.read_text())
        entry = by_id.get(r["run_id"])
        if entry is None:
            excluded.append({
                "run_id": r["run_id"], "engine": r.get("engine"), "journey": r.get("journey"),
                "measurement_class": "diagnostic",
                "reason": "not in baseline manifest (deny by default)",
            })
            continue
        if entry["excluded_from_baseline"]:
            excluded.append({
                "run_id": r["run_id"], "engine": r.get("engine"), "journey": r.get("journey"),
                "measurement_class": entry["measurement_class"],
                "reason": entry.get("exclusion_reason") or "excluded",
            })
            continue
        r["measurement_class"] = entry["measurement_class"]
        included.append(r)
    return included, excluded


def group(runs: list[dict]) -> list[dict]:
    groups: dict[tuple, list] = {}
    for r in runs:
        groups.setdefault((r["engine"], r["journey"]), []).append(r)

    out = []
    for (engine, journey), rs in sorted(groups.items()):
        def vals(key):
            return [r[key] for r in rs if r.get(key) is not None]

        out.append({
            "engine": engine,
            "journey": journey,
            "n": len(rs),
            "pass": sum(1 for r in rs if r["outcome"] == "PASS"),
            "fail": sum(1 for r in rs if r["outcome"] == "FAIL"),
            "t7a": stat(vals("t7a_ms")),
            "t7b": stat(vals("t7b_ms")),
            "t7c": stat(vals("t7c_ms")),
            "total_wall": stat(vals("total_wall_ms")),
            "setup_wall": stat(vals("setup_wall_ms")),
            "model_requests": sum((r.get("model_requests") or 0) for r in rs),
            "input_tokens": sum((r.get("input_tokens") or 0) for r in rs),
            "output_tokens": sum((r.get("output_tokens") or 0) for r in rs),
            "screenshots": sum(r.get("screenshots", 0) for r in rs),
            "layout_dumps": sum(r.get("layout_dumps", 0) for r in rs),
            "retries": sum(r.get("retries", 0) for r in rs),
            "human_interventions": sum(r.get("human_interventions", 0) for r in rs),
        })
    return out


def main() -> int:
    runs, excluded = load_runs()
    measured = [r for r in runs if r["measurement_class"] == "measured"]
    control = [r for r in runs if r["measurement_class"] == "control"]

    measured_groups = group(measured)
    control_groups = group(control)

    def med(groups, engine, journey):
        for g in groups:
            if g["engine"] == engine and g["journey"] == journey:
                return g["total_wall"]["median"]
        return None

    per_journey = []
    for journey in ("J1", "J2", "J3"):
        a = med(control_groups, "A", journey)
        b = med(measured_groups, "B", journey)
        c = med(measured_groups, "C", journey)
        per_journey.append({
            "journey": journey,
            "A_total_median_ms": a,
            "B_total_median_ms": b,
            "B_reduction_pct": reduction_pct(a, b),
            "C_total_median_ms": c,
            "C_reduction_pct": reduction_pct(a, c),
        })

    a_sum = sum(x["A_total_median_ms"] for x in per_journey if x["A_total_median_ms"] is not None)
    b_sum = sum(x["B_total_median_ms"] for x in per_journey if x["B_total_median_ms"] is not None)
    c_sum = sum(x["C_total_median_ms"] for x in per_journey if x["C_total_median_ms"] is not None)

    summary = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "allowlist": str(MANIFEST.relative_to(BASE)),
        "final_apk_sha256": load_manifest().get("final_apk_sha256"),
        "rule": "headline summary counts measurement_class == 'measured' only; control is separate",
        "measured": measured_groups,
        "controls": control_groups,
        "compression": {
            "basis": "sum of per-journey median total_wall_ms (A control vs measured)",
            "per_journey": per_journey,
            "aggregate": {
                "A_total_ms": a_sum,
                "B_total_ms": b_sum,
                "B_reduction_pct": reduction_pct(a_sum, b_sum),
                "C_total_ms": c_sum,
                "C_reduction_pct": reduction_pct(a_sum, c_sum),
            },
        },
        "excluded": excluded,
    }
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=2))

    cols = [
        "engine", "journey", "n", "pass", "fail",
        "t7a_median", "t7b_median", "t7b_min", "t7b_max", "t7b_var_pct",
        "t7c_median", "total_median", "setup_median",
        "model_requests", "screenshots", "retries", "human_interventions",
    ]
    with open(RESULTS / "summary.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for s in measured_groups:
            w.writerow([
                s["engine"], s["journey"], s["n"], s["pass"], s["fail"],
                s["t7a"]["median"], s["t7b"]["median"], s["t7b"]["min"], s["t7b"]["max"], s["t7b"]["variation_pct"],
                s["t7c"]["median"], s["total_wall"]["median"], s["setup_wall"]["median"],
                s["model_requests"], s["screenshots"], s["retries"], s["human_interventions"],
            ])

    agg = summary["compression"]["aggregate"]
    print(f"measured groups={len(measured_groups)} control groups={len(control_groups)} "
          f"excluded={len(excluded)}")
    print(f"B reduction={agg['B_reduction_pct']}%  C reduction={agg['C_reduction_pct']}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
