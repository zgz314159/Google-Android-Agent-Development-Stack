# Acceptance Criteria — Phase-4 evidence-only termination smoke

## Acceptance Criteria

### AC-PHASE4SM-001 — The only authorized write surface is the smoke evidence directory

- Given: the generated implementation contract is read
- When: `allowed_paths` is inspected
- Then: it contains exactly `Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/phase4-termination-smoke/` and no other entry
- Verification: read `allowed_paths` from implementation-contract.json and assert it equals the single smoke evidence directory
- PC1 Step: PC1-S01

### AC-PHASE4SM-002 — Control-plane and product surfaces stay forbidden

- Given: the generated implementation contract is read
- When: `allowed_paths` and `forbidden_paths` are compared
- Then: `orchestration/hermes/bridge/`, `orchestration/hermes/evaluation_adapter/`, `orchestration/hermes/HERMES-LOCK.json`, `.hermes.md`, `specification/`, `verification/`, `verification-benchmark/`, `reports/contracts/`, `KeepLab-Relay/`, `KeepLab-Relay-evidence/`, `Testapp/` and `PowerAi/` appear in `forbidden_paths` and in no allowed path, and no allowed path overlaps any forbidden path
- Verification: assert each forbidden entry is present and assert the compiler reports zero E_PATH_CONFLICT and zero E_PROJECT_ESCAPE errors
- PC1 Step: PC1-S02

### AC-PHASE4SM-003 — Exactly one deterministic evidence marker exists

- Given: the smoke task has executed
- When: the authorized evidence directory is inspected
- Then: exactly one marker file exists there, recording the smoke identity, and no other project path was created or modified
- Verification: assert the marker file exists and is the only new artifact, and assert its content matches the expected deterministic shape
- PC1 Step: PC1-S03

### AC-PHASE4SM-004 — PASS terminates in the final response with no extra work

- Given: the deterministic verification reports PASS
- When: the hardened termination semantics apply
- Then: no further tool call, search, read, audit, repeated verification or exploratory check is made, the Phase C report is produced in the final assistant response from evidence already collected, a compact final result is emitted, and the session stops immediately without invoking, inspecting or awaiting Auto-Finalizer
- Verification: assert the verification-layer pass count is exactly one and that the session ends immediately after the final report
- PC1 Step: PC1-S04
