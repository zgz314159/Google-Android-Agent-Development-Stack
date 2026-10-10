# Acceptance Criteria — Phase-4 Hermes Task V1 control kernel install

## Acceptance Criteria

### AC-PHASE4-001 — Bridge write surface is authorized

- Given: the active contract package is PHASE4-HERMES-TASK-V1-KERNEL-001
- When: the generated implementation contract is read
- Then: `allowed_paths` contains `Google-Android-Agent-Development-Stack/orchestration/hermes/bridge/`
- Verification: read `allowed_paths` from implementation-contract.json and assert the entry is present verbatim
- PC1 Step: PC1-01

### AC-PHASE4-002 — Out-of-scope surfaces stay forbidden

- Given: the generated implementation contract is read
- When: `allowed_paths` and `forbidden_paths` are compared
- Then: `KeepLab-Relay/`, `KeepLab-Relay-evidence/`, `Testapp/`, `PowerAi/`, `specification/`, `verification/`, `orchestration/hermes/evaluation_adapter/` and `reports/contracts/` appear in `forbidden_paths` and in no allowed path, and no allowed path overlaps any forbidden path
- Verification: assert each forbidden entry is present and assert the compiler reports zero E_PATH_CONFLICT and zero E_PROJECT_ESCAPE errors
- PC1 Step: PC1-02

### AC-PHASE4-003 — Staged kernel installed verbatim

- Given: the staged kernel tree at orchestration/hermes/evidence/phase4-hermes-task-v1-kernel/bridge/
- When: the install session finishes copying it into orchestration/hermes/bridge/
- Then: protocol.py, bridge_state.py, contract_executor.py, bridge_cli.py, chatgpt_adapter.py and tests/test_bridge_kernel.py each exist at the installed location with a sha256 equal to their staged counterpart
- Verification: per-file sha256 equality between the staged tree and the installed tree
- PC1 Step: PC1-03

### AC-PHASE4-004 — Installed bridge suite passes

- Given: the kernel installed at orchestration/hermes/bridge/
- When: `python3 -m unittest discover -s tests -p "test_*.py"` is run from that directory
- Then: the process exits 0 with zero failures and zero errors
- Verification: the unittest summary line reports `FAILED (failures=0, errors=0)`, or an `OK` result
- PC1 Step: PC1-04

### AC-PHASE4-005 — Staged-versus-installed parity recorded

- Given: the installed kernel and the staged kernel
- When: the parity check runs after the install
- Then: a parity record exists under orchestration/hermes/evidence/phase4-hermes-task-v1-kernel/ that reports equality for every kernel module and reports no module present in only one tree
- Verification: read the parity record and assert every module row is `MATCH` and the two module file sets are equal
- PC1 Step: PC1-05
