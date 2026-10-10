# Hermes Integration Smoke (S1)

Generated: 2026-10-04 · Profile: `android-stack` · Device: `87296ada` (offline this session)

## 1. Install / discovery

| Item | Value |
|---|---|
| Upstream | `https://github.com/NousResearch/hermes-agent.git` (official) |
| Install method | official installer `install.sh` (user scope, no sudo Hermes) |
| Branch / commit | `main` @ `af90026aa09949579bd423d24def3d38f743cde0` |
| Version string | `vgit.af90026 (2026.9.24)` · latest stable tag `v2026.9.24` (v0.21.5) |
| Install dir | `/home/zhong/.hermes/hermes-agent` |
| Python | 3.14.7 (Hermes-managed) |
| Frozen | `orchestration/hermes/HERMES-LOCK.json` |

**Required official CommandCode fixes present in the pinned commit:**

- `779aecb62` — *fix(context): resolve commandcode models via live /models* (model discovery)
- `30d14a3f7` — *fix: name the CommandCode upstream-outage pattern* (transient upstream 429 classification)

No Hermes core patch. No `hermes update` will be run.

### `hermes doctor`

**PASS_WITH_DOCUMENTED_NONBLOCKING_WARNING**: config/venv/SSL/required packages all OK.
Non-blocking warnings only (all expected for this install): `agent-browser` not installed
(skipped by design — browser tools are out of scope), optional `python-telegram-bot` /
`discord.py` not installed, `Docker/Podman` absent, no OAuth portal logins (not used),
lockfile advisories in optional web deps.

## 2. CommandCode provider (one-shot smoke)

```
hermes -p android-stack --usage-file … -z "Reply exactly: HERMES_COMMANDCODE_OK"
```

| Field | Value |
|---|---|
| provider | `commandcode` |
| model | `deepseek/deepseek-v4.1-flash` |
| response | `HERMES_COMMANDCODE_OK` |
| exit code | 0 |
| wall | ≈ 9.2 s |
| credential | `COMMANDCODE_API_KEY` present (value never printed; mapped into profile `.env`, mode 600) |

**Result: PASS.** Credential gate: configured = true (key existed in `~/.hermes/.env`;
mapped into the `android-stack` profile `.env`). `COMMAND_CODE_API_KEY` unset;
`~/.commandcode/auth.json` was **not** read for a value.

## 3. Delegation smoke (read-only, parallel)

Root prompt: batch-delegate three independent read-only readiness summaries
(Specification / Verification / Evaluation), no writes.

| Field | Value |
|---|---|
| root_session | `20261004_234211_d5c6af` |
| children_started | 3 |
| children_completed | 3 |
| max_concurrent_children | 3 |
| parallel_overlap_sec | 12.078 |
| child statuses | completed / completed / completed |
| child sessions | `…_3702d4` (Evaluation), `…_7a30bd` (Specification), `…_aeae6d` (Verification) |
| root wall | ≈ 24.8 s |
| child writes | 0 |

Raw: `orchestration/hermes/evidence/delegation-sessions.json`,
`orchestration/hermes/evidence/hermes-run-summary.json`.

**Result: PASS.** (An earlier attempt was refused because `delegation.oneshot_max_children`
was 2; raised to 4 — recorded honestly.)

## 4. Kanban DAG probe

Board `s1-probe` (isolated, kept for evidence):

| Task | Dependency | State while A/B/C open | After A/B/C done |
|---|---|---|---|
| A `t_86cbe997` | — | ready | done |
| B `t_f528eb29` | — | ready | done |
| C `t_79275590` | — | ready | done |
| D `t_a10901b8` | A,B,C | **todo (blocked)** | **ready** |

**Dependency behavior: PASS** — D was not dispatchable until all three parents completed.
The board is preserved (not used for P0B).

## 5. Evaluation adapter (thin)

`orchestration/hermes/evaluation_adapter/hermes_run_summary.py` read the real profile
`state.db` (read-only) and emitted `hermes-run-summary.json`. Missing fields are
`null` / `NOT_AVAILABLE`. Evaluation Core v0.2.3 untouched.

## Gates

| Gate | Result |
|---|---|
| HERMES INSTALLED | YES |
| OFFICIAL UPSTREAM | YES |
| PINNED VERSION/COMMIT | YES |
| DOCTOR | PASS_WITH_DOCUMENTED_NONBLOCKING_WARNING |
| COMMANDCODE PROVIDER | PASS |
| MODEL | deepseek/deepseek-v4.1-flash |
| HERMES ONE-SHOT | PASS |
| HERMES DELEGATION | PASS |
| HERMES CHILDREN | 3 (≥3) |
| HERMES KANBAN DAG | PASS |
| NO HERMES CORE PATCH | YES |
