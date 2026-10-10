# FINAL — Specification & Design Compiler Layer P0

Generated: 2026-10-04 · Root: /mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack
Layer version: 0.1.0 · Experiment: KEEPLAB-PIN-NOTES-B1

## 0. Headline

The Specification & Design Compiler Layer P0 is **READY**. It compiles a brownfield Android
change request into a frozen, hash-pinned **Android Implementation Contract**. The first
contract — **KEEPLAB-PIN-NOTES-B1** — is **READY** with all five gates PASS and 0 unresolved
questions.

One premise correction shaped this round: **KeepLab-Relay already implements Pin/Unpin
end-to-end** (the `pinned` column and its DAO/repository/ordering/UI have existed since
Phase A/B and were device-verified in Phase B). The experiment was therefore scoped to the
honest delta — a per-note Pin/Unpin action on the Home list plus stable automation
selectors — reusing the existing mechanism, with no schema change. This is recorded as a
frozen decision (DEC-001/DEC-005) and is the reason the contract has `migration_required =
false`.

---

## 1. P0 architecture

```
change request
   │  (LLM/human) author 8 artifacts
   ▼
spec-package/{PRODUCT,requirements,design,tasks,DESIGN,acceptance}.md
            + {project-context,verification-intent}.json
   │  python3 hash_manifest.py    → manifest.json            (deterministic)
   │  python3 build_contract.py   → implementation-contract.json + EXECUTOR-PROMPT.md
   ▼  python3 validate_package.py → validation-report.json (+ READY.json if all gates PASS)
READY — hash-frozen
   ▼
next session reads EXECUTOR-PROMPT.md  →  implement → verify → evaluate
```

Two metadata blocks (fenced JSON under `## Contract Metadata` in `PRODUCT.md` and
`design.md`) plus `project-context.json` and `verification-intent.json` are the machine
inputs; the remaining artifacts are strict markdown parsed by ID heading. `manifest.json`
covers authored artifacts only, so the generated contract embeds their hashes as
`artifact_hashes`.

## 2. Why it is thin

It is five code files: one shared core (`spec_lib.py`) and three entry points
(`hash_manifest`, `build_contract`, `validate_package`). No orchestration platform, no
plugin system, no external framework. It collects, normalizes, cross-references, validates,
hashes and freezes — nothing else. A missing input is a hard failure, never a guess.

## 3. What is deterministic

`hash_manifest.py`, `build_contract.py` and `validate_package.py` are pure Python 3 stdlib.
No LLM, no network, no inference. Same inputs → byte-identical outputs (proven by
`test_build_contract.test_build_is_deterministic_and_complete`). Failures carry **stable
rule ids** (`E_ARTIFACT_MISSING`, `E_HASH_MISMATCH`, `E_READ_FIRST_MISSING`, …) so a result
names its exact reason.

## 4. What still requires an LLM/human

Authoring the eight plain-language artifacts: what the change is, the requirements, the
design, the task boundaries, the acceptance criteria, the File Structure Plan, and the
selector contract. That is the deliberate division: expensive decisions happen once, in
the compiler layer.

## 5. Required artifacts

`PRODUCT.md`, `requirements.md`, `design.md`, `tasks.md`, `DESIGN.md`, `acceptance.md`,
`project-context.json`, `verification-intent.json` (authored) plus generated
`implementation-contract.json`, `manifest.json`, `READY.json`, `EXECUTOR-PROMPT.md`.

## 6. Optional visual artifacts

Declared explicitly, never left absent: `design_source`, `stitch_used`, `reference_apk`.
For brownfield KeepLab: `existing_app` / `false` / `not_required`. Screens lists may be
empty but must be present.

## 7. Brownfield behavior

- `mode = brownfield`; the contract **reuses** existing mechanisms and forbids rebuilding.
- Every MUST TOUCH path was verified to exist against the real tree.
- `data_change` states current == target schema version and `migration_required = false`.
- Frozen governance (`MISSION.md`, `FACTORY_RULES.md`, `harness/`, `.factory/`) is in
  `forbidden_paths`.

