# FINAL — Verification Compression Baseline Audit

Audit → Correct → Freeze for the P0 Verification Compression Benchmark. This report is a
read-only audit over the **existing** artifacts: no engine was re-run, no APK rebuilt, no
KeepLab business logic, journey or Evaluation Core was modified.

Generated: 2026-10-03T13:52Z · Audit root:
`/mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack/verification-benchmark/`

Companion artifacts: `reports/RUN-INVENTORY.md`, `results/run-inventory.json`,
`results/baseline-manifest.json`, `results/summary.json`, `results/summary.csv`.

---

## 1. Run inventory

Full field-level inventory: **`reports/RUN-INVENTORY.md`** (and machine-readable
`results/run-inventory.json`). Counts:

| Set | Runs | Composition |
|---|---|---|
| Formal measured **B** | **11** | J1×3, J2×3, J3×5 |
| Formal measured **C** | **13** | J1×5, J2×3, J3×5 |
| Formal **A** control | **3** | J1×1, J2×1, J3×1 |
| **Total normalized runs** | **27** | 24 measured B/C + 3 A |
| Excluded directories | 9 | 6 warm-up + 3 diagnostic |

### 1.1 The 24/27/28 discrepancy — resolved

Three figures appeared in the logs:

- Stage 1 execution design: **24 measured B/C runs**.
- `normalized-benchmark.json`: **27 total runs**.
- Prior session's terminal summary: **B = 15, C = 13, B/C = 28**.

The artifacts settle it. There are exactly **27 `benchmark-run.json` files** (11 B + 13 C +
3 A). The `15` / `28` figures are **not reproducible**; the only B-labelled directories on
disk are 11 measured + 3 warm-up + 1 fail-test = **15**, and the warm-up directories carry
**no `benchmark-run.json`** at all (they are structurally invisible to the aggregator).
The correct counts are **B = 11 measured, C = 13 measured, 24 measured B/C, 27 total**. The
`15` was a conflation of measured runs with warm-up/diagnostic directories; `28` followed
from it. **The FINAL report body was already consistent** (its tables give B n=3/3/5 and C
n=5/3/5, total 24); only the terminal summary text was wrong.

## 2. Excluded runs (evidence retained, `excluded_from_baseline = true`)

| run_id | class | reason |
|---|---|---|
| `J1-B-WARMUP`, `J2-B-WARMUP`, `J3-B-WARMUP` | warmup | discarded warm-ups (no `benchmark-run.json`) |
| `J1-C-WARMUP`, `J2-C-WARMUP`, `J3-C-WARMUP` | warmup | discarded warm-ups (no `benchmark-run.json`) |
| `FAILTEST-B` | diagnostic | intentional-failure bundle test (native) |
| `FAILTEST-C` | diagnostic | intentional-failure bundle test (Maestro) |
| `CJ1-test` | diagnostic | Maestro J1 smoke spike; only `maestro.xml` retained |

No `failed-pre-fix` run artifact survived as an isolated directory — the pre-freeze Engine B
run(s) were **overwritten** by the post-freeze re-run (see §4). No IME-diagnosis run exists as
a separate artifact. No evidence was deleted by this audit.

## 3. Final measured run count

- **Formal measured: 24** (B 11 + C 13) · **+ 3 A control = 27 normalized runs.**
- Measurements: all 24 measured runs `outcome = PASS`; retries 0; human interventions 0.

## 4. Final APK / hash provenance

| Hash | Size | Status |
|---|---|---|
| `21884d9bd54941ee4ebfaa2dcf31d4d371b2c56156effb429d888d2c41525870` | 19,317,628 B | earlier build (with `ui-test-manifest`); discarded pre-freeze |
| `8e0eafd66c7b77ef02c01e156c4531308b57426d6f19a68afb1e802a5209274f` | 19,317,529 B | first freeze — **pre-`testTag` intermediate build** |
| **`a8858bd1f57b328a5042a120023508ced8e1cbbf68446bab3ce0e5e80f6fdf06`** | **19,358,670 B** | **FINAL** — used by all recorded A/B/C runs |

- The **old hashes are pre-testTag intermediates.** They were superseded when minimal,
  behaviour-neutral `testTag`s / `testTagsAsResourceId` were added to make Maestro/UiAutomator
  selectors stable, after which the APK was **re-frozen once, before Stage 1** (built
  2026-10-03 19:18:20 +0800; frozen copy 19:19:32 +0800 = `11:19:32Z`).
