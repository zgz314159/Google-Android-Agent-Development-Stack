# Evaluation Layer — v0.2.3 Evaluation Core + Auto-Finalizer

Observer-only evidence layer that turns a **Command Code session JSONL** into a
deterministic, low-overhead timeline and metric report — and can archive a
completed task automatically, without ever entering the observed task.

Design source (single authoritative spec):

```
${PROJECTS_ROOT}/Google-Android-Agent-Stack-v1.3-Evaluation-Layer-v0.2-Implementation-Design.md
```

## Architecture

```
Raw Recorder            ~/.commandcode/projects/<slug>/<session-id>.jsonl (append-only, per-turn commit)
    ↓
Task Boundary Detector  core.resolve_task_window()  — structural: message.meta.source
    ↓
Completion Detector     core.detect_completion()    — terminal assistant turn at the window tail
    ↓
Auto-Finalizer          auto_finalize.py / finalize_session.py  — trigger + archive (thin)
    ↓
Evaluation Core         core.py  — clocks, spans, T0-T9, tags, failures, repairs (deterministic)
    ↓
    Evaluation Artifact Store  ${STACK_DATA_ROOT}/artifacts/evaluation/<Project>/<RUN_ID>/{run.json,phase-timeline.csv,analysis.md,finalization.json}
```

The Evaluation Core itself remains **observer-only**. The Auto-Finalizer is only
a trigger/archive layer; it never participates in agent execution.

## Purpose

```
JSONL -> task window -> turn-owned wall timeline -> clocks -> T0-T9 + subphase mapper
      -> WAIT / Waste / Failure / Repair tags -> run.json + phase-timeline.csv + analysis.md
```

## Non-goals (this is an Observer, not an Optimizer)

- No Harbor, no Phoenix, no OpenTelemetry, no dashboard, no database.
- No `command-code-mods`, no provider modification, no agent behaviour change.
- **Zero LLM calls, zero network calls.**
- Never re-runs a build / test / device action (historical shell commands are read, never executed).
- Never modifies or copies the raw JSONL or any product code.
- No auto-retry, no auto-fix, no prompt rewriting.

## Requirements

Python 3 (standard library only). No `pip`, `npm`, `apt` installs.

## CLI

### `analyze_session.py` — on-demand analysis

Mode A — explicit session:

```bash
python3 evaluation/commandcode/analyze_session.py \
  --session /path/to/session.jsonl \
  --run-id PRE-HARBOR-BASELINE-001 \
  --project KeepLab \
  --output ${STACK_DATA_ROOT}/artifacts/evaluation/v0.2-calibration/keeplab
```

Mode B — auto-locate a session (deterministic, no guessing):

```bash
python3 evaluation/commandcode/analyze_session.py \
  --project-cwd ${PROJECTS_ROOT}/KeepLab-Relay \
  --prompt-contains "KeepLab Relay Benchmark" \
  --run-id PRE-HARBOR-BASELINE-001 --project KeepLab --output <dir>
```

Mode B matches on **both** project cwd and prompt substring; 0 or >1 candidates is
a **FAIL** (exit 4) and never guesses.

### `finalize_session.py` — Auto-Finalizer (deterministic, idempotent, atomic)

```bash
# explicit session, auto run-id
python3 evaluation/commandcode/finalize_session.py \
  --session /path/to/session.jsonl --prompt-contains "Verification Harness Hardening v0.1" \
  --project KeepLab --output-root ${STACK_DATA_ROOT}/artifacts/evaluation

# or auto-locate by project cwd + prompt
python3 evaluation/commandcode/finalize_session.py \
  --project-cwd ${PROJECTS_ROOT}/KeepLab-Relay \
  --prompt-contains "KeepLab Relay Benchmark" --project KeepLab
```

Writes the standard layout (never a free-form `--output` path):

```
<output-root>/<Project>/<RUN_ID>/
├── run.json
├── phase-timeline.csv
├── analysis.md
└── finalization.json
```