## 8. Greenfield extension point

No compiler code path is brownfield-specific. Greenfield differs only in authored values:
`experiment_type = SPEC_FIRST_GREENFIELD`, `mode = greenfield`,
`schema_version_current = 0`, `design_source = stitch|ai_studio_reference`.

## 9. Contract schema

`contracts/android-implementation-contract.schema.json` (draft-07, closed objects) covers
all §22 fields: `contract_version/id`, `experiment_id/type`, `matched_control_available`,
`project`, `mode`, `feature`, `artifact_refs/hashes`, `scope/non_goals`,
`decisions/assumptions`, `read_first`, `allowed/forbidden_paths`, `requirements`,
`acceptance_ids`, `data_change`, `ui_change`, `selector_contract`, `tasks`,
`verification_intent`, `stop_conditions`, `unresolved_questions`, `readiness`. The
readiness and manifest schemas are in the same directory.

## 10. READY gate

`READY` iff all five gates PASS: `schema`, `traceability`, `boundaries`, `acceptance`,
`hashes`. `READY.json` is written only then (and removed otherwise). Because an unresolved
question forces the traceability gate to FAIL, READY implies `unresolved_questions == []`.

## 11. Freeze / hashing

`manifest.json` records `path`, `sha256`, `size`, `role`, `required`, `source` for every
authored artifact. `validation-report.json` records `contract_sha256` and
`manifest_sha256`. The next session recomputes them and stops with `CONTRACT_CHANGED` on
any difference (unless `--accept-contract-update`; defined, not implemented in P0).

## 12. Executor recon policy

`project-context.json.read_first` lists ≤12 files. `EXECUTOR-PROMPT.md` states
`broad repo scan = forbidden`; any extension must carry an `EXTRA_RECON_REASON`. The B1
package lists exactly 12 read_first files.

## 13. Verification integration

`verification-intent.json` is the spec→verification bridge (journey, engine, required
selectors, persistence/rotation/search checks). It is not a runnable plan and carries no
APK hash. `verification/**` was not modified this round. Interface note recorded as
`VERIFICATION_INTEGRATION_GAP = NONE`: the intent maps directly onto the existing
`verification-plan.schema.json` fields.

## 14. Evaluation integration

`evaluation/**` was not modified. This session was finalized through the Auto-Finalizer
(`finalize_session.py`, Evaluation Core v0.2.2), not `analyze_session.py`, into
`_evaluation/Google-Android-Agent-Development-Stack/SPEC-COMPILER-P0-001/`.
`specification/**` is not yet matched by the phase rule table, so its authoring wall
classifies as UNKNOWN (23.8% of agent-owned wall) — recorded as
**`EVALUATION_TAXONOMY_GAP`**, not fixed.

## 15. KeepLab B1 package

`/mnt/AndroidDev/Projects/KeepLab-Relay/specs/phase-c-pin-notes-b1/` — 13 requirements,
14 acceptance criteria, 5 dependency-ordered tasks, 12 read_first files, 5 frozen
decisions, 3 selectors. See `COMPILATION-REPORT.md` in that package for the full
traceability matrix.

## 16. Known limitations

- Strict markdown parsing: content outside the documented shape is invisible by design.
- `--accept-contract-update` defined but not implemented.
- No cross-package index; each package validates in isolation.
- `specification/**` has no Evaluation Core phase rule → UNKNOWN wall (recorded gap).
- The visual layer (Stitch / AI Studio) is an interface, not an implementation.

## 17. P0 success status

**READY.** Self-tests: 14/14 pass (`python3 -m unittest discover -s specification/tests`),
covering a valid→READY package and seven negative cases, each asserting its exact rule id
(`E_ARTIFACT_MISSING`, `E_DUP_AC_ID`, `E_MISSING_DEPENDENCY`, `E_PATH_CONFLICT`,
`E_READ_FIRST_MISSING`, `E_UNRESOLVED_QUESTIONS`, `E_HASH_MISMATCH`) plus build fail-fast
and tamper detection.

## 18. Experiment B readiness

