# P0B — Performance & Reliability Measurement
### + live AI-Stack effectiveness observation

**Program:** `KEEP-LAB-GOOGLE-KEEP-PARITY` · **Phase:** P0B (measurement / reliability foundation)
**Executed:** 2026-10-05 · **Reference date (unchanged):** 2026-10-04 · **Truth source:** the frozen
P0B Implementation Contract compiled in this phase

**Headline:** the first matched, repeated, per-app KeepLab ↔ Google Keep performance baseline now
exists on the reference device, with median/p95 and separated raw results. **P0B recorded a large
cold-start and frame-jank gap and did not fix it** — that is the intended outcome of a measurement
phase. Reliability and accessibility rows gained real evidence; the matched 10/100/500/1000 data
scale could not be established and is reported as `BLOCKED_DATA_SCALE`.

---

## 1. Environment

| | |
| --- | --- |
| Device serial | `87296ada` |
| Model / device | Redmi Note 7 Pro / `violet` |
| Android | release **16**, SDK **36**, build `BP4A.251205.006` |
| Fingerprint | `xiaomi/violet/violet:10/QKQ1.190915.002/V12.5.1.0.QFHINXM:user/release-keys` |
| Display | physical 1080x2340, density **440 dpi** |
| Locale | `zh-Hans-CN` |
| Theme at measurement | system default (light); dark captured separately for the dark-theme row |
| Orientation | portrait (rotation measured as the transition to landscape) |

**Recorded build-identity mismatch (not smoothed over):** the fingerprint and build id encode an
Android-10-era vendor build while `ro.build.version.release` reports 16 / SDK 36 — a ported ROM.
Because both apps are measured on the *same* device and display, the factor cancels in the matched
comparison; it is recorded so no one mistakes this for stock Android 16.

## 2. App versions

| App | Package | Version | Code | Variant |
| --- | --- | --- | --- | --- |
| KeepLab | `com.keeplab.app` | 0.1.0 | 1 | **debug** (see §9 limitation) |
| Google Keep | `com.google.android.keep` | **5.26.391.03.90** | 220677611 | release |

**Reference check:** the installed Google Keep is `5.26.391.03.90`, which **matches** the frozen
P0A capture manifest (`KeepLab-Relay-evidence/google-keep/v1.0.1/`, reference date 2026-10-04).
Therefore **no `REFERENCE_VERSION_MISMATCH`** and **no re-baseline**. The P0A captures remain valid
and were reused read-only for the Google Keep side of the contrast measurement.

## 3. Specification / contract path

No frozen P0B contract existed at the start (confirmed absent by targeted recon). P0B was therefore
compiled through the **canonical Specification Compiler**, with no invented entry point:

```
python3 specification/compiler/hash_manifest.py   <pkg>
python3 specification/compiler/build_contract.py  <pkg>
python3 specification/compiler/validate_package.py <pkg> --project-root /mnt/AndroidDev/Projects
```

Package: `KeepLab-Relay/specs/p0b-performance-reliability/` — 8 authored artifacts
(`PRODUCT.md`, `requirements.md`, `design.md`, `tasks.md`, `DESIGN.md`, `acceptance.md`,
`project-context.json`, `verification-intent.json`) → 14 requirements, 14 acceptance criteria,
8 tasks, 8 decisions (`DEC-001..DEC-008`).

Result: **`STATUS=READY schema=PASS traceability=PASS boundaries=PASS acceptance=PASS hashes=PASS`
`errors=0`**. Handoff artifacts generated: `implementation-contract.json`, `manifest.json`,
`READY.json`, `EXECUTOR-PROMPT.md`. Re-validating the package after the whole phase still returns
READY with all gates PASS, which proves the frozen contract was never reopened or re-hashed.

## 4. Harness

New, external, non-invasive: `KeepLab-Relay/benchmark/` (see `benchmark/P0B-MEASUREMENT-RECORDS.md`).
It creates **no Gradle module**, edits **no build file**, and writes **nothing under `app/**`**.

