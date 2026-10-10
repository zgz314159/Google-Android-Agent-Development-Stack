# STACK-SIMPLIFICATION-S2-WAVE2 — Phase C Report

**Contract:** `STACK-SIMPLIFICATION-S2-WAVE2-001` (v0.1.0, `experiment_id` `STACK-SIMPLIFICATION-S2-WAVE2`)
**Package:** `/tmp/STACK-SIMPLIFICATION-S2-WAVE2-001` (compiler-generated, READY)
**Pinned Hermes:** `af90026aa09949579bd423d24def3d38f743cde0`
**Result:** **PASS** — the deterministic Specification Compiler is the canonical Contract path,
proved READY and Guard-compatible from authored inputs alone.

---

## 1. Contract verification

All eight authored artifacts were re-hashed against `manifest.json` — 8/8 match on sha256 and
size; `hash_manifest.py --verify` prints `MANIFEST=OK`; `READY.json` reports `status = READY`.
**No `CONTRACT_CHANGED`.** No frozen decision (DEC-001…DEC-006) was reopened.

## 2. What was executed

| Task | Action | Outcome |
| --- | --- | --- |
| TASK-01 | Ran the real compiler (`hash_manifest.py` → `build_contract.py` → `validate_package.py`) over the eight authored artifacts | exit 0, `STATUS=READY`, five gates PASS |
| TASK-02 | Compiled the unchanged inputs a second time into a same-named directory; `cmp` every generated file | BYTE_IDENTICAL (also identical to the frozen bootstrap package) |
| TASK-03 | Fired the real pinned dispatcher (`hermes hooks test pre_tool_call`) four times with `HERMES_CONTRACT_PACKAGE` scoped to the child | ALLOW / PRODUCTION_IMMUTABLE / UNCLASSIFIED_FAIL_CLOSED / CONTRACT_SELF_PROTECTION — all as intended |
| TASK-04 | Published the generated-artifact ownership invariant in `.hermes.md` | items 18–20 added; 11 added lines, 0 removed |
| TASK-05 | Measured compile-only wall time separately from validation and guard probes | 0.119 s over 2 commands; 22270.6× vs M4, 45445.4× vs WAVE1A |
| TASK-06 | Hashed the frozen layer before/after and checked the out-of-scope scope | 16 files byte-identical; no device command; KeepLab/Testapp/PowerAi untouched |

## 3. Acceptance

| AC | Verdict | Evidence |
| --- | --- | --- |
| AC-W2-001 | PASS | five generated files, each with size/sha256/producer; none hand-edited |
| AC-W2-002 | PASS | validator exit 0, `STATUS=READY`, gates schema/traceability/boundaries/acceptance/hashes PASS |
| AC-W2-003 | PASS | `cmp` clean for all five generated files, both runs |
| AC-W2-004 | PASS | allowed write exits 0 (manifest integrity accepted, no block payload) |
| AC-W2-005 | PASS | three block payloads with their guard classes |
| AC-W2-006 | PASS | invariant present; diff is add-only |
| AC-W2-007 | PASS | compile-only 0.119 s ≤ 30 s; both ratios recorded |
| AC-W2-008 | PASS | frozen layer byte-identical before/after |
| AC-W2-009 | PASS | no out-of-scope write; no adb/maestro; M5 NOT_STARTED |

## 4. Evidence

All under `orchestration/hermes/evidence/stack-simplification-s2-wave2/`:

- `wave2-acceptance.json` — compact record (authored/generated tables, per-AC verdicts)
- `benchmark.json` (TASK-05), `task03-guard-shadow.json` (TASK-03), `scope.json` (TASK-06)
- `frozen-pre-hashes.txt` / `frozen-post-hashes.txt` (TASK-06)
- `task04-hermes-md-diff.txt` (TASK-04, add-only diff)
- `probe-0{1..4}-*.json` + `out-probe-0{1..4}.txt` (TASK-03 transcripts)
- `targeted-tests-compiler.txt`, `targeted-tests-guard*.txt`
- `verification-plan.json` + `replay/verification/PC1-S2-WAVE2/` (Verification Layer, offline)

## 5. Generated vs authored ownership

- **Authored (model-owned):** `PRODUCT.md`, `requirements.md`, `design.md`, `tasks.md`,
  `DESIGN.md`, `acceptance.md`, `project-context.json`, `verification-intent.json` — 8 files, 36 841 bytes.
- **Generated (compiler-owned):** `implementation-contract.json`, `manifest.json`,
  `EXECUTOR-PROMPT.md`, `validation-report.json`, `READY.json` — 5 files, 28 116 bytes. No model
  ever wrote or patched these.

## 6. Verification & Handoff

- **Verification Plan:** `verification-plan.json` (engine `uiautomator`, journey `PC1-S2-WAVE2`,
  `require_verify_part=false`) — `PLAN_VALID=true`.
- **Verification Layer:** `run_verification.sh <plan> --dry-run` (offline, no device) →
  `DRY_RUN=OK`; `verification-result.json` outcome `PASS`, `app_apk_sha256 = 7ce0bc57…` (the
  byte-pinned compiled contract). No adb, no Maestro, no screenshot.
- **Evaluation:** recorded by the Auto-Finalizer (Evaluation Core, see `replay/`).

## 7. Deviations / Notes

- **None declared.** No `CONTRACT_DEVIATION`, no stop condition was hit.
- The Verification Layer is a device layer; because this wave has no UI or device surface
  (frozen decision DEC-006), it was exercised in its **offline `--dry-run`** mode with the
  compiled contract as the byte-pinned artifact under verification. The wave's PASS/FAIL oracle
  is the deterministic host check set named in the contract's `verification_intent`.
- `evaluation/commandcode/auto_finalize.py` reports **Evaluation Core v0.2.3**; the executor
  prompt's boilerplate text referenced v0.2.2. The authoritative version is the one the core
  itself records in `finalization.json`.
- **Non-blocking observation:** the guard treats a terminal write target containing an
  unexpanded shell variable as unresolvable and fails closed (`AMBIGUOUS_WRITE_TARGET`); literal
  paths must be used in write-bearing commands. Observed live in this session.

## 8. Scope

**Changed by this wave:** `Google-Android-Agent-Development-Stack/.hermes.md` (invariant only)
plus the evidence directory and this report. **Unchanged:** the compiler, schemas, templates, the
Contract Guard, the pinned Hermes identity, the Evaluation Core, the verification layer, KeepLab
product code, Testapp, PowerAi, and the device.
