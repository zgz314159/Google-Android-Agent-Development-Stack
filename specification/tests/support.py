"""Shared helpers for the P0 self-tests. Not a test module itself."""

import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
COMPILER = os.path.abspath(os.path.join(HERE, os.pardir, "compiler"))
FIXTURES = os.path.join(HERE, "fixtures")
if COMPILER not in sys.path:
    sys.path.insert(0, COMPILER)

import build_contract  # noqa: E402
import hash_manifest  # noqa: E402
import spec_lib  # noqa: E402
import validate_package  # noqa: E402


def fresh_package(tmp_dir: str) -> str:
    """Copy the valid fixture package into tmp_dir/pkg and return its path."""
    pkg = os.path.join(tmp_dir, "pkg")
    shutil.copytree(os.path.join(FIXTURES, "valid_package"), pkg)
    return pkg


def run_pipeline(pkg: str, project_root: str | None = None) -> dict:
    """hash_manifest -> build_contract -> validate_package; return the report."""
    manifest, missing = hash_manifest.build_manifest(pkg)
    assert not missing, f"fixture unexpectedly missing artifacts: {missing}"
    spec_lib.write_json(os.path.join(pkg, "manifest.json"), manifest)
    contract = build_contract.build(pkg)
    spec_lib.write_json(os.path.join(pkg, "implementation-contract.json"), contract)
    return validate_package.validate(pkg, project_root=project_root or os.path.join(pkg, "project"))


def rule_ids(report: dict) -> set:
    return {error["rule_id"] for error in report["errors"]}


def write(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def append(path: str, text: str) -> None:
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(text)


def read(path: str) -> str:
    return spec_lib.read_text(path)
