# P0B-EVAL-GUARD-FIX — Evaluation False-Positive Correction + Hermes Contract Guard Live Activation

**Phase:** P0B-EVAL-GUARD-FIX (targeted infrastructure fix) · **Executed:** 2026-10-05
**Hermes session under proof:** `20261005_032302_4c6c40` (NEW process; the P0B-CLOSE session itself)
**Evaluation run re-examined:** `HERMES-20261005_032302_4c6c40`
**Scope:** (A) correct evidenced failure-classification false positives; (B) prove the P0B-CLOSE
`pre_tool_call` Contract Guard is live in a new session. Nothing else — no P0B re-run, no P1, no
product code, no Hermes upgrade, no Hermes core patch, no Evaluation rewrite.

**Status: READY.** One operator expectation did not survive contact with the evidence and is
reported honestly instead of forced (§9): the event the brief calls `FAIL-002` is **not** a false
positive — it is a real test failure. See §9.

---

## 1. Contract Guard — live activation (part B, done first)

This is a new Hermes process, so the hook configured during P0B-CLOSE had to be re-registered at
startup. `hermes hooks test` was **not** used as the activation proof.

| Step | Command | Result |
|---|---|---|
| Registration | `hermes hooks list` | `[pre_tool_call] …/contract_guard.py matcher='write_file\|patch\|terminal'` present |
| Health | `hermes hooks doctor` | all hooks healthy; guard runs clean (exit 0, 0.04 s) |
| Live session write probe | `write_file` → `…/.guard-live-probe/SHOULD_NOT_EXIST.txt` | **BLOCKED before any filesystem mutation** |
| Post-state | `test -e .guard-live-probe/SHOULD_NOT_EXIST.txt` | **does not exist** (the probe directory was never created) |
| Audit trail | `contract-guard-decisions.jsonl` line 53 | `{"tool": "write_file", "decision": "BLOCK", "class": "UNCLASSIFIED_FAIL_CLOSED", "target": "…/.guard-live-probe/SHOULD_NOT_EXIST.txt"}` |

The blocked tool call returned to the agent as:

```
[P0B-CLOSE CONTRACT GUARD] BLOCK write_file (UNCLASSIFIED_FAIL_CLOSED)
target=Google-Android-Agent-Development-Stack/.guard-live-probe/SHOULD_NOT_EXIST.txt
— project path not listed in the frozen contract; failing closed
```

**Verdict: `HERMES_PROJECT_LOCAL_GUARD: ACTIVE`** — proven inside the live session, on a
disposable unclassified Stack path, not on a protected production path.

### 1.1 Additional live evidence observed (fail-closed over-blocks)

While doing this work, three further live blocks occurred. All are *over*-blocks, i.e. the safe
direction, and all are recorded as observations only (fixing them is out of scope):

1. `terminal` with an unexpanded shell variable (`mkdir -p "$EVID"`) → `AMBIGUOUS_WRITE_TARGET`
   (the guard cannot resolve `$EVID`, so it refuses).
2. `terminal` running `sed -i 's/envelope_text(case)/case_result_text(case)/g' <file>` → the sed
   script itself was read as a write target → `UNCLASSIFIED_FAIL_CLOSED`.
3. `terminal` with `echo "=== timeline diff BEFORE -> AFTER ==="` → the `>` in `->` was read as a
   redirect → `UNCLASSIFIED_FAIL_CLOSED`.

### 1.2 Append-only audit integrity

The guard's decision log is shared P0B-CLOSE evidence, so its integrity was checked rather than
assumed: the first **51** lines (the entire pre-probe file) still hash to
`3027a9953306ab9035d13a05cdc2b7c0b22912dff7f99ca19bf05514ea03cd1d`, and every later entry is an
append. No pre-existing line was rewritten. The file grew 51 → 152 lines as a side effect of the
guard's own normal operation (10 of them BLOCK).

---

