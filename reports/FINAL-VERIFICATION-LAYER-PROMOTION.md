# FINAL — Verification Layer Promotion / Productization v1.0

Promoted the proven deterministic UiAutomator harness out of `verification-benchmark/` into a
formal, project-agnostic, reusable **Verification Layer** at
`Google-Android-Agent-Development-Stack/verification/` (v1.0.0).

Generated: 2026-10-03
Root: `/mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack`

---

## 1. Source baseline

`verification-benchmark/harness/` **Harness v1.0** (`PROMOTION_READINESS = READY`), with
`docs/VERIFICATION-SELECTOR-CONTRACT.md`, `reports/FINAL-VERIFICATION-HARNESS-HARDENING.md`,
`reports/hardening/health.json`, and `results/baseline-manifest.json` as the frozen
reference. No A/B/C re-run, no baseline mutation, no frozen-APK replacement.

## 2. Files extracted

Extract → Generalize (not copy-with-renamed-paths). ~30 new production files under
`verification/`:

- `contracts/` — 4 JSON schemas
- `core/` — `lib_common.sh`, `provenance.py`, `schema.py`, `validate_result.py`,
  `evidence_completeness.py`, `plan_validate.py`, `result_emit.py`
- `android/` — `lib_android.sh`, `preflight.sh`, `lifecycle.sh`, `ime.sh`, `install.sh`,
  `cleanup_engine.sh`, `input_smoke.sh`, `collect_failure.sh`, `evidence/layout.sh`
- `android/uiautomator/` — `TimingLogger.kt`, `JourneyBase.kt`, `UiDriver.kt`,
  `FailureBundleRule.kt`, `README.md`
- `runner/` — `run_verification.sh`, `orchestrator.py`
- `adapters/evaluation/` — `verification_adapter.py`
- `integration/autofinalizer/` — service/timer templates, `install.sh`, `README.md`
- `challengers/maestro/` — `run_maestro.sh`, `README.md`
- `examples/keeplab/` — plan(s), journey/fixture/oracle Kotlin, selectors, maestro flows,
  expected PASS/FAIL artifacts, README
- `tests/` — 8 unit modules, fixtures, `smoke/selftest_static.sh`
- `docs/` — ARCHITECTURE, VERIFICATION-SELECTOR-CONTRACT, FAILURE-EVIDENCE-CONTRACT,
  ANDROID-LIFECYCLE-CONTRACT, INTEGRATION-GUIDE
- `README.md`, `VERSION` (`1.0.0`)

## 3. Generic vs Android vs KeepLab-specific boundaries

- **Generic** → `core/` (timeout/watchdog, fail-fast, provenance, schema, evidence,
  plan validation, result emit).
- **Android-specific** → `android/` (preflight, lifecycle, IME, install, cleanup, evidence)
  + device-side `uiautomator/` support sources.
- **KeepLab-specific** → `examples/keeplab/` only.
- **Benchmark-only** → stays in `verification-benchmark/` (drivers, `measure.py`,
  `baseline_guard.py`, frozen data).
- **Challenger-only** → `challengers/maestro/`.

Plan: `reports/VERIFICATION-LAYER-PROMOTION-PLAN.md`.

## 4. Production architecture

```
project-agnostic core + Android adapter + project-supplied journey/fixture/oracle/selectors
```

`verification/docs/ARCHITECTURE.md` documents the fixed responsibility boundary, the host/
instrumentation split, and the benchmark→layer migration mapping.

## 5. Contracts

`contracts/verification-plan.schema.json`, `verification-result.schema.json`,
`failure-bundle.schema.json`, `run-state.schema.json`. Validated by
`core/plan_validate.py` and `core/schema.py` (stdlib only). Result values that cannot be
proven are `null`, never estimated.

## 6. Runner

`verification/runner/run_verification.sh <verification-plan.json>` → `orchestrator.py`:
bounded fail-fast stage machine (load → validate → preflight → provenance → snapshot/apply →
cleanup → IME → install → reset → input smoke → seed → journey → oracle → collect → emit →
(failure bundle) → cleanup + restore). `--dry-run` for offline use.

## 7. UiAutomator default

`engine: uiautomator` is the production default. The benchmark name "Engine B" does not appear
in production. The runner drives the project's instrumentation classes by declared name.

## 8. Maestro challenger

Under `verification/challengers/maestro/`, invoked only when a plan declares
`engine: maestro`; always a separate plan; never shares a UiAutomator run.

## 9. Compose deferred

```
Compose UI Test: DEFERRED
reason: observed Android 16 / API 36 Espresso/InputManager compatibility gap
```

Recorded in README + ARCHITECTURE; not retried this round.

## 10. Host / instrumentation lifecycle

Host owns install/force-stop/orientation/theme/IME/logcat/`am instrument`/pull/cleanup/
provenance/timeout. Instrumentation owns UI actions/assertions/oracle/timing and never
force-stops the app. `docs/ANDROID-LIFECYCLE-CONTRACT.md`.

## 11. Evidence contract

PASS → compact `verification-result.json` (large run-scoped logcat removed). FAIL →
`failure/` bundle with metadata/screenshot/layout/logcat/dumpsys/executor-output/
failed-assertion/db-state, merged in-process artifacts, and `completeness.json`. Provider
chain android_cli → uiautomator_xml → unavailable; XML never relabelled `.json`.
`docs/FAILURE-EVIDENCE-CONTRACT.md`.

