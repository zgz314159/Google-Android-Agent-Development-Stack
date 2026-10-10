# Tasks — Phase-4 Hermes Task V1 control kernel install

## Tasks

### TASK-01 — Install the staged Phase-4 kernel into orchestration/hermes/bridge/

- Goal: Copy every Phase-4 kernel module from the staging tree orchestration/hermes/evidence/phase4-hermes-task-v1-kernel/bridge/ into orchestration/hermes/bridge/, agreeing with the staged bytes and redesigning nothing.
_Boundary:_ The bridge install write surface only. No module content is authored, edited or reorganised during install.
_Depends:_ none
- Allowed Paths: `Google-Android-Agent-Development-Stack/orchestration/hermes/bridge/`
- Acceptance: AC-PHASE4-001, AC-PHASE4-003
- Verification: compare the staged kernel module file set and the installed kernel module file set and assert per-file sha256 equality
- Done When: protocol.py, bridge_state.py, contract_executor.py, bridge_cli.py, chatgpt_adapter.py and tests/ all exist at orchestration/hermes/bridge/ with the sha256 of their staged counterparts

### TASK-02 — Run the deterministic bridge test suite against the installed kernel

- Goal: Run the bridge unit suite from the installed location and report its pass/fail counts for the installed tree.
_Boundary:_ Test execution and result capture only. No test source and no kernel source is modified.
_Depends:_ TASK-01
- Allowed Paths: `Google-Android-Agent-Development-Stack/orchestration/hermes/bridge/`, `Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/phase4-hermes-task-v1-kernel/`
- Acceptance: AC-PHASE4-004
- Verification: `python3 -m unittest discover -s tests -p "test_*.py"` executed in orchestration/hermes/bridge/ exits 0
- Done When: the installed suite reports zero failures and zero errors

### TASK-03 — Prove and record staged-versus-installed parity

- Goal: Prove that the installed kernel equals the staged kernel and write the parity record into the Phase-4 evidence directory.
_Boundary:_ Comparison and evidence writing only. No kernel source change.
_Depends:_ TASK-01
- Allowed Paths: `Google-Android-Agent-Development-Stack/orchestration/hermes/bridge/`, `Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/phase4-hermes-task-v1-kernel/`
- Acceptance: AC-PHASE4-005
- Verification: recompute sha256 for every staged and installed kernel module, assert equality, and assert the two module file sets are equal
- Done When: a parity record exists under orchestration/hermes/evidence/phase4-hermes-task-v1-kernel/ reporting equality for every kernel module
