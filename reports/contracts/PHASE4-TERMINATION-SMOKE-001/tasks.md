# Tasks — Phase-4 evidence-only termination smoke

## Tasks

### TASK-01 — Write exactly one evidence-only marker

- Goal: Create exactly one marker file under orchestration/hermes/evidence/phase4-termination-smoke/ recording the smoke identity and a deterministic timestamp, and write nothing else anywhere in the project.
_Boundary:_ The smoke evidence directory only. No control-plane path, no contract package, no product code is read for write purposes or touched.
_Depends:_ none
- Allowed Paths: `Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/phase4-termination-smoke/`
- Acceptance: AC-PHASE4SM-001, AC-PHASE4SM-002, AC-PHASE4SM-003
- Verification: assert the single marker file exists under the authorized directory and assert no write occurred outside it
- Done When: exactly one marker file exists under orchestration/hermes/evidence/phase4-termination-smoke/ and nothing else was created or modified

### TASK-02 — Verify once, report in the final response, stop

- Goal: Verify the marker exactly once, run the normal verification layer exactly once, and on PASS produce the Phase C report in the final assistant response from evidence already collected, emit a compact final result and stop immediately with no further tool call, search, read, audit or repeated verification.
_Boundary:_ Verification and reporting only. No additional artifact is created and no Auto-Finalizer is invoked, inspected or awaited.
_Depends:_ TASK-01
- Allowed Paths: `Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/phase4-termination-smoke/`
- Acceptance: AC-PHASE4SM-004
- Verification: assert the marker content matches the expected deterministic shape and that the session terminates after the single verification-layer pass
- Done When: the smoke reports PASS once, with the Phase C report in the final assistant response and no post-PASS tool call
