# P0B-EVALUATION-WRAPPER-ROLE-FIX

Process-wrapper unwrapping (role resolution) + latest-session semantic recheck.

Scope: the last minimal follow-up to **P0B-EVAL-INSPECTION-CONTEXT-FIX**. One defect only — the
operation-role classifier did not unwrap process-control wrappers (`timeout 300`, `nice -n 5`, …), so
a **wrapped execution was resolved to the wrapper token instead of its payload** and a real unittest
failure was downgraded to `INSPECTS_EVIDENCE` and removed. No Google Keep sandbox, no P1, no P0B
rerun, no KeepLab production change, no Hermes core change, no Evaluation Core rewrite.

Evidence root: `orchestration/hermes/evidence/p0b-eval-wrapper-role-fix/`
(pre-fix audit, raw audit JSON, isolated re-evaluations, comparison JSON, transcripts, tools).

---

## 1. Root cause

`failure_evidence.classify_operation_role(command)` resolves the *program* of each simple command in
order to decide what the operation **did**. Before this phase the resolver stripped only a fixed set
of **bare** wrappers:

```python
if tok in ("sudo", "command", "builtin", "nohup", "time", "nice", "exec"):
    tokens.pop(0)          # the wrapper token is dropped …
    continue               # … but its OPTIONS/DURATION are left in front of the payload
```

For a wrapper that carries its own options or a duration, the token that survived was the wrapper's
**argument**, not the payload:

| command | resolved program | role before | role required |
|---|---|---|---|
| `timeout 300 python3 -m unittest … -v \| tail -40` | `timeout` → neutral; only `tail` classified | `INSPECTS_EVIDENCE` | **`EXECUTES_TEST`** |
| `nice -n 5 python3 -m unittest …` | `-n` → unknown | `OTHER` | **`EXECUTES_TEST`** |
| `ionice -c2 -n7 …`, `chrt -f 50 …`, `stdbuf -oL …`, `setsid …` | the wrapper token → neutral/OTHER | wrong | resolved payload |

Because `timeout` is a neutral token, the only positively-classified simple command left in
`timeout 300 python3 -m unittest … -v | tail -40` was `tail` → the whole command aggregated to
`INSPECTS_EVIDENCE`. Then, in `INSPECTION_CONTEXT_NO_VERDICT_OWNER`:

* no operation could own the failure's `TEST` verdict family (`INSPECTS_EVIDENCE` owns none),
* the quoted `FAILED (failures=N)` was read as historical text, and
* the pipeline advisory made the persisted exit status non-authoritative,

so a **real test execution was removed as a quoted-verdict false positive**. The invariant
“execution role wins over inspection role” was silently violated at the wrapper boundary.

This is a *pure resolution* defect: the role priority (`_aggregate_roles`: BUILD → TEST → PROVIDER
beat INSPECT) and the verdict-ownership model were already correct and are unchanged.

## 2. timeout-wrapper evidence (latest completed session)

Full audit: `evidence/p0b-eval-wrapper-role-fix/pre-fix-audit.md` (+ raw structured dump
`pre-fix-latest-session-audit.raw.json`), recorded **before any code change** by re-running the frozen
core and the correction layer on the session shim.

Session `20261005_090430_53ce78`, published `run.json`
sha256 `f5074f246ac1591373214226a2c54e1677857591cac94df8716fd24f401b7099`.
Published correction: `module_version p0b-eval-inspection-context-fix-1`, `before 3 → after 1`,
`removed 2`.

### 2.1 The wrongly-removed `FAIL-003` (real unittest execution)

| event | exact command |
|---|---|
| row 125 | `cd …/Google-Android-Agent-Development-Stack && timeout 300 python3 -m unittest orchestration.hermes.evaluation_adapter.tests.test_failure_evidence -v 2>&1 \| tail -40` |
| row 135 | `cd …/Google-Android-Agent-Development-Stack && timeout 300 python3 -m unittest orchestration.hermes.evaluation_adapter.tests.test_failure_evidence -v 2>&1 \| tail -45` |

