# P0B-CLOSE — BENCHMARKABILITY + HERMES RUNTIME

**Program:** `KEEP-LAB-GOOGLE-KEEP-PARITY` · **Phase:** P0B-CLOSE (blocker removal / measurement
enablement) · **Executed:** 2026-10-05 · **Reference date (unchanged):** 2026-10-04 ·
**Orchestrator:** Hermes, profile `android-stack`, pinned `vgit.af90026 (2026.9.24)` — **not**
upgraded, reinstalled or core-patched.

**Headline.** Every P0B blocker that had a Stack-side fix is closed with new evidence, and the two
blockers that cannot be closed safely are recorded as exact blockers rather than papered over.

1. **The debug-vs-release confound is removed for cold start.** On a release-derived,
   non-debuggable, profileable **benchmark-only** variant, KeepLab's cold start is
   **433.5 ms median (p95 447.5 ms)** against Google Keep's 599 ms — **0.72×, inside the 1.10×
   target**. P0B's 2.59× gap (1549 ms) was dominated by measuring the debug build.
2. **Matched data scale is no longer blocked on the KeepLab side.** A benchmark-only,
   dataset-scoped seeder reaches **10 / 100 / 500 / 1000** exactly, is idempotent, and cleans up
   only its own dataset. Google Keep's side stays **`BLOCKED_GOOGLE_KEEP_SAFE_SEEDING`** at all
   four scales, with the reason evidenced.
3. **PERF-10 (Room query latency) is measured** — `observeAll()` median 7 / 12 / 35 / **62** ms and
   `getById()` median 2 / 2 / 3 / 2 ms at 10 / 100 / 500 / 1000 notes (through the production DAO).
4. **GKP-A11Y-005's dynamic-type half is closed** — PASS at font scales 1.0 / 1.3 / 1.5 / 2.0 with
   deterministic checks and a proven font-scale restore.
5. **The old contract contradiction is resolved by design**, not by reinterpreting it: the new
   P0B-CLOSE contract classifies `verification/.state/**` as `RUNTIME_EPHEMERAL` (allowed) and the
   frozen `verification/**` subtrees individually as `FORBIDDEN`, so no allowed path overlaps a
   forbidden one and `boundaries` passes with zero path conflicts.
6. **Hermes now enforces the contract boundary with a native, fail-closed `pre_tool_call` hook**
   (`INSTALLED_REQUIRES_NEW_SESSION`), verified against the real Hermes hook dispatcher.
7. **Hermes Evaluation attribution is real**: model, provider and token totals now come from
   stored Hermes rows, and the P0B session's UNKNOWN classification drops
   **74.7 % → 32.0 %** without inventing a single phase.

**Production behaviour did not change.** `app/src/main/**` is 45/45 files byte-identical, and so
are the other source sets, the production resources, the production manifest, the frozen P0B
contract package and the P0B run evidence.

---

## 1. Environment and provenance

| | |
| --- | --- |
| Device | `87296ada` — Redmi Note 7 Pro / `violet`, Android release 16 / SDK 36 |
| Display | 1080x2340, 440 dpi |
| KeepLab | `com.keeplab.app` 0.1.0 (code 1) — **benchmark variant** for the closure measurements |
| Google Keep | `com.google.android.keep` **5.26.391.03.90** (code 220677611) — unchanged, matches the frozen P0A manifest → **no `REFERENCE_VERSION_MISMATCH`**, no re-baseline |
| Hermes | pinned `vgit.af90026 (2026.9.24)`, upstream `af90026aa…`, profile `android-stack` |

Closure evidence root: `KeepLab-Relay/benchmark/results/P0B-CLOSE/`.
Stack-side evidence: `orchestration/hermes/evidence/p0b-close/`.

**Pre-phase baseline hashes** (taken before any edit):
`benchmark/results/P0B-CLOSE/_baseline/*.sha256`.

---

## 2. Contract fix

### 2.1 New contract

A new canonical package was authored and compiled through the **existing** Specification Compiler
(no new entry point):

```
python3 specification/compiler/hash_manifest.py   KeepLab-Relay/specs/p0b-close-benchmarkability
python3 specification/compiler/build_contract.py  KeepLab-Relay/specs/p0b-close-benchmarkability
python3 specification/compiler/validate_package.py KeepLab-Relay/specs/p0b-close-benchmarkability \
        --project-root /mnt/AndroidDev/Projects
```

Result — first pass and after all P0B-CLOSE work, unchanged:

```
STATUS=READY schema=PASS traceability=PASS boundaries=PASS acceptance=PASS hashes=PASS errors=0
```

`contract_id = KEEPLAB-P0B-CLOSE-001` · 10 requirements · 10 acceptance criteria · 8 tasks ·
13 frozen decisions (`DEC-001..DEC-013`) · 5 assumptions.

**The old P0B contract was not modified.** `specs/p0b-performance-reliability/` is 13/13 files
byte-identical, and it still validates `STATUS=READY`. `FROZEN_CONTRACT_REOPEN_COUNT: 0`.

### 2.2 Path classes and the resolved contradiction

The new contract models explicit classes in `project-context.json` and compiles them into
`allowed_paths` / `forbidden_paths`:

| Class | Examples |
| --- | --- |
| `PRODUCTION_IMMUTABLE` | `app/src/main/**`, `app/src/debug/**`, `app/src/release/**`, `app/src/test/**`, `app/src/androidTest/**`, production resources/manifest, `MISSION.md`, `FACTORY_RULES.md`, `.hermes.md`, `specification/**`, `evaluation/commandcode/core.py`, `phase_rules.json`, `evaluation/taxonomy/**`, `HERMES-LOCK.json`, `specs/p0b-performance-reliability/**` |
| `BENCHMARK_SOURCE` | `app/build.gradle.kts`, `app/src/benchmark/**`, `benchmark/**`, `settings.gradle.kts`, `build.gradle.kts`, `gradle/libs.versions.toml` |
| `TEST_SOURCE` | `orchestration/hermes/evaluation_adapter/tests/**` |
| `RUNTIME_EPHEMERAL` | `verification/.state/**`, `verification/.runs/**`, `benchmark/.state/**` |
| `EVIDENCE_OUTPUT` | `benchmark/results/**`, `reports/**`, `orchestration/hermes/evidence/**` |
| `FORBIDDEN` | `Testapp/**`, `PowerAi/**`, `verification/{core,runner,adapters,contracts,reference-replay,android,tests,docs}/**`, `verification-benchmark/**`, `references/**`, `harness/**`, `.factory/**`, `KeepLab-Relay-evidence/**` |