`--run-id` is optional; if omitted it is generated as
`<PROJECT>-<TASK-SLUG>-<YYYYMMDD-HHMMSS>` from the task prompt and task start,
and the full identity (session id, prompt head, cwd, task start/end, JSONL
SHA256) is always recorded in `finalization.json`.

### `auto_finalize.py` — trigger layer

```bash
# one cheap pass: finalize every stable, not-yet-finalized session
python3 evaluation/commandcode/auto_finalize.py scan \
  --projects-root ~/.commandcode/projects --output-root ${STACK_DATA_ROOT}/artifacts/evaluation

# long-running non-invasive watcher (cheap mtime/size polling)
python3 evaluation/commandcode/auto_finalize.py watch --poll-seconds 15 --stable-seconds 5

# replay one already-complete historical session through the production path
python3 evaluation/commandcode/auto_finalize.py replay \
  --session /path/to/session.jsonl --project KeepLab \
  --run-id KEEPLAB-VERIFICATION-HARDENING-001-v021
```

## Auto-Finalizer guarantees

| Property | How |
|---|---|
| **Idempotent** | `finalization.json` marks a published run; a second trigger for the same `session_id + run_id` returns `ALREADY_FINALIZED` unless `--force`. |
| **Atomic output** | Built in `<RUN_ID>.tmp/`, then `os.replace`d into `<RUN_ID>/`. An interrupted run never leaves a half-written Evaluation. |
| **Stability-checked** | The JSONL mtime/size is stat'ed before and after analysis; a change during analysis discards the tmp output. `--stable-seconds` refuses to finalize a still-active file. |
| **Outcome isolation** | `task_outcome` (observed completion: `COMPLETED`/`INCOMPLETE`/`UNKNOWN`) and `evaluation_outcome` (`SUCCESS`/`ALREADY_FINALIZED`/`INCOMPLETE`/`FAIL`) are separate. An Evaluation failure never rewrites the task outcome. |
| **Non-invasive** | `scan`/`watch` only stat session files; the full core runs **once** a session is stable. The raw JSONL is opened read-only. |

### Why not a Command Code `Stop` hook?

Command Code's official lifecycle hook for "assistant finished its turn" is
`Stop`. It fires **inside** the observed turn and runs synchronously, so wiring
it up would put the Evaluation layer into the observed task's timing path and
add a process spawn on every turn — exactly the contamination the design
forbids. The Auto-Finalizer therefore uses the non-invasive filesystem/session
watcher (`auto_finalize.py scan|watch`) instead, and can be driven from a
launcher wrapper after `cmd` exits. No Command Code internals are modified.

## Task window (v0.2.1)

Command Code JSONL v3 tags every message with `message.meta.source`:

| `meta.source` | Meaning | Task boundary? |
|---|---|---|
| `user` | genuine user-authored message | **YES** — opens/closes a task window |
| `model` | assistant output | no |
| `tool` | tool result injected as a user-side message | no |
| `steering` | runtime-injected control message (monitor pings, plan/ask responses) | no |

v0.2.1 detects boundaries **structurally** from this field. v0.2 used a
text-only heuristic (`role == user` with no `tool_result`), which mis-split a
task every time a `steering` control ping landed mid-task — the real hardening
session was truncated at its 10th monitor ping, hiding ~46 minutes of work.

Sessions without `message.meta.source` (legacy/synthetic) fall back to the old
heuristic and are flagged in `run.json.task_window.uncertainty`. Nothing is
guessed: a boundary the schema cannot prove is recorded as uncertain.

## Clock model (v0.2.2)

Four clocks, all offline and structural:

```
session_open             = session row timestamp
pre_prompt_user_wait     = session_open -> task prompt            (NOT agent work)
task_elapsed_wall        = task prompt  -> final assistant completion
interactive_user_wait    = proven model->human->resume time at a human-in-the-loop
                           boundary (ask_user_question / plan approval); null if none
unattributed_idle_wall   = proven non-agent wall that is NOT a provable human
                           boundary (OS idle / client suspend); 0 unless such
                           evidence exists
agent_owned_wall         = task_elapsed_wall - interactive_user_wait
                           - unattributed_idle_wall
session_wall             = session_open -> task end
```