| item | value |
|---|---|
| wrapper chain | `timeout 300` → payload `python3 -m unittest …` → pipeline `2>&1 \| tail -40/45` |
| underlying executable | `python3 -m unittest` (stdlib runner, module `…test_failure_evidence`) |
| structured exit (row 125) | `exit_code 0`, **`exit_reliable = False`**, runner hint = *last pipeline stage only* → `UNKNOWN` |
| structured exit (row 135) | `exit_code 0`, `exit_reliable = True` → `SUCCEEDED` |
| result text (row 125) | `Ran 20 tests in 0.042s` … `FAILED (failures=2)` |
| result text (row 135) | `Ran 34 tests in 0.039s` … `FAILED (failures=1)` |
| current role (both) | `INSPECTS_EVIDENCE` — **WRONG** |
| correct role (both) | **`EXECUTES_TEST`** |
| verdict ownership | `TEST_PROBLEM` ∈ family `TEST`; **`EXECUTES_TEST` owns it** → must survive |
| published result | **REMOVED** (`INSPECTION_CONTEXT_NO_VERDICT_OWNER`) — wrong |

Both are genuine failing unittest runs performed *inside this session* (mid-TDD; the suite re-ran
green later at row 139). Their `Failed (failures=N)` is the operation's **own** termination verdict.

### 2.2 The surviving `FAIL-001` (historical-inspection audit — brief §2)

The brief asked whether the surviving `TEST_PROBLEM` whose operation target is
`python3 …/inspect_rows.py … 20261005_075257_cb5233.jsonl …` is a clean historical inspection that
should be removed. **Real structured evidence says no** (`raw_types = ["PROVIDER_TIMEOUT",
"TEST_PROBLEM"]`, `raw_events = [46, 100]`):

| event | command | role | structured state |
|---|---|---|---|
| row 46 | `python3 …/tools/audit_failures.py …/20261005_075257_cb5233.jsonl … \| head -120` | `INSPECTS_EVIDENCE` | exit 0, reliable, SUCCEEDED (quotes the old `FAILED (failures=2)`) |
| row 100 | `python3 …/tools/role_probe.py` | `EXECUTES_PROVIDER` (name token `probe`) | **exit 124, reliable, FAILED** (`[Command timed out after 180s]`) |

row 100 is an operation that **really failed in this session**. So the failure is not backed
exclusively by `INSPECTS_EVIDENCE` operations *and* not every backing operation is a clean success —
the inspection-context rule cannot fire under either condition. **Verdict: `EVIDENCE_SAYS_REAL` →
PRESENT.** It stays. (It is not kept *because* of the quoted historical verdict; it is kept because a
backing operation genuinely failed. The two commands collapsed into one logical failure only because
the frozen core's 80-char `_op_signature` truncation makes their prefixes identical — recorded as a
structural limitation, `core.py` is `PRODUCTION_IMMUTABLE`.)

## 3. Wrapper resolver

`failure_evidence._unwrap_wrappers(tokens) -> (tokens, ok)` replaces the old flat pop loop. It strips
leading `VAR=value` assignments and consumes each recognised **process-control wrapper together with
its own options/duration**, then the payload is classified recursively (the outer loop repeats, so
nested wrappers resolve — `timeout 300 nice -n 5 python3 -m unittest …` → `EXECUTES_TEST`):

| wrapper | consumed grammar |
|---|---|
| `timeout` | options before the duration (`-k DUR`, `--kill-after=DUR`, `-s SIG`, `--signal=SIG`, `--preserve-status`, `--foreground`, `-v`), then `DURATION` (`300`, `300s`, `1.5m`), then the command |
| `sudo` | value options (`-u -g -p -C -U -r -t -T -h -R -D`) and boolean/long flags |
| `env` | `VAR=value`, `-i -0 -v`, value options `-u -C -S`, `--` |
| `nice` | `-n N`, `-N`, `--adjustment[=N]` |
| `ionice` | `-c -n -p --class --classdata --pid` (+ attached forms) |
| `chrt` | scheduling flags (`-f -r -d …`), `-p PID`, then the required numeric priority |
| `stdbuf` | `-i/-o/-e` (attached or spaced mode) |
| `nohup`, `command`, `builtin`, `exec`, `setsid` | boolean/long flags, `--` |
| `time` | `-p`-style flags, `-o FILE` / `--output FILE` |

**Conservative failure mode (brief §5/§6):** a *recognised* wrapper whose payload cannot be resolved
confidently (unknown option, missing/unparseable duration, no command after the duration, `chrt`
without a priority) yields `ok = False`, and the simple command is classified **`OTHER` — never
`INSPECTS_EVIDENCE`**. `OTHER` is treated by verdict ownership as potentially owning every family, so
an unresolvable wrapper can never cause a failure to be dropped.

The resolver never scans the command *text* for test/build words; it resolves the underlying
executable and classifies it with the pre-existing rules. A trailing `tail`/`head`/`cat`/`grep`
remains an inspection stage but can no longer override an execution role (`_aggregate_roles` is
unchanged).

`MODULE_VERSION` is now `p0b-eval-wrapper-role-fix-1`.

