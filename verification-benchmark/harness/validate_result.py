#!/usr/bin/env python3
"""CLI: validate one or more benchmark-run.json files against harness/schema.py.

  validate_result.py <file.json> [more.json ...]

Prints PASS/FAIL per file and exits non-zero if any file is invalid.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: validate_result.py <benchmark-run.json> [...]", file=sys.stderr)
        return 2
    bad = 0
    for name in argv[1:]:
        errs = schema.validate_file(Path(name))
        if errs:
            bad += 1
            print(f"FAIL {name}")
            for e in errs:
                print(f"  - {e}")
        else:
            print(f"PASS {name}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
