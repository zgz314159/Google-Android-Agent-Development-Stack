#!/usr/bin/env python3
"""Verification-plan contract validation (stdlib only).

  plan_validate.py <verification-plan.json>

Validates the plan against contracts/verification-plan.schema.json (the machine-readable
source of truth) using a dependency-free checker so the runner needs no third-party
packages. Prints PLAN_VALID=true/false and exits non-zero on any violation.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ENGINES = {"uiautomator", "maestro"}
EVIDENCE_POLICIES = {"failure-only", "always"}
MEASUREMENT_CLASSES = {"measured", "control", "warmup", "diagnostic", "failed-pre-fix"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
TIMEOUT_KEYS = {"preflight", "install", "instrumentation", "oracle", "evidence", "cleanup", "shell"}


def validate_plan(plan: dict) -> list[str]:
    errs: list[str] = []
    if not isinstance(plan, dict):
        return [f"plan is not an object: {type(plan).__name__}"]

    for k in ("verification_id", "project", "android", "engine", "journey"):
        if k not in plan:
            errs.append(f"missing required field: {k}")
    for k in ("verification_id", "project"):
        if k in plan and (not isinstance(plan[k], str) or not plan[k]):
            errs.append(f"{k} must be a non-empty string")

    if plan.get("engine") not in ENGINES:
        errs.append(f"engine '{plan.get('engine')}' not in {sorted(ENGINES)}")

    # android
    android = plan.get("android")
    if not isinstance(android, dict):
        errs.append("android must be an object")
    else:
        for k in ("package_name", "apk"):
            if not isinstance(android.get(k), str) or not android.get(k):
                errs.append(f"android.{k} must be a non-empty string")
        for k in ("expected_app_sha256", "expected_test_sha256"):
            v = android.get(k)
            if v is not None and not (isinstance(v, str) and SHA256_RE.match(v)):
                errs.append(f"android.{k} must be a 64-hex sha256")
        if "runner" in android and not isinstance(android["runner"], str):
            errs.append("android.runner must be a string")

    # journey
    journey = plan.get("journey")
    if not isinstance(journey, dict):
        errs.append("journey must be an object")
    else:
        for k in ("id", "test_class"):
            if not isinstance(journey.get(k), str) or not journey.get(k):
                errs.append(f"journey.{k} must be a non-empty string")
        if "flow" in journey and not isinstance(journey["flow"], str):
            errs.append("journey.flow must be a string")
        if "args" in journey and not isinstance(journey["args"], dict):
            errs.append("journey.args must be an object")
        if plan.get("engine") == "maestro" and not journey.get("flow"):
            errs.append("journey.flow is required when engine=maestro")

    # device
    device = plan.get("device")
    if device is not None:
        if not isinstance(device, dict):
            errs.append("device must be an object")
        else:
            for k in ("serial", "expected_model", "expected_api"):
                if k in device and not isinstance(device[k], str):
                    errs.append(f"device.{k} must be a string")

    # fixture / oracle
    fixture = plan.get("fixture")
    if fixture is not None:
        if not isinstance(fixture, dict) or not fixture.get("class") or not fixture.get("method"):
            errs.append("fixture requires non-empty class and method")
    oracle = plan.get("oracle")
    if oracle is not None:
        if not isinstance(oracle, dict) or not oracle.get("class"):
            errs.append("oracle requires a non-empty class")
        elif oracle.get("expected_outcome", "PASS") not in ("PASS", "FAIL"):
            errs.append("oracle.expected_outcome must be PASS or FAIL")

    # timeouts
    timeouts = plan.get("timeouts")
    if timeouts is not None:
        if not isinstance(timeouts, dict):
            errs.append("timeouts must be an object")
        else:
            for k, v in timeouts.items():
                if k not in TIMEOUT_KEYS:
                    errs.append(f"unknown timeout key '{k}'")
                elif not isinstance(v, int) or isinstance(v, bool) or v < 1:
                    errs.append(f"timeouts.{k} must be a positive integer")

    if "evidence_policy" in plan and plan["evidence_policy"] not in EVIDENCE_POLICIES:
        errs.append(f"evidence_policy '{plan['evidence_policy']}' not in {sorted(EVIDENCE_POLICIES)}")
    if "require_verify_part" in plan and not isinstance(plan["require_verify_part"], bool):
        errs.append("require_verify_part must be a boolean")
    if "measurement_class" in plan and plan["measurement_class"] not in MEASUREMENT_CLASSES:
        errs.append(
            f"measurement_class '{plan['measurement_class']}' not in {sorted(MEASUREMENT_CLASSES)}")
    if "excluded_from_baseline" in plan and not isinstance(plan["excluded_from_baseline"], bool):
        errs.append("excluded_from_baseline must be a boolean")

    prov = plan.get("provenance")
    if prov is not None and not isinstance(prov, dict):
        errs.append("provenance must be an object")
    ev = plan.get("evaluation")
    if ev is not None and not isinstance(ev, dict):
        errs.append("evaluation must be an object")

    return errs


def load_plan(path: str | Path) -> dict:
    return json.loads(Path(path).read_text())


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: plan_validate.py <verification-plan.json>", file=sys.stderr)
        return 2
    try:
        plan = load_plan(argv[1])
    except Exception as e:  # noqa: BLE001
        print(f"PLAN_VALID=false\n  - cannot read/parse {argv[1]}: {e}")
        return 1
    errs = validate_plan(plan)
    if errs:
        print("PLAN_VALID=false")
        for e in errs:
            print(f"  - {e}")
        return 1
    print("PLAN_VALID=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
