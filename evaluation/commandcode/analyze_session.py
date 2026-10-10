#!/usr/bin/env python3
"""Command Code session analyzer - v0.2 Minimal Evaluation Core CLI.

Mode A - explicit session:
  python3 evaluation/commandcode/analyze_session.py \\
    --session /path/to/session.jsonl \\
    --run-id PRE-HARBOR-BASELINE-001 --project KeepLab \\
    --output /mnt/AndroidDev/Projects/_evaluation/v0.2-calibration/keeplab

Mode B - auto-locate (deterministic, fails on 0 or ambiguous matches):
  python3 evaluation/commandcode/analyze_session.py \\
    --project-cwd /mnt/AndroidDev/Projects/KeepLab-Relay \\
    --prompt-contains "KeepLab Relay Benchmark" \\
    --run-id PRE-HARBOR-BASELINE-001 --project KeepLab --output <dir>

Always emits exactly three artifacts: run.json, phase-timeline.csv, analysis.md.
Zero LLM calls, zero network calls, read-only against the source JSONL.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core  # noqa: E402


def build_parser():
    p = argparse.ArgumentParser(description="Command Code Evaluation Core v0.2")
    p.add_argument("--session", help="path to a Command Code session .jsonl (mode A)")
    p.add_argument("--project-cwd", help="project cwd to auto-locate a session (mode B)")
    p.add_argument("--prompt-contains", help="substring that must appear in the task prompt")
    p.add_argument("--run-id", required=True, help="run identifier")
    p.add_argument("--project", default=None, help="project label")
    p.add_argument("--workflow", default=None, help="workflow label (e.g. Archon+Factory)")
    p.add_argument("--result", default=None, choices=["PASS", "FAIL", "UNKNOWN"],
                   help="override result detection")
    p.add_argument("--output", required=True, help="output directory")
    p.add_argument("--projects-root", default=None,
                   help="override ~/.commandcode/projects for mode B (testing)")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if not args.session and not args.project_cwd:
        print("ERROR: provide either --session (mode A) or --project-cwd (mode B)", file=sys.stderr)
        return 2

    session_path = args.session
    if not session_path:
        if not args.prompt_contains:
            print("ERROR: mode B requires --prompt-contains (no guessing allowed)", file=sys.stderr)
            return 2
        try:
            candidates, reasons = core.locate_sessions(
                args.project_cwd, args.prompt_contains, args.projects_root
            )
        except core.SessionLocateError as exc:
            print(f"SESSION_LOCATE_FAIL: {exc}", file=sys.stderr)
            return 4
        if len(candidates) == 0:
            print("SESSION_LOCATE_FAIL: 0 candidates matched cwd + prompt", file=sys.stderr)
            for r in reasons[:20]:
                print(f"  candidate rejected: {r}", file=sys.stderr)
            return 4
        if len(candidates) > 1:
            print("SESSION_LOCATE_FAIL: multiple candidates, cannot confirm uniquely:", file=sys.stderr)
            for c in candidates:
                print(f"  {c}", file=sys.stderr)
            return 4
        session_path = candidates[0]

    project = args.project or os.path.basename(os.path.abspath(args.project_cwd or "")) or "unknown"

    t0 = time.perf_counter()
    try:
        run = core.analyze(
            session_path=session_path,
            run_id=args.run_id,
            project=project,
            workflow=args.workflow,
            prompt_contains=args.prompt_contains,
            explicit_result=args.result,
            projects_root=args.projects_root,
        )
    except core.UnsupportedSchema as exc:
        print(f"UNSUPPORTED_SCHEMA: {exc.version}", file=sys.stderr)
        return 3
    except core.EvaluationError as exc:
        print(f"EVALUATION_ERROR: {exc}", file=sys.stderr)
        return 2

    core.write_outputs(run, args.output)
    elapsed = time.perf_counter() - t0

    tr = run["tokens_raw"]
    print(f"run_id            : {run['run_id']}")
    print(f"session           : {run['source']['jsonl_path']}")
    print(f"schema_version    : {run['schema_version']}")
    print(f"task_wall_sec     : {run['clocks']['task_wall_sec']}")
    print(f"session_wall_sec  : {run['clocks']['session_wall_sec']}")
    print(f"reconciliation    : {'PASS' if run['reconciliation']['ok'] else 'FAIL'}"
          f" (delta {run['reconciliation']['delta_sec']} s)")
    print(f"unknown_ratio     : {run['unknown_ratio']} ({run['observability_quality']})")
    print(f"requests          : {tr['requests']}")
    print(f"input_tokens      : {tr['input']:,}")
    print(f"output_tokens     : {tr['output']:,}")
    print(f"cache_read_tokens : {tr['cache_read']:,}")
    print(f"cost              : ${tr['cost']:.4f}")
    print(f"logical_failures  : {len(run['logical_failures'])}  repairs: {len(run['repairs'])}")
    print(f"eval_wall_seconds : {elapsed:.3f}")
    print(f"outputs           : {args.output}/run.json, phase-timeline.csv, analysis.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
