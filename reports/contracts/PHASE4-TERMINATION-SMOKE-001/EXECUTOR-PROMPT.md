# EXECUTOR PROMPT — PHASE4-TERMINATION-SMOKE

You are the execution agent for a FROZEN Implementation Contract. Work from the contract
and the listed `read_first` files. Do not re-do reconnaissance, re-choose architecture, or
re-plan decisions this contract has already frozen.

## 0. Verify the frozen contract
- Contract: `implementation-contract.json` (contract_id `PHASE4-TERMINATION-SMOKE-001`, version `0.1.0`)
- Package manifest: `manifest.json` — sha256 of every authored artifact
- Recompute the manifest hashes. If any artifact differs, emit `CONTRACT_CHANGED` and STOP
  (unless this session was explicitly launched with `--accept-contract-update`).
- Confirm `READY.json` reports `status == READY`.

## 1. Read, in this order
1. `implementation-contract.json`
2. `project-context.json` (then ONLY the `read_first` files it lists)
3. `requirements.md`, `acceptance.md`, `design.md`, `DESIGN.md`, `tasks.md`
4. `verification-intent.json`

## 2. Recon budget
- `broad repo scan = forbidden`.
- Read only these 2 `read_first` files:
  1. Google-Android-Agent-Development-Stack/orchestration/hermes/README.md
  2. Google-Android-Agent-Development-Stack/orchestration/hermes/INTEGRATION.md
- Extend to a targeted search ONLY for `CONTRACT_GAP`, `CONTRACT_CONTRADICTION`, a missing
  dependency, or compile evidence that requires one extra file. Record `EXTRA_RECON_REASON`
  (file + why) for every extension.

## 3. Execute tasks in dependency order
  TASK-01  Create exactly one marker file under orchestration/hermes/evidence/phase4-termination-smoke/ recording the smoke identity and a deterministic timestamp, and write nothing else anywhere in the project.  (depends: none)
  TASK-02  Verify the marker exactly once, run the normal verification layer exactly once, and on PASS produce the Phase C report in the final assistant response from evidence already collected, emit a compact final result and stop immediately with no further tool call, search, read, audit or repeated verification.  (depends: TASK-01)

## 4. Boundaries
Allowed paths:
  - Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/phase4-termination-smoke/
Forbidden paths:
  - Google-Android-Agent-Development-Stack/orchestration/hermes/bridge/
  - Google-Android-Agent-Development-Stack/orchestration/hermes/evaluation_adapter/
  - Google-Android-Agent-Development-Stack/orchestration/hermes/HERMES-LOCK.json
  - Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/phase4-hermes-task-v1-kernel/
  - Google-Android-Agent-Development-Stack/specification/
  - Google-Android-Agent-Development-Stack/.hermes.md
  - Google-Android-Agent-Development-Stack/evaluation/
  - Google-Android-Agent-Development-Stack/verification/
  - Google-Android-Agent-Development-Stack/verification-benchmark/
  - Google-Android-Agent-Development-Stack/reports/contracts/
  - KeepLab-Relay/
  - KeepLab-Relay-evidence/
  - Testapp/
  - PowerAi/
Frozen decisions (do not reopen): DEC-001, DEC-002, DEC-003.

## 5. If the contract is wrong
If a contract fact contradicts the source, a required file is missing, an assumption is
wrong, an acceptance is impossible, or a boundary is unsafe:
  STOP → emit `CONTRACT_DEVIATION` with evidence. Do NOT silently redesign.

## 6. Verify and hand off
1. Run the targeted tests named in `tasks.md`.
2. Build the Verification Plan (engine `maestro`,
   journey `PHASE4-TERMINATION-SMOKE-EVIDENCE-ONLY`).
3. Run the deterministic Verification Layer exactly once.
4. On PASS: make NO further tool call, search, read, audit, repeated verification or
   exploratory check. Produce the Phase C report in the FINAL ASSISTANT RESPONSE using only
   evidence already collected in this session, emit the compact final task result, and STOP
   immediately.
5. On FAIL: repair only the failed contract item and re-run only the work that repair
   invalidated. Do not repeat unaffected PASS work.

After this session (POST-SESSION observers, not in-session steps):
- `on_session_finalize` / Auto-Finalizer are POST-SESSION observers.
- Do NOT invoke, inspect, wait for, or verify Auto-Finalizer from inside this Hermes session.
- Auto-Finalizer runs only AFTER this Hermes session exits and is NOT an in-session acceptance
  criterion.

## Stop conditions
  - A required write falls outside the smoke evidence directory: STOP, CONTRACT_DEVIATION.
  - Satisfying the smoke would require touching bridge/, evaluation_adapter/, specification/, HERMES-LOCK.json, .hermes.md, KeepLab, Testapp or PowerAi: STOP, ABSOLUTE_BLOCK_VIOLATION.
  - The smoke is asked to do anything beyond one marker and one verification-layer pass: STOP, SCOPE_WIDENING.
  - A post-PASS tool call, search, read, audit or repeated verification appears necessary: STOP, TERMINATION_SEMANTICS_VIOLATION.
  - Auto-Finalizer would have to be invoked, inspected or awaited in-session: STOP, POST_SESSION_ONLY_VIOLATION.