The human wait is the **boundary turn's own span**, not the gap after the answer.
Command Code commits an assistant row when the turn completes; for a turn ending
in a blocking tool the row is committed on RESUME, so the span
`(previous turn end, resume]` is where the wait lives. `message.meta.createdAt`
(when the question was actually emitted) vs the row timestamp (resume) separates
the model generation from the human round-trip **exactly**; when `createdAt` is
absent, the whole boundary span is used as an **upper bound** — but it is never
counted as agent work.

Phase shares and the UNKNOWN ratio use **`agent_owned_wall`** as the denominator
(`phase_share_denominator_sec`), never `task_elapsed_wall`: proven human wait must
not dilute every phase.

Command Code's own `Worked for …` UI timer is a separate *client clock*; it can
include human input and idle time and is not required to equal
`task_elapsed_wall`.

### Wait semantics (v0.2.3)

`total_wait_tag_wall_sec` is the sum of **all** wait tags (build / device /
AI-node / tool / provider / dependency). `user_wait_seconds` is a **deprecated**
alias for that total and is **not** human wait. The only human-in-the-loop figure
is `interactive_user_wait`.

## Failure parsing (v0.2.2)

Test-runner transcripts are parsed **per result line**: a line ending in
`... ok` is a PASS and can never become a logical failure, even when the test
name contains `timeout`/`error`/`failure`. Only a `... FAIL`/`... ERROR` line or
an aggregate `FAILED (failures=…)` / `SELFTEST_*=FAIL` / `BUILD FAILED` signal
counts. A bare failure-like word (e.g. a passing `test_timeouts ... ok`) is never
a failure and the old substring `timeout` match no longer mints an
`INFRASTRUCTURE_ERROR`.

## Project identity (v0.2.2)

`core.discover_project_identity()` resolves the project label deterministically:
explicit caller `--project` → nearest `.evaluation.json` (`{"project": "..."}`)
walking up from the session cwd → cwd basename. Never inferred from prompt text.
A Stack can drop `.evaluation.json` at its root to group long-term artifacts.

## Task completion & result contract (v0.2.1)

`task_completion_detected` is **structural**: the window must end on a terminal
assistant turn (text, no pending `tool_use`) that is the last row in the window.

`result` is **not** keyword-inferred. The raw JSONL carries no authoritative task
outcome field, so `result` stays `UNKNOWN` unless the caller asserts
`--result {PASS,FAIL,UNKNOWN}`. Seeing a string like `READY` in the transcript is
never treated as PASS.

## Time model

Command Code writes an **assistant row whose timestamp is the turn end**, and the
matching `tool_result` shares that timestamp; real wall time lives in the gap to
the next assistant turn. v0.2.1 therefore uses **turn-owned exclusive wall spans**:

```
span(turn_k) = (previous turn end, turn_k end]
```

Every millisecond of `task_elapsed_wall` is owned exactly once, so
`Σ span == task_elapsed_wall` (asserted in `run.json.reconciliation`).
Background jobs never add their duration again — only summed `shell_output`
waits are reported, and marginal wall is `NOT AVAILABLE`.

## Phase model

Top level `T0–T9` + `UNKNOWN`. Subphases: `T1a/T1b`, `T7a/T7b/T7c`.
Mapping is **deterministic and rule-based** (`commandcode/phase_rules.json`) over
tool name, agent subagent type, command, path and result signatures, with
`HIGH/MEDIUM/LOW` confidence and an explicit `UNKNOWN` fallback (never guessed).

- `T0` Agent Intake & Requirement Normalization (excludes pre-prompt wait)
- `T1` Workflow Routing & Readiness — `T1a` Routing, `T1b` Bootstrap & Provider Readiness
- `T2` Context Acquisition · `T3` Planning/Architecture · `T4` Implementation
- `T5` Build/Compile · `T6` Tests
- `T7` Device/Runtime Verification — `T7a` Deploy, `T7b` UI Driving, `T7c` Evidence/State
- `T8` Repair/Rework (only with a failure→fix→rerun causal chain)
- `T9` Final Verification/Handoff

