#!/usr/bin/env python3
"""Result-schema validation for verification-result.json.

No third-party dependencies. Defines the canonical field set, types and closed enums for a
Verification Layer result. `result_emit.py` calls this on every written result; the CLI
`validate_result.py` exposes it; `plan_validate.py` reuses the shared enums.
"""
from __future__ import annotations

import json
from pathlib import Path

ENGINES = {"uiautomator", "maestro"}
OUTCOMES = {"PASS", "FAIL"}
PROCESS_EVIDENCE = {"CRASH", "no-crash"}
UI_EVIDENCE = {"uiautomator", "maestro", "screenshot+vision-inspection"}
MEASUREMENT_CLASSES = {"measured", "control", "warmup", "diagnostic", "failed-pre-fix"}
EVIDENCE_POLICIES = {"failure-only", "always"}

REQUIRED = [
    "verification_id", "project", "engine", "journey", "outcome",
    "started_at", "finished_at", "app_apk_sha256",
    "verification_layer_version", "device", "measurements", "checks", "evidence",
]

_OPTIONAL_NUM = {"t7a_ms", "t7b_ms", "t7c_ms", "setup_wall_ms", "total_wall_ms"}
_STR_FIELDS = {"verification_id", "project", "journey", "started_at", "finished_at",
               "app_apk_sha256", "verification_layer_version", "runner_version"}


def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def validate_result(result: dict) -> list[str]:
    """Return a list of human-readable error strings (empty == valid)."""
    errs: list[str] = []
    if not isinstance(result, dict):
        return [f"result is not an object: {type(result).__name__}"]

    for k in REQUIRED:
        if k not in result:
            errs.append(f"missing required field: {k}")

    if result.get("engine") not in ENGINES:
        errs.append(f"engine '{result.get('engine')}' not in {sorted(ENGINES)}")
    if result.get("outcome") not in OUTCOMES:
        errs.append(f"outcome '{result.get('outcome')}' not in {sorted(OUTCOMES)}")

    for k in sorted(_STR_FIELDS):
        if k in result and not isinstance(result[k], str):
            errs.append(f"{k} must be a string, got {type(result[k]).__name__}")

    # device
    device = result.get("device")
    if not isinstance(device, dict):
        errs.append("device must be an object")
    else:
        if not isinstance(device.get("serial"), str):
            errs.append("device.serial must be a string")
        for k in ("model", "api"):
            if k in device and device[k] is not None and not isinstance(device[k], str):
                errs.append(f"device.{k} must be string|null")

    # measurements
    m = result.get("measurements")
    if not isinstance(m, dict):
        errs.append("measurements must be an object")
    else:
        if m.get("class") not in MEASUREMENT_CLASSES:
            errs.append(
                f"measurements.class '{m.get('class')}' not in {sorted(MEASUREMENT_CLASSES)}")
        for k in sorted(_OPTIONAL_NUM):
            if k in m and m[k] is not None and not _is_num(m[k]):
                errs.append(f"measurements.{k} must be number|null")

    # checks
    checks = result.get("checks")
    if not isinstance(checks, dict):
        errs.append("checks must be an object")
    else:
        ui = checks.get("ui", {})
        if ui.get("evidence") not in UI_EVIDENCE:
            errs.append(f"checks.ui.evidence '{ui.get('evidence')}' not in {sorted(UI_EVIDENCE)}")
        proc = checks.get("process", {})
        if proc.get("evidence") not in PROCESS_EVIDENCE:
            errs.append(
                f"checks.process.evidence (process_evidence) '{proc.get('evidence')}' "
                f"not in {sorted(PROCESS_EVIDENCE)}")
        for k in ("ui", "database", "process", "visual"):
            if k not in checks:
                errs.append(f"missing required field: checks.{k}")

    # evidence
    ev = result.get("evidence")
    if not isinstance(ev, dict):
        errs.append("evidence must be an object")
    elif ev.get("policy") not in EVIDENCE_POLICIES:
        errs.append(f"evidence.policy '{ev.get('policy')}' not in {sorted(EVIDENCE_POLICIES)}")

    # nullable
    if "test_apk_sha256" in result and result["test_apk_sha256"] is not None and \
            not isinstance(result["test_apk_sha256"], str):
        errs.append("test_apk_sha256 must be string|null")

    return errs


def validate_file(path: Path) -> list[str]:
    try:
        result = json.loads(Path(path).read_text())
    except Exception as e:  # noqa: BLE001
        return [f"cannot read/parse {path}: {e}"]
    return validate_result(result)
