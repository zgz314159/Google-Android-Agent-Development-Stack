#!/usr/bin/env python3
"""Evaluation Core v0.2.3 - Auto-Finalizer.

Deterministic, offline, observer-only. Wraps the *same* deterministic core used
by analyze_session.py and publishes a complete Evaluation artifact set into the
standard location:

    <output-root>/<Project>/<RUN_ID>/
    ├── run.json
    ├── phase-timeline.csv
    ├── analysis.md
    └── finalization.json

Guarantees:
  * zero LLM calls, zero network calls;
  * read-only against the raw JSONL (never copied, never modified);
  * atomic output: builds <RUN_ID>.tmp/ then renames it into place, so an
    interrupted run never leaves a half-written Evaluation;
  * idempotent: a second trigger for the same session + run id returns
    ALREADY_FINALIZED unless --force;
  * task outcome and evaluation outcome are isolated: an Evaluation failure is
    reported as its own failure and never rewrites the task outcome.

This module does NOT enter the observed task's execution/timing path.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core  # noqa: E402

def _evaluation_output_default() -> str:
    _repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    _lib = os.path.join(_repo, "scripts", "lib")
    if _lib not in sys.path:
        sys.path.insert(0, _lib)
    import stack_paths  # noqa: PLC0415

    return str(stack_paths.evaluation_output_root())


DEFAULT_OUTPUT_ROOT = os.environ.get("HERMES_EVALUATION_OUTPUT_ROOT") or _evaluation_output_default()
FINALIZATION_FILE = "finalization.json"

# The P0B-EVAL-GUARD-FIX proof layer lives in the Hermes evaluation adapter (the only
# layer the frozen P0B-CLOSE contract allows this correction to be implemented in).
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_FAILURE_EVIDENCE_DIR = os.path.join(_REPO_ROOT, "orchestration", "hermes", "evaluation_adapter")
_failure_evidence_cache = None


def _load_failure_evidence():
    """Lazy import of the structured failure-evidence proof layer (P0B-EVAL-GUARD-FIX)."""
    global _failure_evidence_cache
    if _failure_evidence_cache is None:
        if _FAILURE_EVIDENCE_DIR not in sys.path:
            sys.path.insert(0, _FAILURE_EVIDENCE_DIR)
        import failure_evidence  # noqa: E402
        _failure_evidence_cache = failure_evidence
    return _failure_evidence_cache


def _calls_by_row(session_path: str, prompt_contains: str = None) -> dict:
    """Re-index the session's calls exactly as ``core.analyze`` does (read-only).

    ``core.analyze`` does not return its ``Call`` objects, so the correction layer re-derives
    them with the frozen core's own loaders. Same input, same functions => same calls.
    """
    data = core.load_session(session_path)
    start, end, _matched = core.resolve_task_window(data.rows, prompt_contains)
    calls, _by_id, _origins = core.index_calls(data.rows, list(range(start, end)))
    by_row = defaultdict(list)
    for call in calls:
        by_row[call.row_index].append(call)
    return by_row

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_EVAL_FAIL = 6
EXIT_INCOMPLETE = 5


def _utcnow():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def slugify(text: str, maxlen: int = 40) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", (text or "").strip()).strip("-").upper()
    return (s[:maxlen].rstrip("-")) or "TASK"


def make_run_id(project: str, prompt_head: str, task_start_iso: str) -> str:
    dt = core.parse_ts(task_start_iso)
    stamp = dt.astimezone(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{slugify(project, 24)}-{slugify(prompt_head, 40)}-{stamp}"


def _load_finalization(final_dir: str):
    path = os.path.join(final_dir, FINALIZATION_FILE)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _publish(tmp_dir: str, final_dir: str, force: bool) -> None:
    if os.path.exists(final_dir):
        if not force:
            raise FileExistsError(final_dir)
        shutil.rmtree(final_dir)
    os.replace(tmp_dir, final_dir)


def _apply_identity(run: dict, identity: dict) -> None:
    """Overlay a source's PERSISTED identity/usage onto the core's analysis output (P0B-CLOSE).

    Only values the source actually stored are written; a missing field is left exactly as the
    frozen core produced it. Nothing is inferred, and no phase classification is touched — only
    identity and usage attribution.
    """
    if not isinstance(identity, dict):
        return
    agent_host = identity.get("agent_host")
    if isinstance(agent_host, str) and agent_host.strip():
        run["agent_host"] = agent_host.strip()

    model = identity.get("model")
    source = run.get("source")
    if isinstance(model, str) and model.strip() and isinstance(source, dict):
        model = model.strip()
        run["model"] = model
        source["model"] = model
        models = list(source.get("models") or [])
        if model not in models:
            models.insert(0, model)
        source["models"] = models

    tokens = run.get("tokens_raw")
    if not isinstance(tokens, dict):
        return
    provider = identity.get("provider")
    if isinstance(provider, str) and provider.strip():
        tokens["provider"] = provider.strip()
    if isinstance(source, dict) and source.get("models"):
        tokens["models"] = list(source["models"])

    usage = identity.get("usage") if isinstance(identity.get("usage"), dict) else {}
    for key in ("requests", "input", "output", "cache_read", "cache_write", "reasoning"):
        value = usage.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            tokens[key] = value
    cost = usage.get("cost")
    if isinstance(cost, (int, float)) and not isinstance(cost, bool):
        tokens["cost"] = round(float(cost), 6)
    if usage.get("cost_status") is not None:
        tokens["cost_status"] = usage["cost_status"]
    if identity.get("usage_provenance"):
        tokens["provenance"] = identity["usage_provenance"]
    run["identity"] = {
        "agent_host": identity.get("agent_host"),
        "provider": identity.get("provider"),
        "model": identity.get("model"),
        "agent_product": identity.get("agent_product"),
        "usage_provenance": identity.get("usage_provenance"),
        "tool_name_map": identity.get("tool_name_map"),
        "not_available": identity.get("not_available"),
    }


def _apply_failure_evidence(run: dict, session_path: str, prompt_contains: str = None) -> dict:
    """Apply the P0B-EVAL-GUARD-FIX proof layer to one analysis result.

    Returns the audit summary. An internal error is reported as ``applied: False`` rather than
    raised: this is an observer-side correction and must never turn an Evaluation into a crash.
    The failure is still recorded in the published artifacts, so it is never silent.
    """
    try:
        failure_evidence = _load_failure_evidence()
        summary = failure_evidence.correct_run(run, _calls_by_row(session_path, prompt_contains))
        return {"applied": True, **summary}
    except Exception as exc:  # noqa: BLE001 - observation failure must stay isolated
        summary = {"applied": False, "error": f"{type(exc).__name__}: {exc}",
                   "failures_before": len(run.get("logical_failures") or []),
                   "failures_after": len(run.get("logical_failures") or [])}
        run["failure_evidence_correction"] = summary
        return summary


def finalize(
    session_path: str = None,
    project_cwd: str = None,
    prompt_contains: str = None,
    run_id: str = None,
    project: str = None,
    workflow: str = None,
    explicit_result: str = None,
    output_root: str = None,
    projects_root: str = None,
    force: bool = False,
    stable_seconds: float = 0.0,
    require_completion: bool = True,
    execution_source: dict = None,
    identity: dict = None,
    failure_evidence: bool = False,
) -> dict:
    """Run the finalizer. Never raises: returns a diagnostics dict.

    Evaluation failures are reported in ``evaluation_outcome`` and never change
    ``task_outcome`` (which reflects the observed task, not this tool).

    ``execution_source`` is an ADDITIVE, optional provenance block (S1.1). When
    omitted the published ``finalization.json`` is byte-identical to v0.2.3, so
    existing Command Code consumers are unaffected.

    ``identity`` is a second ADDITIVE, optional block (P0B-CLOSE) carrying the executed
    agent's real identity and persisted usage: ``agent_host``, ``provider``, ``model`` and
    ``usage{requests,input,output,cache_read,cache_write,reasoning,cost,cost_status}``.
    It is applied to the analysis output *after* ``core.analyze`` and *before*
    ``core.write_outputs``, i.e. it never changes the frozen core's semantics; it only
    supplies values the source genuinely stores. Omitted => output is byte-identical to
    the pre-P0B-CLOSE behaviour for every existing caller.

    ``failure_evidence`` is a third ADDITIVE, optional switch (P0B-EVAL-GUARD-FIX). When true,
    every logical failure the frozen core derived from *text* is re-checked against the
    operations' *structured execution state* (exit status, tool status, provider error) and a
    failure whose every underlying operation is proven successful is removed as a false
    positive (see ``orchestration/hermes/evaluation_adapter/failure_evidence.py``). The switch
    can only ever remove failures, never add one, and it leaves phases, clocks, tokens, the task
    window and identity attribution untouched. Default False => byte-identical to v0.2.3.
    """
    output_root = output_root or DEFAULT_OUTPUT_ROOT
    diag = {
        "run_id": run_id,
        "session_id": None,
        "project": project,
        "jsonl_path": None,
        "task_outcome": "UNKNOWN",
        "evaluation_outcome": "PENDING",
        "evaluation_error": None,
        "task_completion_detected": False,
        "finalized": False,
        "already_finalized": False,
        "evaluation_core_version": core.CORE_VERSION,
        "raw_jsonl_modified": False,
        "output_dir": None,
        "generated_utc": _utcnow(),
        "task_identity": {},
        "failure_evidence_correction": None,
    }

    tmp_dir = None
    try:
        # ---- 1. locate the raw session ------------------------------------ #
        if not session_path:
            if not (project_cwd and prompt_contains):
                diag["evaluation_outcome"] = "FAIL"
                diag["evaluation_error"] = "need --session OR (--project-cwd + --prompt-contains)"
                return diag
            candidates, reasons = core.locate_sessions(project_cwd, prompt_contains, projects_root)
            if len(candidates) != 1:
                diag["evaluation_outcome"] = "FAIL"
                diag["evaluation_error"] = (
                    f"session locate failed: {len(candidates)} candidates "
                    f"(rejected={len(reasons)})"
                )
                return diag
            session_path = candidates[0]
        session_path = os.path.abspath(session_path)
        diag["jsonl_path"] = session_path

        # ---- 2. stability pre-check ---------------------------------------- #
        st0 = os.stat(session_path)
        if stable_seconds > 0 and (time.time() - st0.st_mtime) < stable_seconds:
            diag["evaluation_outcome"] = "FAIL"
            diag["evaluation_error"] = (
                f"session JSONL is not stable yet (mtime age "
                f"{round(time.time() - st0.st_mtime, 1)}s < {stable_seconds}s)"
            )
            return diag

        # ---- 3. deterministic analysis (same core as analyze_session.py) --- #
        run = core.analyze(
            session_path=session_path,
            run_id=run_id or "PENDING",
            project=project or os.path.basename(os.getcwd()) or "unknown",
            workflow=workflow,
            prompt_contains=prompt_contains,
            explicit_result=explicit_result,
            projects_root=projects_root,
        )
        src = run["source"]
        diag["session_id"] = src["session_id"]
        # P0B-CLOSE: apply the source's persisted identity/usage BEFORE anything is written.
        _apply_identity(run, identity)
        # P0B-EVAL-GUARD-FIX: prove failure from structured execution state before a text-only
        # failure classification is trusted. Additive and optional; skipped by default.
        if failure_evidence:
            diag["failure_evidence_correction"] = _apply_failure_evidence(
                run, session_path, prompt_contains)
        diag["jsonl_path"] = src["jsonl_path"]
        completion = run["task_completion"]
        diag["task_completion_detected"] = completion["task_completion_detected"]
        diag["task_outcome"] = "COMPLETED" if completion["task_completion_detected"] else "INCOMPLETE"

        project = core.discover_project_identity(src.get("cwd"), project)
        prompt_head = src["prompt_match"].get("prompt_head") or "task"
        if not run_id:
            run_id = make_run_id(project, prompt_head, src["task_prompt_timestamp"])
        run["run_id"] = run_id
        run["project"] = project
        diag["run_id"] = run_id
        diag["project"] = project
        diag["task_identity"] = {
            "prompt_contains": prompt_contains,
            "prompt_head": prompt_head,
            "cwd": src.get("cwd"),
            "task_start": src["task_prompt_timestamp"],
            "task_end": src["task_end_timestamp"],
            "final_session_timestamp": src["final_session_timestamp"],
            "sha256": src["sha256"],
        }

        final_dir = os.path.join(output_root, project, run_id)
        diag["output_dir"] = final_dir

        # ---- 4. idempotency ----------------------------------------------- #
        existing = _load_finalization(final_dir)
        if existing and existing.get("finalized") and not force:
            diag["evaluation_outcome"] = "ALREADY_FINALIZED"
            diag["already_finalized"] = True
            diag["finalized"] = True
            return diag

        # ---- 5. refuse to publish an unfinished task ---------------------- #
        if require_completion and not diag["task_completion_detected"]:
            diag["evaluation_outcome"] = "INCOMPLETE"
            diag["evaluation_error"] = "task completion not detected; not publishing"
            return diag

        # ---- 6. atomic write into <run-id>.tmp/ --------------------------- #
        tmp_dir = final_dir + ".tmp"
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
        core.write_outputs(run, tmp_dir)

        finalization = {
            "run_id": run_id,
            "session_id": src["session_id"],
            "project": project,
            "task_completion_detected": diag["task_completion_detected"],
            "finalized": True,
            "evaluation_core_version": core.CORE_VERSION,
            "raw_jsonl_modified": False,
            "task_outcome": diag["task_outcome"],
            "evaluation_outcome": "SUCCESS",
            "task_identity": diag["task_identity"],
            "clocks": {
                "task_elapsed_wall_sec": run["clocks"]["task_elapsed_wall_sec"],
                "agent_owned_wall_sec": run["clocks"]["agent_owned_wall_sec"],
                "interactive_user_wait_sec": run["clocks"]["interactive_user_wait_sec"],
                "unattributed_idle_wall_sec": run["clocks"]["unattributed_idle_wall_sec"],
                "phase_share_denominator": "agent_owned_wall",
            },
            "result": run["result"],
            "generated_utc": _utcnow(),
        }
        if execution_source:
            finalization["execution_source"] = execution_source
        if isinstance(identity, dict):
            finalization["identity"] = identity
        # P0B-EVAL-GUARD-FIX: the false-positive audit trail of the proof layer (omitted when
        # the switch is off, so existing callers keep a byte-identical finalization.json).
        if diag.get("failure_evidence_correction") is not None:
            finalization["failure_evidence_correction"] = diag["failure_evidence_correction"]
        with open(os.path.join(tmp_dir, FINALIZATION_FILE), "w", encoding="utf-8") as f:
            json.dump(finalization, f, ensure_ascii=False, indent=2)

        # ---- 7. verify the source did not change during analysis ---------- #
        st1 = os.stat(session_path)
        if (st0.st_size, st0.st_mtime_ns) != (st1.st_size, st1.st_mtime_ns):
            shutil.rmtree(tmp_dir, ignore_errors=True)
            diag["evaluation_outcome"] = "FAIL"
            diag["evaluation_error"] = "raw JSONL changed during analysis; discarded tmp output"
            return diag

        # ---- 8. atomic publish -------------------------------------------- #
        _publish(tmp_dir, final_dir, force)
        tmp_dir = None
        diag["finalized"] = True
        diag["evaluation_outcome"] = "SUCCESS"
        diag["raw_jsonl_modified"] = False
        return diag

    except Exception as exc:  # noqa: BLE001 - evaluation failure must be isolated
        if tmp_dir and os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)
        diag["evaluation_outcome"] = "FAIL"
        diag["evaluation_error"] = f"{type(exc).__name__}: {exc}"
        diag["finalized"] = False
        return diag


def build_parser():
    p = argparse.ArgumentParser(description="Evaluation Core v0.2.3 Auto-Finalizer")
    p.add_argument("--session", help="path to a Command Code session .jsonl")
    p.add_argument("--project-cwd", help="project cwd to auto-locate a session")
    p.add_argument("--prompt-contains", help="substring that must appear in the task prompt")
    p.add_argument("--run-id", default=None, help="run id (auto-generated if omitted)")
    p.add_argument("--project", default=None, help="project label")
    p.add_argument("--workflow", default=None)
    p.add_argument("--result", default=None, choices=["PASS", "FAIL", "UNKNOWN"])
    p.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    p.add_argument("--projects-root", default=None)
    p.add_argument("--stable-seconds", type=float, default=0.0,
                   help="require the JSONL mtime be at least this old")
    p.add_argument("--allow-incomplete", action="store_true",
                   help="publish even if task completion was not detected")
    p.add_argument("--force", action="store_true", help="overwrite an existing finalization")
    p.add_argument("--failure-evidence", action="store_true",
                   help="P0B-EVAL-GUARD-FIX: drop logical failures disproven by the structured "
                        "execution state of the operations behind them (false-positive correction)")
    p.add_argument("--json", action="store_true", help="print the raw diagnostics dict")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    diag = finalize(
        session_path=args.session,
        project_cwd=args.project_cwd,
        prompt_contains=args.prompt_contains,
        run_id=args.run_id,
        project=args.project,
        workflow=args.workflow,
        explicit_result=args.result,
        output_root=args.output_root,
        projects_root=args.projects_root,
        force=args.force,
        stable_seconds=args.stable_seconds,
        require_completion=not args.allow_incomplete,
        failure_evidence=args.failure_evidence,
    )

    if args.json:
        print(json.dumps(diag, ensure_ascii=False, indent=2))
    else:
        print(f"run_id                  : {diag['run_id']}")
        print(f"session_id              : {diag['session_id']}")
        print(f"task_outcome            : {diag['task_outcome']}")
        print(f"evaluation_outcome      : {diag['evaluation_outcome']}")
        print(f"task_completion_detected: {diag['task_completion_detected']}")
        print(f"finalized               : {diag['finalized']}")
        print(f"raw_jsonl_modified      : {diag['raw_jsonl_modified']}")
        print(f"output_dir              : {diag['output_dir']}")
        if diag.get("evaluation_error"):
            print(f"evaluation_error        : {diag['evaluation_error']}")

    outcome = diag["evaluation_outcome"]
    if outcome in ("SUCCESS", "ALREADY_FINALIZED"):
        return EXIT_OK
    if outcome == "INCOMPLETE":
        return EXIT_INCOMPLETE
    return EXIT_EVAL_FAIL


if __name__ == "__main__":
    raise SystemExit(main())