## 2. Root cause of the false positives (old logic)

`evaluation/commandcode/core.py` classifies a logical failure by **searching a tool result's
text** (`core._FAIL_PATTERNS`, `classify_failure`). The operation behind that text only had to be
a *command tool* — nothing required it to have actually failed:

- most patterns (`BUILD_ERROR`, `TEST_PROBLEM`, `PROVIDER_*`) are matched **unconditionally**;
  only `DEVICE_STATE_GAP` / `INFRASTRUCTURE_ERROR` consult a `failed` flag;
- for a Hermes transcript, `exit_code` was never populated at all: `core._parse_result_signals`
  only understands the Command Code text header (`Exit code: N`, `EXIT=N`, `(shell, failed)`),
  while a Hermes `terminal` result is a JSON envelope (`{"output":…, "exit_code":N, "error":…}`);
- the `PROVIDER_FALLBACK` execution deviation is *derived* from any `PROVIDER_*` failure, so one
  text match manufactured two findings.

### 2.1 The evidenced `FAIL-001` false positive

| | |
|---|---|
| classified as | `PROVIDER_AUTH`, phase `T0`, owner row 1, raw event row 71 |
| actual operation | `cd …Stack && echo "=== core.py provider/agent_host refs ==="; grep -n "provider\|agent_host" evaluation/commandcode/core.py \| head -40; …` |
| actual structured state | `exit_code: 0`, `error: null`, no pipeline advisory → **SUCCEEDED** |
| why it matched | the output is `core.py` **source code**; line 673 literally contains `("PROVIDER_AUTH", re.compile(r"(?i)\b401\b[^\n]{0,40}(unauthor\|api\|provider)\|authentication failed\|invalid api key…"))` |
| verification | the row's full text contains **no** tool-termination verdict (`BUILD FAILED`, `FAILED (failures=`, `Traceback`, `TIMEOUT`); only `401` ×2, `authentication failed` ×1, `invalid api key` ×1 — all from that one source line |

So a *successful read-only inspection* produced a provider-auth failure and a provider-fallback
deviation. That is exactly the "search text for a failure word → declare failure" architecture the
brief forbids.

### 2.2 Where the correction could be implemented

The frozen P0B-CLOSE contract marks these `PRODUCTION_IMMUTABLE` / unclassified, so they are
physically unwritable through the (live, fail-closed) guard:

```
BLOCK  PRODUCTION_IMMUTABLE      evaluation/commandcode/core.py
BLOCK  PRODUCTION_IMMUTABLE      evaluation/commandcode/phase_rules.json
BLOCK  UNCLASSIFIED_FAIL_CLOSED  evaluation/tests/**
ALLOW  …/orchestration/hermes/evaluation_adapter/**      ALLOW …/reports/**   ALLOW …/evidence/**
ALLOW  evaluation/commandcode/finalize_session.py        ALLOW evaluation/commandcode/auto_finalize.py
```

This is not a workaround: the same contract's **DEC-010** states "The Evaluation Core … is
unchanged. Only the Hermes source adapter and one additive optional finalizer parameter change."
The correction is therefore implemented exactly there — proof layer in the adapter directory, one
additive optional switch in the finalizer. **No contract decision was reopened**; no
`CONTRACT_DEVIATION` is raised.

---

## 3. New logic — prove failure, then classify failure

```
PROVE FAILURE (structured execution state: exit status · tool status · provider error)
        ↓
CLASSIFY FAILURE (textual evidence may only classify a failure that has been proven/left plausible)
```

New file `orchestration/hermes/evaluation_adapter/failure_evidence.py`:

* `parse_operation_state(result_text, tool)` → `{exit_code, error, exit_reliable, status, source}`,
  from the runner's JSON envelope (`exit_code`, `error`, and Hermes's own pipeline advisory `hint`)
  or the Command Code text header. Nothing is inferred from prose: an absent exit status stays
  `None` (**never** "0").