- **All 27 artifact-bearing runs record `apk_sha256 == final`.** Provenance is provable, not
  assumed: `run_engine_b.sh` / `run_engine_c.sh` read the hash from `benchmark-apk.json` at run
  time **and** `adb install -r` the frozen copy (`frozen/app-debug-frozen.apk`, verified
  byte-identical, sha256 = final) during setup. A run executed before the re-freeze would have
  recorded an old hash; none did.
- **Freeze ordering:** every measured run executed *after* the final freeze — run artifact
  times span 19:44–20:51 (+0800), i.e. after 19:19:32. ✓
- **Uncertainty:** low, but not zero — see §13.

## 5. Corrected B medians (formal measured n=11)

| Journey | n | pass | t7a (med) | t7b (med) | t7c (med) | total (med) | total var |
|---|---|---|---|---|---|---|---|
| B J1 | 3 | 3 | 1835.2 ms | 17,162.9 ms | 59.0 ms | **21,342 ms** | 0.9 % |
| B J2 | 3 | 3 | 1837.0 ms | 15,881.0 ms | 506.2 ms | **20,588 ms** | 2.1 % |
| B J3 | 5 | 5 | 1829.2 ms | 7594.5 ms | 1909.1 ms | **13,479 ms** | 9.3 % |

All B times are harness monotonic (host / in-process event log). B J3 t7b variance 18.7 % is
dominated by rotation/dark-mode transitions (2 of 5 runs), not failures.

## 6. Corrected C medians (formal measured n=13)

| Journey | n | pass | t7b | t7c (med) | total (med) | total var |
|---|---|---|---|---|---|---|
| C J1 | 5 | 5 | null (not provable) | 2189.8 ms | **67,099 ms** | 3.9 % |
| C J2 | 3 | 3 | null (not provable) | 2245.7 ms | **76,587 ms** | 1.2 % |
| C J3 | 5 | 5 | null (not provable) | 1990.9 ms | **28,993 ms** | 8.2 % |

`t7b = null` by construction: Maestro exposes no per-command monotonic timestamps; it is never
estimated. `t7c` is the host-measured shared-oracle (`DbProbe`) probe.

## 7. Corrected compression (recomputed from corrected measured set)

Basis: sum of per-journey **median** total verification wall vs the live Engine A control
(A totals: J1 252,562 ms · J2 1,095,870 ms · J3 277,920 ms; ΣA = 1,626,352 ms).

| Journey | A total | B total | B reduction | C total | C reduction |
|---|---|---|---|---|---|
| J1 | 252,562 ms | 21,342 ms | **91.5 %** | 67,099 ms | **73.4 %** |
| J2 | 1,095,870 ms | 20,588 ms | **98.1 %** | 76,587 ms | **93.0 %** |
| J3 | 277,920 ms | 13,479 ms | **95.2 %** | 28,993 ms | **89.6 %** |
| **Aggregate** | 1,626,352 ms | 55,409 ms | **96.6 %** | 172,679 ms | **89.4 %** |

**Confirmed.** Recomputing from the corrected measured set reproduces the headline figures
**B ≈ 96.6 %** and **C ≈ 89.4 %**. Two per-journey cells moved by 0.1 pt versus the original
report (B J1 91.6 → **91.5**, B J3 95.1 → **95.2**), which is rounding only. Percentages are
**not** carried over from the old report — they are regenerated by `harness/measure.py`.

## 8. Aggregator correction

`harness/measure.py` no longer substring-matches `WARMUP`/`TEST`. It is driven by an explicit
machine-readable allowlist:

- `results/baseline-manifest.json` — authoritative `measurement_class` per run:
  `measured | control | warmup | diagnostic | failed-pre-fix`, plus
  `excluded_from_baseline` and `exclusion_reason`.
- Headline summary counts **`measurement_class == "measured"` only**.
- Engine A (`measurement_class == "control"`) is aggregated in a **separate `controls` block**.
- Runs absent from the manifest are **excluded by default** (deny-by-default).
- `summary.json` now carries `measured`, `controls`, `compression` (per-journey + aggregate)
  and `excluded`. `summary.csv` contains measured groups only.

## 9. Technical-conclusion wording (corrected)

- **Engine B's actually-verified stack is `UiAutomator 2.4.0 + deterministic harness`.** It is
  **not** "Compose UI Test + UiAutomator".
- **Compose UI Test: `BLOCKED / DEFERRED` on the current Android 16 / API 36 environment** due
  to an observed Espresso compatibility gap (`InputMethodManagerEventInjectionStrategy` →
  `InputManager.getInstance()` `NoSuchMethodException`, reproducing `GAP-ESPRESSO`).
