#!/usr/bin/env python3
"""Dry-run the contract-package gate over every existing READY package.

Not part of the unit suite (no ``test_`` prefix): it depends on repository
state and on the compiler validator, so it is run explicitly.

It never executes a contract. ``contract_executor.gate`` is a pure validation:
real path + project containment + artifacts + manifest integrity + manifest
hash + READY + the existing deterministic compiler validator. The validator is
applied to a byte-for-byte SNAPSHOT, so the frozen packages are not mutated.

    python3 tests/dryrun_ready_packages.py
"""

from __future__ import annotations

import sys
from pathlib import Path

BRIDGE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BRIDGE_DIR))

import contract_executor as ce  # noqa: E402

CONTRACTS_DIR = ce.PROJECT_ROOT / "reports" / "contracts"


def main() -> int:
    if not CONTRACTS_DIR.is_dir():
        print("no contracts dir at %s" % CONTRACTS_DIR)
        return 0

    rows = []
    for package in sorted(p for p in CONTRACTS_DIR.iterdir() if p.is_dir()):
        if not (package / "READY.json").is_file():
            continue
        try:
            sha = ce.manifest_sha256(package)
        except OSError as exc:
            rows.append((package.name, "NO_MANIFEST", str(exc)))
            continue
        try:
            result = ce.gate(str(package), sha)
            rows.append((package.name, "GATE_PASS",
                         "validator=%s %s" % (result["validator"]["status"],
                                              result["validator"]["summary"])))
        except ce.GateError as exc:
            rows.append((package.name, "GATE_REJECT:%s" % exc.code, exc.message))

    width = max((len(r[0]) for r in rows), default=0)
    for name, verdict, detail in rows:
        print("%-*s  %-24s  %s" % (width, name, verdict, detail[:160]))
    print("\npackages inspected: %d" % len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