* `outcome` → `FAILED` (structured error, non-zero exit, or failed tool status) ·
  `SUCCEEDED` (exit 0 **and** no error **and** the runner did not flag the status as
  non-authoritative) · `UNKNOWN` (everything else, including a pipeline-lost status).
* `correct_run(run, calls_by_row)` → removes failures its own operations cannot support, drops
  their repairs, drops the `PROVIDER_FALLBACK` deviation when no provider failure remains, and
  recomputes `repair_linkage`. `FAIL-xxx` ids of surviving failures are **unchanged**.

### 3.1 The two rules

| Rule id | Fires when | Why it is safe |
|---|---|---|
| `OPERATION_SUCCEEDED` | **every** operation the failure was drawn from is a *clean* structured success **and** none of their output carries the invoked tool's own termination verdict (`BUILD FAILED`, `FAILURE: Build failed`, `Execution failed for task`, `FAILED (failures=\|errors=`, `N tests failed`, `TESTS FAILED`, `Traceback (most recent call last)`, `[TIMEOUT]`, `EXIT=124`) | A real build/test failure always returns a non-zero status, is flagged pipeline-lost, or prints its tool's own verdict — so it can never be "clean" |
| `PROVIDER_TYPED_FROM_INSPECTION_TEXT` | a `PROVIDER_*` type was asserted from read-only inspection commands (`grep`/`cat`/`sed`/`head`/`sort`/…) whose command carries **no** provider-operation token | No provider operation was executed. A genuine provider probe (`claude`, `curl https://…`, `PROBE_`, `provider_probe`, …) is disqualified from this rule even when piped through `tail`, so a real provider failure can never be dropped by it |

Properties, by construction:

* the layer **can only remove** failures and can never add one, so it cannot introduce a new
  false positive;
* a **compound shell's** exit 0 is never enough on its own: `./gradlew … ; echo DONE` exits 0 while
  Gradle fails (see §6), and that real failure is kept. This distinction was found *because* the
  first rule draft wrongly removed 7 real Command Code build errors; the verdict check was added
  and the case turned into fixture `CASE-E3`;
* phases, clocks, token attribution, the task window and identity are untouched (proved in §10).

---

## 4. Fixtures

`orchestration/hermes/evaluation_adapter/tests/fixtures/failure_evidence_cases.json` — each case
is one tool result plus (a) the type the **frozen core** classifies it as, (b) the structured
outcome, (c) what the correction must do. The test serialises the case verbatim, so nothing is
hand-transformed.

| Fixture | Shape | Core type | Structured | Correction |
|---|---|---|---|---|
| `CASE-A` | successful `grep` printing `core.py` source with `PROVIDER_AUTH`/`401`/`authentication failed` | `PROVIDER_AUTH` | SUCCEEDED | **removed** |
| `CASE-B` | successful unittest, `… ok` lines, `Ran N tests` / `OK` | *(none)* | SUCCEEDED | kept (nothing to remove) |
| `CASE-C` | real test failure, exit 1, `FAILED (failures=1)` | `TEST_PROBLEM` | FAILED | **kept** |
| `CASE-C2` | real test failure, pipeline-lost exit 0 + advisory, `FAILED (failures=2)` — the live `FAIL-002` shape | `TEST_PROBLEM` | UNKNOWN | **kept** |
| `CASE-D` | real provider failure: `claude -p …`, exit 1, `error: "PROVIDER_AUTH: 401 unauthenticated"` | `PROVIDER_AUTH` | FAILED | **kept** |
| `CASE-E` | real build error, exit 1, `BUILD FAILED` | `BUILD_ERROR` | FAILED | **kept** |
| `CASE-E2` | real build error, pipeline-lost exit 0 + advisory, `BUILD FAILED in 28s` — the live `FAIL-003` shape | `BUILD_ERROR` | UNKNOWN | **kept** |
| `CASE-E3` | real build error inside `… \| tail -40; echo "DONE"` → shell exit 0, gradle `BUILD FAILED in 59s` | `BUILD_ERROR` | SUCCEEDED | **kept** (verdict check) |
| `CASE-I` | successful `cat` of a doc that literally quotes `BUILD FAILED` | `BUILD_ERROR` | SUCCEEDED | kept (documented conservative residual) |
| `CASE-G` | `grep -rn "401" docs/` (exit 2) whose output is documentation text | `PROVIDER_AUTH` | FAILED | **removed** (inspection rule) |
| `CASE-F` | session-level: `BUILD_ERROR` → fix edit → same-target successful rerun | `BUILD_ERROR` | FAILED | **kept**, repair `PASS` |

