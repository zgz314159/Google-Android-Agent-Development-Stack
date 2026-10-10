# Verification Layer Promotion — Recon & Classification Plan

Reconnaissance for **Verification Layer Promotion / Productization v1.0**.

- Status: recon complete, classification frozen
- Date: 2026-10-03
- Root: `/mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack`
- Source of truth: `verification-benchmark/` (harness v1.0), `evaluation/` (v0.2.1)
- Principle: **Extract → Generalize → Validate → Freeze interface**

Scope of this recon was limited to `verification-benchmark/`, `evaluation/`, the Stack
`reports/`, and the KeepLab benchmark `androidTest` sources. No whole-`Projects` scan.

---

## 1. What was read

| Area | Files | Lines |
|---|---|---|
| Harness | `verification-benchmark/harness/*` (20 files) | ~2,460 |
| Harness tests | `harness/tests/*.py` (6 test modules) | ~472 |
| Docs | `docs/VERIFICATION-SELECTOR-CONTRACT.md`, `README.md` | ~105 |
| Hardening proof | `reports/FINAL-VERIFICATION-HARNESS-HARDENING.md`, `reports/hardening/health.json` | — |
| Journeys / flows | `journeys/J1..J3`, `maestro/J1..J3`, `maestro/INPUT-SMOKE.yaml` | — |
| Frozen identity | `benchmark-apk.json`, `results/baseline-manifest.json` | — |
| Evaluation | `evaluation/commandcode/*` (core, adapter, auto-finalizer), `README.md`, tests | — |
| Device instrumentation | `Worktrees/.../androidTest/.../benchmark/*.kt` (13 files) | 750 |

## 2. Structural finding

The proven harness is already **two halves**, which is the whole basis for the promotion:

| Half | Location | Reusability |
|---|---|---|
| Host orchestration | `harness/*.sh`, `harness/*.py` | Generic once KeepLab constants are removed |
| Device instrumentation | project `androidTest` APK (Kotlin) | Project-specific by definition |

Therefore the **project plugin boundary** is: the project ships an androidTest APK
(journey, fixture seeder, DB oracle, failure rule); the Verification Layer ships all host
orchestration and addresses those classes by name via a machine-readable plan.

## 3. Hardcoded KeepLab seams in the harness (de-projectization targets)

| File | Hardcode |
|---|---|
| `lib.sh` | `PKG=com.keeplab.app`, `TEST_PKG=com.keeplab.app.test`, `WT=…/KeepLab-Verification-Compression`, `APP_APK=$BASE/frozen/app-debug-frozen.apk`, engine→IME map |
| `run_engine_b.sh` | `SERIAL=87296ada`, frozen SHA read from `benchmark-apk.json`, `…benchmark.${JOURNEY}JourneyTest`, `FixtureSeeder#seed$JOURNEY`, device model `Redmi Note 7 Pro`, `API=36` |
| `run_engine_c.sh` | same + `DbProbe`, `$BASE/maestro/$JOURNEY.yaml`, AOSP IME |
| `emit_run.py` | crash scope `com\.keeplab\.app`, default launch test `com.keeplab.app.benchmark.*` |
| `input_smoke.sh` | `com.keeplab.app.benchmark.InputSmokeTest`, Maestro PATH |
| `collect_failure.sh` / `cleanup_engine.sh` | KeepLab + Maestro + Android-CLI package lists |

## 4. Classification

### A. Generic reusable → `verification/core/`
- `with_timeout` + `TIMEOUT_STAGE` + watchdog heartbeat
- fail-fast (`die` / `STAGE_FAIL` / `HARNESS_ERROR`) + `run-state.json`
- APK provenance (`apk_provenance.py`: app + optional test, expected-hash STOP)
- result schema validation (`schema.py`, `validate_result.py`)
- failure-bundle completeness (`evidence_completeness.py`)
- measurement classification / deny-by-default concept (from `measure.py` + manifest)

### B. Android-specific reusable → `verification/android/`
- `preflight.sh` — device identity, awake, keyguard, storage, orientation/theme, IME availability
- lifecycle — state snapshot/restore (stay-awake, orientation, night mode, IME)
- `ime.sh` — deterministic IME, verify-set, engine→component
- idempotent install (`adb install -r` + package verify)
- `cleanup_engine.sh` — targeted force-stop + UiAutomation conflict check
- `input_smoke.sh` — bounded input round-trip, never a metric
- `collect_failure.sh` + layout fallback chain (android_cli → uiautomator_xml → screenshot/logcat/dumpsys)
- `uiautomator/` device-side support sources (TimingLogger, JourneyBase, UiDriver, FailureBundleRule)

### C. KeepLab-specific → `verification/examples/keeplab/` only
- `J1/J2/J3JourneyTest.kt`, `FixtureSeeder.kt`, `Verifier.kt`, `DbProbe.kt`, `IntentionalFailureTest.kt`, `SpikeTest.kt`
- `VC-*` fixtures, `keeplab.db`, `Work` label, KeepLab business assertions
- `maestro/J1..J3.yaml`, `journeys/J1..J3-*.md`
- concrete plan / selectors / expected PASS + FAIL artifacts

### D. Benchmark-only → stays in `verification-benchmark/`
- benchmark drivers (`run_engine_*.sh`, `stage1.sh`), `measure.py` + `summary.*`
- `baseline_guard.py`, `results/baseline-manifest.json`, frozen 27-run data
- `benchmark-apk.json`, `frozen/app-debug-frozen.apk`, `selftest_device.sh`

### E. Challenger-only → `verification/challengers/maestro/`
- Maestro flow runner + input smoke, AOSP IME for the challenger, shared DB oracle plumbing

## 5. Reference fixed facts (trusted, not re-derived)

- Frozen APK sha256: `a8858bd1f57b328a5042a120023508ced8e1cbbf68446bab3ce0e5e80f6fdf06`
- Baseline: A=3 / B=11 / C=13 = 27; compression B=96.6%, C=89.4%
- Production engine: UiAutomator 2.4.0. Maestro = challenger. Compose UI Test = DEFERRED (API 36).

## 6. Target layout

`verification/{contracts,core,android,runner,adapters,challengers,examples,tests,docs}` + `VERSION 1.0.0`.
Full structure and contracts in the approved plan
(`~/.commandcode/plans/verification-layer-promotion-v1.0.md`).

`verification-benchmark/` is **not modified**; migration mapping is documented in
`verification/docs/ARCHITECTURE.md` (no compatibility wrapper — frozen reproducibility is
preserved by leaving the old harness byte-identical).

## 7. Go / no-go

Classification complete. No blocker identified. Proceeding to scaffold + extraction.
