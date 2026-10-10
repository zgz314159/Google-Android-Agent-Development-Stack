#!/usr/bin/env python3
"""Lightweight result-schema validation for benchmark-run.json.

No third-party dependencies. Defines the canonical field set, types and closed enums for a
run result. `emit_run.py` calls this on every written result; `validate_result.py` exposes it
as a CLI. Unknown `measurement_class` (or any other closed enum) is a hard failure.
"""
from __future__ import annotations

import json
from pathlib import Path

ENGINES = {"A", "B", "C"}
OUTCOMES = {"PASS", "FAIL"}
PROCESS_EVIDENCE = {"CRASH", "no-crash"}
UI_EVIDENCE = {"uiautomator", "maestro", "screenshot+vision-inspection"}
# Canonical measurement_class enum (mirrors results/baseline-manifest.json "classes").
MEASUREMENT_CLASSES = {"measured", "control", "warmup", "diagnostic", "failed-pre-fix"}

REQUIRED = [
    "engine", "journey", "iteration", "run_id", "outcome",
    "apk_sha256", "git_commit", "device_serial", "device_model", "api",
    "setup_wall_ms", "t7a_ms", "t7b_ms", "t7c_ms", "total_wall_ms",
    "model_requests", "input_tokens", "output_tokens", "assertions",
    "screenshots", "layout_dumps", "retries", "human_interventions",
    "ui_evidence", "database_evidence", "process_evidence", "visual_evidence", "spans",
]

_OPTIONAL_NUM = {"t7a_ms", "t7b_ms", "t7c_ms", "setup_wall_ms",
                 "input_tokens", "output_tokens", "assertions", "model_requests"}
_INT_FIELDS = {"iteration", "total_wall_ms", "screenshots", "layout_dumps", "retries",
               "human_interventions"}
_STR_FIELDS = {"run_id", "git_commit", "device_serial", "device_model", "journey"}


def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def validate_benchmark_run(run: dict) -> list[str]:
    """Return a list of human-readable error strings (empty == valid)."""
    errs: list[str] = []

    if not isinstance(run, dict):
        return [f"result is not an object: {type(run).__name__}"]

    for k in REQUIRED:
        if k not in run:
            errs.append(f"missing required field: {k}")

    # engine
    if "engine" in run and run["engine"] not in ENGINES:
        errs.append(f"engine '{run.get('engine')}' not in {sorted(ENGINES)}")
    # outcome
    if "outcome" in run and run["outcome"] not in OUTCOMES:
        errs.append(f"outcome '{run.get('outcome')}' not in {sorted(OUTCOMES)}")
    # process / ui evidence enums
    if "process_evidence" in run and run["process_evidence"] not in PROCESS_EVIDENCE:
        errs.append(f"process_evidence '{run.get('process_evidence')}' not in {sorted(PROCESS_EVIDENCE)}")
    if "ui_evidence" in run and run["ui_evidence"] not in UI_EVIDENCE:
        errs.append(f"ui_evidence '{run.get('ui_evidence')}' not in {sorted(UI_EVIDENCE)}")

    # measurement_class (optional; only present on diagnostic/self-test runs)
    if "measurement_class" in run and run["measurement_class"] is not None:
        if run["measurement_class"] not in MEASUREMENT_CLASSES:
            errs.append(
                f"unknown measurement_class '{run['measurement_class']}' "
                f"(allowed: {sorted(MEASUREMENT_CLASSES)})")

    # api is a STRING by contract
    if "api" in run and not isinstance(run["api"], str):
        errs.append(f"api must be a string, got {type(run['api']).__name__}")

    # string fields
    for k in sorted(_STR_FIELDS):
        if k in run and not isinstance(run[k], str):
            errs.append(f"{k} must be a string, got {type(run[k]).__name__}")

    # nullable numeric fields
    for k in sorted(_OPTIONAL_NUM):
        if k in run and run[k] is not None and not _is_num(run[k]):
            errs.append(f"{k} must be number|null, got {type(run[k]).__name__}")
    # required int fields
    for k in sorted(_INT_FIELDS):
        if k in run and not isinstance(run[k], int):
            errs.append(f"{k} must be an integer, got {type(run[k]).__name__}")

    # database_evidence: string | null
    if "database_evidence" in run and run["database_evidence"] is not None and \
            not isinstance(run["database_evidence"], str):
        errs.append("database_evidence must be string|null")

    # visual_evidence: string
    if "visual_evidence" in run and not isinstance(run["visual_evidence"], str):
        errs.append("visual_evidence must be a string")

    # spans: list of {kind,name,ms}
    if "spans" in run:
        spans = run["spans"]
        if not isinstance(spans, list):
            errs.append("spans must be a list")
        else:
            for i, s in enumerate(spans):
                if not isinstance(s, dict):
                    errs.append(f"spans[{i}] must be an object")
                    continue
                for k in ("kind", "name", "ms"):
                    if k not in s:
                        errs.append(f"spans[{i}] missing '{k}'")
                if "ms" in s and not _is_num(s["ms"]):
                    errs.append(f"spans[{i}].ms must be numeric")

    # optional bool
    if "excluded_from_baseline" in run and not isinstance(run["excluded_from_baseline"], bool):
        errs.append("excluded_from_baseline must be a boolean")

    return errs


def validate_file(path: Path) -> list[str]:
    try:
        run = json.loads(Path(path).read_text())
    except Exception as e:  # noqa: BLE001
        return [f"cannot read/parse {path}: {e}"]
    return validate_benchmark_run(run)