* `run_p0b.sh` — device battery under the host device lock (`flock device:87296ada`, capacity 1,
  fail-closed `DEVICE_BUSY`), fail-fast.
* `lib/measure.py` — environment capture, data-scale probe, startup/memory/jank/rotation/restart
  battery, crash scan, and a **static self-check that refuses to touch the device if the harness
  contains any `adb shell input …` pattern**.
* `lib/measure_flows.py` + `flows/**` — selector-driven Maestro journeys.
* `lib/aggregate.py` — median/p95 + the full rig metadata record per metric per app.
* `lib/a11y.py` — touch-target bounds analysis and WCAG contrast computation.

**Rejected with reason:** a stock Jetpack Macrobenchmark `:benchmark` module. `androidx.benchmark.macro`
needs the target app to expose a **signed, non-debuggable, profileable** variant; KeepLab's only
non-debug build type (`release`) has **no signing config** and produces an unsigned APK, so a
`benchmark` build type plus a `profileable` manifest flag would have to be added in `app/**` —
forbidden by the contract boundary. Platform tooling was used instead and every metric that would
genuinely need macrobenchmark is reported PARTIAL/BLOCKED rather than forced.

## 5. Measurement methods

| Metric | Method |
| --- | --- |
| PERF-01 cold start | `am force-stop` → `am start -W -n <component>`, `TotalTime`, 7 runs/app, first-run warm-up discarded |
| PERF-02 warm start | `am start` HOME intent to background, then `am start -W`; harness fails fast if `TotalTime == 0` (that means the activity never left the front and is not a warm start) |
| PERF-12 restart recovery | `am force-stop` → `am start -W` → foreground/state check |
| PERF-08 jank | `dumpsys gfxinfo <pkg> reset` → window → `dumpsys gfxinfo` frame statistics (`Janky frames %`) |
| PERF-09 memory | `dumpsys meminfo <pkg>` (idle and after launch) |
| PERF-11 rotation | `settings put system user_rotation` + poll `dumpsys window displays` for `ROTATION_90`; restored afterwards |
| PERF-04/05/07 | selector-driven Maestro journey; wall time + frame statistics over the same window |
| reliability | `logcat -b crash` + `AndroidRuntime:E`, attributed by `Process:` / `ANR in:`; non-destructive `run-as` DB copy read with Python `sqlite3` |
| A11Y-003 | `uiautomator dump` → clickable node bounds → dp at 440 dpi (48 dp = 132 px) |
| A11Y-005 / DARK-002 | WCAG relative-luminance contrast over KeepLab's own declared colour tokens; Google Keep sampled from the frozen P0A PNGs with `Pillow` |

Disclosed device commands beyond pure telemetry: `am start` (HOME intent, for backgrounding and
launching), `am force-stop`, `settings put system user_rotation/accelerometer_rotation` (restored),
and `uiautomator dump` (observation). **No `adb shell input tap/swipe/text/keyevent` is used
anywhere** — verified by the harness self-check (`clean: true, hits: []`).

## 6. Raw-result locations

`KeepLab-Relay/benchmark/results/P0B-CANONICAL/` — KeepLab and Google Keep raw runs in **separate
directories**, never merged.

* `records/measurement-records.md` / `.json` — the records and the matched comparison
* `keeplab/*.json`, `googlekeep/*.json` — raw runs
* `env.json`, `data-scale.json`, `reliability/`, `a11y/`, `flows-index.json`, `lock.log`
* `MERGE.json` — provenance: which metric came from `P0B-RUN1` (initial battery) and which from
  `P0B-RUN2` (the minimal post-fix re-run)

## 7. Matched comparison (median / p95)

Every value is a median/p95 over the recorded repetitions. KeepLab and Google Keep were measured
separately and stored separately. Full table plus per-metric metadata:
`records/measurement-records.md`.