## 12. Timeout / watchdog

Every stage bounded; `with_timeout` emits `TIMEOUT_STAGE=<stage>` (verified in
`selftest_static.sh`). `run-state.json` records `stage/started_at/last_progress_at/
cleanup_at` (verified in the device smoke).

## 13. Provenance

`core/provenance.py` records `apk_sha256` (+ optional `test_apk_sha256`), STOPS with
`APK_SHA_MISMATCH` on mismatch. The result carries app/test hashes, layer/runner version, and
device identity. Smoke app sha256 =
`a8858bd1f57b328a5042a120023508ced8e1cbbf68446bab3ce0e5e80f6fdf06`.

## 14. Evaluation integration

`adapters/evaluation/verification_adapter.py` produces a T7-attributable handoff document
(read-only, add-on). Contract test:
`tests/unit/test_verification_adapter.py` + a real handoff run against the smoke result
(`clocks.total_wall_ms=21385`, `T7a/T7b/T7c` = 1802.849 / 17252.901 / 61.275 ms). No Evaluation
Core rewrite, no Phase C.

## 15. Auto-Finalizer operational state

Installed as `systemd --user` timer + oneshot `scan` (non-root, `~/.config/systemd/user/` only,
no `/etc`, bounded journald logs, crash-safe re-fire, `--stable-seconds 60`):

```
timer:   active
service: Result=success  ExecMainStatus=0
scan:    SUCCESS/INCOMPLETE/ALREADY_FINALIZED as appropriate
```

## 16. Compatibility

`verification-benchmark/` is **unchanged**. No compatibility wrapper was inserted (adding files
there could disturb reproducibility). Migration mapping is documented in
`verification/docs/ARCHITECTURE.md`.

## 17. Decoupling audit

`reports/VERIFICATION-LAYER-DECOUPLING-AUDIT.md` →

```
DECOUPLING_AUDIT=PASS
```

Enforced by `tests/unit/test_decoupling_audit.py`.

## 18. Tests

- Static: `bash -n`, `py_compile`, JSON schema parse, `selftest_static.sh` → `SELFTEST_STATIC=PASS`.
- Unit/contract: 38 tests, `OK` (schema, plan validation, evidence completeness, provenance,
  result emit, adapter, decoupling, dry-run).
- Fixture integration (no device): runner `--dry-run` → schema-valid result.

## 19. Device smoke

Exactly one UiAutomator reference smoke (no J2/J3, no A/B/C, no compression recompute):

```
verification_id  KEEPLAB-REFERENCE-J1   (measurement_class=diagnostic, excluded_from_baseline=true)
outcome          PASS
setup_wall_ms    15189
total_wall_ms    21385
t7a/t7b/t7c      1802.849 / 17252.901 / 61.275 ms
database         PASS (4/4 checks)
process          no-crash
```
Output under `verification/.runs/` — never in the frozen benchmark.

## 20. Baseline unchanged

```
BASELINE_COUNTS A=3 B=11 C=13 total=27
BASELINE_COMPRESSION B=96.6% C=89.4%
BASELINE_FROZEN_FILES checked=34 changed=0
BASELINE_GUARD=PASS
```

## 21. Known limitations

- Device-side support is reference Kotlin source, not a packaged AAR.
- Runner targets project instrumentation by declared class name; no dynamic plugin discovery.
- Compose UI Test deferred; Maestro challenger-only.
- One Command Code session ⇒ one auto-archived Evaluation (core limit; docs recommendation).

## 22. Phase C readiness

The layer exposes T7 evidence and machine markers; `verification-plan`/result contracts are
frozen. Phase C (`KeepLab Phase C — Real Feature Increment`) can now run the full loop. No
T2/T6 optimization was performed; event hooks (`verification_execution_started/finished`) are
recorded in the plan rather than implemented.

---

```
VERIFICATION LAYER PROMOTION v1.0
=================================

SOURCE HARNESS: READY
PRODUCTION LAYER CREATED: PASS
PROJECT-AGNOSTIC CORE: PASS
ANDROID ADAPTER: PASS
UIAUTOMATOR DEFAULT: PASS
MAESTRO CHALLENGER ISOLATED: PASS
COMPOSE UI TEST STATUS: DEFERRED
VERIFICATION PLAN CONTRACT: PASS
RUNNER: PASS
SELECTOR CONTRACT: PASS
HOST / INSTRUMENTATION SEPARATION: PASS
FAIL-FAST: PASS
EVIDENCE CONTRACT: PASS
TIMEOUT / WATCHDOG: PASS
APK PROVENANCE: PASS
EVALUATION ADAPTER: PASS
AUTO-FINALIZER OPERATIONAL: PASS
KEEP LAB DECOUPLING: PASS
CAPABILITY MATRIX: PASS
STATIC / CONTRACT TESTS: PASS
DEVICE REFERENCE SMOKE: PASS
FROZEN BENCHMARK MODIFIED: NO
TESTAPP MODIFIED: NO
POWERAI MODIFIED: NO
GIT COMMIT CREATED: NO
VERIFICATION LAYER VERSION: 1.0.0
PROMOTION STATUS: READY
PHASE C READINESS: READY
REPORT: /mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack/reports/FINAL-VERIFICATION-LAYER-PROMOTION.md
```
