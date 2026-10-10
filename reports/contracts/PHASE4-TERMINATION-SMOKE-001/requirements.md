# Requirements — Phase-4 evidence-only termination smoke

## Requirements

### REQ-PHASE4SM-001 — The write surface is exactly one isolated evidence directory

- Statement: The generated contract must list `Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/phase4-termination-smoke/` in `allowed_paths` and must list no other project path as allowed, and its forbidden list must cover the bridge, the evaluation adapter, the pinned Hermes revision, `.hermes.md`, the Specification Compiler, the Android verification layers, `reports/contracts/`, KeepLab, `Testapp` and `PowerAi`, with no allowed path overlapping any forbidden path.
- Conditions: When the bridge's contract gate validates this package for the single live sequence-4 smoke.
- Expected: A write inside the smoke evidence directory is allowed; a write to the bridge, the guard, the compiler, any contract package or any product path is blocked.
- Edge case: No parent directory above the smoke evidence directory is allow-listed, so the authorization cannot widen into the control plane.
- Acceptance: AC-PHASE4SM-001, AC-PHASE4SM-002
- Tasks: TASK-01

### REQ-PHASE4SM-002 — The task is tiny, deterministic and terminates on PASS

- Statement: The task must create exactly one evidence-only marker under the authorized directory, verify that marker once, run the normal verification layer exactly once, and then honour the hardened termination semantics: on PASS, no further tool call, search, read, audit, repeated verification or exploratory check; the Phase C report is produced in the final assistant response from evidence already collected; a compact final result is emitted and the session stops immediately.
- Conditions: When the smoke task executes.
- Expected: One marker exists, one deterministic verification is recorded, one verification-layer pass is recorded, and the session terminates without extra work.
- Edge case: If verification fails, only the failed item is repaired and only the work that repair invalidated is re-run; the marker file is the only artifact.
- Acceptance: AC-PHASE4SM-003, AC-PHASE4SM-004
- Tasks: TASK-01, TASK-02
