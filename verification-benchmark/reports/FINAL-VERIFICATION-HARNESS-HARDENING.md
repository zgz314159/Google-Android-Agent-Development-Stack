# FINAL — Verification Harness Hardening v0.1 → v1.0

Hardened the proven deterministic UiAutomator harness from "works" to stable, repeatable,
fail-fast, low-touch, promotable. **No A/B/C benchmark re-run, no baseline mutation, no
app/PowerAi/Journey/Evaluation-Core change.**

Generated: 2026-10-03 · Root:
`/mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack/verification-benchmark/`

Machine-readable companion: **`reports/hardening/health.json`**, plus
`reports/hardening/device-smoke.json`, `reports/hardening/baseline-invariants.json`,
`reports/hardening/baseline-before.sha256`.

## Verdict

```
PROMOTION_READINESS = READY
```

All P0 and P1 items PASS. The frozen 27-run baseline is provably unchanged.

---

## 1. P0 / P1 checklist

### P0

| # | Item | Artifact | Result |
|---|---|---|---|
| 1 | device preflight | `harness/preflight.sh` + `harness/preflight-result.json` | **PASS** |
| 2 | fail-fast | `harness/lib.sh`, runners, `stage1.sh` | **PASS** |
| 3 | Engine B/C isolation | `harness/cleanup_engine.sh` | **PASS** |
| 4 | deterministic IME | `harness/ime.sh` | **PASS** |
| 5 | host/device lifecycle separation | `harness/lib.sh`, docs | **PASS** |
| 6 | stable install/instrumentation runner | `install_idempotent`, `am instrument` host flow | **PASS** |
| 7 | UiAutomation cleanup | `harness/cleanup_engine.sh` | **PASS** |
| 8 | evidence fallback | `harness/collect_failure.sh` | **PASS** |
| 9 | failure bundle completeness | `harness/evidence_completeness.py` | **PASS** |
| 10 | run-state cleanup/idempotency | `run-state.json` + trap | **PASS** |
| 11 | timeout/watchdog | `with_timeout`, heartbeat | **PASS** |
| 12 | result schema validation | `harness/schema.py`, `validate_result.py` | **PASS** |

### P1

| # | Item | Artifact | Result |
|---|---|---|---|
| 13 | selector contract | `docs/VERIFICATION-SELECTOR-CONTRACT.md` | **PASS** |
| 14 | Evaluation adapter tests | `harness/tests/test_external_adapter.py` | **PASS** |
| 15 | crash attribution tests | `harness/tests/test_emit_run.py` | **PASS** |
| 16 | APK provenance enforcement | `harness/apk_provenance.py` | **PASS** |
| 17 | deterministic device-state restore | `lib.sh` `state_snapshot`/`state_restore` | **PASS** |
| 18 | machine-readable health report | `reports/hardening/health.json` | **PASS** |

## 2. Files changed / added

**Added (harness):** `lib.sh`, `preflight.sh`, `ime.sh`, `cleanup_engine.sh`,
`input_smoke.sh`, `apk_provenance.py`, `schema.py`, `validate_result.py`,
`evidence_completeness.py`, `baseline_guard.py`, `selftest_static.sh`, `selftest_device.sh`,
`VERSION`, `tests/` (`__init__`, `test_emit_run`, `test_schema`,
`test_evidence_completeness`, `test_measurement_classification`, `test_external_adapter`,
`test_baseline_guard`).

**Modified (harness):** `run_engine_b.sh`, `run_engine_c.sh`, `collect_failure.sh`,
`emit_run.py`, `stage1.sh`.

**Added (benchmark):** `maestro/INPUT-SMOKE.yaml`,
`docs/VERIFICATION-SELECTOR-CONTRACT.md`, `reports/HARDENING-PLAN.md`,
`reports/GIT-BASELINE-RECOMMENDATION.md`, `reports/FINAL-VERIFICATION-HARNESS-HARDENING.md`,
`reports/hardening/{health,device-smoke,baseline-invariants}.json`,
`reports/hardening/baseline-before.sha256`.