## 5. Tests

`orchestration/hermes/evaluation_adapter/tests/test_failure_evidence.py` — 20 deterministic,
offline cases: envelope/text/exit-status parsing, "an absent status is never 0", the frozen-core
tool-set drift guard (`OPERATION_TOOLS == core._COMMAND_TOOLS`), all fixtures above, the
end-to-end finalizer path with the switch on/off, the case-F repair chain, and the §7 audit pin.

Targeted battery (all offline, deterministic, no device, no benchmark):

| Suite | Result |
|---|---|
| `evaluation/tests/test_evaluation_core.py` | 11 tests — OK |
| `evaluation/tests/test_evaluation_core_v022.py` | 21 tests — OK |
| `evaluation/tests/test_evaluation_core_v023.py` | 9 tests — OK |
| `evaluation/tests/test_finalize_session.py` (Auto-Finalizer regression) | 6 tests — OK |
| `evaluation/tests/test_task_window_v021.py` (task-window) | 15 tests — OK |
| `evaluation/tests/test_hermes_source.py` (Hermes source adapter) | `HERMES_SOURCE_TEST=PASS` |
| `orchestration/…/evaluation_adapter/tests` (contract guard + failure evidence) | 42 tests — OK |

104 unittest cases + 1 script, all green; logs in
`orchestration/hermes/evidence/p0b-eval-guard-fix/testlogs/`.

## 6. P0B-CLOSE isolated re-evaluation (before/after)

Isolated and non-mutating: the production run is opened **read-only** as the reference, both
re-evaluations write under `orchestration/hermes/evidence/p0b-eval-guard-fix/`, and the production
Auto-Finalizer index is neither opened nor duplicated.

```bash
python3 evaluation/commandcode/auto_finalize.py hermes-session \
  --session-id 20261005_032302_4c6c40 --hermes-db ~/.hermes/profiles/android-stack/state.db \
  --output-root <evidence>/reeval-before --hermes-staging-root <evidence>/reeval-before/_hermes_staging \
  --project Google-Android-Agent-Development-Stack
# (AFTER = same command against <evidence>/reeval-after, with the fix in place)
python3 orchestration/hermes/evaluation_adapter/tests/run_p0b_eval_guard_fix_compare.py
```

| | BEFORE (fix off) | AFTER (fix on) |
|---|---|---|
| logical failures | 3 | 2 |
| `FAIL-001` PROVIDER_AUTH | **present** (false positive) | **GONE** |
| `FAIL-002` TEST_PROBLEM | present | present |
| `FAIL-003` BUILD_ERROR | present | present |
| repairs | `REPAIR-001` → `FAIL-003`, `PASS` | `REPAIR-001` → `FAIL-003`, `PASS` |
| `PROVIDER_FALLBACK` deviation | present | **GONE** |
| UNKNOWN | 31.28 % / 41 spans | 31.28 % / 41 spans (**identical**) |
| `agent_host` / `model` / `provider` | Hermes / `deepseek/deepseek-v4.1-flash` / `commandcode` | unchanged |
| tokens (req / in / out / cache-read) | 177 / 728461 / 203459 / 45404416 | unchanged |