**The P0B contradiction is gone.** P0B forbade `verification/**` while simultaneously *requiring*
the in-tree device lock, whose helper creates `verification/.state/locks/device-87296ada.lock`
(P0B counted `CONTRACT_DEVIATION_COUNT = 1`). P0B-CLOSE expresses the same intent without the
overlap: `verification/.state/**` is `RUNTIME_EPHEMERAL` (allowed, because the lock must be able to
write it) while `verification/core/**` — including `device_lock.sh` itself — stays `FORBIDDEN`
(it is executed, never modified). The boundaries gate evaluates this with the compiler's own
`overlaps()` rule and reports **zero `E_PATH_CONFLICT`**.

Two consequence checks (both asserted in the guard's test suite): writing the lock path is
**ALLOW** with class `RUNTIME_EPHEMERAL`; writing `verification/core/device_lock.sh` is **BLOCK**.

The new contract also **explicitly supersedes** P0B's `DEC-002` (which rejected a Macrobenchmark
module) *for the closure phase only*, and says so in `contract_notes.supersedes`. The historical
decision is preserved, not rewritten.

---

## 3. Hermes runtime enforcement (the contract guard)

### 3.1 What the pinned Hermes actually supports

Established from the **local pinned source**, not from the web (child audit
`P0B-CLOSE-HERMES-CAPABILITY-AUDIT`, evidence in §12). The relevant facts:

* `pre_tool_call` is a real, blocking-capable event: fire site `model_tools.py:769-803`
  (`_pre_dispatch_guards`), consumed at `model_tools.py:790-791` as a synthetic tool error.
* A shell hook on `pre_tool_call` can veto: exit code `2` (`BLOCK_EXIT_CODE`,
  `agent/shell_hooks.py:44`), or stdout `{"action":"block","message":…}` /
  `{"decision":"block","reason":…}` (`_parse_pre_tool_call`).
* `fail_closed: true` is honoured **only** for `pre_tool_call` and makes spawn-error, timeout and
  unparseable stdout block as well (`_evaluate_result`, `shell_hooks.py:380-439`).
* `matcher` is a regex honoured for `pre_tool_call` / `post_tool_call` only.
* stdin payload: `{hook_event_name, tool_name, tool_input, session_id, cwd, profile, extra}`
  (`_payload_fields`).

### 3.2 The guard

`orchestration/hermes/evaluation_adapter/contract_guard.py` reads the **frozen** package at
runtime — `implementation-contract.json` for ALLOW/BLOCK, `project-context.json` for the class
labels, `manifest.json` for integrity — and never hard-codes a path list. A manifest hash mismatch
is reported as `CONTRACT_INTEGRITY_FAILURE` and keeps failing closed.

Decision semantics: inside an allowed path → ALLOW; inside a forbidden path → BLOCK; inside the
project but unlisted → BLOCK (fail closed); outside the project root → ALLOW labelled
`OUT_OF_CONTRACT_SCOPE`; a write verb with no resolvable literal target → BLOCK
(`AMBIGUOUS_WRITE_TARGET`). Terminal commands are parsed for **high-confidence** write intent only
(redirection, `tee`, `cp`/`mv`/`install`, `rm`/`rmdir`, `mkdir`, `touch`, `truncate`, slash-bearing
`chmod`/`chown`/`chgrp`, `dd of=`, `sed -i`), with unexpanded shell variables treated as
unresolvable rather than guessed into a project path. No shell parser was written; anything the
parser cannot see is out of scope and documented as such.

### 3.3 Verification

22 offline deterministic tests (`orchestration/hermes/evaluation_adapter/tests/test_contract_guard.py`),
including the required cases:

| Case | Result |
| --- | --- |
| benchmark-source write | **ALLOW** (`BENCHMARK_SOURCE`) |
| runtime lock creation (`verification/.state/locks/**`) | **ALLOW** (`RUNTIME_EPHEMERAL`) |
| report / evidence output | **ALLOW** (`EVIDENCE_OUTPUT`) |
| `app/src/main/**` modification | **BLOCK** (`PRODUCTION_IMMUTABLE`) |
| `app/src/test/**`, `app/src/androidTest/**` | **BLOCK** |
| `Testapp/**`, `PowerAi/**` | **BLOCK** |
| governance files (`.hermes.md`, `MISSION.md`, `FACTORY_RULES.md`, `specification/**`) | **BLOCK** |
| unclassified in-project path | **BLOCK** (fail closed) |
| ambiguous terminal write (`rm -rf $UNSET`) | **BLOCK** (`AMBIGUOUS_WRITE_TARGET`) |
| read-only terminal commands | **ALLOW** |
| false-positive guards (`chmod +x`, `truncate -s 0`, `python3 -m unittest`, `unzip -l \| grep`) | **ALLOW** |

Full transcript: `orchestration/hermes/evidence/p0b-close/guard-verification.txt`.

And against the **real Hermes hook dispatcher** (not a mock):

```
$ hermes hooks test pre_tool_call --for-tool write_file --payload-file .../guard_block_production_write.json
      exit=2  parsed (Hermes wire shape): {"action": "block", "message": "[P0B-CLOSE CONTRACT GUARD]
              BLOCK write_file (PRODUCTION_IMMUTABLE) target=KeepLab-Relay/app/src/main/... "}
$ hermes hooks test pre_tool_call --for-tool write_file --payload-file .../guard_allow_benchmark_write.json
      exit=0  parsed: <none — hook contributed nothing to the dispatcher>
$ hermes hooks test pre_tool_call --for-tool terminal
      exit=0  parsed: <none>
```

### 3.4 Activation state — reported honestly

```
HERMES PROJECT-LOCAL GUARD: INSTALLED_REQUIRES_NEW_SESSION
```

