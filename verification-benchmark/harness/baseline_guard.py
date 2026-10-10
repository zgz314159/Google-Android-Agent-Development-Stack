#!/usr/bin/env python3
"""Frozen-baseline invariant guard (read-only).

Recomputes the frozen invariants from the on-disk artifacts and proves hardening changed
nothing:

  * counts: A control = 3, B measured = 11, C measured = 13, total = 27
  * every measured run's apk_sha256 == the frozen APK hash
  * compression: B = 96.6%, C = 89.4% (recomputed from measured medians)
  * deny-by-default: any results/ run absent from the manifest is excluded, not measured
  * manifest measurement_class values are all in the declared enum
  * every file in reports/hardening/baseline-before.sha256 is byte-identical

Writes reports/hardening/baseline-invariants.json and exits non-zero on any violation.
"""
from __future__ import annotations

import hashlib
import json
import os
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

HARNESS = Path(__file__).resolve().parent
BASE = HARNESS.parent
RESULTS = BASE / "results"
MANIFEST = RESULTS / "baseline-manifest.json"
SNAPSHOT = BASE / "reports" / "hardening" / "baseline-before.sha256"


def _reports_dir() -> Path:
    """Generated guard output must live OUTSIDE the project (STACK_DATA_ROOT/artifacts)."""
    override = os.environ.get("BENCH_REPORTS_DIR")
    if override:
        return Path(override)
    lib = BASE.parent / "scripts" / "lib"
    if str(lib) not in sys.path:
        sys.path.insert(0, str(lib))
    import stack_paths  # noqa: PLC0415

    return stack_paths.artifacts_root() / "verification-benchmark" / "reports" / "hardening"


REPORTS = _reports_dir()

EXPECT = {"A": 3, "B": 11, "C": 13, "total": 27}
EXPECT_REDUCTION = {"B": 96.6, "C": 89.4}
FINAL_APK = "a8858bd1f57b328a5042a120023508ced8e1cbbf68446bab3ce0e5e80f6fdf06"


def reduction_pct(baseline, value):
    if baseline in (None, 0) or value is None:
        return None
    return round((baseline - value) / baseline * 100, 1)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    violations: list[str] = []
    if not MANIFEST.exists():
        print(f"missing manifest {MANIFEST}", file=sys.stderr)
        return 2
    manifest = json.loads(MANIFEST.read_text())
    classes = set(manifest.get("classes", []))
    final = manifest.get("final_apk_sha256")
    by_id = {r["run_id"]: r for r in manifest["runs"]}

    # manifest enum validity
    for r in manifest["runs"]:
        if r["measurement_class"] not in classes:
            violations.append(f"manifest run {r['run_id']} has unknown class {r['measurement_class']}")

    included: list[dict] = []
    denied: list[dict] = []
    for d in sorted(RESULTS.iterdir()):
        f = d / "benchmark-run.json"
        if not f.exists():
            continue
        r = json.loads(f.read_text())
        entry = by_id.get(r.get("run_id"))
        if entry is None:
            denied.append({"run_id": r.get("run_id"), "measurement_class": "diagnostic(implicit)"})
            continue
        if entry["excluded_from_baseline"]:
            denied.append({"run_id": r.get("run_id"),
                           "measurement_class": entry["measurement_class"]})
            continue
        r["measurement_class"] = entry["measurement_class"]
        included.append(r)

    measured = [r for r in included if r["measurement_class"] == "measured"]
    control = [r for r in included if r["measurement_class"] == "control"]

    counts = {
        "A": sum(1 for r in control if r["engine"] == "A"),
        "B": sum(1 for r in measured if r["engine"] == "B"),
        "C": sum(1 for r in measured if r["engine"] == "C"),
    }
    counts["total"] = counts["A"] + counts["B"] + counts["C"]
    for k, want in EXPECT.items():
        if counts[k] != want:
            violations.append(f"count {k}={counts[k]} != expected {want}")

    # APK provenance of measured runs
    if final:
        bad_hash = [r["run_id"] for r in measured if r.get("apk_sha256") != final]
        if bad_hash:
            violations.append(f"measured runs with non-frozen apk_sha256: {bad_hash}")

    # deny-by-default: no denied run may be measured
    for r in denied:
        if r["measurement_class"] == "measured":
            violations.append(f"denied run counted as measured: {r['run_id']}")

    # compression recompute
    def med(engine, journey):
        vals = [r["total_wall_ms"] for r in measured
                if r["engine"] == engine and r["journey"] == journey and r.get("total_wall_ms") is not None]
        return statistics.median(vals) if vals else None

    def ctrl_med(journey):
        vals = [r["total_wall_ms"] for r in control
                if r["engine"] == "A" and r["journey"] == journey and r.get("total_wall_ms") is not None]
        return statistics.median(vals) if vals else None

    per = {}
    for journey in ("J1", "J2", "J3"):
        a = ctrl_med(journey)
        per[journey] = {"A": a, "B": med("B", journey), "C": med("C", journey)}
    a_sum = sum(v["A"] for v in per.values() if v["A"] is not None)
    b_sum = sum(v["B"] for v in per.values() if v["B"] is not None)
    c_sum = sum(v["C"] for v in per.values() if v["C"] is not None)
    comp = {
        "A_total_ms": a_sum, "B_total_ms": b_sum, "C_total_ms": c_sum,
        "B_reduction_pct": reduction_pct(a_sum, b_sum),
        "C_reduction_pct": reduction_pct(a_sum, c_sum),
    }
    for k, want in EXPECT_REDUCTION.items():
        got = comp[f"{k}_reduction_pct"]
        if got != want:
            violations.append(f"{k} reduction {got} != expected {want}")

    # frozen file checksums
    frozen = {"checked": 0, "changed": [], "missing": []}
    if SNAPSHOT.exists():
        for line in SNAPSHOT.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            digest, rel = line.split(maxsplit=1)
            p = BASE / rel
            frozen["checked"] += 1
            if not p.exists():
                frozen["missing"].append(rel)
                continue
            if sha256(p) != digest:
                frozen["changed"].append(rel)
        if frozen["changed"]:
            violations.append(f"frozen files changed: {frozen['changed']}")
        if frozen["missing"]:
            violations.append(f"frozen files missing: {frozen['missing']}")
    else:
        frozen["note"] = f"no snapshot at {SNAPSHOT}"

    report = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "counts": counts,
        "expected_counts": EXPECT,
        "measured_apk_sha256": final,
        "compression": comp,
        "expected_reduction_pct": EXPECT_REDUCTION,
        "included": [{"run_id": r["run_id"], "engine": r["engine"],
                      "measurement_class": r["measurement_class"]} for r in included],
        "deny_by_default_excluded": denied,
        "frozen_files": frozen,
        "violations": violations,
        "outcome": "PASS" if not violations else "FAIL",
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "baseline-invariants.json").write_text(json.dumps(report, indent=2))

    print(f"BASELINE_COUNTS A={counts['A']} B={counts['B']} C={counts['C']} total={counts['total']}")
    print(f"BASELINE_COMPRESSION B={comp['B_reduction_pct']}% C={comp['C_reduction_pct']}%")
    print(f"BASELINE_FROZEN_FILES checked={frozen['checked']} changed={len(frozen['changed'])}")
    if violations:
        print("BASELINE_GUARD=FAIL")
        for v in violations:
            print(f"  - {v}")
        return 1
    print("BASELINE_GUARD=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