The published production `run.json` is byte-identical to the isolated BEFORE, so the baseline is
genuine and the only delta is the corrected classification. The published originals were not
touched (`reports`/evidence only; production tree hashes recorded in `verification.txt`).

### 6.1 The removal audit is published

`run.json` and `finalization.json` carry a `failure_evidence_correction` block. For `FAIL-001`:

```json
{"logical_failure_id": "FAIL-001", "type": "PROVIDER_AUTH", "raw_events": [71],
 "rule_id": "OPERATION_SUCCEEDED",
 "event_states": [{"tool": "shell_command", "exit_code": 0, "error": null,
                   "exit_reliable": true, "status": null,
                   "source": "runner-json-envelope", "outcome": "SUCCEEDED"}],
 "core_evidence_head": "{\"output\": \"=== core.py provider/agent_host refs ===\\n673:    (\\\"PROVIDER_AUTH\\\"…"}
```

## 7. Real failure preservation

* **`FAIL-003` BUILD_ERROR is intact** and still linked to its repair: `REPAIR-001`, same
  `fix_row` 184 → `rerun_row` 267 → `result: PASS`, `repair_linkage.status` unchanged. The id did
  **not** shift, because the corrector never renumbers surviving failures.
* **`FAIL-002` TEST_PROBLEM is intact** (see §9).
* No new failure appeared anywhere: AFTER ⊂ BEFORE.
* Command Code safety sweep: across **28 live Command Code sessions / 52 published logical
  failures**, the rules remove **exactly 1** — a `PROVIDER_MODEL` asserted from `git status` /
  `git rev-list` output that merely quoted an upstream release note about a "provider setup
  error" (a §4 documentation-text false positive). Every one of the 12 real build failures in the
  largest session survived.

## 8. Pipeline exit status — §7 audit

Commands containing `|`, `tee`, `tail`, `grep` **do** lose their authoritative status today, and
the audit isolates exactly why, with evidence:

| | |
|---|---|
| Observed | row 122: `python3 -m unittest discover … -v 2>&1 \| tail -60` → Hermes envelope `exit_code: 0` **plus** `hint: "exit_code 0 here is the status of the last pipeline command (tail/head/cat/…) … Treat this run as FAILED until proven otherwise"` |
| Root cause | `core._parse_result_signals` cannot read the envelope, so `Call.exit_code` stays `None` and the core's own successful-rerun predicate (`_turn_has_success_op`) can never fire for a Hermes rerun |
| Consequence | a *real* repair (rows 124/126 `edit_file` → row 128 `Ran 22 tests … OK`) is reported `UNPROVABLE_NO_SUCCESSFUL_RERUN` even though it happened |
| Fix applied | the classification path now consumes the runner's structured state directly (envelope `exit_code` / `error` / advisory `hint`), and a pipeline-lost status is treated as `UNKNOWN`, **never** as a success — `CASE-C2`/`CASE-E2` pin this |
| Not done | translating the envelope exit status into the shim so the *core's* rerun matcher would see it. That was implemented and **reverted**: it also let the core invent a "repair" for the `FAIL-001` false positive, which then leaked `T8` spans for a repair that does not exist. Per §7 ("prefer fixing failure classification; do not rewrite the shell execution layer") the correction stays in the classification layer, and this residual is listed in §11 |

`test_core_does_not_read_the_runner_json_envelope_exit_status` pins this audit finding: it fails
loudly if the frozen core is ever changed (or unfrozen) to read the envelope.

## 9. `FAIL-002` is **not** a false positive — honest deviation from the brief

The brief expects `FAIL-002 TEST_PROBLEM` to be a false positive produced by "successful unittest
output". The evidence says otherwise, and per the brief's own instruction *"Do not force result if
evidence differs"* it is reported as found.

Row 122 (`python3 -m unittest discover -s orchestration/hermes/evaluation_adapter/tests -v 2>&1 |
tail -60`) ends with:

```
test_ambiguous_write_intent_fails_closed (test_contract_guard.BlockTests.…) ... FAIL
test_frozen_phase_surfaces_are_blocked     (test_contract_guard.BlockTests.…) ... FAIL
Ran 22 tests in 0.026s
FAILED (failures=2)
```

* 2 of 22 tests really failed (guard assertion mismatches: `UNCLASSIFIED_FAIL_CLOSED` vs
  `AMBIGUOUS_WRITE_TARGET`, `FORBIDDEN` vs `PRODUCTION_IMMUTABLE`);
* the agent then applied two real fixes (row 124 `contract_guard.py`, row 126
  `test_contract_guard.py`) and the same suite re-ran green at row 128 (`Ran 22 tests … OK`).

That is a genuine FAIL → fix → PASS cycle, so the type is correct. Two defects *did* exist and are
now fixed/reported:

1. the recorded **evidence string** was misleading — the core stores the first 160 characters of a
   single-line JSON blob, which happened to be `… ok` lines, which is presumably how the false
   positive classification arose;
2. the repair linkage was unprovable, for the §8 reason. It stays unprovable because fixing it
   requires either the reverted shim translation or editing `core.py` (both out of scope here).

Expectation line `FALSE TEST_PROBLEM: PRESENT`, not `GONE`.

## 10. Non-regression

| Check | Method | Result |
|---|---|---|
| Hermes tool aliases / UNKNOWN improvement | re-evaluated the earlier P0B session `20261005_021134_faf1e3` into an isolated root | UNKNOWN **31.97 % / 24 spans** = the published 32.0 %; staged shim byte-identical (`34a7a64f…`) |
| model / provider / token attribution | both re-evaluations | `Hermes` / `commandcode` / `deepseek/deepseek-v4.1-flash`; 177 / 728461 / 203459 / 45404416 / 0 preserved |
| Command Code regression | re-finalize a real CC session with the switch **off** vs `core.analyze` alone | **no** differing surface (`logical_failures`, `repairs`, `deviations`, `repair_linkage`, phases, clocks, tokens, tools); no correction key emitted |
| Auto-Finalizer regression | `test_finalize_session.py` (idempotency, atomic publish, task/evaluation isolation) + `test_hermes_source.py` | OK / PASS |
| switch is additive | CC session re-finalized on/off | only `logical_failures`/`repairs`/`repair_linkage` change, plus the audit key; switch off ⇒ byte-identical run.json |
| production tree untouched | sha256 of the published `run.json` and the production index | unchanged (recorded in `verification.txt`) |
| phases untouched by the fix | `phase-timeline.csv` BEFORE vs AFTER | **zero** differing spans (177/177) |

The Command Code source keeps the switch **off** by default (`auto_finalize.scan` unchanged), so
historical Command Code evaluations stay comparable; the rule itself is source-agnostic and one
flag enables it.

## 11. Known limitations

1. `FAIL-002`'s repair remains `UNPROVABLE_NO_SUCCESSFUL_RERUN`, because the frozen core cannot see
   the Hermes envelope's exit status (§8). Fixing it needs the reverted shim translation or a
   `core.py` change — both outside this task's scope.
2. `core.py`, `phase_rules.json` and `evaluation/tests/**` are `PRODUCTION_IMMUTABLE` /
   unclassified in the frozen P0B-CLOSE contract and are blocked by the live guard, so the
   correction lives in the adapter + one additive finalizer parameter. A future Evaluation Core
   revision should fold the prove-then-classify rule into `classify_failure` itself.
3. Conservative residual (pinned by `CASE-I`): text that *literally quotes* a tool verdict inside
   a successful operation is kept, not removed. The direction is safe (never drops a real failure).
4. `PROVIDER_TYPED_FROM_INSPECTION_TEXT` cannot fire when the inspection command itself mentions
   provider vocabulary (e.g. `grep -n "provider" core.py`). That is deliberate: it guarantees a
   real provider probe is never dropped. For the live `FAIL-001` case `OPERATION_SUCCEEDED`
   applies anyway.