**READY.** The contract is frozen; the next independent session can read
`EXECUTOR-PROMPT.md`, verify the hashes, read 12 files, and execute TASK-01..05.

---

## SPEC_COMPILER_COST (this round)

Recorded by Evaluation Core v0.2.2 + Auto-Finalizer (snapshot at report time; the
finalizer re-finalizes on session completion).

```
task_elapsed_wall      = 1361.165 s
interactive_user_wait  = 45.227 s
agent_owned_wall       = 1315.938 s
requests               = 39
input tokens           = 5,051,764
output tokens          = 105,482
cache_read             = 4,847,872

T2 Context Acquisition = 541.642 s  (41.16%)
T3 Planning/Spec       = 351.668 s  (26.72%)
T6 Tests               =  20.883 s  ( 1.59%)
T9 Final/Handoff       =  72.122 s  ( 5.48%)
UNKNOWN                = 312.759 s  (23.77%)
```

`unknown_ratio = 0.2377` → `EVALUATION_TAXONOMY_GAP` (specification/ authoring wall).
This is a compiler-layer snapshot only; it is deliberately **not** compared to any executor
cost. `matched_control_available = false` for Experiment B1, so no causal claim is made.

---

## Git

- `Google-Android-Agent-Development-Stack`: **not a git repository** (no `.git`).
- `KeepLab-Relay`: unborn `master`, zero commits, all files untracked. No `git add/commit/push`
  was performed.

---

```
SPECIFICATION & DESIGN COMPILER P0
==================================

LAYER VERSION:
0.1.0

ARCHITECTURE:
PASS

THIN-LAYER PRINCIPLE:
PASS

DETERMINISTIC VALIDATOR:
PASS

CONTRACT SCHEMA:
PASS

PACKAGE MANIFEST:
PASS

HASH FREEZE:
PASS

READY GATE:
PASS

TRACEABILITY:
PASS

BROWNFIELD MODE:
PASS

STITCH ADAPTER SLOT:
READY

STITCH EXECUTED:
NO

AI STUDIO ADAPTER SLOT:
READY

AI STUDIO EXECUTED:
NO

KEEP LAB PRODUCT CODE MODIFIED:
NO

VERIFICATION LAYER MODIFIED:
NO

EVALUATION CORE MODIFIED:
NO

TESTAPP MODIFIED:
NO

POWERAI MODIFIED:
NO

GIT COMMIT CREATED:
NO

P0 TESTS:
PASS

SPEC COMPILER STATUS:
READY


KEEP LAB EXPERIMENT B1
======================

EXPERIMENT:
KEEPLAB-PIN-NOTES-B1

PRODUCT:
Pin / Unpin Notes

PRODUCT.md:
READY

requirements.md:
READY

design.md:
READY

tasks.md:
READY

DESIGN.md:
READY

acceptance.md:
READY

project-context.json:
READY

verification-intent.json:
READY

implementation-contract.json:
READY

manifest.json:
READY

READY.json:
READY

EXECUTOR-PROMPT.md:
READY

UNRESOLVED QUESTIONS:
0

READ_FIRST FILES:
12

TASKS:
5

REQUIREMENTS:
13

ACCEPTANCE CRITERIA:
14

CONTRACT SHA256:
1ddcb5874b9131b055c969855bc5d8b79cfb7590a136e536fa069c45a0df3b0d

PACKAGE MANIFEST SHA256:
ee6c32af6466783325cb86b0bbb2274265fc748d40481bcde2c9b4e11b4acb0a

MATCHED A CONTROL:
NO

EXPERIMENT B STATUS:
READY

NEXT SESSION REQUIRED:
YES

IMPLEMENTATION STARTED:
NO

REPORT:
/mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack/reports/FINAL-SPECIFICATION-COMPILER-P0.md

CONTRACT PACKAGE:
/mnt/AndroidDev/Projects/KeepLab-Relay/specs/phase-c-pin-notes-b1

NEXT SESSION PROMPT:
/mnt/AndroidDev/Projects/KeepLab-Relay/specs/phase-c-pin-notes-b1/EXECUTOR-PROMPT.md
```