| Metric | KeepLab median / p95 | Google Keep median / p95 | ratio | within 1.10× |
| --- | --- | --- | --- | --- |
| Cold start (TTI) | 1549 / 1695 ms | 599 / 634 ms | **2.59×** | NO — gap |
| Warm start | 66 / 76 ms | 127 / 151 ms | 0.52× | YES |
| Process-restart recovery | 1492 / 1515 ms | 635 / 647 ms | **2.35×** | NO — gap |
| Rotation latency (→landscape) | 174 / 206 ms | 160 / 179 ms | 1.09× | YES |
| Frame jank, launch window | 40.0 / 76.0 % | 12.95 / 14.46 % | **3.09×** | NO — gap |
| Frame jank, driven scroll | 33.33 / 33.33 % | 2.29 / 2.44 % | **14.56×** | NO — gap |
| Memory PSS, idle | 134125 / 134826 kB | 113653 / 119877 kB | 1.18× | NO — gap |
| Memory PSS, populated | 135121 / 135244 kB | 119884 / 119925 kB | 1.13× | NO — gap |

**Not scored against the target:** the driven-journey wall times (open note / create / search —
KeepLab 20329 / 24250 / 18630 ms; Google Keep 20764 / n-a / 24667 ms). They include Maestro driver
overhead and are comparable between the apps but are **not** in-app latency. The aggregator marks
them `target_comparable: false` so they can never be quoted as a scored performance claim. The
driver-independent frame statistics from the same journeys **are** scored.

## 8. Blocked metrics (honest, not converted to PASS)

| ID | Metric | Status | Blocker |
| --- | --- | --- | --- |
| PERF-03 | Home first render at 10/100/500/1000 | `BLOCKED_DATA_SCALE` | No parameterised seeder reachable without editing `app/**`; KeepLab's existing `FixtureSeeder` is instrumentation-only and fixed at 3 notes; Google Keep's private database is unwritable and additive UI seeding was not attempted. Measured only at the real scale. |
| PERF-05 | Create note, Google Keep side | `BLOCKED` | Creating a note writes new content into a third-party app. |
| PERF-06 | Save / edit large body | `PARTIAL` | Only a driver-limited journey wall time was obtained. |
| PERF-07 | Search latency vs scale | `PARTIAL` | Latency measured; the scale axis is `BLOCKED_DATA_SCALE`. |
| PERF-10 | DB query latency | `BLOCKED` | No non-invasive Room trace hook exists inside the boundary. |
| PERF-14 | Large checklist 500+ items | `BLOCKED_DATA_SCALE` | No seeder for either app. |
| PERF-15 | Image-heavy note | `BLOCKED_IMAGE_PARITY` | No image notes exist; IMAGE parity is a later phase. |

## 9. Reliability results

| ID | Row | Evidence | Result |
| --- | --- | --- | --- |
| GKP-REL-001 | Zero crash in required journeys | `reliability/reliability.json`, `final-logcat-crash.txt`, `final-logcat-androidruntime.txt` | **0 crashes and 0 ANRs** attributed to either app across the whole measurement window, 21 driven journey executions (3 × 7 flows) and 56 startup/restart launches per app. Stated as "0 crashes in N runs" — **not** an unconditional guarantee and **not** a crash-free-session metric at scale. Status stays `NEAR`. |
| GKP-REL-002 | Zero data loss on upgrade / restore | `reliability/reliability.json`, `data-scale.json` | All **5 pre-existing KeepLab active notes preserved**, schema `user_version` still 2, and **no Google Keep content created, modified or deleted**. The 3 extra rows are the identifiable benchmark notes (`P0B-BENCH-CREATE`) that the create journey removed itself via *Move to trash*. No upgrade/restore was exercised and there was no fault injection → status stays `NEAR`. |
| GKP-REL-003 | Fail-closed verification | `result_emit.py` (Layer 1.0.1), `rebuild-evidence/RUN1-lock.log`, `flows-index.json` | Layer-level fail-closed gate reused as-is; **observed live**: the harness stopped at the first deterministic failure, flushed raw runs + index + failure evidence and exited non-zero; an unmeasurable metric is recorded `BLOCKED`, never defaulted to PASS; the device lock fails closed on `DEVICE_BUSY`. Status stays `NEAR` (per-journey `verify()` overrides remain an implementation obligation). |