**Added (worktree, benchmark-only, test APK only):**
`app/src/androidTest/java/com/keeplab/app/benchmark/InputSmokeTest.kt`; test APK rebuilt via
`./gradlew :app:assembleDebugAndroidTest`. **The frozen app APK was not rebuilt or replaced**
(`frozen/app-debug-frozen.apk` unchanged, sha256 verified).

## 3. Preflight

`harness/preflight.sh B` on device `87296ada`:

```
outcome=PASS api=36 model="Redmi Note 7 Pro" awake=true keyguard_locked=false
ime_available=true orientation_ready=true theme_ready=true adb_ready=true
serial_unique=true free_space_mb≈97334
```

Secure-lock behaviour: a showing keyguard yields `DEVICE_LOCKED_REQUIRES_OWNER_UNLOCK` and
stops (never bypassed); a missing target IME yields `IME_UNAVAILABLE`. Device identity
(model/API/ABI) is recorded as metadata and only fails if `EXPECTED_DEVICE`/`EXPECTED_API`
is set.

## 4. Fail-fast proof

`selftest_device.sh` runs the Engine B intentional-failure run inside `set -e` followed by a
sentinel file that must not be created:

```
fail-fast: rc=1 sentinel_absent=yes
```

The run returned non-zero **before** any subsequent run, collected the failure bundle, and
wrote `outcome.json = {primary_outcome: FAIL, cleanup_outcome: OK}`.
`run-state.json` preserved the failing stage: `"stage": "fail"` (+ `cleanup_at`), so the
watchdog trail survives cleanup. `stage1.sh` now aborts on the first failed run and asserts
the expected run count.

## 5. Engine isolation proof

Orchestrators group by engine (`B … cleanup … UiAutomation release check … C`), never
`B-J1/C-J1` interleaving. `cleanup_engine.sh` targets only known benchmark/tool packages
(`com.keeplab.app`, `.test`, `dev.mobile.maestro(.test)`, `com.android.cli`,
`com.android.cli.interact.instrumentation`) and checks for a surviving UiAutomation holder;
if one persists it prints `UIAUTOMATION_CONFLICT_SUSPECTED` + `CLEANUP_INCOMPLETE` and STOPS.

During the smoke a lingering `com.android.cli.interact.instrumentation` (spawned by our own
`android layout` evidence call) was cleaned and the subsequent `--check-only` passed:
`ENGINE_CLEANUP=OK` → Engine C Maestro smoke `INPUT_SMOKE=PASS engine=C`.

## 6. IME determinism proof

`harness/ime.sh` verifies → enables → sets → **verifies current** IME per engine; failure is
fatal. Observed:

```
Engine B: IME_SET=com.google.android.inputmethod.latin/com.android.inputmethod.latin.LatinIME  IME_VERIFIED=<same>
Engine C: IME_SET=com.android.inputmethod.latin/.LatinIME                                      IME_VERIFIED=<same>
```

The IME is re-established before every measured run; the previous engine's IME is never assumed.

## 7. Host/device lifecycle proof

Host owns install / force-stop / orientation / theme / IME / logcat-clear / `am instrument` /
artifact pull / cleanup; instrumentation owns only UI actions, assertions, DB and timing.
Instrumentation never calls `am force-stop` (documented in `SpikeTest.kt`, enforced by
`input_smoke.sh`/runners). The runner is `adb install -r` + `adb shell am instrument -w`;
Gradle only builds the test APK — `connectedDebugAndroidTest` is not the runner.

## 8. Input smoke (never a metric)

`InputSmokeTest` (Engine B) and `maestro/INPUT-SMOKE.yaml` (Engine C) verify a field is
locatable and that a fixed ASCII probe round-trips, then discard it. Both PASS; the smoke
writes no events and no `verify-part.json`, so it cannot enter the metric. **PASS.**

## 9. Evidence completeness proof

`collect_failure.sh` records every unavailable artifact in `metadata.json` as
`{artifact, available:false, reason}` and enforces the format rule (JSON stays `.json`; the
`uiautomator dump` XML stays `layout.xml`, never relabelled). `evidence_completeness.py`
validated the intentional-failure bundle:

```
complete=true present=[db-state, executor-output, failed-assertion, layout.json,
                       logcat, metadata, screenshot]  missing=[] errors=[]
```

