# Verification Layer Architecture (v1.0.0)

## 1. Design identity

```
project-agnostic core
        +
Android adapter
        +
project-supplied journey / fixture / oracle / selectors
```

Extracted from the proven `verification-benchmark/harness/` (Harness v1.0), generalized, and
frozen as an interface. It is deliberately **not** "the KeepLab scripts with renamed paths".

## 2. Responsibility boundary (fixed)

### The layer owns (host side)

Preflight · install (app + test APK) · device lifecycle (snapshot/apply/restore of
orientation, theme, stay-awake, IME) · deterministic IME · executor lifecycle ·
timeout/watchdog · fail-fast · evidence capture + fallback · APK provenance · result schema ·
cleanup · evaluation handoff.

### The project owns (device side)

Journey (UI actions + deterministic assertions) · fixture (deterministic setup) ·
oracle (DB/domain ground truth) · selectors (stable automation identity) · package metadata
and APK paths.

### Host / instrumentation separation (mandatory)

Host owns: APK install, test APK install, force-stop, orientation, theme, IME, logcat,
`am instrument`, artifact pull, cleanup, provenance, timeout/watchdog.

Instrumentation owns: UI actions, deterministic assertions, DB/domain oracle, journey timing.

**Instrumentation NEVER `am force-stop`s the target app** (it runs in the app's process). The
host force-stops host-side before `am instrument`.

## 3. Components

| Component | Path | Responsibility |
|---|---|---|
| Contracts | `contracts/*.schema.json` | machine-readable plan / result / failure-bundle / run-state |
| Core lib | `core/lib_common.sh` | timeouts (`TIMEOUT_STAGE`), fail-fast, logging |
| Provenance | `core/provenance.py` | sha256 + expected-hash STOP (`APK_SHA_MISMATCH`) |
| Schema | `core/schema.py`, `core/validate_result.py` | result validation |
| Plan validation | `core/plan_validate.py` | plan → contract |
| Evidence | `core/evidence_completeness.py` | bundle completeness + format rules |
| Result emit | `core/result_emit.py` | `verification-result.json` (null-honest) |
| Android adapter | `android/*.sh` | preflight, lifecycle, IME, install, cleanup, input smoke, failure bundle |
| Device support | `android/uiautomator/*.kt` | timing log, journey base, UI driver, failure rule |
| Runner | `runner/run_verification.sh`, `runner/orchestrator.py` | bounded fail-fast stage machine |
| Evaluation adapter | `adapters/evaluation/verification_adapter.py` | T7-attributable handoff |
| Challenger | `challengers/maestro/` | reference engine, isolated |
| Auto-finalizer | `integration/autofinalizer/` | systemd --user activation |

## 4. Stage machine (runner)

```
load plan -> validate -> resolve serial -> preflight
-> APK provenance (STOP on mismatch) -> snapshot device state
-> cleanup -> install -> deterministic IME -> input smoke -> fixture seed
-> journey -> oracle -> collect -> emit result
   PASS -> compact result
   FAIL -> failure bundle + completeness
-> cleanup + restore device state -> evaluation handoff
```

Every stage is timeout-bounded and writes `run-state.json`. The first unexpected failure
stops the run (fail-fast) and still emits a standardized failed result.

## 5. Engine policy

- **Production default:** `engine: uiautomator` (UiAutomator 2.4.0).
- **Challenger/reference:** `engine: maestro`, under `challengers/`, always a separate plan.
- **Compose UI Test:** DEFERRED (observed Android 16 / API 36 Espresso/InputManager gap).

## 6. Migration mapping from the frozen benchmark harness

`verification-benchmark/` is **not modified**. It remains the historical benchmark evidence
and regression reference. Mapping:

| Benchmark harness | Verification Layer |
|---|---|
| `harness/lib.sh` (timeout/fail-fast/state) | `core/lib_common.sh` + `android/lib_android.sh` |
| `harness/preflight.sh` | `android/preflight.sh` (engine-agnostic, plan-driven) |
| `harness/ime.sh` | `android/ime.sh` (`uiautomator`/`maestro`) |
| `harness/cleanup_engine.sh` | `android/cleanup_engine.sh` |
| `harness/input_smoke.sh` | `android/input_smoke.sh` |
| `harness/collect_failure.sh` | `android/collect_failure.sh` + `android/evidence/layout.sh` |
| `harness/apk_provenance.py` | `core/provenance.py` |
| `harness/schema.py`, `validate_result.py` | `core/schema.py`, `core/validate_result.py` |
| `harness/evidence_completeness.py` | `core/evidence_completeness.py` |
| `harness/emit_run.py` | `core/result_emit.py` |
| `harness/run_engine_b.sh` / `run_engine_c.sh` | `runner/orchestrator.py` (+ `challengers/maestro/`) |
| `harness/run_engine_a.sh` (control) | benchmark-only (not promoted) |
| `harness/stage1.sh`, `measure.py`, `baseline_guard.py` | benchmark-only (not promoted) |
| `benchmark-apk.json`, `frozen/`, `results/` | benchmark-only (not promoted) |
| Kotlin `BenchSupport/JourneyBase/UiDriver/FailureBundleRule` | `android/uiautomator/*.kt` (generic; package injected) |
| Kotlin `J1..J3JourneyTest`, `FixtureSeeder`, `Verifier`, `DbProbe` | `examples/keeplab/` (project-specific) |

No compatibility wrapper is installed inside the frozen benchmark: adding files there could
disturb reproducibility. The old harness stays byte-identical; this document is the mapping.

## 7. Known limitations

- Device-side support ships as **reference Kotlin source**, not a packaged AAR.
- The runner drives project instrumentation by **declared class name**; there is no dynamic
  plugin discovery.
- Compose UI Test remains DEFERRED.
- Maestro is challenger-only.
- One Command Code session ⇒ one auto-archived Evaluation (Evaluation Core limit; docs
  recommendation added).

## 8. Versioning

`VERSION` = `1.0.0` — the Verification Layer. Distinct from the benchmark's **Harness v1.0**.
