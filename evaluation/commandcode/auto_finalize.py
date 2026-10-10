#!/usr/bin/env python3
"""Evaluation Core v0.2.3 - Auto-Finalizer trigger (non-invasive).

Detects agent sessions that have reached a stable terminal completion and invokes
the production finalizer (`finalize_session.finalize`) on them.

Two execution sources are supported (S1.1):

  * ``commandcode`` -- the original source: append-only session JSONL under
    ``~/.commandcode/projects/*/*.jsonl``.
  * ``hermes``      -- a completed Hermes ROOT session persisted in the pinned
    Hermes SQLite store (``state.db``). It is normalized by
    ``orchestration/hermes/evaluation_adapter/hermes_session_source.py`` into the
    same Command Code JSONL v3 shape the frozen core already consumes, then run
    through the *same* canonical finalization path. No second evaluation system.

Both sources share one index (``<output-root>/.auto_finalize_index.json``), keyed
by an absolute session path (command code) or ``hermes:<session_id>`` (hermes).
New per-record fields are additive; records written before S1.1 stay readable.

Trigger design (priority order from the brief):
  1. official lifecycle hook  -> Command Code's `Stop` hook fires *inside* the
     observed turn, so enabling it would enter the observed task's timing path.
     for HERMES the pinned version exposes a real session-teardown hook
     (`on_session_finalize`, fired by the one-shot CLI exit path too), so a thin
     observer-only shell hook is installed for the hermes source; it launches a
     one-shot finalize detached and never blocks the turn.
  2. non-invasive wrapper     -> `replay`/`scan` can be called from a launcher
     after `cmd` exits.
  3. filesystem/session watcher -> `watch`/`scan` poll the append-only session
     JSONL cheaply: an mtime+size stat decides whether a full Evaluation is
     worth running. The full core only runs once a session is stable and not
     already finalized.

Guarantees: zero LLM calls, zero network calls, never modifies the raw JSONL or
the Hermes store, and never enters the observed task's execution/timing path.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import finalize_session as finalizer  # noqa: E402

INDEX_FILE = ".auto_finalize_index.json"
DEFAULT_PROJECTS_ROOT = os.path.expanduser("~/.commandcode/projects")
DEFAULT_OUTPUT_ROOT = finalizer.DEFAULT_OUTPUT_ROOT

SOURCE_COMMANDCODE = "commandcode"
SOURCE_COMMANDCODE_TYPE = "commandcode_session"
SOURCE_HERMES = "hermes"
HERMES_STAGING_DIRNAME = "_hermes_staging"

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_HERMES_ADAPTER_DIR = os.path.join(_REPO_ROOT, "orchestration", "hermes", "evaluation_adapter")

_hermes_source_cache = None


def _load_hermes_source():
    """Lazy import of the Hermes source adapter (only needed for source=hermes)."""
    global _hermes_source_cache
    if _hermes_source_cache is None:
        if _HERMES_ADAPTER_DIR not in sys.path:
            sys.path.insert(0, _HERMES_ADAPTER_DIR)
        import hermes_session_source  # noqa: E402
        _hermes_source_cache = hermes_session_source
    return _hermes_source_cache


def _utcnow():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iter_sessions(projects_root: str):
    root = Path(projects_root)
    if not root.exists():
        return
    for f in sorted(root.glob("*/*.jsonl")):
        name = f.name
        if name.endswith(".checkpoints.jsonl") or name.endswith(".prompts.jsonl"):
            continue
        yield str(f)


def _load_index(output_root: str) -> dict:
    path = os.path.join(output_root, INDEX_FILE)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_index(output_root: str, index: dict) -> None:
    os.makedirs(output_root, exist_ok=True)
    path = os.path.join(output_root, INDEX_FILE)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def scan(projects_root: str = None, output_root: str = None, stable_seconds: float = 5.0,
         project: str = None, workflow: str = None, force: bool = False) -> list:
    """One cheap pass over the Command Code source: finalize every session that is
    stable and not yet done. Unchanged from the pre-S1.1 behaviour; only additive
    index provenance fields are new."""
    projects_root = projects_root or DEFAULT_PROJECTS_ROOT
    output_root = output_root or DEFAULT_OUTPUT_ROOT
    index = _load_index(output_root)
    results = []
    for path in _iter_sessions(projects_root):
        try:
            st = os.stat(path)
        except OSError:
            continue
        key = os.path.abspath(path)
        rec = index.get(key)
        if not force and rec and rec.get("mtime_ns") == st.st_mtime_ns and rec.get("size") == st.st_size:
            results.append({"session": key, "status": "SKIP_UNCHANGED",
                            "run_id": rec.get("run_id"), "output_dir": rec.get("output_dir")})
            continue
        if stable_seconds > 0 and (time.time() - st.st_mtime) < stable_seconds:
            results.append({"session": key, "status": "SKIP_ACTIVE"})
            continue

        diag = finalizer.finalize(
            session_path=key, output_root=output_root, project=project,
            workflow=workflow, force=force, stable_seconds=0.0, require_completion=True,
            execution_source={"source": SOURCE_COMMANDCODE, "source_type": SOURCE_COMMANDCODE_TYPE},
        )
        if diag["evaluation_outcome"] in ("SUCCESS", "ALREADY_FINALIZED"):
            index[key] = {
                "mtime_ns": st.st_mtime_ns,
                "size": st.st_size,
                "run_id": diag["run_id"],
                "output_dir": diag["output_dir"],
                "session_id": diag["session_id"],
                # --- additive (S1.1) execution-source provenance ---
                "source": SOURCE_COMMANDCODE,
                "source_type": SOURCE_COMMANDCODE_TYPE,
                "fingerprint": f"{st.st_mtime_ns}:{st.st_size}",
                "finalized_at": _utcnow(),
            }
        results.append({
            "session": key,
            "status": diag["evaluation_outcome"],
            "run_id": diag["run_id"],
            "output_dir": diag["output_dir"],
            "error": diag["evaluation_error"],
        })
    _save_index(output_root, index)
    return results


def scan_hermes(output_root: str = None, db: str = None, session_id: str = None,
                staging_root: str = None, force: bool = False,
                include_incomplete: bool = False, project: str = None,
                workflow: str = "hermes", profile: str = None) -> list:
    """One pass over completed Hermes ROOT sessions -> canonical finalization path.

    Idempotent per (source, session_id): a session whose fingerprint is already
    finalized is SKIP_UNCHANGED, and the canonical finalizer itself returns
    ALREADY_FINALIZED on a repeated run id. An unfinished session is never
    finalized unless ``include_incomplete`` is explicitly requested.
    """
    hermes = _load_hermes_source()
    output_root = output_root or DEFAULT_OUTPUT_ROOT
    db_path = hermes.resolve_db(db, profile)
    if not db_path:
        return [{
            "session": None, "status": "NO_HERMES_STORE", "run_id": None, "output_dir": None,
            "source": hermes.SOURCE, "source_type": hermes.SOURCE_TYPE, "session_id": session_id,
            "error": "no Hermes state.db found (set --hermes-db or HERMES_EVAL_DB)",
        }]

    index = _load_index(output_root)
    staging = staging_root or os.path.join(output_root, HERMES_STAGING_DIRNAME)
    results = []
    descriptors = hermes.list_root_sessions(db_path, session_id=session_id, include_incomplete=True)
    if session_id and not descriptors:
        return [{
            "session": hermes.index_key(session_id), "status": "NOT_FOUND", "run_id": None,
            "output_dir": None, "source": hermes.SOURCE, "source_type": hermes.SOURCE_TYPE,
            "session_id": session_id, "completed": None,
            "error": f"no Hermes session with id {session_id!r} in {db_path}",
        }]
    for d in descriptors:
        sid = d["session_id"]
        key = hermes.index_key(sid)
        base = {
            "session": key, "source": hermes.SOURCE, "source_type": hermes.SOURCE_TYPE,
            "session_id": sid, "completed": d["completed"], "error": None,
        }
        rec = index.get(key)
        if not force and rec and rec.get("finalized") and rec.get("fingerprint") == d["fingerprint"]:
            results.append({**base, "status": "SKIP_UNCHANGED",
                            "run_id": rec.get("run_id"), "output_dir": rec.get("output_dir")})
            continue
        if not d["completed"] and not include_incomplete:
            results.append({**base, "status": "INCOMPLETE", "run_id": None, "output_dir": None,
                            "error": "session has not ended (ended_at IS NULL); not finalizable"})
            continue

        os.makedirs(staging, mode=0o700, exist_ok=True)
        shim = os.path.join(staging, f"{sid}.jsonl")
        try:
            meta = hermes.normalize_session(db_path, sid, shim, allow_incomplete=include_incomplete)
        except Exception as exc:  # noqa: BLE001 - observation failure must be isolated
            results.append({**base, "status": "FAIL", "run_id": None, "output_dir": None,
                            "error": f"{type(exc).__name__}: {exc}"})
            continue

        run_id = f"HERMES-{sid}"
        diag = finalizer.finalize(
            session_path=shim, run_id=run_id, project=project, workflow=workflow,
            output_root=output_root, force=force, stable_seconds=0.0,
            require_completion=not include_incomplete,
            execution_source={
                "source": hermes.SOURCE, "source_type": hermes.SOURCE_TYPE,
                "session_id": sid, "fingerprint": d["fingerprint"],
                "hermes_db": db_path, "end_reason": d.get("end_reason"),
                "shim_path": meta["shim_path"],
            },
            # P0B-CLOSE: the persisted identity/usage block the adapter read from the Hermes
            # store. Additive and optional: a caller that does not pass it is unaffected.
            identity=meta.get("identity"),
            # P0B-EVAL-GUARD-FIX: prove every logical failure from the operations' structured
            # execution state before trusting a text-only classification. Additive and optional.
            failure_evidence=True,
        )
        if diag["evaluation_outcome"] in ("SUCCESS", "ALREADY_FINALIZED"):
            index[key] = {
                "source": hermes.SOURCE,
                "source_type": hermes.SOURCE_TYPE,
                "session_id": sid,
                "fingerprint": d["fingerprint"],
                "finalized_at": _utcnow(),
                "finalized": True,
                "run_id": diag["run_id"],
                "output_dir": diag["output_dir"],
                "completed": d["completed"],
                "end_reason": d.get("end_reason"),
            }
        results.append({
            **base, "status": diag["evaluation_outcome"], "run_id": diag["run_id"],
            "output_dir": diag["output_dir"], "error": diag["evaluation_error"],
        })
    _save_index(output_root, index)
    return results


def scan_any(source: str = SOURCE_COMMANDCODE, projects_root: str = None, output_root: str = None,
             stable_seconds: float = 5.0, project: str = None, workflow: str = None,
             force: bool = False, hermes_db: str = None, hermes_session_id: str = None,
             hermes_staging_root: str = None, include_incomplete: bool = False,
             profile: str = None) -> list:
    """Dispatch a single scan pass over the requested execution source(s)."""
    if source == SOURCE_HERMES:
        return scan_hermes(output_root=output_root, db=hermes_db, session_id=hermes_session_id,
                           staging_root=hermes_staging_root, force=force,
                           include_incomplete=include_incomplete, project=project,
                           workflow=workflow or "hermes", profile=profile)
    if source == "all":
        return (scan(projects_root, output_root, stable_seconds, project, workflow, force)
                + scan_hermes(output_root=output_root, db=hermes_db, session_id=hermes_session_id,
                              staging_root=hermes_staging_root, force=force,
                              include_incomplete=include_incomplete, project=project,
                              workflow=workflow or "hermes", profile=profile))
    if source != SOURCE_COMMANDCODE:
        raise ValueError(f"unknown source: {source}")
    return scan(projects_root, output_root, stable_seconds, project, workflow, force)


def watch(projects_root: str, output_root: str, poll_seconds: float, stable_seconds: float,
          project: str, workflow: str, iterations: int = 0) -> list:
    """Poll cheaply; only run the full core for stable, unfinished sessions.

    Command Code source only, unchanged: S1.1 deliberately does NOT add a second
    long-running polling daemon for the Hermes source (the session-end hook covers
    promptness; `scan --source hermes` is the one-shot sweep/backfill).
    """
    all_results = []
    n = 0
    while True:
        n += 1
        results = scan(projects_root, output_root, stable_seconds, project, workflow)
        all_results.extend(results)
        for r in results:
            if r["status"] == "SUCCESS":
                print(f"[{_utcnow()}] finalize {r['status']} {r['run_id']} -> {r['output_dir']}")
            elif r["status"] == "FAIL":
                print(f"[{_utcnow()}] finalize {r['status']} {r['session']}: {r['error']}")
        if iterations and n >= iterations:
            return all_results
        time.sleep(poll_seconds)


def build_parser():
    p = argparse.ArgumentParser(description="Evaluation Core v0.2.3 Auto-Finalizer trigger")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan", help="one pass over the sessions directory")
    s.add_argument("--source", default=SOURCE_COMMANDCODE,
                   choices=[SOURCE_COMMANDCODE, SOURCE_HERMES, "all"],
                   help="execution source (default: commandcode; 'all' = both)")
    s.add_argument("--projects-root", default=DEFAULT_PROJECTS_ROOT)
    s.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    s.add_argument("--stable-seconds", type=float, default=5.0)
    s.add_argument("--project", default=None)
    s.add_argument("--workflow", default=None)
    s.add_argument("--force", action="store_true")
    s.add_argument("--json", action="store_true")
    s.add_argument("--hermes-db", default=None, help="Hermes state.db (auto-discovered if omitted)")
    s.add_argument("--hermes-profile", default=None, help="Hermes profile name to resolve state.db")
    s.add_argument("--hermes-staging-root", default=None,
                   help="where normalized Hermes shims are written (default <output-root>/"
                        + HERMES_STAGING_DIRNAME + ")")
    s.add_argument("--hermes-session-id", default=None, help="restrict to one Hermes session id")
    s.add_argument("--hermes-include-incomplete", action="store_true",
                   help="also finalize sessions that have not ended (diagnostic; off by default)")

    w = sub.add_parser("watch", help="poll the sessions directory (Command Code source)")
    w.add_argument("--projects-root", default=DEFAULT_PROJECTS_ROOT)
    w.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    w.add_argument("--poll-seconds", type=float, default=15.0)
    w.add_argument("--stable-seconds", type=float, default=5.0)
    w.add_argument("--project", default=None)
    w.add_argument("--workflow", default=None)
    w.add_argument("--iterations", type=int, default=0, help="stop after N passes (testing)")

    r = sub.add_parser("replay", help="finalize one already-complete session")
    r.add_argument("--session", required=True)
    r.add_argument("--prompt-contains", default=None)
    r.add_argument("--run-id", default=None)
    r.add_argument("--project", default=None)
    r.add_argument("--workflow", default=None)
    r.add_argument("--result", default=None, choices=["PASS", "FAIL", "UNKNOWN"])
    r.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    r.add_argument("--force", action="store_true")
    r.add_argument("--json", action="store_true")

    h = sub.add_parser("hermes-session",
                       help="one-shot: normalize + finalize ONE Hermes root session (backfill/recovery)")
    h.add_argument("--session-id", required=True)
    h.add_argument("--hermes-db", default=None)
    h.add_argument("--hermes-profile", default=None)
    h.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    h.add_argument("--hermes-staging-root", default=None)
    h.add_argument("--project", default=None)
    h.add_argument("--workflow", default="hermes")
    h.add_argument("--force", action="store_true")
    h.add_argument("--include-incomplete", action="store_true")
    h.add_argument("--json", action="store_true")
    return p


_EXIT_BY_STATUS = {"SUCCESS": 0, "ALREADY_FINALIZED": 0, "SKIP_UNCHANGED": 0,
                   "INCOMPLETE": 5, "FAIL": 6, "NO_HERMES_STORE": 6, "NOT_FOUND": 6,
                   "SKIP_ACTIVE": 0}


def _print_results(results: list) -> None:
    for r in results:
        print(f"{r['status']:16s} {r.get('run_id') or '-':40s} {r['session']}")


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "scan":
        results = scan_any(source=args.source, projects_root=args.projects_root,
                           output_root=args.output_root, stable_seconds=args.stable_seconds,
                           project=args.project, workflow=args.workflow, force=args.force,
                           hermes_db=args.hermes_db, hermes_session_id=args.hermes_session_id,
                           hermes_staging_root=args.hermes_staging_root,
                           include_incomplete=args.hermes_include_incomplete,
                           profile=args.hermes_profile)
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            _print_results(results)
        bad = [r for r in results if r["status"] in ("FAIL", "NO_HERMES_STORE", "NOT_FOUND")]
        return 6 if bad else 0
    if args.cmd == "watch":
        watch(args.projects_root, args.output_root, args.poll_seconds, args.stable_seconds,
              args.project, args.workflow, args.iterations)
        return 0
    if args.cmd == "replay":
        diag = finalizer.finalize(
            session_path=args.session, prompt_contains=args.prompt_contains,
            run_id=args.run_id, project=args.project, workflow=args.workflow,
            explicit_result=args.result, output_root=args.output_root, force=args.force,
        )
        if args.json:
            print(json.dumps(diag, ensure_ascii=False, indent=2))
        else:
            print(f"task_outcome       : {diag['task_outcome']}")
            print(f"evaluation_outcome : {diag['evaluation_outcome']}")
            print(f"run_id             : {diag['run_id']}")
            print(f"output_dir         : {diag['output_dir']}")
            if diag.get("evaluation_error"):
                print(f"error              : {diag['evaluation_error']}")
        return 0 if diag["evaluation_outcome"] in ("SUCCESS", "ALREADY_FINALIZED") else 6
    if args.cmd == "hermes-session":
        results = scan_hermes(output_root=args.output_root, db=args.hermes_db,
                              session_id=args.session_id,
                              staging_root=args.hermes_staging_root, force=args.force,
                              include_incomplete=args.include_incomplete,
                              project=args.project, workflow=args.workflow,
                              profile=args.hermes_profile)
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            _print_results(results)
            for r in results:
                if r.get("error"):
                    print(f"  error: {r['error']}")
        return max((_EXIT_BY_STATUS.get(r["status"], 6) for r in results), default=6)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
