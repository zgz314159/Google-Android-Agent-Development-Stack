# Hermes Orchestration (Integration)

Thin integration of **Hermes** (Nous Research `hermes-agent`, official upstream) as the
**orchestration kernel** of this Stack. Hermes is **not reimplemented and not forked** —
we only add integration config, a project context file, a profile, resource policy, and a
thin evaluation adapter.

## Purpose

The P0A run consumed **4h19m** wall, **78.5%** of it in a per-step device loop with **226
model requests** in T7 and **zero** Command Code native subagents. S1 fixes the architecture
so the agent is a **verification / exception handler**, not a mechanical device executor.

## Insertion point

```
Specification / Contract  (specification/**)   READY + implementation-contract.json
        │
        ▼
Hermes Orchestrator  (orchestration/hermes/)   decomposition → dependency graph → workers
        │
        ▼
Implementation / Analysis
        │
        ▼
Verification Layer  (verification/**)          deterministic, fail-closed
        │
        ▼
UiAutomator / Maestro  →  Android device 87296ada (exclusive, capacity 1)
        │
        ▼
Evaluation Core v0.2.3  (evaluation/**)        observer-only
        │
        ▼
Auto-Finalizer
```

The **thinnest seam** is the `EXECUTOR-PROMPT.md` consumption boundary
(`specification/docs/ARCHITECTURE.md`): today exactly one session consumes the frozen
contract; Hermes replaces that single consumer. The scheduling substrate already exists —
`implementation-contract.json` `tasks[]` carry `id, goal, boundary, depends,
allowed_paths, acceptance_ids, done_when` (schema
`specification/contracts/android-implementation-contract.schema.json`), i.e. a validated
task dependency graph with per-task file boundaries.

## Model source

```
Hermes → CommandCode provider → deepseek/deepseek-v4.1-flash
```

Not `Hermes → cmdc CLI → DeepSeek`. No ACP/CLI bridge in this phase.

## Non-goals

- No reimplemented multi-agent scheduler, worker pool, task queue, delegation engine,
  Kanban, provider routing, worktree engine or session engine — use Hermes upstream.
- No Hermes core patches. If a required upstream fix is missing ⇒ `UPSTREAM_BLOCKER`.
- No Hermes Android computer-use engine.
- No modification of KeepLab production code, Testapp, PowerAi, P0B, or P1.

## Files

| File | Role |
|---|---|
| `HERMES-LOCK.json` | frozen upstream version + commit + provider/model target |
| `INTEGRATION.md` | architecture + seam + how to run |
| `DEVICE-EXECUTION-POLICY.md` | device modes, selector-first, no adb UI input, lock |
| `PARALLEL-EXECUTION-POLICY.md` | read-only parallel / single-writer / worktree isolation |
| `evaluation_adapter/` | thin adapter: Hermes smoke evidence → `hermes-run-summary.json` |

## Limitations

- The device replay success of S1 depends on a physically attached `87296ada`; if absent,
  the device gate is `BLOCKED` (never faked).
- Hermes orchestration was validated with read-only delegation + a Kanban DAG probe; it is
  **not** yet wired to write-side implementation.
