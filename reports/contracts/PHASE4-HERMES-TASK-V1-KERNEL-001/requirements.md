# Requirements — Phase-4 Hermes Task V1 control kernel install

## Requirements

### REQ-PHASE4-001 — Authorized write surface is exactly the bridge directory and the Phase-4 evidence directory

- Statement: The generated contract must list `Google-Android-Agent-Development-Stack/orchestration/hermes/bridge/` and `Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/phase4-hermes-task-v1-kernel/` in `allowed_paths`, and must list no other project path as allowed.
- Conditions: When the Contract Guard activates this package for the Phase-4 install session.
- Expected: A write to `orchestration/hermes/bridge/` is allowed; a write to any KeepLab path, any compiler path, any guard path or any unrelated repository is blocked.
- Edge case: An allowed path that is a prefix of, or inside, a forbidden path must not exist, so no forbidden target can be reached through allow-list widening.
- Acceptance: AC-PHASE4-001, AC-PHASE4-002
- Tasks: TASK-01

### REQ-PHASE4-002 — The staged kernel is installed verbatim

- Statement: Every Phase-4 kernel module present in the staging tree is copied into `orchestration/hermes/bridge/` byte-for-byte, with no module content edited, reformatted or redesigned.
- Conditions: When the install session copies the staged kernel.
- Expected: Each installed module's sha256 equals the sha256 of its staged counterpart.
- Edge case: The Phase-3 `chatgpt_adapter.py` already at the installed location is superseded by the staged Phase-4 version; that single tracked overwrite is the only pre-existing file the install changes.
- Acceptance: AC-PHASE4-003
- Tasks: TASK-01, TASK-03

### REQ-PHASE4-003 — The installed kernel passes its own deterministic test suite

- Statement: The bridge test suite that the Phase-4 run already passed must pass again against the installed tree, offline and without a device.
- Conditions: When the install session runs the bridge unit tests from the installed location.
- Expected: The suite exits zero with zero failures and zero errors.
- Edge case: A test that depends on repository state is not part of the unit suite and must not be silently counted as a passing unit test.
- Acceptance: AC-PHASE4-004
- Tasks: TASK-02

### REQ-PHASE4-004 — Staged-versus-installed parity is proven and recorded

- Statement: The install session must produce a deterministic parity record showing that the installed kernel file set equals the staged kernel file set and that every shared module is byte-identical.
- Conditions: After the install copy completes.
- Expected: A parity record exists under the Phase-4 evidence directory, and it reports equality for every kernel module.
- Edge case: A file present in only one of the two trees must appear as an explicit mismatch, not be ignored.
- Acceptance: AC-PHASE4-005
- Tasks: TASK-03