## 4. Fixtures

`tests/fixtures/failure_evidence_cases.json` gains two lists (the P0B-EVAL-GUARD-FIX /
-INSPECTION-CONTEXT-FIX lists are unchanged):

* **`wrapper_role_cases` — `CASE-W-A … CASE-W-Y`** (the brief's A–J plus residuals), each asserting
  the deterministic role:
  * A `timeout 300 python3 -m unittest tests -v` → TEST; B `… \| tail -40` → TEST; C
    `timeout -k 5 300 …` → TEST; D `timeout 300 ./gradlew assembleBenchmark` → BUILD; E
    `timeout 300 ./gradlew test` → TEST; F `timeout 30 curl https://example.invalid/provider` →
    PROVIDER; G `timeout 30 python3 inspect_rows.py old.jsonl` → INSPECTS; H
    `nice -n 5 python3 -m unittest …` → TEST; I `env FOO=1 ./gradlew test` → TEST; J
    `unknown-wrapper foo python3 -m unittest …` → **OTHER**;
  * timeout option/duration forms: `--signal=TERM 300`, `300s`, `-k 5s 300s`;
  * nested wrappers and the remaining wrappers (`sudo -u`, `ionice`, `chrt`, `stdbuf`, `setsid`,
    `time`);
  * unparseable wrappers (`timeout abc …`, `timeout --bogus 300 …`, bare `timeout 300`) → OTHER;
  * execution-dominates-pipe: `timeout 300 ./gradlew :app:assembleBenchmark 2>&1 \| tail -40` →
    BUILD, `timeout 300 python3 -m unittest … \| head -40` → TEST.
* **`wrapper_failure_cases` — `CASE-W-FAIL-1 … 3`** (the brief §10 mandatory regression): a real
  unittest/build failure behind `timeout … | tail`, printing `FAILED (failures=2)` / `BUILD FAILED`,
  with a top-level exit of 0 (with and without a pipeline advisory) **must survive**.

Tests added: `TestWrapperUnwrapping`, `TestWrapperFailurePreservation` (41 adapter tests, was 34).
The last one also pins the exact evidenced command from the regression.

## 5. Latest-session semantic re-evaluation

Isolated only — the real Hermes Auto-Finalizer path (adapter → finalizer) with an isolated output
root; the production `run.json`, `.auto_finalize_index.json` and the published historical outputs were
never opened for write. Output: `evidence/…/reeval-latest/`, comparison
`evaluation-reeval-and-regression.json`.

| id | type | operation role (before → after) | structured state | before | after | reason |
|---|---|---|---|---|---|---|
| FAIL-001 | TEST_PROBLEM | INSPECTS_EVIDENCE + EXECUTES_PROVIDER (unchanged) | exit 0 / **exit 124** | KEPT | **KEPT** | not all inspections, one op not a clean success → `EVIDENCE_SAYS_REAL` |
| FAIL-002 | BUILD_ERROR | INSPECTS_EVIDENCE ×2 (unchanged) | exit 0, exit 0 | REMOVED | **REMOVED** | clean historical inspection (`INSPECTION_CONTEXT_NO_VERDICT_OWNER`) |
| FAIL-003 | TEST_PROBLEM | **INSPECTS_EVIDENCE ×2 → EXECUTES_TEST ×2** | exit 0 (+advisory) / exit 0 | **REMOVED** | **PRESERVED** | `EXECUTES_TEST` owns `TEST_PROBLEM` |

`failures_before = 3 → failures_after = 2` (`removed = 1`) vs the published `→ 1` (`removed = 2`).

* **REAL UNITTEST FAILURE: PRESERVED** (was LOST).
* INSPECT_ROWS HISTORICAL FAILURE: **EVIDENCE_SAYS_REAL** (PRESENT) — justified above.
* **SEMANTIC SURVIVOR: CORRECT** — the survivor set changes identity from `{FAIL-001}` to
  `{FAIL-001, FAIL-003}`; the wrongly-dropped execution is restored. `failures_after` is not used as
  the success signal.

## 6. Previous-session regressions

Isolated re-evaluations (`evidence/…/reeval-cb5233/`, `evidence/…/reeval-p0b_close/`):

### 6.1 `20261005_075257_cb5233`

| id | type | roles | before | after |
|---|---|---|---|---|
| FAIL-001 | BUILD_ERROR | INSPECTS_EVIDENCE ×10 | REMOVED | **REMOVED** (show_run historical BUILD) |
| FAIL-002 | TEST_PROBLEM | INSPECTS_EVIDENCE | REMOVED | **REMOVED** (scan_calls historical TEST) |
| FAIL-003 | TEST_PROBLEM | **EXECUTES_TEST ×2** | KEPT | **KEPT** (real unittest) |

`3 → 1`, removed 2 — identical to the P0B-EVAL-INSPECTION-CONTEXT-FIX result. **075257 SHOW_RUN:
REMOVED · SCAN_CALLS: REMOVED · REAL TEST: PRESERVED.**

### 6.2 `20261005_032302_4c6c40` (P0B-CLOSE)

| item | value |
|---|---|
| false `PROVIDER_AUTH` (FAIL-001, from a successful `grep` of core.py) | **GONE** (`OPERATION_SUCCEEDED`) |
| real `TEST_PROBLEM` (FAIL-002, `python3 -m unittest discover … \| tail -60`) | **PRESENT** (`EXECUTES_TEST`) |
| real `BUILD_ERROR` (FAIL-003, `./gradlew :app:assembleBenchmark`) | **PRESENT** (`EXECUTES_BUILD`) |
| REPAIR-001 | **PASS** |
| false `PROVIDER_FALLBACK` deviation | **GONE** |
| `failures_before/after` | 3 → 2, removed 1 (identical to the earlier baselines) |

**REPAIR-001: PASS.**

## 7. Command Code / Auto-Finalizer / Contract Guard

### 7.1 Command Code regression

Real Command-Code session finalized OFF and ON into `evidence/…/cc-regression/{off,on}`:

| item | value |
|---|---|
| failures | core 12 · OFF 12 · ON 12 |
| removed by the switch | **0** |
| repairs | 8 → 8 (identical ids) |
| keys added by the switch | `["failure_evidence_correction"]` |
| differing keys OFF vs ON | **none** |
| outcome | SUCCESS / SUCCESS |

**COMMAND CODE REGRESSION: PASS.** Default (switch OFF) output is byte-identical except for the
additive audit key.

### 7.2 Auto-Finalizer regression (`evidence/…/autofinalizer/`)

| check | result |
|---|---|
| idempotency (second pass) | `SKIP_UNCHANGED` |
| atomic publish | no `*.tmp` left behind |
| task/evaluation separation | `evaluation_outcome=SUCCESS`, `task_outcome=COMPLETED`, `raw_jsonl_modified=false` |
| Hermes source uses the correction | yes — `before 3 → after 2`, `removed 1` (the unittest run is now preserved) |
| CC default (`--source commandcode`) | 12 failures, **no** `failure_evidence_correction` block (backward compatible) |

**AUTO-FINALIZER REGRESSION: PASS.** No duplicate production finalization.

### 7.3 Targeted suites / Contract Guard (`verification.txt`, `testlogs/`)

| suite | result |
|---|---|
| adapter suite (guard + failure evidence) | 63 tests OK |
| `test_contract_guard.py` | 22 tests OK |
| `test_evaluation_core.py` (v0.2.1) | 11 OK |
| `test_evaluation_core_v022.py` | 21 OK |
| `test_evaluation_core_v023.py` | 9 OK |
| `test_finalize_session.py` | 6 OK |
| `test_task_window_v021.py` | 15 OK |
| `test_hermes_source.py` | `HERMES_SOURCE_TEST=PASS` |

Contract Guard **ACTIVE** (`pre_tool_call` → `contract_guard.py`, matcher
`write_file|patch|terminal`, fail-closed) and unmodified; the guard decision log shows this phase's
writes evaluated live (one `BLOCK … UNCLASSIFIED_FAIL_CLOSED` for a stray path, then only ALLOWs).
The guard was not touched, and `HERMES CORE MODIFIED: NO`.

### 7.4 Production tree

| artifact | value |
|---|---|
| published 090430 `run.json` | sha256 `f5074f246ac1591373214226a2c54e1677857591cac94df8716fd24f401b7099` — unchanged (still `module_version p0b-eval-inspection-context-fix-1`, `3 → 1`) |
| published cb5233 `run.json` | sha256 `08f4c6390692868dc8215d182694a6272dede43c95446f570bd1cf63f7fcfca4` — unchanged |
| published 4c6c40 `run.json` | sha256 `f13e86517316b2c6f18af9051ae894e41f9547b005f3964f8e19588fa4064aaf` — unchanged (identical to the P0B-EVAL-GUARD-FIX record) |
| raw staging shim 090430 | sha256 `2fd6b0e0babb60f8425b6149734b5bd62ef656e8b40da5d3fb50dceeb9d4060b` — unchanged |
| `.auto_finalize_index.json` | 32 entries, **0** evidence-dir outputs, every published entry (incl. `hermes:20261005_090430_53ce78` @ `2026-10-05T01:29:04Z`) unchanged; content sha256 `c07f0f84fa32fb82e4989579315abb2870d0225befc5c21c62608776fca03493` stable across the whole phase |
| new directories under `_evaluation` | none |
| KeepLab production / Testapp / PowerAi / Hermes core / pinned install | untouched |

Note (same phenomenon the previous phase recorded): the production index mtime advances roughly every
150 s with a **byte-identical** body (new inode via `os.replace`, sha256 constant, no entry
added/removed/altered). An isolated-root probe (`af.scan_hermes(output_root=<isolated>)`: mtime
before == after) proves this phase's harness does not cause it; it is an out-of-band periodic observer
re-saving the same content. No re-finalization occurs.

## 8. Remaining limitations

1. **Wrapper set is finite.** The listed wrappers are unwrapped; a wrapper outside that set (e.g.
   `strace -f python3 …`, an unknown helper script) resolves to its own token → `OTHER` → preserved
   (a missed removal, never a false removal). `strace` remains in the neutral set.
2. **Core failure grouping is untouched.** `_op_signature` still truncates a `cd …; python3 …` prefix
   to 80 characters, collapsing distinct commands into one logical failure (this is exactly why the
   surviving `FAIL-001` mixes an inspection with a real timeout). `core.py` is `PRODUCTION_IMMUTABLE`.
3. **`role_probe.py` is classified `EXECUTES_PROVIDER`** by its name token `probe` — consistent with
   the P0B work (`probe_provider.py` must stay a provider operation). It does not change any verdict
   here: the command failed (exit 124), so its failure is preserved either way.
4. **Only textual-verdict families** (`BUILD_ERROR`, `TEST_PROBLEM`, `PROVIDER_*`) are covered;
   `GENERIC_ERROR`, `INFRASTRUCTURE_ERROR`, `DEVICE_STATE_GAP`, `REGRESSION` are left as the core
   produced them.
5. Out of scope by the brief and **not** fixed: guard variable expansion, `sed -i` parsing, `->`
   redirect parsing, UNKNOWN phase ratio, per-turn token attribution, per-tool persisted timing,
   Google Keep seeding, Android benchmark.

## 9. Files changed

New / modified (all inside the allowed write surfaces):

* `orchestration/hermes/evaluation_adapter/failure_evidence.py` — the process-wrapper unwrapper
  (`_unwrap_wrappers`, `_skip_flags`, duration/option grammars), the conservative `ok=False → OTHER`
  path in `_role_of_simple`, the new docstring section; `MODULE_VERSION = p0b-eval-wrapper-role-fix-1`.
* `orchestration/hermes/evaluation_adapter/tests/fixtures/failure_evidence_cases.json` —
  `wrapper_role_cases` (CASE-W-A…Y) + `wrapper_failure_cases` (CASE-W-FAIL-1…3).
* `orchestration/hermes/evaluation_adapter/tests/test_failure_evidence.py` —
  `TestWrapperUnwrapping`, `TestWrapperFailurePreservation`.
* `orchestration/hermes/evaluation_adapter/tests/run_p0b_eval_wrapper_role_fix_compare.py` (new) —
  isolated re-evaluations + CC / Auto-Finalizer regressions.
* `orchestration/hermes/evaluation_adapter/tests/run_p0b_eval_wrapper_role_fix_verification.sh` (new)
  — transcript generator.
* `orchestration/hermes/evidence/p0b-eval-wrapper-role-fix/**` (new) — `pre-fix-audit.md`, raw audit
  JSON, comparison JSON, transcripts, isolated re-evaluation outputs, tools.
* `reports/P0B-EVALUATION-WRAPPER-ROLE-FIX.md` (this file).

**Not** changed: `evaluation/commandcode/core.py`, `finalize_session.py`, `auto_finalize.py`,
`contract_guard.py`, any KeepLab/Testapp/PowerAi file, Hermes core or pinned install, any published
historical Evaluation output.

### Verdict

`P0B-EVAL-WRAPPER-ROLE-FIX` — **READY**. A process-control-wrapped execution resolves to its payload's
role, so a real unittest failure behind `timeout … | tail` is preserved; every previously-correct
removal (historical inspections, the P0B-CLOSE false `PROVIDER_AUTH`) still happens; Command Code is
unchanged; the Auto-Finalizer is idempotent; the Contract Guard is ACTIVE and production/historical
evidence is untouched.

Next: `P0B-GK-SANDBOX-PROVISION`.
