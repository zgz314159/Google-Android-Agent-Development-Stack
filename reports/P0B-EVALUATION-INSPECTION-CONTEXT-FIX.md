# P0B-EVALUATION-INSPECTION-CONTEXT-FIX

Historical-evidence inspection vs real operation attribution.

Scope: the minimal follow-up to **P0B-EVAL-GUARD-FIX**. One defect only — a *successful evidence
inspection* whose stdout merely **quotes** an archived failure verdict was still attributed to the
current operation as a logical failure. No Google Keep sandbox, no P1, no P0B rerun, no KeepLab
production change, no Hermes core change, no Evaluation Core rewrite.

Evidence root: `orchestration/hermes/evidence/p0b-eval-inspection-context-fix/`
(current-session audit, comparison JSONs, transcripts, isolated re-evaluations, tools.)

---

## 1. Root cause

The frozen Evaluation Core classifies a logical failure purely from the **text** of a tool result
(`evaluation/commandcode/core.py::_FAIL_PATTERNS` + `test_run_verdict`). Nothing in that rule
requires the operation that produced the text to have *executed* the thing the text talks about.

The P0B-EVAL-GUARD-FIX proof layer removed a failure only when **every** backing operation was a
clean structured success **and** none of their outputs carried the invoked tool's own termination
verdict (`BUILD FAILED` / `FAILED (failures=N)` / `Traceback` / `TIMEOUT`). For the two remaining
false positives that quoted verdict *is exactly* the historical text, so the guard blocked the
removal; and one operation carried the runner's pipeline advisory, which makes its persisted exit
status INDETERMINATE rather than SUCCEEDED.

What was missing was a deterministic notion of:

* what the operation **did** (its role), and
* **who owns** the textual verdict the core matched.

---

## 2. Current-session audit (before any code change)

`orchestration/hermes/evidence/p0b-eval-inspection-context-fix/current-session-audit.md`.

Session `20261005_075257_cb5233` published 3 logical failures. Per-event structured evidence:

| failure | type | operations (native `terminal` → canonical `shell_command`) | structured exit | authoritative | role | owner |
|---|---|---|---|---|---|---|
| FAIL-001 | BUILD_ERROR (+raw PROVIDER_AUTH) | `show_run.py`×2, `cmp_runs.py`×3, `dump_failure_events.py`, `dump_raw.py`, `inspect_removals.py`/`cc_regression2.py` — reading archived run.json / old CC JSONL / old shim | 0 ×7 authoritative; 0 with pipeline advisory ×1 | yes / advisory | INSPECTS_EVIDENCE | none |
| FAIL-002 | TEST_PROBLEM | `scan_calls.py <old shim.jsonl>` printing archived call evidence | 0 | yes | INSPECTS_EVIDENCE | none |
| FAIL-003 | TEST_PROBLEM | **`python3 -m unittest ….test_failure_evidence -v \| tail -70`** (+ a second unittest pipeline) | 0 (last pipeline stage; **no** advisory) | no | **EXECUTES_TEST** | **EXECUTES_TEST** |

FAIL-001/FAIL-002 quote historical `BUILD FAILED` / `FAILED (failures=2)` tokens; FAIL-003 is a real
test execution of the adapter suite and must survive.

Secondary structural observation (recorded, not fixed): the core groups failures by `_op_signature`,
which truncates a `cd …; python3 /home/…` prefix to 80 characters — eight unrelated inspection
commands collapsed into the single logical FAIL-001.

---

## 3. Operation-role algorithm (deterministic, no LLM)

`failure_evidence.classify_operation_role(command) -> {EXECUTES_BUILD, EXECUTES_TEST,
EXECUTES_PROVIDER, INSPECTS_EVIDENCE, OTHER}`