Registered through Hermes's own sanctioned interface (`hermes config set hooks.pre_tool_call …`)
and consented via `$HERMES_HOME/shell-hooks-allowlist.json` (the documented manual-allowlisting path
for non-TTY deployments); `hermes hooks list` shows it `✓ allowed` and `hermes hooks doctor` is
clean for both configured hooks. **It is not ACTIVE in this session**, because hook registration
happens at process startup (`register_from_config`) and this session started before the
registration. It is therefore verified by policy function offline and by the hook dispatcher, and
its activation is *not* over-claimed. Undo is `hermes hooks revoke <path>` + `hermes config unset
hooks.pre_tool_call`.

### 3.5 Hermes quality gates

```
HERMES_NATIVE_QUALITY_GATE: NOT_AVAILABLE
```

The pinned Hermes **does** have a Goal/Completion Contract and deterministic goal gate
(`hermes_cli/goals.py::GoalContract`, `GoalGate`, `/goal gate add <cmd>`), but it is **goal-loop
scoped and turn-boundary scoped** — it requires an active `/goal` Ralph loop and runs before the
LLM judge inside that loop. It cannot serve as a phase-level deterministic gate, and it cannot be
retro-fitted to a session already running. Per the brief this is recorded as
`NOT_AVAILABLE_IN_PINNED_HERMES` (for phase-level gates) and the same deterministic gates were
invoked through the **existing Stack runner** instead:

| Gate | Result |
| --- | --- |
| P0B-CLOSE contract validation | **PASS** (`READY`, all five gates, errors=0) |
| guard policy tests (offline) | **PASS** (22/22) |
| guard activation probe (`hermes hooks doctor`) | **PASS** (clean) |
| benchmark build (`:app:assembleBenchmark`) | **PASS** |
| Macrobenchmark driver module build (`:benchmark:assembleBenchmark`) | **PASS** |
| benchmark target `debuggable=false` | **PASS** (`DEBUGGABLE` absent from the installed package flags) |
| profileable / benchmark accessibility | **PASS** (§5.3 shell probe `INCONCLUSIVE` on this ROM; §6 Macrobenchmark run is the authoritative proof) |
| benchmark-only seeder isolation | **PASS** (seeder absent from the release merged manifest) |
| relevant Android/device results | **PASS** (`failures=0`) |
| product-safety hash | **PASS** (`PRODUCTION_BEHAVIOR_CHANGED: NO`) |
| P0B-CLOSE report validation | **PASS** (this document) |

---

## 4. Hermes Evaluation — source-adapter fix

### 4.1 Root cause (from the read-only audit)

* `model = null` — the adapter's row builder never stamped `model`, and
  `core.load_session` derives `source.models` from message rows only (`core.py:150-152`).
* `provider = null` — structurally unfixable upstream: `core.py:1191` initialises
  `provider: None` and **nothing ever assigns it**.
* tokens `0` — no row carried `usage`, and Hermes stores only session-level totals.
* `UNKNOWN = 74.7 %` — the adapter emitted **native Hermes tool names** (`terminal`, `patch`,
  `search_files`, `delegate_task`, `execute_code`) while the frozen phase rules are written in the
  **Command Code** vocabulary (`shell_command`, `edit_file`, `grep`, `agent`), and core has no
  tool-name normalisation. 68 spans fell to `no_rule_match`.

### 4.2 The fix (minimum change, no core edit, no second evaluator)

| File | Change |
| --- | --- |
| `orchestration/hermes/evaluation_adapter/hermes_session_source.py` | adds `HERMES_TOOL_ALIAS` (`terminal→shell_command`, `patch→edit_file`, `search_files→grep`) and `canonical_tool_name()`; stamps the persisted `model` on message rows; preserves native identity as a sibling `native_name` on each `tool_use` part (the `input` payload is untouched); builds a persisted **identity** block (agent host / provider / model / usage / cost status) and writes it into the shim header; returns it in the adapter metadata |
| `evaluation/commandcode/finalize_session.py` | adds one **additive, optional** `identity` parameter plus `_apply_identity()`, applied after `core.analyze` and before `core.write_outputs`; omitted ⇒ byte-identical output for every existing caller |
| `evaluation/commandcode/auto_finalize.py` | passes `identity=meta.get("identity")` on the Hermes path only |

Only **high-confidence** equivalences are aliased. `delegate_task` and `execute_code` are
deliberately **left unmapped** — mapping them would be inventing a phase to lower the UNKNOWN
ratio. `core.py`, `phase_rules.json` and the taxonomy are **untouched**.

### 4.3 Before / after (isolated, non-mutating)

Command: `python3 orchestration/hermes/evaluation_adapter/tests/run_reeval_compare.py`
→ `orchestration/hermes/evidence/p0b-close/evaluation-reeval-comparison.json`.

**BEFORE** re-finalises the *production shim exactly as the pre-P0B-CLOSE adapter wrote it*
(read-only) and **reproduces the published figures exactly**, which validates the comparison
method. **AFTER** re-normalises the same session with the improved adapter. Both write into the
P0B-CLOSE evidence directory; `/mnt/AndroidDev/Projects/_evaluation` is never opened.

| Field | BEFORE | AFTER |
| --- | --- | --- |
| agent host | `Command Code` (hard-coded in the frozen core) | **`Hermes`** |
| model | `null` | **`deepseek/deepseek-v4.1-flash`** |
| provider | `null` | **`commandcode`** |
| requests | `0` | **`89`** (stored `api_call_count`) |
| input tokens | `0` | **`294 384`** |
| output tokens | `0` | **`136 216`** |
| cache read | `0` | **`16 301 312`** |
| cache write | `0` | **`0`** |
| reasoning tokens | — | **`51 626`** |
| cost | `0.0` | `0.0` + `cost_status=unknown` → **cost reported `NOT_AVAILABLE`, never estimated** |
| **UNKNOWN share** | **74.7 %** (68 spans, 1919.2 s) | **32.0 %** (24 spans, 820.9 s) |

**Δ UNKNOWN = −42.7 points / 44 spans recovered.** Every value is read from the Hermes store; none
is inferred. `tokens_raw.provenance = hermes_session_totals` and
`run.identity.not_available` record that per-turn usage, per-tool timing, turn ids and api request
ids are **not persisted** by the pinned Hermes, so they remain absent.