5. A `PROVIDER_*` failure with **no** structured state at all (no exit code, no error field) is
   now removed: §4 requires structured provider evidence. This is a false-**negative** risk for
   sources that persist no status; it does not affect Hermes (its envelope always carries
   `exit_code`/`error`) and the switch is off for Command Code.
6. The guard appends to `orchestration/hermes/evidence/p0b-close/contract-guard-decisions.jsonl`
   by design; that shared audit file therefore grew during this phase (verified append-only, §1.2).
   The guard's write-intent extractor also over-blocks some benign shell text (§1.1).
7. `pytest` is not installed in the pinned toolchain; all suites are `unittest`/script based, and
   nothing was installed.

## 12. Files changed

Created:

| Path | sha256 |
|---|---|
| `orchestration/hermes/evaluation_adapter/failure_evidence.py` | `d1c040bd…` |
| `orchestration/hermes/evaluation_adapter/tests/test_failure_evidence.py` | `dce70b36…` |
| `orchestration/hermes/evaluation_adapter/tests/fixtures/failure_evidence_cases.json` | `9d15160e…` |
| `orchestration/hermes/evaluation_adapter/tests/run_p0b_eval_guard_fix_verification.sh` | `8086bfcc…` |
| `orchestration/hermes/evaluation_adapter/tests/run_p0b_eval_guard_fix_compare.py` | `1e647a11…` |
| `orchestration/hermes/evidence/p0b-eval-guard-fix/**` (verification.txt, testlogs/, reeval-before/, reeval-after/, p0b-reeval-check/, cc-regression/, evaluation-reeval-comparison.json, comparison-console.txt) | evidence |
| `reports/P0B-EVALUATION-FALSE-POSITIVE-FIX.md` | this report |

Modified (both additive and optional):

| Path | Change | sha256 |
|---|---|---|
| `evaluation/commandcode/finalize_session.py` | new optional `failure_evidence=False` parameter, applied between `core.analyze` and `core.write_outputs`; `--failure-evidence` CLI flag | `abe448ac…` |
| `evaluation/commandcode/auto_finalize.py` | `scan_hermes` passes `failure_evidence=True`; the Command Code path unchanged | `f08c29e2…` |
| `orchestration/hermes/evaluation_adapter/README.md` | documents the proof layer | `64008140…` |

Explicitly **not** modified (verified): `evaluation/commandcode/core.py`, `phase_rules.json`,
`analyze_session.py`, `evaluation/taxonomy/**`, `evaluation/tests/**`,
`orchestration/hermes/evaluation_adapter/hermes_session_source.py`,
`orchestration/hermes/evaluation_adapter/contract_guard.py`, `orchestration/hermes/HERMES-LOCK.json`,
the pinned Hermes installation, the frozen P0B and P0B-CLOSE contracts, KeepLab production
(`app/src/main/**` and all other source sets), Testapp, PowerAi, and all P0B / P0B-CLOSE historical
evidence (`core.py` was never targeted by a write tool — 0 mentions in the guard's decision log).

## 13. Reproduction

```bash
cd /mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack

# part B — live guard evidence (hooks + probe post-state + production hashes)
bash orchestration/hermes/evaluation_adapter/tests/run_p0b_eval_guard_fix_verification.sh

# part A — tests
python3 -m unittest discover -s orchestration/hermes/evaluation_adapter/tests -v
python3 evaluation/tests/test_evaluation_core_v023.py
python3 evaluation/tests/test_finalize_session.py
python3 evaluation/tests/test_hermes_source.py

# part A — isolated before/after comparison artifact
python3 orchestration/hermes/evaluation_adapter/tests/run_p0b_eval_guard_fix_compare.py
```

Stopped here. No Google Keep sandbox, no P1.

