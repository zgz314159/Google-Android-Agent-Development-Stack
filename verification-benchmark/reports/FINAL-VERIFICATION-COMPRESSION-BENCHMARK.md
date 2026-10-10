# FINAL — Verification Compression Benchmark

P0 study: can the `Agent → tap → screenshot → model inspect → next action` verification loop be
replaced by **batch, deterministic, failure-only** verification? Measured on a physical
Redmi Note 7 Pro. This report contains only measured evidence; nothing is pre-declared.

> **Audited and frozen (2026-10-03).** This report was reconciled against the run artifacts in
> `reports/FINAL-VERIFICATION-COMPRESSION-AUDIT.md` (formal measured set: **B 11 + C 13 = 24**
> runs, plus 3 A control = 27; final APK `a8858bd1…fdf06`). Aggregation is driven by the
> explicit allowlist `results/baseline-manifest.json` via `harness/measure.py`.

---

## 1. Environment

- Host: Ubuntu, Java 21, Gradle 9.5.1, AGP 9.2.1, Kotlin 2.3.21, Compose BOM 2026.05.01, Room 2.8.4.
- Project isolation: filesystem copy at `/mnt/AndroidDev/Worktrees/KeepLab-Verification-Compression`
  (the repository has **zero commits / unborn HEAD**, so `git worktree` is impossible → deviation `NO_WORKTREE`).
  The original `KeepLab-Relay` tree was never modified.
- Benchmark artifacts: `/mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack/verification-benchmark/`.

## 2. Frozen APK

| Field | Value |
|---|---|
| path | `.../Worktrees/KeepLab-Verification-Compression/app/build/outputs/apk/debug/app-debug.apk` |
| frozen copy | `verification-benchmark/frozen/app-debug-frozen.apk` |
| **sha256** | `a8858bd1f57b328a5042a120023508ced8e1cbbf68446bab3ce0e5e80f6fdf06` |
| size | 19,358,670 B |
| package / version | `com.keeplab.app` / 0.1.0 (code 1) |
| git commit | `NO_GIT` (no history) |

A, B and C all installed this exact APK via `adb install`; it was re-frozen once, before any
measurement, after adding the minimal selectors in §5. Two earlier intermediate hashes —
`8e0eafd66c7b77ef02c01e156c4531308b57426d6f19a68afb1e802a5209274f` (first freeze, pre-`testTag`)
and `21884d9bd54941ee4ebfaa2dcf31d4d371b2c56156effb429d888d2c41525870` — are **superseded
pre-testTag builds**; no recorded measured run used them (all 27 artifact-bearing runs record the
final hash).

## 3. Device

Redmi Note 7 Pro (`violet`, LineageOS 23.2), Android 16 / API 36, arm64-v8a, 1080x2340 @ 440dpi,
serial `87296ada`, screen stay-awake on.

**Environment preconditions (preflight, not measured intervention):** device **unlocked** (the
one-time PIN unlock is an environment prerequisite, not a per-run human intervention); screen
**awake / stay-on**; **Engine B requires the Google IME** (`com.google.android.inputmethod.latin`)
for `ACTION_SET_TEXT`; **Engine C requires the AOSP LatinIME**
(`com.android.inputmethod.latin`) for Maestro `inputText`; orientation baseline `user_rotation=0`
/ `accelerometer_rotation=0`; theme baseline light (`cmd uimode night no`). All are applied inside
each run's timed `setup_wall_ms`, so they never enter T7.

## 4. Exact tool versions

adb 1.0.41 (34.0.4-debian) · Android CLI 1.0.16486076 · Maestro 2.11.0 (installed at Stage C) ·
UiAutomator 2.4.0 · androidx.test runner 1.7.0 / ext.junit 1.3.0 · Compose UI test
**BLOCKED / DEFERRED on API 36** (not benchmark-verified — see §10).

## 5. Changes made

**Test-only (no business behaviour):**
- `gradle/libs.versions.toml`, `app/build.gradle.kts`: added `androidTestImplementation`
  `ui-test-junit4`, `uiautomator:2.4.0`, and the Compose BOM to the androidTest configuration. No toolchain upgrade.

**Production sources — semantics only (documented, behaviour-neutral):**
- `MainActivity.kt`: `Modifier.semantics { testTagsAsResourceId = true }` on the root Surface.
- `EditorScreen.kt`: `testTag("editor-title")`, `testTag("editor-body")`.
- `SearchTopBar.kt`: `testTag("search-field")`.
- Reason: Maestro's `inputText` could not focus an untagged Compose field; these three tags are required
  for stable selectors. No layout, logic, data or state change.

**New test sources** (`app/src/androidTest/.../benchmark/`): `FixtureSeeder`, `TimingLogger`,
`Verifier`, `DbProbe`, `FailureBundleRule`, `UiDriver`, `JourneyBase`, `J1/J2/J3JourneyTest`,
`IntentionalFailureTest`, `SpikeTest`.

**Benchmark tooling** (`verification-benchmark/harness/`): `run_engine_b.sh`, `run_engine_c.sh`,
`collect_failure.sh`, `emit_run.py`, `measure.py`, `stage1.sh`; `maestro/J1-J3.yaml`.