- **Compose UI Test was not benchmark-verified.** No claim to the contrary is made anywhere.

## 10. Engine dependency, preconditions, evidence fallback

### Environment preconditions (formal preflight, not measured human intervention)
- device **unlocked** (the one-time PIN unlock is an environment prerequisite, **not** a
  per-run intervention);
- screen **awake / stay-on**;
- **Engine B requires the Google IME** (`com.google.android.inputmethod.latin`) for
  `ACTION_SET_TEXT`;
- **Engine C requires the AOSP LatinIME** (`com.android.inputmethod.latin`) for Maestro
  `inputText`;
- **orientation baseline** `user_rotation=0`, `accelerometer_rotation=0`;
- **theme baseline** light (`cmd uimode night no`).

These are set in each run's **timed `setup_wall_ms`** (excluded from T7).

### Evidence fallback (formalized)
`harness/collect_failure.sh` now implements a provider-explicit, non-single-point chain:
1. **Android CLI layout** → `layout.json` (`layout_provider=android_cli`);
2. **fallback `uiautomator dump`** → `layout.xml` (**XML, never relabelled `.json`**;
   `layout_provider=uiautomator_xml`);
3. **screenshot + logcat + dumpsys/state** (always).
`layout_provider` is written into the bundle `metadata.json` (`android_cli` |
`uiautomator_xml` | `unavailable`). Existing diagnostic bundles were annotated:
`FAILTEST-B` → `android_cli`; `FAILTEST-C` → `android_cli` with the `uiautomator_xml` fallback
artifact also retained. **Status: PASS** (both providers produced valid output on-device).

## 11. `PASS-path model calls = 0` — definition

`PASS-path model calls = 0` means only that the **already-defined deterministic verification
Journey, during execution, needs no visual-LLM judgement** (B and C: 0 requests, 0
screenshots read). It does **not** mean the whole Command Code development session made no
model calls. The session-level Evaluation Core figures (215 requests, 43.6 M input tokens,
T7 = 3726.2 s) describe the **whole dev/benchmark session including harness construction** and
are reported separately in `reports/evaluation-core-session-run.json`; they must not be mixed
with the verification-executor metric.

## 12. Data-consistency corrections applied

1. **Count corrected:** B measured 15 → **11**; total 28 → **27** (per Stage 1 + artifacts).
2. **False-positive crash flags corrected:** `J2-C-1/2/3` `process_evidence` `CRASH` →
   `no-crash`. The only `FATAL EXCEPTION` in those logs is
   `Process: com.android.cli.interact.instrumentation` (the Android CLI instrumentation
   server) — **zero** app-process crashes in any measured run. Raw value preserved as
   `process_evidence_raw`; `harness/emit_run.py` crash regex scoped to
   `Process: com.keeplab.app` to prevent recurrence; `normalized-benchmark.json` regenerated
   (27 runs).
3. **Report rounding corrected:** B J1 91.6 → 91.5 %, B J3 95.1 → 95.2 %.
4. **Wording corrected:** Compose UI Test status; verified-stack statement; 0-model-call
   definition; environment preconditions; evidence-fallback provider.

## 13. Remaining uncertainties (explicit)

- **Engine A control** is 1 run/journey; A's T7a/T7b/T7c split is **not separately provable**
  per journey and its token accounting is session-level (A0/Phase B remains the historical
  reference). Compression therefore rests on A **total wall**.
- **`NO_WORKTREE` / `NO_GIT`**: repository has zero commits, so no commit SHA is recorded.
- **Engine C `t7b = null`** by construction (Maestro API limitation).
- **Single device / single unit**; no emulator cross-check.
- **Post-session directory mtimes**: 9 B-run directories show mtime `21:19:04` (after the
  session) while their `benchmark-run.json` contents are `20:06–20:09`; contents are intact and
  hash-consistent, so no artifact loss — noted for transparency.
- **A/B/C all used the final APK**, proven by recorded hash + `adb install` of the frozen copy;
  the residual uncertainty is that the pre-freeze B run was overwritten rather than retained.

## 14. Verdict

- Data consistency: **PASS** — Stage 1 design, run inventory, baseline manifest,
  `summary.json`, `normalized-benchmark.json` and the FINAL report now agree at
  **24 measured B/C + 3 A = 27**, one final APK hash, and **B 96.6 % / C 89.4 %**.
- **P0 Verification Compression baseline: FROZEN.**
