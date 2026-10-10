#!/usr/bin/env python3
"""KeepLab decoupling audit.

The production Verification Layer must not hardcode KeepLab identity or business semantics.
Only `examples/`, `challengers/`, `reference-replay/`, `tests/` and `.runs/` may mention them.
"""
import re
import sys
import unittest
from pathlib import Path

VERIFY = Path(__file__).resolve().parents[2]

EXCLUDE_DIRS = {"examples", "challengers", "reference-replay", "tests", ".runs", ".state", "__pycache__"}

# Strong, project-specific tokens only (never bare generic words in prose).
FORBIDDEN = {
    "keeplab_package": re.compile(r"com\.keeplab"),
    "keeplab_db": re.compile(r"keeplab\.db"),
    "keeplab_fixture": re.compile(r"VC-J[123]-"),
    "harden_runid": re.compile(r"HARDEN-[BC]-"),
    "keeplab_business_literal": re.compile(r'"(Work|Archive|Trash)"'),
}

TEXT_SUFFIXES = {".sh", ".py", ".json", ".md", ".kt", ".yaml", ".yml"}


def scan() -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {k: [] for k in FORBIDDEN}
    for path in sorted(VERIFY.rglob("*")):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        if any(part in EXCLUDE_DIRS for part in path.relative_to(VERIFY).parts):
            continue
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        for name, rx in FORBIDDEN.items():
            for i, line in enumerate(text.splitlines(), 1):
                if rx.search(line):
                    hits[name].append(f"{path.relative_to(VERIFY)}:{i}: {line.strip()}")
    return hits


class TestDecouplingAudit(unittest.TestCase):
    def test_no_keeplab_hardcodes_in_production(self):
        hits = scan()
        offenders = {k: v for k, v in hits.items() if v}
        self.assertEqual(offenders, {}, f"KeepLab hardcodes found in production tree:\n{offenders}")


if __name__ == "__main__":
    hits = scan()
    bad = {k: v for k, v in hits.items() if v}
    if bad:
        print("DECOUPLING_AUDIT=FAIL")
        for k, v in bad.items():
            for line in v:
                print(f"  {k}: {line}")
        sys.exit(1)
    print("DECOUPLING_AUDIT=PASS")
