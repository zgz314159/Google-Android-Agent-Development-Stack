# INTEGRATION — Hermes Orchestration Kernel

本文保留早期 S1 集成设计。当前操作请看 [中文教程](../../docs/SYSTEM-USAGE.zh-CN.md)：
下面的直接 `hermes run` smoke 会调用模型，不能替代 AEGL 受控任务入口或只读检查。

## Principle

Use Hermes upstream as-is. We add only:

- configuration (provider = `commandcode`, model = `deepseek/deepseek-v4.1-flash`)
- a dedicated profile (`android-stack`, terminal backend = `local`, cwd = this Stack)
- a project context file (`.hermes.md`)
- resource policy (device lock; parallelism rules)
- one thin evaluation adapter (`evaluation_adapter/`)

We do **not** reimplement the scheduler, worker pool, task queue, delegation engine,
Kanban, provider routing, worktree engine, or session engine.

## Seam

Contract → Hermes is a **document boundary**, so there is no executor code to refactor:

1. Hermes reads `implementation-contract.json` after hash-verifying `manifest.json` and
   `READY.json` (`CONTRACT_CHANGED` ⇒ stop).
2. Hermes schedules `contract.tasks[]` topologically by `depends`.
3. Each `TASK-NN` is dispatched to a worker with its `allowed_paths` + `read_first` (≤12
   files). Workers honour `CONTRACT_DEVIATION` and `do-not-reopen` semantics.
4. Implementation output flows to the existing `verification-intent.json` →
   `verification-plan.schema.json` bridge → `verification/runner/orchestrator.py` →
   Auto-Finalizer.

## Provider

Hermes `commandcode` provider uses `COMMANDCODE_API_KEY` (stored in `~/.hermes/.env`,
mode 0600). The Command Code CLI may use `COMMAND_CODE_API_KEY`; if only the latter is
present, map it in the Hermes process/profile env. Values are never printed.

## How to run (profile `android-stack`)

```bash
# one-shot provider smoke
hermes --profile android-stack run "Reply exactly: HERMES_COMMANDCODE_OK"

# read-only multi-agent delegation smoke (3 independent tasks)
hermes --profile android-stack run "<delegation prompt>"   # see reports/HERMES-INTEGRATION-SMOKE.md

# Kanban DAG probe: A,B,C independent -> D depends on A,B,C
hermes kanban ...   # exact CLI per `hermes kanban --help`
```

Exact subcommands and flags are confirmed against the installed CLI
(`hermes <cmd> --help`) at S1 time — never guessed.

## Device path

Hermes never taps a device step-by-step. It calls one command:

```
verification/reference-replay/runner/run_reference_replay.sh --flows R1,R2,R3 --runs 3
```

and receives the compact `index.json` result. The device lock
(`verification/core/device_lock.sh`) guarantees exclusive access.

## Constraints

- No automatic `hermes update` during/after the benchmark; the version is frozen in
  `HERMES-LOCK.json`.
- No Hermes core source edits. Missing upstream fix ⇒ `UPSTREAM_BLOCKER`.