**The 24 spans that remain UNKNOWN are attributable, and none is an adapter failure:**

| Native tool | spans | why it stays UNKNOWN |
| --- | --- | --- |
| `write_file` | 12 | all under `benchmark/**` (harness sources, results JSON) — no phase rule covers the harness tree |
| `edit_file` (← `patch`) | 8 | `benchmark/lib/*.py`, `benchmark/flows/*.yaml` — `t4_impl_code` omits `.py`, `t6_maestro_def` requires `/maestro/` |
| `shell_command` (← `terminal`) | 1 | a `python3 - <<EOF` heredoc; the rule expects `python3 -` |
| `delegate_task` | 2 | genuinely ambiguous — no Command Code equivalent, no `subagent_type` shape |
| `execute_code` | 1 | genuinely ambiguous — no Command Code equivalent |

Fixing those would require adding rules to the **frozen** Evaluation Core vocabulary. That is out of
scope and was not done; the residual is reported, not hidden.

**Child attribution: `PASS`.** Stable parent→child linkage **is** persisted
(`sessions.parent_session_id`); the three P0B children (`…287b0f`, `…42767d`, `…204d08`) carry
`parent_session_id = 20261005_021134_faf1e3`, confirmed independently by `hermes_run_summary.py`
(`children=3`, `max_concurrent=3`, `parallel_overlap_sec=162.864`). No timestamp inference was used.

**Regressions: PASS.** Command Code suites: `test_evaluation_core.py` 11/11,
`_v022` 21/21, `_v023` 9/9, `test_task_window_v021.py` 15/15, `test_finalize_session.py` 6/6 —
62/62. Hermes source test: `HERMES_SOURCE_TEST=PASS`. Auto-Finalizer: unchanged and working
(idempotency `ALREADY_FINALIZED` → `SKIP_UNCHANGED`, incomplete-session refusal, NOT_FOUND).
Auto-Finalizer was **not** rebuilt and the real P0B session was **not** re-finalized into the
production index (see §9).

---

## 5. Android benchmark surface

### 5.1 The benchmark target variant

`app/build.gradle.kts` gains one build type and nothing else:

```kotlin
create("benchmark") {
    initWith(getByName("release"))              // minify stays false, as shipping release has it
    isDebuggable = false
    signingConfig = signingConfigs.getByName("debug")
    matchingFallbacks += listOf("release")
}
```

The shipping `release` build type is **not** altered. `app/src/benchmark/AndroidManifest.xml`
(merged only into the `benchmark` variant) adds `<profileable android:shell="true"
tools:targetApi="29"/>` and the benchmark-only ops receiver. `settings.gradle.kts` gains
`include(":benchmark")` and a `pluginManagement` resolution mapping for `com.android.test` (AGP
publishes no standalone plugin marker for that id); `gradle/libs.versions.toml` gains
`androidxBenchmark = "1.5.0"`, `benchmark-macro-junit4`, `benchmark-junit4` and the
`com.android.test` plugin alias.

* **minSdk 24 caveat, stated plainly:** `<profileable>` exists only from API 29 (and
  `android:enabled` from 30). On API 24–28 it is inert; it is effective on the API 36 reference
  device. Recorded, not claimed as wider coverage.

### 5.2 No hidden optimisation — proven, not asserted

AGP merges **library-provided** ART profiles into every non-debuggable variant. The benchmark
variant must not get more than the shipping release would:

```
$ diff <(sort .../merged_art_profile/release/.../baseline-prof.txt) \
       <(sort .../merged_art_profile/benchmark/.../baseline-prof.txt)
(no output — byte-identical, 3534 lines each)
```

The project commits **no** `baseline-prof.txt` / startup profile of its own. So the benchmark
variant's profile situation is exactly the shipping release's: library profiles only, no
app-authored profile. **No baseline profile, startup profile, paging, DAO or search optimisation
was added.**

### 5.3 Non-debuggable and profileable — verified on the device

```
$ adb shell dumpsys package com.keeplab.app | grep -E '^(flags|pkgFlags)=\['
    flags=[ HAS_CODE ALLOW_CLEAR_USER_DATA ALLOW_BACKUP KILL_AFTER_RESTORE ]
    pkgFlags=[ HAS_CODE ALLOW_CLEAR_USER_DATA ALLOW_BACKUP KILL_AFTER_RESTORE ]
          ^ DEBUGGABLE is ABSENT  (before the phase the installed debug build showed DEBUGGABLE)
```

`versionName=0.1.0`, `variantName: "benchmark"` (from `output-metadata.json`).

**Profileable:** this ROM's `dumpsys package` exposes no `PROFILEABLE` token and `am profile
start` produced no acknowledgement, so the shell probe is recorded as **`INCONCLUSIVE`** rather
than claimed. The authoritative proof is the **Macrobenchmark run** (§6): `androidx.benchmark`
refuses to measure a debuggable target and requires shell profiling access, so a successful
measurement is the profileable/non-debuggable proof. The device was restored to the variant it was
found with afterwards (`reinstall_debug_rc=0`, `DEBUGGABLE` present again).

### 5.4 The benchmark-only N-note seeder

`app/src/benchmark/java/com/keeplab/app/benchmark/` — `BenchmarkOps`, `BenchmarkOpsReceiver`.
Compiled **only** into the `benchmark` variant. Driven deterministically by `am broadcast`
(no UI injection, no LLM judgement):

```
adb shell am broadcast -n com.keeplab.app/com.keeplab.app.benchmark.BenchmarkOpsReceiver \
    -a com.keeplab.app.benchmark.OPS --es op seed --es dataset MAIN --ei count 500
```

Properties: dataset id + known title prefix `P0BCLOSE-<dataset>#` (the body repeats the key);
deterministic note shape (index-derived key, colour by `index % 10`, `pinned = index % 25 == 0`);
idempotent (cleanup-then-insert); **cleanup deletes only rows whose title carries that dataset's
key**; every write goes through the production DAO (`NoteDao.insertNote`), every read through
`NoteDao.observeAll()`; no production entity, DAO, schema or migration is touched.

Measured results (`records/measurement-records.md`):

