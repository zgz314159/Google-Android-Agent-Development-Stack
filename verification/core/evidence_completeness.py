#!/usr/bin/env python3
"""Failure-bundle completeness validation.

  evidence_completeness.py <failure-dir | run-dir>

A failed run's bundle must contain (or explicitly declare unavailable) every required
artifact. Nothing is allowed to be silently missing. Writes `completeness.json` into the
bundle and exits non-zero when incomplete.

Format rules enforced:
  * a `.json` artifact must parse as JSON;
  * a `.xml` artifact must be XML (uiautomator dump XML is NEVER relabelled `.json`);
  * metadata.layout_provider in {android_cli, uiautomator_xml, unavailable}.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

LAYOUT_PROVIDERS = {"android_cli", "uiautomator_xml", "unavailable"}

# (file, logical-name, allow_unavailable)
REQUIRED = [
    ("metadata.json", "metadata", False),
    ("executor-output.txt", "executor-output", False),
    ("failed-assertion.json", "failed-assertion", False),
    ("logcat.txt", "logcat", False),
    ("screenshot.png", "screenshot", True),
    ("db-state.json", "db-state", True),
]


def _nonempty(p: Path) -> bool:
    try:
        return p.is_file() and p.stat().st_size > 0
    except OSError:
        return False


def _unavailable_reason(meta: dict, name: str) -> str | None:
    for a in meta.get("artifacts", []) or []:
        if isinstance(a, dict) and a.get("name") == name and a.get("available") is False:
            return a.get("reason") or "unavailable"
    key = f"{name}_unavailable"
    if key in meta and meta[key]:
        return str(meta[key])
    return None


def check_bundle(failure_dir: Path) -> dict:
    meta_path = failure_dir / "metadata.json"
    meta: dict = {}
    meta_err = None
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text())
        except Exception as e:  # noqa: BLE001
            meta = {}
            meta_err = f"metadata.json is not valid JSON: {e}"

    present: list[str] = []
    missing: list[str] = []
    unavailable: list[str] = []
    errors: list[str] = []
    if meta_err:
        errors.append(meta_err)

    for fname, logical, allow_unavail in REQUIRED:
        p = failure_dir / fname
        if _nonempty(p):
            present.append(logical)
        else:
            reason = _unavailable_reason(meta, logical) if allow_unavail else None
            if reason:
                unavailable.append(f"{logical}: {reason}")
            else:
                missing.append(logical)

    lay_json = failure_dir / "layout.json"
    lay_xml = failure_dir / "layout.xml"
    provider = meta.get("layout_provider")
    if provider is not None and provider not in LAYOUT_PROVIDERS:
        errors.append(f"layout_provider '{provider}' not in {sorted(LAYOUT_PROVIDERS)}")
    if _nonempty(lay_json):
        present.append("layout.json")
        try:
            json.loads(lay_json.read_text())
        except Exception as e:  # noqa: BLE001
            errors.append(f"layout.json is not valid JSON: {e}")
    elif _nonempty(lay_xml):
        head = lay_xml.read_text(errors="replace")[:200]
        if not (head.lstrip().startswith("<?xml") or "<hierarchy" in head):
            errors.append("layout.xml is not XML (format rule: XML must stay .xml)")
        present.append("layout.xml")
    else:
        reason = _unavailable_reason(meta, "layout")
        if provider == "unavailable" or reason:
            unavailable.append(f"layout: {reason or 'unavailable'}")
        else:
            missing.append("layout")

    complete = not missing and not errors
    return {
        "bundle": str(failure_dir),
        "complete": complete,
        "present": sorted(present),
        "unavailable": sorted(unavailable),
        "missing": sorted(missing),
        "errors": sorted(errors),
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def resolve_bundle(arg: str) -> Path:
    p = Path(arg)
    if (p / "failure").is_dir():
        return p / "failure"
    return p


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: evidence_completeness.py <failure-dir|run-dir>", file=sys.stderr)
        return 2
    bundle = resolve_bundle(argv[1])
    if not bundle.is_dir():
        print(f"MISSING_BUNDLE={bundle}", file=sys.stderr)
        return 2
    report = check_bundle(bundle)
    (bundle / "completeness.json").write_text(json.dumps(report, indent=2))
    if report["complete"]:
        print(f"EVIDENCE_COMPLETE=true bundle={bundle}")
        return 0
    print(f"EVIDENCE_COMPLETE=false bundle={bundle}")
    for m in report["missing"]:
        print(f"  missing: {m}")
    for e in report["errors"]:
        print(f"  error: {e}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