## 10. Accessibility / dark-theme results

Evidence: `benchmark/results/P0B-CANONICAL/a11y/A11Y-EVIDENCE.md` + `a11y.json`.

**GKP-A11Y-003 — touch targets ≥ 48dp → PASS (measured).** From real hierarchy dumps at 440 dpi
(48 dp = 132 px): KeepLab **Home 15 clickable controls, 0 under 48 dp**; KeepLab **note editor 8
controls, 0 under 48 dp**. Google Keep Home: 13 controls, its single sub-48 dp node is a note card
clipped by the viewport bottom edge and is recorded as not scoreable.
*Measurement artifact corrected before reporting:* an earlier pass counted non-clickable
`Button`-class children of `IconButton`s and produced 10 false 40 dp violations; the rule was
tightened to `clickable=true AND enabled=true` and the finding was withdrawn.

**GKP-DARK-002 — note tints readable in dark → PASS (measured).** All **10** note tints with
`onColor = Ink` (`NoteColors.kt`) give WCAG ratios from **7.17:1** (CORAL, lowest) to **17.12:1**
(DEFAULT) against a 4.5 requirement. The tints are identical in light and dark by construction, so
the dark ratio is the same by proof, not by assumption. Google Keep's dark home sampled 13.96:1.

**GKP-A11Y-005 — contrast / dynamic type → PARTIAL.** All **7 light and 7 dark** KeepLab UI colour
pairs pass (lowest 5.93:1 against 4.5). The `outline`-vs-background pairs measure 1.29 (light) and
1.58 (dark) and are recorded as **informational**: `outline` is used as a decorative card/section
divider, not as a meaningful component boundary. **Dynamic type / font-scale was not exercised** —
that half of the row stays open.

## 11. Matrix / document changes

Changed files (evidence-pointer and measured-status updates only — no reference change, no version
bump, no re-baseline):

* `specs/google-keep-parity/PERFORMANCE-PARITY.md` — status `MEASUREMENT_REQUIRED` →
  `PARTIALLY_MEASURED`; measured results, ratios, confounds and the blocked-metric table added;
  the "definition of done" section now states the P0B position honestly.
* `specs/google-keep-parity/PARITY-MATRIX.md` — 12 rows updated with a clearly labelled
  *"P0B measurement update (2026-10-05) — not a re-baseline"* note at the top.

| Row | Before | After |
| --- | --- | --- |
| GKP-PERF-001 cold start | UNVERIFIED | PARTIAL (2) — measured, 2.59× outside target |
| GKP-PERF-002 home render at scale | UNVERIFIED | BLOCKED (`BLOCKED_DATA_SCALE`) |
| GKP-PERF-003 open/create/save | UNVERIFIED | PARTIAL (2) — measured but driver-limited |
| GKP-PERF-004 search vs scale | UNVERIFIED | PARTIAL (2) — measured at real scale only |
| GKP-PERF-005 scroll / frame jank | UNVERIFIED | PARTIAL (2) — measured, 14.56× gap |
| GKP-PERF-006 memory + large note | UNVERIFIED | PARTIAL (2) — PSS measured, large note blocked |
| GKP-A11Y-003 touch targets | NEAR (3) | **PASS (4)** — measured compliant |
| GKP-A11Y-005 contrast / dynamic type | UNVERIFIED | PARTIAL (2) — text contrast measured, dynamic type open |
| GKP-DARK-002 note tints in dark | NEAR (3) | **PASS (4)** — measured compliant |
| GKP-REL-001 crash-free journeys | NEAR (3) | NEAR (3) — bounded-window crash evidence added |
| GKP-REL-002 no data loss | NEAR (3) | NEAR (3) — preservation evidence added |
| GKP-REL-003 fail-closed | NEAR (3) | NEAR (3) — live fail-fast/fail-closed evidence added |

No other matrix row was touched. `UI_VISUAL_FIDELITY` is unaffected by P0B and remains
capture-backed, pending human review.