| requested N | actual benchmark count | db rows before | db rows after | replay actual | benchmark rows left after cleanup |
| --- | --- | --- | --- | --- | --- |
| 10 | **10** | 8 | 18 | **10** | **0** |
| 100 | **100** | 8 | 108 | **100** | **0** |
| 500 | **500** | 8 | 508 | **500** | **0** |
| 1000 | **1000** | 8 | 1008 | **1000** | **0** |

The 8 non-benchmark rows are the pre-existing real notes and are provably preserved
(`non_benchmark_count = 8` before and after every scale).

**Seeder unreachable from the production variant — proven from the built manifests, not asserted:**

| Variant | merged manifest contains `BenchmarkOpsReceiver` | contains `<profileable>` |
| --- | --- | --- |
| `benchmark` | yes (benchmark-only surface) | yes |
| `debug` | **no** | **no** |
| `release` | **no** | **no** |

### 5.5 PERF-10 — Room query latency

**Status: `PARTIAL`** — measured at every required scale, but not with the official
`androidx.benchmark` Microbenchmark API and KeepLab-only. Full disclosure below.

Measured inside the benchmark variant over the seeded dataset through the **production DAO**;
7 iterations per scale after a discarded warm-up; median and nearest-rank p95:

| notes | `observeAll()` median / p95 | `getById()` median / p95 |
| --- | --- | --- |
| 10 | 7 / 9 ms | 2 / 3 ms |
| 100 | 12 / 15 ms | 2 / 3 ms |
| 500 | 35 / 46 ms | 3 / 3 ms |
| 1000 | 62 / 72 ms | 2 / 9 ms |

`observeAll()` grows ~linearly with note count — consistent with the un-paged full-table relation
load hypothesised in P0B. **It is KeepLab-only**: Google Keep's database is inaccessible, so this
is **not** a matched comparison and is not scored against the 1.10× target.

**Method limitation, stated plainly:** this is a benchmark-variant-only deterministic timing
harness, **not** `androidx.benchmark` Microbenchmark. A self-instrumenting `com.android.test`
module runs in its own process and cannot reach the app's private Room types, and the app's
`androidTest` source set is outside this contract's boundary. The harness is deterministic,
seeded, repeated, and its iterations are recorded with every number.

---

## 6. Macrobenchmark

A separate `com.android.test` driver module (`benchmark/build.gradle.kts`,
`benchmark/src/main/java/com/keeplab/app/macrobenchmark/ColdStartupBenchmark.kt`) targets `:app`'s
`benchmark` build type. It uses the standard Android benchmark API —
`MacrobenchmarkRule.measureRepeated` with `StartupTimingMetric` + `FrameTimingMetric`,
`StartupMode.COLD`, `CompilationMode.DEFAULT`, 5 iterations.

```
MACROBENCHMARK: PASS
$ bash benchmark/run_macrobenchmark.sh     # under the host device lock
> Task :benchmark:connectedBenchmarkAndroidTest
Starting 1 tests on Redmi Note 7 Pro - 16
Finished 1 tests on Redmi Note 7 Pro - 16     (0 skipped, 0 failed)
BUILD SUCCESSFUL in 5m 5s     gradle_connected_rc=0
```

**This run is itself the authoritative profileable / non-debuggable proof.** `androidx.benchmark`
refuses to measure a debuggable target and requires shell profiling access; a completed measurement
with 5 perfetto traces therefore establishes both properties functionally, which is why the
`INCONCLUSIVE` `am profile` shell probe in §5.3 is not relied on.

Raw results (copied to `benchmark/results/P0B-CLOSE/raw/macrobenchmark/`):

| Metric | n | min | median | max | CV |
| --- | --- | --- | --- | --- | --- |
| `timeToInitialDisplayMs` | 5 | 684.8 | **690.0** | 739.7 | 3.3 % |
| `frameCount` (startup window) | 5 | 3 | 3 | 5 | 26.3 % |

| Sampled frame metric | P50 | P90 | P95 | P99 |
| --- | --- | --- | --- | --- |
| `frameDurationCpuMs` | 35.2 | 193.8 | 194.8 | 195.9 |
| `frameOverrunMs` | 29.0 | 238.7 | 244.6 | 249.2 |

Rig, recorded by the library: `Redmi Note 7 Pro` / `violet`, SDK 36, `userdebug` build
`BP4A.251205.006`, 8 cores, `cpuLocked: true`, `memTotalBytes: 5811085308`,
`compilationMode: **run-from-apk**` — the project commits no app-authored profile, so there is
nothing to AOT-compile and the measurement is the conservative "just-installed" case. Five perfetto
traces (one per iteration, ~1.1 MB each) are stored alongside.

**Method caveat — two startup numbers, not one.** Macrobenchmark's `timeToInitialDisplayMs`
(**690 ms**) and the `am start -W` `TotalTime` of §7 (**433.5 ms**) are **different metrics produced
by different tools** over different windows and compilation states; they must not be averaged or
substituted for each other. The Google Keep reference (599 ms) is an `am start -W` figure, so the
scored 1.10× comparison uses the **`am start -W` pair only**. The Macrobenchmark figure is reported
as an independent, more rigorous startup measurement and is deliberately **not** compared against
Google Keep.

The `frameOverrunMs` P90/P95 of ~240 ms also means the launch window still has a real frame-time
problem on the benchmark variant — consistent with the P0B jank finding and **not** fixed by the
build variant. Frame jank was not otherwise re-measured (§7).

---

## 7. Cold start re-measurement (build-sensitive metric)

`am force-stop` + `am start -W -n com.keeplab.app/.MainActivity` (`TotalTime`) — **identical to the
P0B method**; the only change is the build variant. 7 runs, first discarded (n=6).

| | n | median | p95 | min | max |
| --- | --- | --- | --- | --- | --- |
| benchmark variant, **final canonical run** | 6 | **433.5 ms** | 447.5 ms | 403 | 450 |
| benchmark variant, earlier run of the same batch | 6 | 384 ms | 400.5 ms | 370 | 401 |
| P0B debug (historical) | 7 | 1549 ms | 1695 ms | — | — |
| Google Keep (release, frozen reference) | 7 | 599 ms | 634 ms | — | — |