The two historical diagnostic bundles (`FAILTEST-B`, `FAILTEST-C`) also validate `complete=true`.

## 10. Crash attribution

`emit_run.py` scopes FATAL to `Process: com.keeplab.app` (boundary-aware, so
`com.keeplab.app.test` does not match) and maps `ANR in com.keeplab.app` → CRASH; raw signal
kept as `process_evidence_raw`. Unit tests (no device):

- CASE 1 app-process FATAL → `CRASH` ✓
- CASE 2 `com.android.cli.interact.instrumentation` FATAL → `no-crash` ✓
- CASE 3 `ANR in com.keeplab.app` → `CRASH` ✓
- CASE 4 unrelated system FATAL → `no-crash` ✓
- extra: `com.keeplab.app.test` FATAL / ANR → `no-crash` ✓

## 11. Schema validation

`harness/schema.py` validates required fields, types (`api` is a **string**; `t7a/b/c_ms`
nullable numeric) and closed enums (`outcome`, `process_evidence`, `ui_evidence`,
`measurement_class`). `emit_run.py` self-validates every written result; unknown
`measurement_class` fails. All 27 frozen runs and both HARDEN runs validate PASS.

## 12. APK provenance

`apk_provenance.py` computes sha256 and enforces `EXPECTED_APK_SHA` (STOP on mismatch); every
result records `apk_sha256`, `test_apk_sha256`, `harness_version`, `runner_version`.

```
frozen/observed app apk_sha256 = a8858bd1f57b328a5042a120023508ced8e1cbbf68446bab3ce0e5e80f6fdf06
test_apk_sha256                = c13b8def9d34dae7753106aeebc9da0c7959f51e3781b1b5880dac6f49e2f821
harness_version = 1.0   runner_version = androidx.test.runner.AndroidJUnitRunner
```

## 13. Cleanup / timeout / watchdog behaviour

Cleanup is exact and bounded; a cleanup failure is recorded separately and never overwrites
the primary outcome (`primary_outcome=FAIL`, `cleanup_outcome=OK`).

`with_timeout` prints `TIMEOUT_STAGE=<stage>` and returns 124; verified in the static
self-test (`TIMEOUT_STAGE=timeout_probe`). `run-state.json` carries
`stage/journey/engine/started_at/last_progress_at/cleanup_at`, so a hang is attributable to a
stage; verified in the static self-test and in the intentional-failure run.

## 14. Diagnostic smoke (on-device)

```
Engine B J1 x1     HARDEN-B-J1-smoke          outcome=PASS
Engine B intent-fail HARDEN-B-INTENTIONAL-FAIL outcome=FAIL (expected), bundle complete
Engine C isolation  cleanup + IME(B→C) + Maestro input smoke  PASS
```

All runs carry `measurement_class=diagnostic` and `excluded_from_baseline=true`.

## 15. Baseline unchanged proof

`baseline_guard.py` recomputes the invariants and re-hashes every frozen file against the
pre-hardening snapshot:

```
BASELINE_COUNTS A=3 B=11 C=13 total=27
BASELINE_COMPRESSION B=96.6% C=89.4%
BASELINE_FROZEN_FILES checked=34 changed=0
BASELINE_GUARD=PASS
```

`baseline-manifest.json`, `summary.json`, `summary.csv`, `normalized-benchmark.json`,
`run-inventory.json`, `benchmark-apk.json`, `frozen/app-debug-frozen.apk` and all 27
`benchmark-run.json` are byte-identical. `HARDEN-*` runs are excluded by deny-by-default and
never counted.

## 16. Self-test commands

```bash
bash harness/selftest_static.sh     # bash -n, py_compile, 41 unit tests, timeout/watchdog
bash harness/selftest_device.sh     # preflight, B J1 smoke, fail-fast, bundle, C isolation, baseline
python3 harness/baseline_guard.py   # frozen invariants + checksums (read-only)
```

## 17. Out of scope / unchanged

Frozen APK (not rebuilt/replaced), frozen baseline data, KeepLab business code, PowerAi,
Journeys J1/J2/J3, Evaluation Core. No git commit was created — see
`reports/GIT-BASELINE-RECOMMENDATION.md`.