## 12. Known limitations

1. **Debug-vs-release confound (largest).** KeepLab is measured on its **debug** build — no
   minification, no baseline/startup profile, JIT instead of AOT — because the only non-debug
   variant is unsigned and cannot be installed. Google Keep is a shipping release build with
   profiles. Cold start and frame jank are exactly the metrics most sensitive to this. The numbers
   are real and matched by device, display, locale and method, but they are **not** a final product
   parity verdict.
2. **Matched data scale not achieved.** KeepLab 5 active notes vs Google Keep 6 visible cards.
   Every scale-dependent row is `BLOCKED_DATA_SCALE` or PARTIAL.
3. **`am start -W` reports `TotalTime`**, which is a platform figure whose relation to
   time-to-initial-display is version-dependent; the same method was used for both apps.
4. **Driven-journey wall times** include Maestro driver overhead and are deliberately not scored.
5. **Jank windows are short** (a launch + 6 s settle, and a scripted scroll), not a soak.
6. **Reliability evidence is window-bounded.** Logcat is a rolling buffer; there is no
   crash-free-session aggregate.
7. **Google Keep's contrast** was obtained by automated pixel-histogram sampling of frozen
   captures (a labelled heuristic), not by reading its theme source, which is unavailable.
8. **Accessibility coverage** is limited to the Home list and the note editor; other surfaces
   (colour sheet, labels, archive, trash) were not dumped.

## 13. Product gaps discovered (recorded, NOT fixed)

P0B deliberately did not modify production code. Recorded for a later phase:

1. **Cold start 2.59× Google Keep** (1549 ms vs 599 ms) and **process-restart recovery 2.35×**.
   No baseline/startup profile is committed anywhere in KeepLab.
2. **Frame jank 14.56× on a driven scroll** (33.33 % vs 2.29 % janky frames) and 3.09× on launch.
   This is the strongest signal in P0B and is driver-independent. The unmeasured hypotheses in
   `PERFORMANCE-PARITY.md` (in-memory filter+sort over all notes on every emission;
   `NoteDao.observeAll()` loading all notes with items+labels and no paging; per-keystroke autosave
   writing the whole note row) remain **hypotheses**, not proven causes, but they are now
   consistent with the observed jank.
3. **Memory 1.13–1.18× above Google Keep** — bounded, but consistently higher idle and populated.
4. **`:app` has no signed release build** — build types are `release` only with minify off and no
   signing config, so no profileable/release variant can be installed or benchmarked. This is a
   build-configuration gap that blocks correct performance measurement itself.
5. **No N-note data seeder** outside instrumentation — it blocks every scale-dependent performance
   row and it sits under `app/**`, so a measurement phase cannot add it.
6. **Dynamic type / font-scale is not audited** anywhere.

None of these was fixed; none is claimed to be fixed.

## 14. P0B exit assessment

| Exit criterion (ROADMAP P0B) | State |
| --- | --- |
| P0 matrix rows addressed | **YES** — all 12 scoped rows updated with real evidence |
| Matched performance evidence where measurable | **PARTIAL** — 8 metrics measured for both apps; scale-dependent ones blocked |
| median/p95 available for scored matched measurements | **YES** — `records/measurement-records.json` |
| Google Keep / KeepLab results separated | **YES** — separate directories, separate records |
| Reference coverage remains valid | **YES** — installed Google Keep matches the frozen manifest; no re-capture |
| `UI_VISUAL_FIDELITY` remains evidence-backed | **YES** — untouched, P0A captures intact |
| Reliability evidence updated | **YES** — all three rows gained real, bounded evidence |
| `UNVERIFIED` rows moved only where evidence permits | **YES** — 6 moved off UNVERIFIED, 2 to PASS, 4 stayed open/blocked |
| No production behaviour change | **YES** — `app/**` byte-identical across 2450 files |
| No required measurement converted from BLOCKED to PASS | **YES** — 7 blocked/method-limited metrics reported as such |