**Evaluation Core:** new, isolated `evaluation/commandcode/external_adapter.py`. `core.py`,
`phase_rules.json`, the taxonomy and the JSONL v3 schema were **not** modified.

## 6. Three Journey definitions

`journeys/J1-compose-crud.md`, `J2-complex-state.md`, `J3-rotation-state.md` — business goals identical
across A/B/C; real-UI mappings recorded (e.g. Archive long-press = unarchive, so J2 trashes via the editor).

## 7. Common ground-truth oracle

One verifier used by both engines (`Verifier.kt`): asserts real `keeplab.db` rows (title/body/archived/
trashed/labels), plus process (instrumentation result + logcat crash scan) and UI evidence. Screenshots are
used only for the visual/theme checkpoint, never as the PASS oracle. Unified output: `verification-result.json`.

## 8. Historical A0 baseline (Phase B)

T7 = 71.7% (T7a 1.7% / T7b 29.6% / T7c 40.4%) of 6415.955 s → T7b ≈ 1899.6 s, T7c ≈ 2594.3 s;
107 model requests, 26,607,055 input tokens, ≈ $0.2772.

## 9. Engine A control (live, agent-driven)

Same frozen APK, fixture, device and oracle; driven by `adb` + Android CLI with per-step screenshots read by the model.

| Journey | total wall | screenshots taken/read | model inspections | oracle |
|---|---|---|---|---|
| A J1 | 252,562 ms | 5 / 5 | 5 | PASS |
| A J2 | 1,095,870 ms | 11 / 10 | 10 | PASS |
| A J3 | 277,920 ms | 4 / 4 | 4 | PASS |

Per-journey T7b/T7c for A are **not separately provable** (null). The observer's Evaluation Core run over the
whole working session reports T7 = 3726.2 s (T7a 1445.6 / T7b 1261.4 / T7c 1019.2) with 215 requests and
43,589,348 input tokens — but that window includes harness construction, so it is not a clean A control.

## 10. Engine B (Native)

Compose UI Test is **BLOCKED / DEFERRED on API 36** (`GAP-ESPRESSO` reproduces exactly:
`InputMethodManagerEventInjectionStrategy` → `InputManager.getInstance()` `NoSuchMethodException`).
It is **not benchmark-verified** and no part of this study claims it was. Engine B therefore runs
the stack that **was** actually verified: **UiAutomator 2.4.0 + deterministic harness**
(accessibility-tree driving + `ACTION_SET_TEXT`), native with **0 LLM calls** and 0 screenshots on
the PASS path.

| Journey | n | pass | t7a (med) | t7b (med) | t7c (med) | total (med) |
|---|---|---|---|---|---|---|
| B J1 | 3 | 3 | 1835 ms | 17,163 ms | 59 ms | 21,342 ms |
| B J2 | 3 | 3 | 1837 ms | 15,881 ms | 506 ms | 20,588 ms |
| B J3 | 5 | 5 | 1829 ms | 7595 ms | 1909 ms | 13,479 ms |

## 11. Engine C (Maestro)

| Journey | n | pass | t7c (med) | total (med) |
|---|---|---|---|---|
| C J1 | 5 | 5 | 2190 ms | 67,099 ms |
| C J2 | 3 | 3 | 2246 ms | 76,587 ms |
| C J3 | 5 | 5 | 1991 ms | 28,993 ms |

Maestro exposes no per-command monotonic timestamps, so **t7b_ms = null** (never estimated); t7c is the
host-measured shared-oracle probe; the DB oracle runs as an instrumentation companion (`DbProbe`).

## 12. Failure-only evidence test

- **Native:** `IntentionalFailureTest` asserting `__KEEP_LAB_INTENTIONAL_FAILURE__` → bundle produced
  automatically: `failed-assertion.json`, `screenshot.png`, `layout.json`, `logcat.txt`, `db-state.json`,
  `executor-output.txt`, `metadata.json`. **PASS.**
- **Maestro:** `INTENTIONAL-FAIL.yaml` → `failed-assertion.json`, `screenshot.png`, `layout.json/xml`,
  `logcat.txt`, `db-state.json`, `executor-output.txt`, `metadata.json`. **PASS.**
- No production change was made to create the failure; assertions were restored.

**Formalized fallback (no single-point dependency on `android layout`):** the bundle collector
now tries, in order, (1) **Android CLI layout** → `layout.json` (`layout_provider=android_cli`),
(2) **`uiautomator dump`** → `layout.xml` — **XML, never relabelled `.json`**
(`layout_provider=uiautomator_xml`), (3) **screenshot + logcat + dumpsys/state** (always).
`layout_provider` is recorded in the bundle `metadata.json`
(`android_cli` | `uiautomator_xml` | `unavailable`). Both providers produced valid output on-device
(native: `android_cli`; Maestro: `android_cli` with the `uiautomator_xml` fallback artifact also
retained) — **fallback status PASS**.

## 13. T7 / T7b / T7c comparison

Per-journey total verification wall vs the live A control:

| Journey | A total | B total | B reduction | C total | C reduction |
|---|---|---|---|---|---|
| J1 | 252,562 ms | 21,342 ms | **91.5%** | 67,099 ms | **73.4%** |
| J2 | 1,095,870 ms | 20,588 ms | **98.1%** | 76,587 ms | **93.0%** |
| J3 | 277,920 ms | 13,479 ms | **95.2%** | 28,993 ms | **89.6%** |

Aggregate across journeys: **B 96.6% reduction, C 89.4% reduction** — both exceed the ≥70% target and land
in the 80–90%+ ideal band. On the T7b+T7c basis, B J1 = 17.2 s, J2 = 16.4 s, J3 = 9.5 s of instrumented work
per journey; there is no per-journey A split to divide against, so the honest comparison is total wall.

## 14. Model-request comparison

| Engine | PASS-path model requests |
|---|---|
| A (live control) | 4–10 vision inspections per journey (screenshots read) |
| B (Native) | **0** every run |
| C (Maestro) | **0** every run |

**Definition — `PASS-path model calls = 0`.** This means only that the already-defined
deterministic verification Journey, *during execution*, needs no visual-LLM judgement (0 requests,
0 screenshots read for B and C). It does **not** mean the whole Command Code development/benchmark
session made no model calls. Session-level Evaluation Core figures (215 requests, 43.6 M input
tokens, T7 = 3726.2 s) describe the **entire session including harness construction** and are
reported separately in `reports/evaluation-core-session-run.json`; they are not verification-executor
metrics and must not be conflated with them.

## 15. Token comparison

B and C PASS paths make no model calls → 0 tokens. A's per-journey tokens are not attributable; the
observer reports 43.6 M input tokens for the whole session (which includes all harness construction), and
A0 gives the clean historical figure (26.6 M input tokens for a 107-request Phase B run).

## 16. Screenshot / evidence comparison

| Engine | screenshots (success path) | layout dumps | evidence |
|---|---|---|---|
| A | 4–11 per journey, all read by the model | 0 | per-step vision |
| B | **0** | 0 | DB oracle + process + a11y |
| C | **0** | 0 | DB oracle via companion probe |

Failure paths produce the full bundle on demand (screenshot + layout + logcat + DB state).

## 17. Flakiness / retries

- Measured runs: 24 for B/C (extended to 5 for B-J3, C-J1, C-J3 where variance exceeded 10%). **All PASS.**
- Retries within a run: 0. Human interventions per run: 0.
- Variance: B-J1 0.9%, B-J2 2.1%, C-J2 1.2% on total wall; the high-variance combos (B-J3 ~9%, C-J3 ~8%)
  are dominated by rotation/dark-mode transitions, not failures.
- One environment prerequisite (device was PIN-locked) required a one-time owner unlock before Stage 1 —
  recorded as an environment precondition, not a per-run intervention.

## 18. Maintenance complexity discovered

1. **GAP-ESPRESSO**: Compose UI Test cannot run on API 36 → B had to fall back to UiAutomator.
2. **IME coupling**: Engine B's `setText` works only with the Google IME; Maestro's `inputText` works only
   with the AOSP LatinIME. The harness must set the IME per engine — a real, non-obvious fragility.
3. **Maestro selector/API drift**: `setOrientation` needs `{orientation: LANDSCAPE_LEFT}` (not `LANDSCAPE`);
   `inputText` appends (needs `eraseText`); `toggleDarkMode` is the working dark-mode command.
4. **Android CLI `layout` broke** after Maestro ran (`Error communicating with instrumentation server`);
   `uiautomator dump` remains a working fallback and is now built into `collect_failure.sh`.
5. Driver/`UiAutomation` interactions and the need to force-stop the app host-side (never in-process) are
   sharp edges that cost real debugging time.

## 19. Limitations

- Engine B measured version is UiAutomator-only (not Compose semantics assertions), because Compose UI test
  is blocked on this OS.
- Engine C's t7b is null (Maestro gives no per-command timestamps); its total includes Maestro's engine overhead.
- The live A control is 1 run/journey; A's split is not provable per journey, and its token accounting is
  session-level only. A0 (Phase B) remains the authoritative A baseline.
- Single device, single physical unit; no emulator cross-check. `NO_WORKTREE` (no commit SHA recorded).

## 20. Recommendation (strictly from measured evidence)

- **Production default — Engine B (native UiAutomator, batch + deterministic).** 0 model calls, oracle PASS,
  91.5–98.1% wall reduction, sub-second evidence cost, lowest evidence volume, no external tool.
- **Challenger — Engine C (Maestro).** 0 model calls and 73.4–93.0% reduction with far less Kotlin, but
  ~3× the wall of B, null t7b, an IME/API-drift tax and a separate runtime to maintain. Strong for
  cross-platform, quick-to-author flows; not the fastest here.
- **Failure / exploration fallback — Engine A.** Keep the agentic loop only for diagnosis after a failed
  deterministic check, and for genuinely novel UI; it is ~10–50× the wall cost per journey.
- **Defer / reject:** Compose UI Test on API 36 (blocked); per-step screenshots on the PASS path (rejected —
  no VALUE-added evidence; the DB+process oracle is sufficient).
