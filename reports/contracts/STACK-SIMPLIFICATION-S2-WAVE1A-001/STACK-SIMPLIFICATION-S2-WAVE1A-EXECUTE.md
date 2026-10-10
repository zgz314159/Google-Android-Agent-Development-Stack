# STACK-SIMPLIFICATION-S2-WAVE1A-EXECUTE

Executor prompt for contract `STACK-SIMPLIFICATION-S2-WAVE1A-001`.
Package: `Google-Android-Agent-Development-Stack/reports/contracts/STACK-SIMPLIFICATION-S2-WAVE1A-001/`
Normative inputs: `implementation-contract.json` (scope, boundaries, hashes, stop conditions),
`acceptance.md` (exact acceptance evidence), this file (the run order).

You are executing **WAVE1A only**. It is a low-risk measurement/classification-cleanup wave plus
shadow observability preparation. It changes no product behaviour, no Contract safety decision, no
Guard behaviour, no Hermes core, no live profile hook behaviour and no Android verification behaviour.

---

## 0. FAST POLICY

```
PLAN ONCE -> EXECUTE -> VERIFY ONCE -> PASS = STOP -> FAIL = FIX FAILED PART ONLY
```

Forbidden: review of the review; verification of the verification; post-PASS audit; an unexplained
full-repository scan; re-checking M4; reopening A0/A1/A2/M2/M3/M4; creating a second wave-1A contract.

---

## 1. ACTIVATE (before any write)

1. Verify `manifest.json`: every entry's sha256 must equal the file on disk.
2. Re-hash the 8 `frozen_inputs.files`; on any drift STOP with `STALE_WAVE1A_INPUT`.
3. Export `HERMES_CONTRACT_PACKAGE=<this package directory>`.
   The currently live guard package is `KEEPLAB-P0B-CLOSE-001`; it BLOCKS
   `evaluation/commandcode/phase_rules.json` and `.hermes.md`, and leaves `orchestration/hermes/tools/`
   unclassified (therefore blocked). Point the guard at THIS package instead.
   This is an environment change. **`config.yaml` must not be edited.**
4. Confirm the guard now reports `MANIFEST_OK` for this package and ALLOW for a probe write inside
   `allowed_paths`.
5. Targeted discovery only: read the files in `read_first`. Do not rescan the repository.

## 2. FIX THE CLASSIFICATION RULES (TASK-01, TASK-02)

A. **T7c / WAIT_DEVICE false positive.** Reproduce first: applying the current
   `t7c_evidence_cmd` alternative `(layout|ui|window_dump)…\.(json|xml)` to the frozen M4 transcript
   must yield exactly 3 matches (hrows h000061, h000351, h000353). Then tighten the rule so the
   substring `ui` inside `build` can never match, and so device classification requires a bounded
   device/evidence token or a real device command signal. Exact negative and positive command sets:
   `acceptance.md` 2.1 / 2.2. Do not add another broad regex; do not lose device coverage.

B. **The seven UNKNOWN Hermes-artifact spans.** Classify all of them in the existing phase vocabulary
   using data/rules/adapters only, per `classification_fix.requirement_B_intended_mappings`:
   scratch/cache tooling -> T2; `tool_call` / `process_manage` -> a DEDICATED rule (never a forced
   `HERMES_TOOL_ALIAS` entry); `orchestration/hermes/evidence/**` writes -> T9. If one span genuinely
   cannot be classified without `core.py`, record it as `UNCLASSIFIED_JUSTIFIED` with its reason.

Rules: `evaluation/commandcode/core.py` stays byte-identical. Preserve every existing successful
mapping and every existing alias. Add the regression tests under `evaluation/commandcode/tests/`
(deterministic, offline, direct rule-table application, no `core.py` import, no device).

## 3. ADD THE SHADOW OBSERVER (TASK-03)

Create `orchestration/hermes/evaluation_adapter/hooks/hermes-transient-observer.py`.
Real payload field names come from the pinned source (`agent/shell_hooks.py`), never from assumption.
Capture metadata only; emit append-only JSONL; fail safe on malformed input; print nothing; exit 0;
never touch the product tree or a Guard decision.

