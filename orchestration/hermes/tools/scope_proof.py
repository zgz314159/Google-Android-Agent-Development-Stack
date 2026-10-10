#!/usr/bin/env python3
"""Deterministic scope / hash / metric proof utility (STACK-SIMPLIFICATION-S2-WAVE1A-001, TASK-04).

ONE reusable checked-in utility that replaces the per-phase scratch proof/hash/report scripts
(``m4_hashes.py``, ``m4_verify_manifest.py``, ``m4_postrun_proof.py`` style). It reuses the
Specification Compiler's hashing and path helpers instead of reimplementing SHA256 or path logic:

    specification/compiler/spec_lib.py  ->  sha256_file, load_json, write_json,
                                            rel, is_relative_within, overlaps

It is deliberately NOT a Guard: it takes no allow/block decision, is never wired as a hook and
duplicates no Contract Guard behaviour. It performs NO secret/credential detection — a
secret/security scanner is explicitly deferred to mature tooling (Hermes native security /
Semgrep / Gitleaks). Every output is deterministic JSON (sorted keys, stable ordering).

Subcommands
-----------
  hash     --root DIR --paths PATHS.json --out OUT.json
           SHA256 (and size) of a declared file list, keyed by project-relative path.

  compare  --before A.json --after B.json --out OUT.json
           Deterministic diff of two flat string->scalar maps (as produced by ``hash`` /
           ``metrics``): equal / changed / only_before / only_after.

  metrics  --run RUN.json --keys KEYS.json --out OUT.json
           Extract declared dotted key paths (e.g. ``phase_totals.T7.wall_seconds``) from a run
           JSON so two runs can be compared with ``compare``.

  scope    --contract implementation-contract.json --changed CHANGED.json --source-root DIR --out OUT.json
           Classify a changed-file list against the frozen contract's allowed_paths /
           forbidden_paths (prefix semantics) and report the changed scope summary.

Exit codes: 0 ok, 2 usage/IO error.
"""

from __future__ import annotations

import argparse
import os
import sys

_COMPILER = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))),
    "specification", "compiler")
sys.path.insert(0, _COMPILER)

from spec_lib import (  # noqa: E402  (reused, not reimplemented)
    is_relative_within,
    load_json,
    overlaps,
    rel,
    sha256_file,
    write_json,
)


def _norm(path: str) -> str:
    return path.replace("\\", "/").rstrip("/")


def _as_list(value) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        if isinstance(value.get("paths"), list):
            return value["paths"]
        if isinstance(value.get("files"), list):
            return value["files"]
        if isinstance(value.get("changed"), list):
            return value["changed"]
    raise ValueError("expected a JSON list, or an object with a 'paths'/'files'/'changed' list")


# --------------------------------------------------------------------------- #
# subcommands
# --------------------------------------------------------------------------- #
def cmd_hash(args) -> int:
    root = os.path.abspath(args.root)
    out = {}
    for entry in _as_list(load_json(args.paths)):
        raw = str(entry)
        full = raw if os.path.isabs(raw) else os.path.join(root, raw)
        full = os.path.normpath(full)
        key = rel(full, root) if full.startswith(root + os.sep) or full == root else _norm(full)
        record = {"sha256": sha256_file(full), "exists": True, "size": os.path.getsize(full)}
        out[key] = record
    write_json(args.out, {"algorithm": "sha256", "root": root, "count": len(out), "files": out})
    print("HASH=WROTE files=%d out=%s" % (len(out), args.out))
    return 0


def _flatten(doc) -> dict:
    """Map of key -> scalar; a nested {'sha256': ...} record is reduced to its digest."""
    data = doc.get("files", doc) if isinstance(doc, dict) else {}
    flat = {}
    for key, value in data.items():
        if isinstance(value, dict) and "sha256" in value:
            flat[key] = value["sha256"]
        elif isinstance(value, (str, int, float, bool)) or value is None:
            flat[key] = value
        else:
            flat[key] = str(value)
    return flat