**P0B STATUS: PARTIAL.** The measurement foundation is real and honest, but P0B does **not** meet its
full exit gate: the matched 10/100/500/1000 data scale is `BLOCKED_DATA_SCALE`, PERF-10 and PERF-15
are blocked, the reliability rows remain `NEAR` (no crash-free-session metric at scale, no fault
injection), the dynamic-type half of GKP-A11Y-005 is open, and the debug-vs-release confound means
the performance numbers cannot yet be presented as a product parity verdict.

**Next: fix the P0B blocker — not P1.** The single highest-leverage blocker is matched data scale,
which is blocked by the absence of a seeder outside `app/**`.

---

# Appendix — P0B SYSTEM EFFECTIVENESS OBSERVATION

Passive observation of the real P0B run. No synthetic test task was created and no extra model call
was made to inspect the Stack.

```
FROZEN_CONTRACT_REOPEN_COUNT: 0
CONTRACT_DEVIATION_COUNT: 1
OUT_OF_SCOPE_WRITE_COUNT: 0
RULE_VIOLATION_COUNT: 0
DEVICE_CONCURRENCY_VIOLATION_COUNT: 0
REDUNDANT_FULL_RESCAN_COUNT: 0
REDUNDANT_VERIFICATION_AFTER_PASS_COUNT: 0
FAIL_FAST_VIOLATION_COUNT: 0
UNSUPPORTED_PERFORMANCE_CLAIM_COUNT: 0
READ_ONLY_PARALLEL_OPPORTUNITIES: 1
READ_ONLY_PARALLEL_OPPORTUNITIES_USED: 1
MODEL_REQUESTS_DURING_DETERMINISTIC_DEVICE_STEPS: 0
VISUAL_LLM_CALLS_DURING_PASS_PATH: 0
DIRECT_ADB_UI_INPUTS_DURING_PASS_PATH: 0
AUTO_FINALIZER: PENDING_POST_SESSION
GOOGLE_APK_TEMPLATE_EFFECTIVENESS: NOT_EXERCISED_IN_P0B
```

### A. Did Hermes obey the Frozen Contract? — **YES**
The contract was compiled first and then followed. `validate_package.py` re-run after the whole
phase returns `STATUS=READY` with all five gates PASS, so no authored artifact changed after
hashing. No allowed path was exceeded (one exception below), no frozen decision was reopened, and
every metric the contract predicted might be blocked was in fact recorded as blocked.

### B. Did it avoid reopening frozen architecture/scope? — **YES**
`FROZEN_CONTRACT_REOPEN_COUNT: 0`. The macrobenchmark-vs-external-harness architecture decision
(DEC-002) was settled once, before any device work; the `app/**` prohibition (DEC-001) held; the
`BLOCKED_*` policy (DEC-004/006) was followed rather than relaxed to make a row pass.

### C. Did it avoid `app/**` writes? — **YES**
`find app -type f | sha256sum` over **2450 files** is byte-identical before and after the phase
(`results/_baseline/app-pre-phase.sha256` vs `results/P0B-CANONICAL/product-safety-app-post.sha256`),
`settings.gradle.kts` / `build.gradle.kts` / `gradle.properties` / `app/build.gradle.kts` hashes are
unchanged, and no file under `app/` has an mtime after phase start.

### D. Did read-only independent recon actually parallelize? — **YES**
One `delegate_task` call dispatched **3 read-only children simultaneously** (performance/benchmark
audit, matched-device/data/reliability audit, AI-rule/contract-effectiveness audit). Transcripts:
`~/.hermes/profiles/android-stack/cache/delegation/live/deleg_a1c117af/{manifest.json,task-0..2.log}`.
All three completed; no child wrote a file.

### E. Did write operations remain single-writer? — **YES**
Every file written in P0B was written by the root Hermes session. Children were read-only by
instruction and by outcome.

### F. Was device capacity = 1 respected? — **YES**
Every device batch ran under `verification/core/device_lock.sh` (`flock device:87296ada`), and the
lock was released on process exit each time. The only other device touch was one read-only
`logcat`/`dumpsys` probe. Only one agent ever held the device. `DEVICE_CONCURRENCY_VIOLATION_COUNT: 0`.