1. **Split** the command into simple commands, quote-aware, after joining `\` line continuations and
   stripping redirection operators (`2>&1`, `>>`, …) so they can never masquerade as a program token
   or a separator.
2. **Resolve the program** of each simple command: strip `sudo`/`env`/`VAR=value`/`nohup`/… wrappers.
3. **Classify the program**, in this order:
   * `bash|sh|zsh|… -c '<payload>'` → **recurse** into the payload (a wrapper is exactly as executing
     as its payload);
   * interpreters (`python3 …`): `-m unittest|pytest` → TEST; `-m <module>` / `-c` → OTHER (inline
     capability unknown); a **named script** is decided by its *name tokens* — test words → TEST,
     build words → BUILD, probe/provider words → PROVIDER, helper verbs
     (`show/scan/dump/cmp/compare/diff/inspect/list/print/summari/parse/extract/report/…`) → INSPECT,
     anything else → **neutral**;
   * `gradlew|gradle` → TEST only for a test task (`test*`, `connectedAndroidTest`), otherwise BUILD;
   * pytest/jest/mocha/… → TEST; maven/make/ninja/bazel/cmake/… → BUILD (with `cargo|go|dotnet test`
     → TEST); `claude|codex|curl|wget|…` → PROVIDER; `npm|npx|yarn` → TEST/BUILD by its script;
   * read/print tools (`cat grep sed head tail awk jq ls find wc diff …`) → INSPECT;
   * shell keywords and pure file bookkeeping (`cd export set echo for do mkdir cp rm …`) → neutral;
   * a directly-invoked, unrecognised executable or bare path → **OTHER** (conservative).
4. **Aggregate**: any execution role wins (BUILD → TEST → PROVIDER); else INSPECTS_EVIDENCE only when
   at least one simple command is positively an inspection **and none is OTHER**; else OTHER.

The role never reads the result text, never calls a model, never looks up a file's contents, and does
not special-case any session id, path or command. `grep provider core.py` is INSPECTS_EVIDENCE; a real
provider probe is not.

## 4. Verdict-ownership model

`verdict_family(type)` maps `BUILD_ERROR → BUILD`, `TEST_PROBLEM → TEST`, `PROVIDER_* → PROVIDER`
(anything else → None, untouched).

`verdict_family_is_owned(family, operations)` is True when some operation can own the verdict:
`EXECUTES_BUILD`/`EXECUTES_TEST` own BUILD (a gradle test task prints a `Build failed` verdict),
`EXECUTES_TEST` owns TEST, `EXECUTES_PROVIDER` owns PROVIDER — and an **OTHER / unknown** role is
treated as potentially owning **every** family, so an operation whose capability cannot be determined
is never used to drop a failure (brief §11).

Rule `INSPECTION_CONTEXT_NO_VERDICT_OWNER` removes a failure **iff all** of:

1. every operation it was drawn from is positively `INSPECTS_EVIDENCE`;
2. every one of those inspections is a **clean success** — `SUCCEEDED`, or exit 0 whose only
   degradation is the runner's pipeline advisory (a read-only inspection executes nothing, so exit 0
   of its own read/print stages is still clean);
3. the failure type belongs to a textual-verdict family;
4. **no** operation can own that family; and
5. one of the outputs actually carries the family's verdict token.

Rule order (stronger, existing disproofs keep their attribution):
`OPERATION_SUCCEEDED` → `PROVIDER_TYPED_FROM_INSPECTION_TEXT` → `INSPECTION_CONTEXT_NO_VERDICT_OWNER`.
The layer can still only ever **remove** a failure; it never invents one.

## 5. Fixtures

`tests/fixtures/failure_evidence_cases.json`

* `cases` — the P0B-EVAL-GUARD-FIX set. `CASE-I` (a successful `cat docs/troubleshooting.md` quoting
  `BUILD FAILED`), previously a documented conservative residual, now **removed** by the new rule.
* `inspection_context_cases` — `CASE-IC-A … CASE-IC-L`, the brief's CASE A–J plus two residuals:
  * A `show_run.py old-run.json` (exit 0, quotes historical `BUILD FAILED`) → INSPECTS → removed;
  * B `scan_calls.py old-session.jsonl` (exit 0, quotes `FAILED (failures=2)`) → INSPECTS → removed;
  * C `cat analysis.md` (exit 0, quotes `Traceback`) → INSPECTS, no current failure;
  * D real `python3 -m unittest` exit 1 → EXECUTES_TEST, TEST_PROBLEM kept;
  * E real unittest behind `| tail -60` + advisory → EXECUTES_TEST, kept;
  * F `./gradlew :app:assembleBenchmark` exit≠0 → EXECUTES_BUILD, BUILD_ERROR kept;
  * G gradle behind a pipe + advisory → EXECUTES_BUILD, kept;
  * H real provider probe with a structured 401 → EXECUTES_PROVIDER, PROVIDER_AUTH kept;
  * I successful `cat … | grep 401` → INSPECTS, provider failure removed;
  * J successful inspection of a report quoting test+build+provider verdicts → removed;
  * K **conservative residual** — an `OTHER` (unknown) role quoting `BUILD FAILED` → preserved;
  * L successful piped inspection (exit 0 + advisory) quoting a historical `BUILD FAILED` → removed.

Tests added: `TestOperationRole`, `TestVerdictOwnership`, `TestInspectionContextCases`; the CASE-I
test was repurposed to assert the new rule.

---

## 6. Before / after

### 6.1 Current session `20261005_075257_cb5233`

Isolated re-evaluation through the **real** Hermes Auto-Finalizer path (adapter → finalizer), output
root `evidence/…/reeval-current/` (production tree opened read-only):

| id | type | operation role | structured state | verdict owner | before | after |
|---|---|---|---|---|---|---|
| FAIL-001 | BUILD_ERROR | INSPECTS_EVIDENCE (×8) | exit 0 / 0 (1 advisory) | none | published | **REMOVED** (`INSPECTION_CONTEXT_NO_VERDICT_OWNER`) |
| FAIL-002 | TEST_PROBLEM | INSPECTS_EVIDENCE | exit 0 | none | published | **REMOVED** (`INSPECTION_CONTEXT_NO_VERDICT_OWNER`) |
| FAIL-003 | TEST_PROBLEM | EXECUTES_TEST | own verdict `FAILED (failures=2)` | EXECUTES_TEST | published | **KEPT** |

`failures_before = 3 → failures_after = 1`, `removed_count = 2`.

Result: SHOW_RUN old BUILD verdict FIXED; SCAN_CALLS old TEST verdict FIXED; real test failure
PRESERVED. (This session contains no real build/provider execution; those are covered by the
regressions below.)

### 6.2 P0B-CLOSE regression `20261005_032302_4c6c40`

Isolated re-evaluation (`evidence/…/reeval-p0b-close/`); the published run and the P0B-EVAL-GUARD-FIX
published re-evaluation were left untouched.

| item | value |
|---|---|
| false `PROVIDER_AUTH` (FAIL-001, from a successful `grep` of core.py) | **GONE** (rule `OPERATION_SUCCEEDED`, unchanged from P0B-EVAL-GUARD-FIX) |
| real `TEST_PROBLEM` (FAIL-002, `python3 -m unittest discover … \| tail -60`) | **PRESENT** (role EXECUTES_TEST) |
| real `BUILD_ERROR` (FAIL-003, `./gradlew :app:assembleBenchmark`) | **PRESENT** (role EXECUTES_BUILD) |
| REPAIR-001 | **PASS** |
| false `PROVIDER_FALLBACK` deviation | **GONE** |
| `failures_before/after` | 3 → 2, removed 1 (identical to the P0B-EVAL-GUARD-FIX baseline) |

### 6.3 Command Code regression

Real Command-Code session `d64d231e-…` finalized OFF and ON into `evidence/…/cc-regression/{off,on}`:

| item | value |
|---|---|
| failures | core 12 · OFF 12 · ON 12 |
| removed by the switch | **0** |
| repairs | 8 → 8 (identical ids) |
| keys added by the switch | `["failure_evidence_correction"]` |
| differing keys OFF vs ON | **none** |
| outcome | SUCCESS / SUCCESS |

Real build failures (11 gradle `BUILD_ERROR`s) and the `GENERIC_ERROR` repair chain all survive; the
default (switch OFF) Command Code output is byte-identical except for the additive audit key.
**COMMAND CODE REGRESSION: PASS.**

### 6.4 Auto-Finalizer regression

| check | result |
|---|---|
| idempotency (second pass) | `SKIP_UNCHANGED` (then `ALREADY_FINALIZED`) |
| atomic publish | no `*.tmp` directory left behind |
| task/evaluation separation | `evaluation_outcome=SUCCESS`, `task_outcome=COMPLETED`, `raw_jsonl_modified=false` |
| Hermes source uses the correction | yes — `failures_before=3 → after=1`, `removed=2` |
| CC default (`--source commandcode`) | 12 failures, **no** `failure_evidence_correction` block (backward compatible) |
| identity | Hermes · commandcode · `deepseek/deepseek-v4.1-flash` (token attribution preserved) |

**AUTO-FINALIZER REGRESSION: PASS.**

### 6.5 Targeted suites

| suite | result |
|---|---|
| adapter suite (`guard + failure evidence`) | 56 tests OK |
| `test_contract_guard.py` (Contract Guard regression) | 22 tests OK |
| `test_evaluation_core.py` (v0.2.1) | 11 OK |
| `test_evaluation_core_v022.py` | 21 OK |
| `test_evaluation_core_v023.py` | 9 OK |
| `test_finalize_session.py` | 6 OK |
| `test_task_window_v021.py` | 15 OK |
| `test_hermes_source.py` | `HERMES_SOURCE_TEST=PASS` |

No device, no benchmark, no P0B rerun.

### 6.6 Production tree

* published `HERMES-20261005_075257_cb5233/run.json` — unchanged; still `module_version
  p0b-eval-guard-fix-1`, `failures_before=3 after=3 removed=0` (re-evaluation was isolated only).
* published `HERMES-20261005_032302_4c6c40/run.json` sha256 `f13e8651…4064aaf` — **identical** to the
  value recorded by P0B-EVAL-GUARD-FIX.
* `.auto_finalize_index.json` — 31 entries, **no** evidence-dir `output_dir`, every published entry
  (incl. the cb5233 `finalized_at 00:45:51Z`) unchanged. Its mtime advanced during the phase, which
  `tools/index_probe.py` shows the phase's own harness does **not** cause (mtime/size constant across
  `af.scan`/`af.scan_hermes` with isolated output roots), i.e. consistent with an idempotent re-save
  by the pinned Hermes runtime when its observer hook was exercised — no entry was added, removed or
  altered and no re-finalization occurred.
* historical P0B / P0B-CLOSE / P0B-EVAL-GUARD-FIX evidence — untouched; KeepLab production, Testapp,
  PowerAi, Hermes core and the pinned install — untouched.

---

## 7. Remaining limitations

1. **Role classification is structural/name-based.** An unrecognised wrapper (`./bin/aegl verify`,
   `python3 -c '…'`) is `OTHER` → preserved, so a real build/test executed by an unrecognised helper
   is never dropped (correct), but an *inspection* run through an unrecognised helper name is also
   preserved (a missed removal, never a false removal). This is the deliberate §11 direction.
2. **Core failure grouping is untouched.** `_op_signature` still truncates a `cd …; python3 …` prefix
   to 80 chars, collapsing distinct commands into one logical failure; the fix works around it
   per-event but cannot repair the grouping (`core.py` is `PRODUCTION_IMMUTABLE`).
3. **Only textual-verdict families** (`BUILD_ERROR`, `TEST_PROBLEM`, `PROVIDER_*`) are covered;
   `GENERIC_ERROR`, `INFRASTRUCTURE_ERROR`, `DEVICE_STATE_GAP`, `REGRESSION` are left exactly as the
   frozen core produced them.
4. A quoted verdict inside a **non-clean** inspection (its own exit ≠ 0) is not removed by the new
   rule; `PROVIDER_TYPED_FROM_INSPECTION_TEXT` still handles provider types typed from inspection text.
5. Out of scope by the brief and **not** fixed: guard variable expansion, `sed -i` parsing, `->`
   redirect parsing, UNKNOWN phase ratio, per-turn token attribution, per-tool persisted timing,
   Google Keep seeding, Android benchmark.

## 8. Files changed

New / modified (all inside the allowed write surfaces):

* `orchestration/hermes/evaluation_adapter/failure_evidence.py` — operation-role classifier,
  verdict-ownership model, `is_clean_success`, the `INSPECTION_CONTEXT_NO_VERDICT_OWNER` rule, the
  per-event role audit; module version `p0b-eval-inspection-context-fix-1`.
* `orchestration/hermes/evaluation_adapter/tests/test_failure_evidence.py` — role/ownership/context
  tests; CASE-I test repurposed.
* `orchestration/hermes/evaluation_adapter/tests/fixtures/failure_evidence_cases.json` —
  `inspection_context_cases` (CASE-IC-A…L), CASE-I flipped to removed.
* `orchestration/hermes/evaluation_adapter/tests/run_p0b_eval_inspection_context_fix_compare.py` (new)
  — isolated re-evaluations + CC / Auto-Finalizer regressions.
* `orchestration/hermes/evaluation_adapter/tests/run_p0b_eval_inspection_context_fix_verification.sh`
  (new) — transcript generator.
* `orchestration/hermes/evidence/p0b-eval-inspection-context-fix/**` (new) — audit, comparison JSONs,
  transcripts, isolated re-evaluation outputs, tools.
* `reports/P0B-EVALUATION-INSPECTION-CONTEXT-FIX.md` (this file).

**Not** changed: `evaluation/commandcode/core.py`, `finalize_session.py`, `auto_finalize.py`
(the additive switch already existed), any KeepLab/Testapp/PowerAi file, Hermes core or pinned install.

---

### Verdict

`P0B-EVAL-INSPECTION-CONTEXT-FIX` — **READY**. The inspection-derived false positives are gone while
every real build/test/provider failure survives; Contract Guard ACTIVE; production and historical
evidence untouched.

Next: `P0B-GK-SANDBOX-PROVISION`.
