# EXECUTOR PROMPT — PHASE4-HERMES-TASK-V1-KERNEL

You are the execution agent for a FROZEN Implementation Contract. Work from the contract
and the listed `read_first` files. Do not re-do reconnaissance, re-choose architecture, or
re-plan decisions this contract has already frozen.

## 0. Verify the frozen contract
- Contract: `implementation-contract.json` (contract_id `PHASE4-HERMES-TASK-V1-KERNEL-001`, version `0.1.0`)
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
- Read only these 8 `read_first` files:
  1. Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/phase4-hermes-task-v1-kernel/STAGING.md
  2. Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/phase4-hermes-task-v1-kernel/bridge/protocol.py
  3. Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/phase4-hermes-task-v1-kernel/bridge/bridge_state.py
  4. Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/phase4-hermes-task-v1-kernel/bridge/contract_executor.py
  5. Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/phase4-hermes-task-v1-kernel/bridge/bridge_cli.py
  6. Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/phase4-hermes-task-v1-kernel/bridge/chatgpt_adapter.py
  7. Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/phase4-hermes-task-v1-kernel/bridge/tests/test_bridge_kernel.py
  8. Google-Android-Agent-Development-Stack/orchestration/hermes/bridge/chatgpt_adapter.py
- Extend to a targeted search ONLY for `CONTRACT_GAP`, `CONTRACT_CONTRADICTION`, a missing
  dependency, or compile evidence that requires one extra file. Record `EXTRA_RECON_REASON`
  (file + why) for every extension.

## 3. Execute tasks in dependency order
  TASK-01  Copy every Phase-4 kernel module from the staging tree orchestration/hermes/evidence/phase4-hermes-task-v1-kernel/bridge/ into orchestration/hermes/bridge/, agreeing with the staged bytes and redesigning nothing.  (depends: none)
  TASK-02  Run the bridge unit suite from the installed location and report its pass/fail counts for the installed tree.  (depends: TASK-01)
  TASK-03  Prove that the installed kernel equals the staged kernel and write the parity record into the Phase-4 evidence directory.  (depends: TASK-01)

## 4. Boundaries
Allowed paths:
  - Google-Android-Agent-Development-Stack/orchestration/hermes/bridge/
  - Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/phase4-hermes-task-v1-kernel/
Forbidden paths:
  - Google-Android-Agent-Development-Stack/specification/
  - Google-Android-Agent-Development-Stack/verification/
  - Google-Android-Agent-Development-Stack/verification-benchmark/
  - Google-Android-Agent-Development-Stack/orchestration/hermes/evaluation_adapter/
  - Google-Android-Agent-Development-Stack/orchestration/hermes/tools/
  - Google-Android-Agent-Development-Stack/orchestration/hermes/HERMES-LOCK.json
  - Google-Android-Agent-Development-Stack/reports/contracts/
  - Google-Android-Agent-Development-Stack/.hermes.md
  - KeepLab-Relay/
  - KeepLab-Relay-evidence/
  - Testapp/
  - PowerAi/
Frozen decisions (do not reopen): DEC-001, DEC-002, DEC-003, DEC-004, DEC-005.

## 5. If the contract is wrong
If a contract fact contradicts the source, a required file is missing, an assumption is
wrong, an acceptance is impossible, or a boundary is unsafe:
  STOP → emit `CONTRACT_DEVIATION` with evidence. Do NOT silently redesign.

## 6. Verify and hand off
1. Run the targeted tests named in `tasks.md`.
2. Build the Verification Plan (engine `maestro`,
   journey `PHASE4-INSTALL-STAGED-KERNEL`).
3. Run the Verification Layer.
4. Let the Auto-Finalizer record Evaluation (Evaluation Core v0.2.2).
5. Produce the Phase C report.

## Stop conditions
  - A required write falls outside allowed_paths or targets a forbidden path: STOP, CONTRACT_DEVIATION.
  - Installing the kernel would require editing, reformatting or redesigning a kernel module: STOP, PHASE4_REDESIGN_FORBIDDEN.
  - The staged tree and the installed tree cannot be made byte-identical by a plain copy: STOP, PARITY_UNREACHABLE.
  - The bridge test suite fails against the installed tree: STOP, INSTALLED_TEST_FAILURE; do not patch the kernel from this contract.
  - Satisfying the install would require modifying specification/, verification/, evaluation_adapter/, HERMES-LOCK.json or the profile config: STOP, ABSOLUTE_BLOCK_VIOLATION.
  - Satisfying the install would require broadening allowed_paths or a broad project write surface: STOP, SCOPE_WIDENING.