v0.2.1 adds deterministic rules for plan-mode control transitions
(`enter_plan_mode`/`exit_plan_mode` → T3), human-in-the-loop clarification
(`ask_user_question` → T3), agent subagent type (`explore` → T2, `plan` → T3),
`monitor_command` Gradle build/test jobs (T5/T6), harness self-tests (T6) and
result/report artifacts (T9). v0.2.2 adds `plan_review` → T3, `agent_output` →
T2, and the `verification/**` harness tree (`*.py`, `*.sh`,
`contracts`/`tests`/`examples`/`fixtures` → T6, `README.md` → T9). v0.2.3 adds the
Verification Layer runner execution (`run_verification.sh` / `verification/runner`
/ `orchestrator.py` → T7) so running the harness is never UNKNOWN.

Orthogonal tags: WAIT (`WAIT_PROVIDER/BUILD/DEVICE/AI_NODE/NETWORK/DEPENDENCY/INDEX/TOOL`)
and time class (`PRODUCTIVE / NECESSARY_OVERHEAD / AVOIDABLE_WASTE / UNKNOWN`).

Logical failures are grouped by **operation target** (v0.2.3): repeated failures of
one target form a single logical failure with a repair chain, never several product
faults. A `repair_id` is created only for a real `FAIL → relevant code/test/config edit
→ successful re-run of the same target` (same signature, exit 0). A failure whose
linkage cannot be proven is labelled `repair_status`
(`UNPROVABLE_NO_FIX_EDIT` / `UNPROVABLE_NO_SUCCESSFUL_RERUN`) and rolled up in
`repair_linkage`; no repair is credited from "a later test passed" alone.

## Output artifacts

| File | Contents |
|---|---|
| `run.json` | run identity, source evidence identity, task window, task completion, clocks, phase + subphase totals, raw + per-phase tokens, tool stats, logical failures, repairs, interventions, deviations, WAIT totals, time classes, waste, background jobs, UNKNOWN ratio |
| `phase-timeline.csv` | one row per turn-owned span |
| `analysis.md` | readable report (evidence identity, window, completion, clocks, phases, tokens, failures, repairs, UNKNOWN, design/reality notes) |
| `finalization.json` | Auto-Finalizer record: run/session id, `task_completion_detected`, `finalized`, `evaluation_core_version`, `raw_jsonl_modified`, `task_outcome`, `evaluation_outcome`, task identity |

Evidence snippets are redacted before being written. The raw JSONL is never copied.

## Tests

```bash
python3 -m unittest discover -s evaluation/tests -v
```

- `test_evaluation_core.py` — core unit tests (legacy/synthetic sessions without `meta`).
- `test_evaluation_core_v022.py` — human-wait attribution (ask_user_question / plan
  review), failure false-positive parsing, agent-owned phase denominator, project
  identity, and a read-only replay of the real promotion session.
- `test_task_window_v021.py` — task-window/completion/clock regression on a minimal
  schema fixture, plus an optional replay of the real hardening session.
- `test_finalize_session.py` — end-to-end Auto-Finalizer flow (completion →
  finalize → artifacts → later task excluded → idempotent → atomic → isolated).

Tests only exercise the Evaluation Core with synthetic JSONL; they never run an
Android build/test/device.

## Current limitations

- Schema version **3** only; unknown schemas abort with `UNSUPPORTED_SCHEMA`.
- Task boundaries require `message.meta.source`; older sessions fall back to the
  legacy heuristic and are marked uncertain.
- The Auto-Finalizer archives the **first** independent task window in a session;
  multi-task sessions are not yet split into one Evaluation per task.
- Background marginal wall is `NOT AVAILABLE` (only summed waits reported).
- `result` is only reported when asserted with `--result`; completion is reported
  separately as `task_completion_detected`.
- Failure-type precision for compound shell commands is heuristic.
- Client-side token normalization is not produced; raw provider fields are preserved.