def cmd_compare(args) -> int:
    before = _flatten(load_json(args.before))
    after = _flatten(load_json(args.after))
    keys = sorted(set(before) | set(after))
    equal, changed, only_before, only_after = [], [], [], []
    for key in keys:
        if key not in before:
            only_after.append(key)
        elif key not in after:
            only_before.append(key)
        elif before[key] == after[key]:
            equal.append(key)
        else:
            changed.append({"path": key, "before": before[key], "after": after[key]})
    write_json(args.out, {
        "identical": not changed and not only_before and not only_after,
        "counts": {"equal": len(equal), "changed": len(changed),
                   "only_before": len(only_before), "only_after": len(only_after)},
        "equal": equal, "changed": changed, "only_before": only_before, "only_after": only_after,
    })
    print("COMPARE equal=%d changed=%d only_before=%d only_after=%d identical=%s"
          % (len(equal), len(changed), len(only_before), len(only_after),
             not changed and not only_before and not only_after))
    return 0


def _resolve(doc, dotted: str):
    node = doc
    for part in dotted.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        elif isinstance(node, list) and part.isdigit() and int(part) < len(node):
            node = node[int(part)]
        else:
            return None
    return node if isinstance(node, (str, int, float, bool)) or node is None else str(node)


def cmd_metrics(args) -> int:
    doc = load_json(args.run)
    values = {key: _resolve(doc, key) for key in _as_list(load_json(args.keys))}
    write_json(args.out, {"source": os.path.abspath(args.run), "count": len(values), "files": values})
    print("METRICS=WROTE keys=%d out=%s" % (len(values), args.out))
    return 0


def _inside(rel_path: str, pattern: str) -> bool:
    p = _norm(pattern)
    if not p:
        return False
    return rel_path == p or rel_path.startswith(p + "/")


def cmd_scope(args) -> int:
    contract = load_json(args.contract)
    allowed = [_norm(p) for p in contract.get("allowed_paths", [])]
    forbidden = [_norm(p) for p in contract.get("forbidden_paths", [])]
    source_root = os.path.abspath(args.source_root)
    changed = [str(p) for p in _as_list(load_json(args.changed))]

    allowed_hits, forbidden_hits, unclassified, malformed = [], [], [], []
    for raw in changed:
        if not is_relative_within(raw):
            malformed.append(raw)  # absolute or '..' escaping: not a project-relative path
            continue
        relp = _norm(raw)
        if any(_inside(relp, p) for p in forbidden):
            forbidden_hits.append(relp)
        elif any(_inside(relp, p) for p in allowed):
            allowed_hits.append(relp)
        else:
            unclassified.append(relp)

    overlap_pairs = sorted(
        {"%s <-> %s" % (a, f) for a in allowed for f in forbidden if overlaps(a, f)}
    )
    write_json(args.out, {
        "source_root": source_root,
        "contract": contract.get("contract_id"),
        "counts": {"changed": len(changed), "allowed": len(allowed_hits),
                   "forbidden": len(forbidden_hits), "unclassified": len(unclassified),
                   "malformed": len(malformed)},
        "within_allowed_paths": not forbidden_hits and not unclassified,
        "allowed": sorted(allowed_hits),
        "forbidden": sorted(forbidden_hits),
        "unclassified": sorted(unclassified),
        "malformed": sorted(malformed),
        "allowed_forbidden_overlaps": overlap_pairs,
    })
    print("SCOPE allowed=%d forbidden=%d unclassified=%d within_allowed_paths=%s"
          % (len(allowed_hits), len(forbidden_hits), len(unclassified),
             not forbidden_hits and not unclassified))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="deterministic scope/hash/metric proof utility")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("hash", help="sha256 of a declared file list")
    p.add_argument("--root", required=True)
    p.add_argument("--paths", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_hash)

    p = sub.add_parser("compare", help="deterministic diff of two flat maps")
    p.add_argument("--before", required=True)
    p.add_argument("--after", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_compare)

    p = sub.add_parser("metrics", help="extract declared key paths from a run JSON")
    p.add_argument("--run", required=True)
    p.add_argument("--keys", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_metrics)

    p = sub.add_parser("scope", help="classify a changed-file list against the contract")
    p.add_argument("--contract", required=True)
    p.add_argument("--changed", required=True)
    p.add_argument("--source-root", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_scope)

    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (OSError, ValueError, KeyError) as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