Ratio vs Google Keep: **0.72×** → **inside the 1.10× target**.
Median change vs the P0B debug figure: **−1115.5 ms**.

Both benchmark-variant runs of the same protocol are reported: **433.5 ms** (the final canonical
run whose raw evidence is in the closure directory) and **384 ms** (an earlier run of the same
batch). The ~13 % spread between them is run-to-run variance on this device, is recorded rather
than averaged away, and does not change the conclusion — both are comfortably inside the 1.10×
target.

**Interpretation, and its limit.** P0B's 2.59× cold-start gap was dominated by measuring the debug
build (no AOT of app code, JIT, debug overhead). Under a release-derived, non-debuggable variant
KeepLab starts **faster** than Google Keep on this device. This is a **measurement** result. The
limit is stated in the matrix row: the shipping `release` artifact itself was never installed or
measured, so this is a release-derived verdict, not a shipping-build verdict.

**Provenance of every replaced metric:** `benchmark/results/P0B-CLOSE/records/provenance.json`
records, per metric, the old artifact, the old value, the old build variant, the new artifact, the
new value, the new build variant, the reason for replacement, the measurement-method change and
the build-variant change.

**Metrics deliberately NOT re-measured** (method impact assessed): warm start, rotation, memory
and the driven-journey wall times keep their P0B debug-variant values, and **frame jank was not
re-measured on the benchmark variant** — so the 14.56× scroll-jank row is untouched and still
carries its stated confound. This is recorded rather than quietly re-run.

---

## 8. Google Keep matched data scale

```
10:   BLOCKED
100:  BLOCKED
500:  BLOCKED
1000: BLOCKED

BLOCKED_GOOGLE_KEEP_SAFE_SEEDING
UNRELATED GOOGLE KEEP DATA CHANGED: NO
CLEANUP VERIFIED: NOT_APPLICABLE (nothing was created)
```

**No Google Keep content was created, modified or deleted by this phase.** The decision was to
stop rather than mutate, and it is backed by recorded evidence
(`raw/googlekeep/assessment.txt`):

1. **The private database is not writable**, proven rather than assumed:
   ```
   $ adb shell run-as com.google.android.keep ls
   run-as: package not debuggable: com.google.android.keep
   $ adb shell ls /data/data/com.google.android.keep/databases
   ls: /data/data/com.google.android.keep/databases: Permission denied
   ```
   Root-patching the data, modifying the APK, clearing app data, switching accounts and using an
   unofficial private API are all forbidden by the brief and were not attempted.
2. **No reversible bulk-select/cleanup strategy could be proven before mutation.** Google Keep
   offers no "select all" affordance for an arbitrary N-note set; removing 500–1000 notes would
   require a UI-driven selection of every card — long, fragile, and irreversible if a step fails
   mid-cleanup. Because cleanup could not be *proven* first, the per-scale prerequisite in the
   brief is unmet at 500 and 1000, and (by the same test) at 100 and 10 as well.
3. **Public intent surface is insufficient**: `ACTION_SEND` can request a new note but offers no
   programmatic dataset selection or deletion, so it cannot make the mutation reversible.
4. The reference itself is intact and unchanged: `com.google.android.keep` **5.26.391.03.90**
   (code 220677611), matching the frozen P0A manifest; the visible-content census was read
   read-only (uiautomator hierarchy, 31 146 bytes) and shows **zero** `P0BCLOSE-`-prefixed notes.

**Consequence, stated honestly:** the *matched* 10/100/500/1000 axis is still blocked, so
`GKP-PERF-002` stays `PARTIAL` and no KeepLab-vs-Google-Keep parity value is claimed at scale. The
KeepLab side of the scale axis is no longer blocked — that half of the P0B blocker is closed.

---

## 9. Existing P0B evidence and production safety

### 9.1 Preservation

| Scope | Result |
| --- | --- |
| `benchmark/results/P0B-RUN1`, `P0B-RUN2`, `P0B-CANONICAL` | **97/97 files byte-identical** |
| `specs/p0b-performance-reliability/**` (the frozen P0B contract) | **13/13 files byte-identical**, still validates `READY` |
| `reports/P0B-PERFORMANCE-RELIABILITY.md` | preserved; a dated P0B-CLOSE amendment appended (no historical value rewritten) |
| Production evaluation tree `/mnt/AndroidDev/Projects/_evaluation` | **not written by P0B-CLOSE**; the P0B run directory is unmodified (mtime 02:54, pre-phase) and the index still holds exactly one Hermes record, `hermes:20261005_021134_faf1e3` |

Note: a pre-existing user systemd timer (`commandcode-autofinalizer.timer`, every 2 min) rewrites
the production index file with identical content. It is not part of P0B-CLOSE, it never entered
P0B-CLOSE's output root, and no second evaluation of the P0B session was produced.

### 9.2 Product safety

```
$ bash benchmark/lib/verify_product_safety.sh
KeepLab app/src/main/**                              45/45 identical
KeepLab app/src/{debug,release,test,androidTest}     18/18 identical
KeepLab production resources                         11/11 identical
KeepLab production manifest                          1/1 identical
frozen P0B contract package                          13/13 identical
P0B run evidence (RUN1/RUN2/CANONICAL)               97/97 identical
Stack reports/evidence                               1/1 identical

AUTHORISED_CHANGE (benchmark wiring):
  app/build.gradle.kts, settings.gradle.kts, gradle/libs.versions.toml  (the three the contract authorises)

PRODUCTION_BEHAVIOR_CHANGED: NO
```

Also not touched: production Kotlin, Room production schema/migrations (`version = 2`,
`user_version = 2` on device after all seeding), repository/ViewModel/Compose behaviour,
`MISSION.md`, `FACTORY_RULES.md`, `.hermes.md`, `HERMES-LOCK.json`, Testapp, PowerAi.
No `git reset`/`clean`/`commit`/`push` was issued.

---

## 10. Tests run (targeted regression only)

