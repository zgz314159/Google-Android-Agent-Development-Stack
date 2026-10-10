# Verification Harness Hardening Plan (v0.1 → v1.0)

Target: raise the proven deterministic UiAutomator harness from "works" to stable,
repeatable, fail-fast, low-touch, promotable. **No A/B/C re-run, no baseline mutation.**

Frozen baseline (do not change): 27 runs (A=3, B=11, C=13), B=96.6% / C=89.4%,
APK `a8858bd1f57b328a5042a120023508ced8e1cbbf68446bab3ce0e5e80f6fdf06`.

Status legend: `PENDING` · `IN_PROGRESS` · `PASS` · `FAIL` · `N/A`

## P0

| # | Item | Artifact | Status |
|---|---|---|---|
| P0-1 | device preflight | `harness/preflight.sh`, `harness/preflight-result.json` | PASS |
| P0-2 | fail-fast | `harness/lib.sh`, runners, `stage1.sh` | PASS |
| P0-3 | Engine B/C isolation | `harness/cleanup_engine.sh`, orchestrator grouping | PASS |
| P0-4 | deterministic IME | `harness/ime.sh`, preflight | PASS |
| P0-5 | host/device lifecycle separation | `harness/lib.sh`, docs | PASS |
| P0-6 | stable install/instrumentation runner | `harness/lib.sh` (`install_idempotent`), runners | PASS |
| P0-7 | UiAutomation cleanup | `harness/cleanup_engine.sh` | PASS |
| P0-8 | evidence fallback | `harness/collect_failure.sh` | PASS |
| P0-9 | failure bundle completeness | `harness/evidence_completeness.py` | PASS |
| P0-10 | run-state cleanup/idempotency | `harness/lib.sh` (`run-state.json`, trap) | PASS |
| P0-11 | timeout/watchdog | `harness/lib.sh` (`with_timeout`, heartbeat) | PASS |
| P0-12 | result schema validation | `harness/schema.py`, `harness/validate_result.py` | PASS |

## P1

| # | Item | Artifact | Status |
|---|---|---|---|
| P1-13 | selector contract | `docs/VERIFICATION-SELECTOR-CONTRACT.md` | PASS |
| P1-14 | Evaluation adapter tests | `harness/tests/test_external_adapter.py` | PASS |
| P1-15 | crash attribution tests | `harness/tests/test_emit_run.py` | PASS |
| P1-16 | APK provenance enforcement | `harness/apk_provenance.py`, runners | PASS |
| P1-17 | deterministic device-state restore | `harness/lib.sh` (`state_snapshot`/`state_restore`) | PASS |
| P1-18 | machine-readable hardening health report | `reports/hardening/health.json`, `reports/FINAL-VERIFICATION-HARNESS-HARDENING.md` | PASS |

## Frozen-file guard

`reports/hardening/baseline-before.sha256` captures sha256 of every frozen file before
hardening (`benchmark-apk.json`, `frozen/app-debug-frozen.apk`, `results/baseline-manifest.json`,
`results/summary.json`, `results/summary.csv`, `results/normalized-benchmark.json`,
`results/run-inventory.json`, and all 27 `results/*/benchmark-run.json`). `harness/baseline_guard.py`
re-checks them after hardening.

## Diagnostic runs

Hardening smoke runs use `BENCH_DIAGNOSTIC=1` → run id `HARDEN-*`, `measurement_class=diagnostic`,
`excluded_from_baseline=true`, written under `results/HARDEN-*`. `measure.py`'s deny-by-default
allowlist keeps them out of the measured set. `baseline-manifest.json` is **not** edited.

## Not in scope

Re-running A/B/C, re-measuring compression, rebuilding/replacing the frozen APK, modifying
KeepLab business code / PowerAi, redesigning journeys or the Evaluation Core, upgrading
AGP/Kotlin/Compose/Room, re-attempting Compose UI Test, evaluating new frameworks.
