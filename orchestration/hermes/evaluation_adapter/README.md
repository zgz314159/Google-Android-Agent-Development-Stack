# Evaluation Adapter (thin)

A **thin** prototype adapter that turns real Hermes evidence into one
`hermes-run-summary.json`. It does not reimplement Evaluation, does not call a model, and
does not modify `evaluation/**` (Evaluation Core v0.2.3 stays frozen).

## Inputs (real evidence only)

| Input | Source |
|---|---|
| `--db <state.db>` | Hermes profile state DB, opened **read-only** (`/home/zhong/.hermes/profiles/android-stack/state.db`) |
| `--root-session <id>` | the root session id of the run |
| `--kanban-json <file>` | optional `hermes kanban list --json` capture |
| `--out <path>` | output `hermes-run-summary.json` |
| `--evidence-out <path>` | optional raw root+child rows (evidence) |

## Output fields

`root_session`, `provider`, `model`, `children_started`, `children_completed`,
`max_concurrent_children`, `parallel_overlap_sec`, `kanban_tasks`, `failed_tasks`,
`root_tool_calls`, `root_message_count`, `wall_sec`, `api_calls`, `tokens{input,output,
cache_read,cache_write}`, `children[]`.

Missing/unprovable values are `null` or `"NOT_AVAILABLE"` — never guessed.

## Example

```bash
python3 hermes_run_summary.py \
  --db /home/zhong/.hermes/profiles/android-stack/state.db \
  --root-session 20261004_234211_d5c6af \
  --kanban-json ../evidence/kanban-s1-probe.json \
  --out ../evidence/hermes-run-summary.json \
  --evidence-out ../evidence/delegation-sessions.json
```

`parallel_overlap_sec` is the wall time during which **≥2 children** were simultaneously
active (interval sweep), so it is a genuine concurrency measurement, not a guess.

## Limitations

- The adapter reads Hermes's local SQLite session store; a different Hermes version could
  change the schema. It fails loudly (exit 2) if the root session is absent.
- Kanban task/board semantics are captured verbatim; it does not interpret board state.

---

# Hermes session source (S1.1)

`hermes_session_source.py` is the second, separate file in this directory: the
**execution-source adapter** that lets the existing Auto-Finalizer ingest a completed
Hermes ROOT session.

- `hermes_run_summary.py` (above) = read-only *observability* summary for S1 evidence.
- `hermes_session_source.py` (this) = *ingestion*: Hermes store -> Command Code JSONL v3
  shim -> the frozen canonical finalization path
  (`evaluation/commandcode/finalize_session.py::finalize` -> `core.analyze`).

It is NOT a second Evaluation system: it writes no metrics and duplicates no core logic.

## Where it plugs in

| Layer | File | Role |
|---|---|---|
| Source discovery | `hermes_session_source.py` | read-only `state.db` queries: root sessions, completion (`ended_at`), fingerprint |
| Normalization | `hermes_session_source.py` | Hermes rows -> CC-v3 JSONL shim (`type=session` v3 + `message.meta.source` rows) written under the staging root (never under `~/.commandcode/projects`) |
| Trigger | `evaluation/commandcode/auto_finalize.py` | `scan --source hermes` / `hermes-session --session-id X` |
| Finalize | `evaluation/commandcode/finalize_session.py` | unchanged canonical publish (`run.json`, `phase-timeline.csv`, `analysis.md`, `finalization.json`) |

## Commands

```bash
# sweep every completed Hermes root session (one-shot; not a daemon)
python3 evaluation/commandcode/auto_finalize.py scan --source hermes

# one-shot backfill / recovery for a known session (isolated output root shown)
python3 evaluation/commandcode/auto_finalize.py hermes-session \
  --session-id 20261005_001816_3eedd8 --output-root /tmp/_evaluation

# both sources in one pass
python3 evaluation/commandcode/auto_finalize.py scan --source all
```

Statuses: `SUCCESS`, `ALREADY_FINALIZED`, `SKIP_UNCHANGED` (all exit 0), `INCOMPLETE`
(unfinished session; exit 5, never published), `NOT_FOUND` / `FAIL` (exit 6).

## Idempotency / safety

- Idempotent per `(source, session_id)`; the index key is `hermes:<session_id>`. A second
  trigger is `ALREADY_FINALIZED` (core) or `SKIP_UNCHANGED` (index/fingerprint) — never a
  second evaluation.
- An unfinished session (`ended_at IS NULL`) is never finalized.
- The Hermes store is opened `mode=ro`; the raw store is never modified.
- Index records are additive (`source`, `source_type`, `session_id`, `fingerprint`,
  `finalized_at`); pre-S1.1 records (plain session paths) stay valid.

## Session-end hook (trigger for new sessions)

`hooks/hermes-autofinalizer-hook.sh` is a thin, observer-only shell hook. The pinned
Hermes (`vgit.af90026`) exposes a real session-teardown hook:

| Event | Fire site | Payload | Id field |
|---|---|---|---|
| `on_session_finalize` | `hermes_cli/lifecycle.py::finalize_session` (CLI teardown, one-shot CLI exit via `hermes_cli/cli_shutdown.py::_notify_single_query_session_finalize`, TUI, gateway) | `session_id`, `platform`, optional `reason` | `session_id` |
| `on_session_end` | `agent/turn_finalizer.py` (every turn finalization) | `session_id`, `task_id`, `turn_id`, `completed`, `failed`, `interrupted`, `turn_exit_reason`, `model`, `platform` | `session_id` |

This adapter hooks `on_session_finalize` (once per session, not per turn). Configured in the
profile `config.yaml`:

```yaml
hooks:
  on_session_finalize:
    - command: "<repo>/orchestration/hermes/evaluation_adapter/hooks/hermes-autofinalizer-hook.sh"
      timeout: 15
```

The hook prints nothing (observer-only), extracts `session_id` from the stdin payload, and
launches `auto_finalize.py hermes-session --session-id <id>` **detached** so the turn is
never blocked. Shell hooks require approval; the documented non-TTY path is manual
allowlisting in `$HERMES_HOME/shell-hooks-allowlist.json` (verify with `hermes hooks list`,
undo with `hermes hooks revoke <command>` and `hermes config unset hooks`).

## Known limitations

- Per-turn token usage is NOT available: Hermes persists session-level totals only
  (`sessions.*_tokens`, `session_model_usage`) and `messages.token_count` may be NULL. No
  per-turn usage is invented; the evaluation reports zero/None tokens.
- Hermes child/subagent sessions are not enumerated in S1.1 (out of scope); only Hermes
  ROOT sessions are ingested.
- `core.analyze` stamps `agent_host = "Command Code"` (frozen core). The true source is
  recorded in `finalization.json.execution_source` and in the index.
- The shim transcript is a redaction-input copy of the session, staged under
  `<output-root>/_hermes_staging/` (mode 0700). The core's redactor applies to evaluation
  outputs, exactly as it does for the raw Command Code JSONL.

---

# Structured failure evidence (P0B-EVAL-GUARD-FIX)

`failure_evidence.py` is the third file in this directory: the **proof layer** that makes the
frozen core's failure classification conditional on the operation having actually failed.

## The defect it fixes

`core._FAIL_PATTERNS` classifies a logical failure by searching a tool result's **text** for
failure-looking patterns. Nothing there requires the operation behind that text to have failed,
so in the P0B-CLOSE run `HERMES-20261005_032302_4c6c40`:

- `FAIL-001 PROVIDER_AUTH` came from a **successful** `grep` (exit 0) that merely printed
  `evaluation/commandcode/core.py` source lines containing `PROVIDER_AUTH`, `401` and
  `authentication failed`. No provider operation ran, and the `PROVIDER_FALLBACK` execution
  deviation was derived from it.

## The rule

```
PROVE FAILURE (structured execution state)  ->  CLASSIFY FAILURE (text)
```

A logical failure is removed only when its own operations cannot support it:

| rule | fires when |
|---|---|
| `OPERATION_SUCCEEDED` | every operation the failure was drawn from is a *clean* structured success (exit 0, no structured error, exit status not flagged non-authoritative) **and** none of their output carries the invoked tool's own termination verdict (`BUILD FAILED`, `FAILED (failures=N)`, `Traceback…`, `TIMEOUT`) |
| `PROVIDER_TYPED_FROM_INSPECTION_TEXT` | a `PROVIDER_*` type was asserted from read-only inspection commands (`grep`/`cat`/`sed`/…) that carry no provider-operation token |

The layer **only ever removes** failures — it can never add one. Real failures are never
weakened: a genuine build/test failure either returns a non-zero status, is flagged by the
runner as pipeline-lost, or prints its tool's own termination verdict.

## Where it plugs in

| Layer | File | Role |
|---|---|---|
| Proof layer | `orchestration/hermes/evaluation_adapter/failure_evidence.py` | parse the runner envelope, prove an operation's outcome, correct the failure set |
| Finalizer | `evaluation/commandcode/finalize_session.py` | additive optional `failure_evidence=False` switch; applied between `core.analyze` and `core.write_outputs` |
| Trigger | `evaluation/commandcode/auto_finalize.py` | `scan_hermes` passes the switch on; the Command Code path is unchanged |
| Audit | `run.json.failure_evidence_correction`, `finalization.json.failure_evidence_correction` | every removal with its rule, event states and the core's evidence |

`core.py` is `PRODUCTION_IMMUTABLE` in the frozen P0B-CLOSE contract, so the correction lives in
this adapter plus one additive finalizer parameter — exactly what that contract's DEC-010 allows.

## Verification

```bash
python3 -m unittest discover -s orchestration/hermes/evaluation_adapter/tests -v   # guard + fixtures
bash    orchestration/hermes/evaluation_adapter/tests/run_p0b_eval_guard_fix_verification.sh
python3 orchestration/hermes/evaluation_adapter/tests/run_p0b_eval_guard_fix_compare.py
```

`tests/fixtures/failure_evidence_cases.json` holds the CASE A–I fixtures (source-code 401,
passing unittest, real test failure, real provider failure, real build error, pipeline-lost
status, documentation text).