| Suite | Result |
| --- | --- |
| Specification Compiler package validation (new P0B-CLOSE contract) | `READY`, 5/5 gates |
| Old P0B contract validation (unchanged) | `READY`, 5/5 gates |
| Contract-guard policy tests | **22/22 PASS** |
| `hermes hooks list` / `doctor` | clean, hook allowlisted |
| Real hook-dispatcher fixtures (block × 2, allow × 2) | correct block/allow |
| `evaluation/tests/test_evaluation_core.py` | 11/11 |
| `…_v022.py` / `…_v023.py` / `test_task_window_v021.py` | 21/21, 9/9, 15/15 |
| `test_finalize_session.py` | 6/6 |
| `evaluation/tests/test_hermes_source.py` | `HERMES_SOURCE_TEST=PASS` |
| Isolated before/after re-evaluation of the P0B session | comparison written, production index untouched |
| `:app:assembleBenchmark` | BUILD SUCCESSFUL |
| `:benchmark:assembleBenchmark` (Macrobenchmark driver) | BUILD SUCCESSFUL |
| release vs benchmark merged ART profile | identical (3534 lines) |
| Variant install + `debuggable=false` assertion | PASS |
| Seeder 10/100/500/1000 + idempotency + dataset-scoped cleanup | PASS (0 harness failures) |
| PERF-10 per scale | PASS |
| Dynamic-type deterministic check at 1.0/1.3/1.5/2.0 + font-scale restore | PASS (`match=YES`) |
| Device lock (capacity = 1) | held for every batch, released on exit |
| Product-safety hash check | PASS |

**Not run** (deliberately): P0A, S1, S1.1, the full historical journey set, the P0B device battery,
and any Hermes benchmark. No shared dependency of those changed.

---

## 11. Remaining blockers and P0B status

| Blocker | State |
| --- | --- |
| Matched 10/100/500/1000 data scale | **KeepLab: CLOSED** (seeder + per-scale verification) · **Google Keep: OPEN** — `BLOCKED_GOOGLE_KEEP_SAFE_SEEDING` |
| Debug-vs-release confound for startup | **CLOSED for cold start** (0.72× on a release-derived variant). Frame jank / restart / memory were not re-measured and keep their confound note |
| PERF-10 Room query latency | **PARTIAL** — measured at 10/100/500/1000 through the production DAO, but by a benchmark-variant-only deterministic harness rather than the official `androidx.benchmark` Microbenchmark API, and KeepLab-only |
| GKP-A11Y-005 dynamic type | **CLOSED** (measured PASS at 1.0/1.3/1.5/2.0, font scale restored) |
| `verification/**` vs `verification/.state/**` contradiction | **CLOSED** (path classes; `E_PATH_CONFLICT = 0`) |
| Hermes Evaluation observability | **CLOSED for attribution and tool-span recovery** (UNKNOWN 74.7 % → 32.0 %, model/provider/tokens real). Per-turn tokens, per-tool timing, turn/api ids remain `NOT_AVAILABLE` in the pinned Hermes |
| PERF-05 Google Keep create/save | **OPEN** — would write content into a third-party app |
| PERF-15 image-heavy note | **OPEN** — IMAGE parity not reached (out of scope) |
| Reliability rows (`NEAR`) | **OPEN** — window-bounded crash evidence, no fault injection, no soak |

```
P0B STATUS AFTER CLOSURE: PARTIAL
REMAINING BLOCKER: matched Google Keep data scale (BLOCKED_GOOGLE_KEEP_SAFE_SEEDING)
NEXT: FIX REMAINING P0B BLOCKER   (not P1)
```

P0B does **not** become READY by having written code. Its hardest blocker — the matched data-scale
axis — is half-closed: KeepLab is measurable at 10/100/500/1000, Google Keep is not, and no parity
value is fabricated for the unmeasurable half.

---

## 12. Child audits (read-only, parallel Hermes delegation)

Three independent **read-only** children were launched in **one** `delegate_task` batch; none wrote
a file. Root Hermes was the single writer for every artifact in this phase.

| Child | Deliverable | Status |
| --- | --- | --- |
| A | `P0B-CLOSE-HERMES-CAPABILITY-AUDIT` — pinned-Hermes capability matrix from local source | completed |
| B | `P0B-CLOSE-ANDROID-BENCHMARK-AUDIT` — KeepLab build/AGP/benchmarkability audit | completed |
| C | `P0B-CLOSE-EVALUATION-AUDIT` — evaluation root cause + minimum adapter design | completed |

Full audit texts are preserved as evidence:
`orchestration/hermes/evidence/p0b-close/P0B-CLOSE-HERMES-CAPABILITY-AUDIT.md`,
`…-ANDROID-BENCHMARK-AUDIT.md`, `…-EVALUATION-AUDIT.md`.
Live Hermes transcripts: `~/.hermes/profiles/android-stack/cache/delegation/live/deleg_a4dcc1d6/task-{0,1,2}.log`.

Child B correctly flagged that, **under the old P0B contract**, adding a benchmark build type and
touching root Gradle files is a `CONTRACT_DEVIATION` — it did not silently redesign, and the new
human-authorised P0B-CLOSE contract is what legitimises that surface. Child C's predicted residual
UNKNOWN (~25–31 spans) matches the measured 24.

---

## 13. AI-stack effectiveness — passive observation

Passive observation of **this real closure**. No synthetic task was created and no extra model call
was made to inspect the Stack.

```
FROZEN_CONTRACT_REOPEN_COUNT: 0
CONTRACT_DEVIATION_COUNT: 0
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
VISUAL_LLM_CALLS: 0
DIRECT_ADB_UI_INPUTS: 0
HERMES_PROJECT_LOCAL_GUARD: INSTALLED_REQUIRES_NEW_SESSION
HERMES_NATIVE_QUALITY_GATE: NOT_AVAILABLE
AUTO_FINALIZER: PENDING_POST_SESSION
GOOGLE_APK_TEMPLATE_EFFECTIVENESS: NOT_EXERCISED_IN_P0B_CLOSE
```

Notes on the counters that were not simply zero:

* **`CONTRACT_DEVIATION_COUNT: 0`** — P0B's one deviation was a *contract-scope imprecision*, and
  P0B-CLOSE fixed the contract rather than the record. No deviation was emitted this phase.
