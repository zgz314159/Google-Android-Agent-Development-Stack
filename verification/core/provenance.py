#!/usr/bin/env python3
"""APK provenance enforcement + record.

  provenance.py --app <apk> [--test <apk>] [--expected-app <sha256>]
                [--expected-test <sha256>] [--verification-layer-version V]
                [--runner-version V] [--json <out>] [--require-test]

Computes sha256 of the target APK(s); if an expected hash is supplied and differs, prints
APK_SHA_MISMATCH and exits non-zero (STOP). Records the hashes so every result carries its
provenance. Never rebuilds or replaces an APK.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--app", required=True)
    p.add_argument("--test", default=None)
    p.add_argument("--expected-app", default=None)
    p.add_argument("--expected-test", default=None)
    p.add_argument("--verification-layer-version", default="unknown")
    p.add_argument("--runner-version", default="unknown")
    p.add_argument("--json", dest="json_out", default=None)
    p.add_argument("--require-test", action="store_true")
    args = p.parse_args()

    app = Path(args.app)
    if not app.is_file():
        print(f"APK_MISSING={app}", file=sys.stderr)
        return 2
    app_sha = sha256(app)
    rec = {
        "apk_sha256": app_sha,
        "apk_size_bytes": app.stat().st_size,
        "apk_path": str(app),
        "verification_layer_version": args.verification_layer_version,
        "runner_version": args.runner_version,
    }
    if args.expected_app and app_sha != args.expected_app:
        print(f"APK_SHA_MISMATCH=expected:{args.expected_app} actual:{app_sha}", file=sys.stderr)
        return 3

    if args.test:
        test = Path(args.test)
        if not test.is_file():
            if args.require_test:
                print(f"TEST_APK_MISSING={test}", file=sys.stderr)
                return 2
        else:
            test_sha = sha256(test)
            rec["test_apk_sha256"] = test_sha
            rec["test_apk_size_bytes"] = test.stat().st_size
            if args.expected_test and test_sha != args.expected_test:
                print(f"TEST_APK_SHA_MISMATCH=expected:{args.expected_test} actual:{test_sha}",
                      file=sys.stderr)
                return 3
    elif args.require_test:
        print("TEST_APK_MISSING=no --test provided", file=sys.stderr)
        return 2

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(rec, indent=2))

    print(f"APK_SHA256={app_sha}")
    if "test_apk_sha256" in rec:
        print(f"TEST_APK_SHA256={rec['test_apk_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