**Do NOT enable it.** `config.yaml` stays byte-identical; the hook is `SHADOW_ONLY` and its live
enablement belongs to WAVE1B. Exercise it with synthetic local fixtures or direct invocation.

## 4. PROOF TOOLING (TASK-04) AND THE .hermes.md RULE (TASK-05)

Create at most ONE reusable deterministic hash/scope utility under `orchestration/hermes/tools/`,
importing the hashing/path helpers from `specification/compiler` (read-only) rather than
reimplementing SHA. It must not scan secrets, must not replace the Guard, and must not spawn a new
per-phase script. Then add exactly ONE compact rule to `.hermes.md`:

> Do not create per-phase ad-hoc scratch proof/hash/report scripts when `execute_code` or an existing
> checked-in deterministic utility can do the same job.

Nothing else in `.hermes.md` changes. Do not enable Skills.

## 5. RUN THE TARGETED TESTS

Phase-rule regression tests, the observer hook test, and the adapter round-trip. Offline, deterministic.
No device. One pass.

## 6. REPLAY THE M4 FIXTURE ONCE (TASK-06)

Read-only on `/mnt/AndroidDev/Projects/_evaluation/_hermes_staging/20261006_171926_af865e.jsonl` and on the
existing results directory. Write the WAVE1A replay result into a SEPARATE directory under
`orchestration/hermes/evidence/stack-simplification-s2-wave1a/`. Never overwrite `run.json`,
`analysis.md`, `phase-timeline.csv`, `finalization.json` or any historical evidence.

Prove, from the replay output:

| Target | Before | After |
|---|---|---|
| WAIT_DEVICE attributable to the 3 false-positive spans | 105.567 s | 0.000 s |
| UNKNOWN share of `agent_owned_wall` | 11.6 % | < 2 % or all 7 spans justified |

Unchanged, proven equal: logical failures (FAIL-001 / FAIL-003 / FAIL-004), repair linkage
(REPAIR-002 / REPAIR-003), task completion detection, token totals (requests 113, input 673851,
output 148391, cache read 25064448, cache write 0).

Do not fake the result. If a span cannot be classified without `core.py`, record it — never modify
`core.py` to force a PASS.

## 7. VERIFY SCOPE ONCE

Pre/post sha256 for every frozen input and external read-only input. Classify every changed file as
inside `allowed_paths` or a deviation. Prove `core.py`, `contract_guard.py`, `config.yaml`, the pinned
Hermes source, every historical evidence directory and every completed contract package are
byte-identical. Write the small evidence set under
`orchestration/hermes/evidence/stack-simplification-s2-wave1a/`.

Then STOP.

---

## FAILURE HANDLING

Read the failure once. Fix only the failed part. Re-run only the failed step or task.
A gate that already PASSED is never re-run to "confirm" it. A fix that would need `core.py`, the
Guard, `config.yaml`, the pinned Hermes source, `specification/**` or `verification/**` is a STOP, not
a workaround. Two genuine fixes without success: emit `REPEATED_FAILURE` and do one root-cause analysis.

## STOP CONDITIONS

See `implementation-contract.json` → `stop_conditions`. Emit the named code and stop:
`CONTRACT_DEVIATION` · `STALE_WAVE1A_INPUT` · `CORE_CHANGE_REQUIRED` · `OVER_BUDGET_FIX` ·
`OVER_CORRECTION` · `SHADOW_NOT_TESTABLE` · `ABSOLUTE_BLOCK_VIOLATION` · `DEFERRED_TO_MATURE_TOOLING` ·
`REPEATED_FAILURE` · `PROCESS_OVERHEAD_TOO_HIGH`.

## OUT OF SCOPE — do not start

M5 / A8 multi-device · A9 multi-account · WAVE1B (live observer enablement, live telemetry A/B) ·
WAVE2 (Specification Compiler restoration) · Contract Guard replacement · Evaluation Core rewrite ·
Hermes upgrade · OPA / Conftest · Serena · Langfuse · Spec Kit · any KeepLab product change ·
any custom secret scanner · any git initialization.

## DONE

`PASS = STOP`.