* **`FAIL_FAST_VIOLATION_COUNT: 0`** — two harness failures occurred (a self-check false positive
  and a `set -e`/`pipefail` abort on an *expected* `Permission denied`). Both were infrastructure
  bugs in the harness, not device or product failures: the failure was inspected **once**, a
  minimal fix was applied, and only the affected batch was re-run. The seeder/measurement evidence
  was not re-derived by hand and the P0B canonical metrics were not re-run.
* **`UNSUPPORTED_PERFORMANCE_CLAIM_COUNT: 0`** — three claims that could have been over-read were
  actively constrained: (i) the 0.72× cold-start result is labelled release-*derived*, not
  shipping-release; (ii) PERF-10 is labelled KeepLab-only and not matched; (iii) frame jank was
  left un-re-measured rather than re-run on a variant that would flatter it.
* **Google APK Template** — P0B-CLOSE creates no new Android app project; the canonical design
  selects a benchmark-only module inside an existing brownfield project, so the template was not
  naturally selected and was not invoked. Per the brief this is **not a FAIL**.

---

## 14. Product-safety final statement

| Check | Result |
| --- | --- |
| `KeepLab-Relay/app/src/main/**` modified | **NO** (45/45 byte-identical) |
| Other production source sets / resources / manifest modified | **NO** |
| Product behaviour changed | **NO** — `PRODUCTION_BEHAVIOR_CHANGED: NO` |
| Performance optimisation added (baseline/startup profile, paging, DAO/search) | **NO** |
| Old P0B Frozen Contract modified | **NO** (13/13 byte-identical, still READY) |
| P0B run evidence / canonical report erased | **NO** (97/97 byte-identical) |
| Google Keep existing unrelated data destroyed | **NO** (0 created / 0 modified / 0 deleted) |
| Hermes upgraded / reinstalled / core-patched | **NO** (`vgit.af90026` unchanged) |
| Testapp / PowerAi touched | **NO** |
| Device left as found | **YES** (debug variant reinstalled, benchmark dataset cleared, font scale restored) |
| Git state-changing command issued | **NO** |

---

## Appendix — final P0B-CLOSE status block

```
P0B-CLOSE — BENCHMARKABILITY + HERMES RUNTIME
==============================================

ORCHESTRATOR:                                  HERMES
PROFILE:                                       android-stack
PINNED HERMES CORE MODIFIED:                   NO

NEW P0B-CLOSE CONTRACT:                        READY
OLD P0B CONTRACT MODIFIED:                     NO

CONTRACT RUNTIME
----------------
HERMES PROJECT-LOCAL GUARD:                    INSTALLED_REQUIRES_NEW_SESSION
PRE_TOOL_CALL FAIL-CLOSED:                     PASS
OLD verification/.state CONTRADICTION:         RESOLVED

QUALITY GATES
-------------
HERMES NATIVE QUALITY GATES:                   NOT_AVAILABLE
CONTRACT VALIDATION:                           PASS
PRODUCT SAFETY:                                PASS

ANDROID BENCHMARK
-----------------
RELEASE-LIKE BENCHMARK TARGET:                 PASS
DEBUGGABLE:                                    FALSE
PROFILEABLE:                                   YES
MACROBENCHMARK:                                PASS

KEEP-LAB SEEDER
---------------
BENCHMARK-ONLY:                                YES
10:                                            PASS
100:                                           PASS
500:                                           PASS
1000:                                          PASS
PRODUCTION VARIANT EXPOSES SEEDER:             NO

GOOGLE KEEP MATCHED SCALE
-------------------------
10:                                            BLOCKED
100:                                           BLOCKED
500:                                           BLOCKED
1000:                                          BLOCKED
UNRELATED GOOGLE KEEP DATA CHANGED:            NO
CLEANUP VERIFIED:                              NOT_APPLICABLE

DYNAMIC TYPE
------------
GKP-A11Y-005 DYNAMIC TYPE:                     PASS
FONT SCALE RESTORED:                           YES

PERF-10
-------
ROOM QUERY BENCHMARK:                          PARTIAL
  (measured at 10/100/500/1000 through the production DAO, median+p95, 7 iterations
   each — but by a benchmark-variant-only deterministic timing harness, NOT the
   official androidx Microbenchmark API, and KeepLab-only: Google Keep's database is
   inaccessible, so it is not a matched comparison)

HERMES EVALUATION
-----------------
P0B SESSION:                                   20261005_021134_faf1e3
BEFORE UNKNOWN:                                74.7%
AFTER UNKNOWN:                                 32.0%
MODEL ATTRIBUTION:                             PASS
PROVIDER ATTRIBUTION:                          PASS
TOKEN ATTRIBUTION:                             PASS
CHILD ATTRIBUTION:                             PASS
COMMAND CODE REGRESSION:                       PASS
AUTO-FINALIZER REGRESSION:                     PASS

AI RULE EFFECTIVENESS
---------------------
FROZEN_CONTRACT_REOPEN_COUNT:                  0
CONTRACT_DEVIATION_COUNT:                      0
OUT_OF_SCOPE_WRITE_COUNT:                      0
RULE_VIOLATION_COUNT:                          0
DEVICE_CONCURRENCY_VIOLATION_COUNT:            0
REDUNDANT_FULL_RESCAN_COUNT:                   0
REDUNDANT_VERIFICATION_AFTER_PASS_COUNT:       0
FAIL_FAST_VIOLATION_COUNT:                     0
UNSUPPORTED_PERFORMANCE_CLAIM_COUNT:           0
MODEL_REQUESTS DURING DETERMINISTIC DEVICE STEPS: 0
VISUAL LLM CALLS:                              0
DIRECT ADB UI INPUTS:                          0

GOOGLE APK TEMPLATE
-------------------
GOOGLE_APK_TEMPLATE_EFFECTIVENESS:             NOT_EXERCISED_IN_P0B_CLOSE

P0B STATUS AFTER CLOSURE:                      PARTIAL
REMAINING BLOCKER:                             matched Google Keep data scale
                                               (BLOCKED_GOOGLE_KEEP_SAFE_SEEDING)
NEXT:                                          FIX REMAINING P0B BLOCKER

REPORT: /mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack/reports/P0B-CLOSE-BENCHMARKABILITY.md
==============================================
```