### G. Did fail-fast stop deterministic failures early? — **YES**
The flow batch stopped at the **first** deterministic failure
(`KL-scroll.yaml: Unknown Property: direction`), still flushed the raw runs, `flows-index.json` and
the failure evidence, and exited non-zero with `stopped_early: true` and `first_failure` recorded —
no partial PASS was emitted.

### H. Did Hermes avoid repeating broad reconnaissance? — **YES**
`REDUNDANT_FULL_RESCAN_COUNT: 0`. Recon was three targeted, bounded children reading a named file
list; no whole-workspace recursive scan was performed, and no target already covered by the children
was re-explored.

### I. Did it avoid repeating verification after a valid PASS? — **YES**
`REDUNDANT_VERIFICATION_AFTER_PASS_COUNT: 0`. P0A, S1 and S1.1 were **not** re-run. Reconciliation
was achieved by re-running **only** the two metrics whose method was defective
(`perf-02-warm-start`, and the Google Keep note-count probe) plus the single failed flow; all other
metrics kept their original valid evidence. `MERGE.json` records the exact provenance.

### J. Did it avoid unsupported performance claims? — **YES**
`UNSUPPORTED_PERFORMANCE_CLAIM_COUNT: 0`. Nothing is quoted from a single run; every scored row is a
median/p95 over ≥3 repetitions. Two potential unsupported claims were caught and neutralised rather
than published: (1) the Maestro-driven wall times are marked `target_comparable: false` and printed
as "NOT SCORED (driver-overhead dominated)" so the 0.98× / 0.76× "within target" readings in the
first aggregation could not be quoted as a KeepLab win; (2) a first-pass touch-target result of
10 sub-48dp controls was recognised as a measurement artifact and withdrawn after the rule was fixed.

### K. Did deterministic device steps stay free of per-step visual LLM reasoning? — **YES**
`MODEL_REQUESTS_DURING_DETERMINISTIC_DEVICE_STEPS: 0` and
`VISUAL_LLM_CALLS_DURING_PASS_PATH: 0`. No `vision_analyze` call was made anywhere in this session.
Every device interaction was a lifecycle/telemetry command or a selector-driven Maestro flow
(`launchApp`, `tapOn <id|text>`, `assertVisible`, `scroll`, `swipe`, `back`).

### L. Did Auto-Finalizer receive the Hermes root session? — **PENDING_POST_SESSION**
The `on_session_finalize` hook fires after this session closes; within the running session the
correct value is `PENDING_POST_SESSION`. It is not claimed to have happened. (No Auto-Finalizer
entry for this session exists yet under `~/.hermes/logs/`.)

### Contract-scope contradiction (the one counted deviation)
`CONTRACT_DEVIATION_COUNT: 1`. The contract's `forbidden_paths` covered the whole Stack
`verification/` tree, while the contract also *required* the in-tree device lock, whose helper
creates `verification/.state/locks/device-87296ada.lock`. The contract was **not** reopened: the
higher-precedence `.hermes.md` device-lock invariant was honoured, the write was confined to that
one lock file, and the contradiction is recorded in full in
`KeepLab-Relay/benchmark/CONTRACT-DEVIATION-NOTES.md`. Class: contract-scope imprecision, not a
product or governance violation.

### Google APK Template
```
GOOGLE_APK_TEMPLATE_EFFECTIVENESS: NOT_EXERCISED_IN_P0B
```
P0B is brownfield measurement: it creates no new Android app and the canonical design selects an
external adb/Maestro harness rather than a generated app scaffold. The template was not invoked, no
dummy app was created to exercise it, and per the brief this is **not a FAIL**.

---

## Product-safety final check

