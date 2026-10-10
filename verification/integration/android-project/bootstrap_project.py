#!/usr/bin/env python3
"""Project integration bootstrap (Verification Layer v1.0.1).

    bootstrap_project.py --project <android-project-dir> [--app-module app] [--dry-run] [--json]

Installs the layer's PINNED, generic device-side support sources into a project's
`androidTest` source set and ensures the UiAutomator test dependency — so a new project
never has to find, understand, copy and hand-edit the same four files again.

What it installs (generic layer support only):
    dev.androidstack.verification.TimingLogger
    dev.androidstack.verification.JourneyBase
    dev.androidstack.verification.UiDriver
    dev.androidstack.verification.FailureBundleRule
    androidTestImplementation("androidx.test.uiautomator:uiautomator:<pinned>")

What it NEVER does (project-owned semantics — see the Integration Guide):
    FixtureSeeder / journey / DB oracle / selectors / acceptance. Those stay with the
    Specification Contract + the project.

Guarantees:
  * idempotent: first run INSTALLs, a second identical run is a NO-OP (nothing rewritten);
  * non-destructive: existing project files are never overwritten. If a destination file
    differs from the layer template it is reported as INTEGRATION_DRIFT and left untouched;
  * no duplicate dependency is ever added (an existing alias or coordinate is detected).

Exit codes: 0 = INSTALL/NO-OP, 3 = INTEGRATION_DRIFT, 2 = usage/validation error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve()
VERIFY_ROOT = HERE.parents[2]                      # verification/
LAYER_VERSION = (VERIFY_ROOT / "VERSION").read_text().strip() \
    if (VERIFY_ROOT / "VERSION").exists() else "unknown"
TEMPLATE_DIR = VERIFY_ROOT / "android" / "uiautomator"
SUPPORT_FILES = ["TimingLogger.kt", "JourneyBase.kt", "UiDriver.kt", "FailureBundleRule.kt"]
SUPPORT_PACKAGE = "dev.androidstack.verification"

UIAUTOMATOR_MODULE = "androidx.test.uiautomator:uiautomator"
UIAUTOMATOR_VERSION = "2.4.0"

MANIFEST_REL = ".verification/integration-manifest.json"

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_DRIFT = 3


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def _gradle_file(module_dir: Path) -> Path | None:
    for name in ("build.gradle.kts", "build.gradle"):
        f = module_dir / name
        if f.is_file():
            return f
    return None


def _dependency_present(text: str) -> bool:
    return bool(re.search(r"androidx\.test\.uiautomator", text)
                or re.search(r"libs\.androidx\.test\.uiautomator", text))


def _install_dependency(build_file: Path) -> str:
    """Return ADDED|PRESENT|UNCHANGED. Never duplicates; never touches unrelated deps."""
    text = build_file.read_text()
    if _dependency_present(text):
        return "PRESENT"
    lines = text.splitlines(keepends=True)
    insert_at = None
    for i, line in enumerate(lines):
        if re.match(r"^\s*dependencies\s*\{", line):
            insert_at = i + 1
            break
    if insert_at is None:
        return "NO_DEPENDENCIES_BLOCK"
    kts = build_file.suffix == ".kts"
    if kts:
        dep_line = f'    androidTestImplementation("{UIAUTOMATOR_MODULE}:{UIAUTOMATOR_VERSION}")\n'
    else:
        dep_line = f"    androidTestImplementation '{UIAUTOMATOR_MODULE}:{UIAUTOMATOR_VERSION}'\n"
    lines.insert(insert_at, dep_line)
    build_file.write_text("".join(lines))
    return "ADDED"


def _parse_identity(module_dir: Path) -> dict:
    """Best-effort namespace/applicationId read (never required for the bootstrap)."""
    ids: dict[str, str | None] = {"namespace": None, "applicationId": None}
    f = _gradle_file(module_dir)
    if f:
        text = f.read_text()
        ns = re.search(r'namespace\s*=\s*"([^"]+)"', text)
        app = re.search(r'applicationId\s*=\s*"([^"]+)"', text)
        if ns:
            ids["namespace"] = ns.group(1)
        if app:
            ids["applicationId"] = app.group(1)
    manifest = module_dir / "src/main/AndroidManifest.xml"
    if manifest.is_file():
        m = re.search(r'package="([^"]+)"', manifest.read_text())
        if m and not ids["namespace"]:
            ids["namespace"] = m.group(1)
    return ids


def bootstrap(project: Path, app_module: str, dry_run: bool) -> dict:
    diag: dict = {
        "verification_layer_version": LAYER_VERSION,
        "generated_utc": utcnow(),
        "project": str(project),
        "app_module": app_module,
        "package": SUPPORT_PACKAGE,
        "status": None,
        "support_files": [],
        "dependency": {},
        "drift": [],
        "identity": {},
        "errors": [],
    }

    if not project.is_dir():
        diag["status"] = "INVALID_PROJECT"
        diag["errors"].append(f"project dir not found: {project}")
        return diag
    module_dir = project / app_module
    build_file = _gradle_file(module_dir)
    if build_file is None:
        diag["status"] = "INVALID_PROJECT"
        diag["errors"].append(f"no build.gradle(.kts) in {module_dir}")
        return diag

    android_test_dir = module_dir / "src/androidTest/java"
    dest_dir = android_test_dir / SUPPORT_PACKAGE.replace(".", "/")
    diag["identity"] = _parse_identity(module_dir)

    changed = False
    for name in SUPPORT_FILES:
        src = TEMPLATE_DIR / name
        if not src.is_file():
            diag["errors"].append(f"layer template missing: {src}")
            continue
        template_sha = sha256_file(src)
        dst = dest_dir / name
        if not dst.exists():
            status = "INSTALLED"
            if not dry_run:
                dest_dir.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
            changed = True
        elif sha256_file(dst) == template_sha:
            status = "VERIFIED"
        else:
            status = "DRIFT"
            diag["drift"].append({"file": str(dst), "reason": "differs from layer template"})
        diag["support_files"].append({
            "name": name,
            "source": str(src),
            "destination": str(dst),
            "template_sha256": template_sha,
            "installed_sha256": sha256_file(dst) if dst.exists() else None,
            "status": status,
        })

    dep_action = "PRESENT" if _dependency_present(build_file.read_text()) else "MISSING"
    if dep_action == "MISSING":
        if dry_run:
            dep_action = "WOULD_ADD"
        else:
            dep_action = _install_dependency(build_file)
            if dep_action == "ADDED":
                changed = True
    diag["dependency"] = {
        "module": UIAUTOMATOR_MODULE,
        "version": UIAUTOMATOR_VERSION,
        "file": str(build_file),
        "action": dep_action,
    }

    if diag["errors"]:
        diag["status"] = "INVALID_PROJECT"
    elif diag["drift"] or dep_action == "NO_DEPENDENCIES_BLOCK":
        diag["status"] = "INTEGRATION_DRIFT"
    elif changed:
        diag["status"] = "INSTALL"
    else:
        diag["status"] = "NO-OP"

    if diag["status"] in ("INSTALL", "NO-OP", "INTEGRATION_DRIFT") and not dry_run:
        mpath = project / MANIFEST_REL
        mpath.parent.mkdir(parents=True, exist_ok=True)
        mpath.write_text(json.dumps(diag, indent=2))
    return diag


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Verification Layer project bootstrap")
    p.add_argument("--project", required=True, help="Android project root directory")
    p.add_argument("--app-module", default="app")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    diag = bootstrap(Path(args.project).expanduser().resolve(), args.app_module, args.dry_run)
    if args.json:
        print(json.dumps(diag, ensure_ascii=False, indent=2))
    else:
        print(f"BOOTSTRAP_STATUS={diag['status']}")
        print(f"layer_version      : {diag['verification_layer_version']}")
        print(f"project            : {diag['project']}")
        for f in diag["support_files"]:
            print(f"  {f['status']:9s} {f['name']} -> {f['destination']}")
        print(f"dependency         : {diag['dependency'].get('action')} "
              f"{UIAUTOMATOR_MODULE}:{UIAUTOMATOR_VERSION}")
        for d in diag["drift"]:
            print(f"INTEGRATION_DRIFT  {d['file']}: {d['reason']}")
        for e in diag["errors"]:
            print(f"ERROR              {e}")

    if diag["status"] == "INVALID_PROJECT":
        return EXIT_USAGE
    if diag["status"] == "INTEGRATION_DRIFT":
        return EXIT_DRIFT
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
