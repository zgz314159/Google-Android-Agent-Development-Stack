# Filesystem Layout and Host Portability

This document is normative for where the Google Android Agent Development Stack reads and
writes bytes. It separates **copying the project** from **migrating private host state**.

## The model

The project root (`PROJECT_ROOT`, discovered from the checked-out source tree) contains only
reproducible, reviewable material:

- source code and scripts;
- test source, fixtures, schemas and acceptance rules;
- authored specifications and durable design documents;
- configuration templates without secrets;
- dependency locks, checksums, patches, and bootstrap/import/export tools.

The project root must **not** receive generated or host-specific material: runtime state,
locks/PIDs/sockets, telemetry, test/benchmark results, evidence, generated reports,
screenshots, recordings, logs, APKs, build directories, caches, virtual environments,
`__pycache__`, `.pytest_cache`, credentials, cookies, or browser profiles.

## The path contract

One canonical implementation: [`scripts/lib/stack_paths.py`](../../scripts/lib/stack_paths.py),
with a shell query command [`scripts/stack-paths.sh`](../../scripts/stack-paths.sh). Resolution
logic is never duplicated.

```text
PROJECT_ROOT      = discovered from the checked-out source tree (or $ANDROID_AGENT_STACK_ROOT)
STACK_STATE_ROOT  = ${ANDROID_AGENT_STACK_STATE_ROOT:-${XDG_STATE_HOME:-$HOME/.local/state}/google-android-agent-stack}
STACK_DATA_ROOT   = ${ANDROID_AGENT_STACK_DATA_ROOT:-${XDG_DATA_HOME:-$HOME/.local/share}/google-android-agent-stack}
STACK_CACHE_ROOT  = ${ANDROID_AGENT_STACK_CACHE_ROOT:-${XDG_CACHE_HOME:-$HOME/.cache}/google-android-agent-stack}
STACK_CONFIG_ROOT = ${ANDROID_AGENT_STACK_CONFIG_ROOT:-${XDG_CONFIG_HOME:-$HOME/.config}/google-android-agent-stack}
HERMES_HOME       = ${HERMES_HOME:-$HOME/.hermes}
```

No hard-coded username appears anywhere in the contract.

| Root | Holds |
|---|---|
| `STACK_STATE_ROOT` | bridge / supervisor / browser state, live telemetry, locks, PIDs, sockets |
| `STACK_DATA_ROOT/artifacts` | evidence, evaluation sessions, benchmark results, screenshots, APKs, reports |
| `STACK_CACHE_ROOT` | disposable downloads, build caches, temporary baselines, reconstructed checkouts |
| `STACK_CONFIG_ROOT` | non-secret host configuration (rendered profile templates) |
| `HERMES_HOME` | installed Hermes runtime, profiles, provider state, secrets (mode 0600) |

Query from Python (see the module docstring) or from shell:

```bash
eval "$(scripts/stack-paths.sh export)"      # export all roots
scripts/stack-paths.sh query STACK_DATA_ROOT # one value
```

## Hermes source integrity

`orchestration/hermes/HERMES-LOCK.json` pins the upstream checkout at commit
`af90026aa0…`. The checkout under `$HERMES_HOME/hermes-agent` is a **clean pinned
third-party runtime** (verified: `git status --porcelain` empty, `HEAD` == the lock).
It stays under `HERMES_HOME` and is reproduced by `scripts/bootstrap-host.sh` from the lock.
Project-specific behaviour (provider, model, hooks, cwd) lives in the rendered profile
template, never as edits to Hermes core.

## Copy the project vs migrate host state

- **Copy the project** (source copy): enough to rebuild the runtime — run
  `scripts/bootstrap-host.sh` on the new host; it installs the pinned Hermes revision,
  renders the non-secret profile template, and prepares the Playwright venv (no Chromium
  download unless `--with-chromium`).
- **Migrate host state** (resume a live campaign): additionally export/import state:
  - `scripts/export-host-state.sh` → checksummed archive outside the project (secrets
    excluded unless `--include-secrets`);
  - `scripts/import-host-state.sh <archive>` → verifies checksums, rejects path traversal,
    restores with safe permissions, **never advances a campaign**.

## Tools

| Script | Purpose |
|---|---|
| `scripts/bootstrap-host.sh` | rebuild the host runtime from the lock (supports `--dry-run`) |
| `scripts/export-host-state.sh` | checksummed host-state archive outside the project |
| `scripts/import-host-state.sh` | verify + restore a host-state archive safely |
| `scripts/verify-layout.sh` | fail when generated outputs / absolute host paths reappear |
| `scripts/stack-paths.sh` | query the canonical path contract |

## Migration policy for existing generated data

Existing evidence/results/logs are **not deleted or moved** in the first pass. Instead they
are counted, hashed, archived under
`STACK_DATA_ROOT/artifacts/migration-archive/<timestamp>/` with a verified manifest, and a
proposed cleanup plan is written for human approval. New writes go to the external roots
immediately.