| Check | Result |
| --- | --- |
| KeepLab `app/**` modified | **NO** — 2450 files byte-identical, no post-phase mtimes |
| Testapp modified | **NO** |
| PowerAi modified | **NO** |
| P1 started | **NO** |
| Google Keep existing unrelated user data destroyed | **NO** — 0 Keep content created/modified/deleted |
| Hermes core patched | **NO** — pinned upstream, no core file touched |
| Governance invariant files modified | **NO** — `MISSION.md`, `FACTORY_RULES.md`, `.hermes.md` untouched |
| `git reset` / `git clean` / `git commit` / `git push` | **NO** — no git state-changing command was issued |

---

## Amendment — P0B-CLOSE (2026-10-05)

**This section is additive. No figure, status or statement above was rewritten, and the P0B run
evidence (`benchmark/results/P0B-{RUN1,RUN2,CANONICAL}`) is byte-identical (97/97 files).**

P0B-CLOSE removed the blockers P0B's own evidence exposed. Canonical closure report:
`reports/P0B-CLOSE-BENCHMARKABILITY.md`. Closure evidence:
`KeepLab-Relay/benchmark/results/P0B-CLOSE/`.

What changed for the P0B figures:

1. **Cold start (§7 row `PERF-01`) — superseded for scoring by a release-derived measurement.**
   On a benchmark-only variant derived from `release` (non-debuggable, profileable, minify off
   exactly as the shipping release has it) the cold-start median is **433.5 ms** (p95 447.5 ms,
   n=6) against Google Keep's 599 ms — **0.72×, inside the 1.10× target**. The P0B figure of
   **1549 ms** was measured on the **debug** build and is retained above as historical evidence,
   but the debug-vs-release confound recorded in P0B §12.1 is now quantified as the dominant cause
   of the 2.59× gap. Method unchanged (`am force-stop` + `am start -W`); only the build variant
   changed. An earlier run of the same batch gave 384 ms; both are reported rather than averaged.
   Provenance: `benchmark/results/P0B-CLOSE/records/provenance.json`.
2. **Matched data scale — half closed.** KeepLab 10/100/500/1000 is now **PASS** via a
   benchmark-only, dataset-scoped seeder (`BLOCKED_DATA_SCALE` in P0B §8 is resolved on the KeepLab
   side). Google Keep remains **`BLOCKED_GOOGLE_KEEP_SAFE_SEEDING`** at all four scales: the private
   database is not writable (`run-as` → *package not debuggable*; `/data/data/…/databases` →
   *Permission denied*) and no reversible bulk-cleanup strategy could be proven before mutation, so
   the mutation was stopped rather than risked. No Google Keep content was created, modified or
   deleted.
3. **PERF-10 — `BLOCKED` → measured (KeepLab-only).** `observeAll()` median 7 / 12 / 35 / **62 ms**
   and `getById()` median 2 / 2 / 3 / 2 ms at 10 / 100 / 500 / 1000 notes, via the production DAO
   in the benchmark variant. Not a matched comparison; not scored against the 1.10× target, and
   measured by a benchmark-variant timing harness rather than the official `androidx.benchmark`
   Microbenchmark API (status `PARTIAL`).
4. **GKP-A11Y-005 dynamic type — `PARTIAL` → measured PASS** at platform font scales 1.0 / 1.3 /
   1.5 / 2.0 (critical text visible, no clipping, controls reachable, font scale restored).
5. **The `verification/**`-vs-`verification/.state/**` contradiction** recorded in the Appendix is
   **resolved by contract design** in the new frozen P0B-CLOSE contract (path classes), so
   `CONTRACT_DEVIATION_COUNT` is 0 for the closure phase.
6. **Unchanged:** frame jank, memory, warm start, rotation and the driven-journey wall times were
   **not** re-measured; their P0B values and their debug-variant confound still apply. The
   reliability rows stay `NEAR`. `PERF-05` (Google Keep create) and `PERF-15` (IMAGE parity) remain
   open/out of scope.

**P0B status after closure: `PARTIAL`.** KeepLab `app/src/main/**` remains 45/45 byte-identical;
`PRODUCTION_BEHAVIOR_CHANGED: NO`. The remaining P0B blocker is the matched **Google Keep** data
scale. Next: fix that remaining blocker — not P1.
