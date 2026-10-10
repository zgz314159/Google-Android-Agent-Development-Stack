# Tasks — KeepLab M5 = A8 Multi-Device Hardening

## Tasks

### TASK-01 — Freeze D-05/D-11 and implement the server session/device/account lifecycle

- Goal: Record D-05 = ACCOUNT_DELETE_GRACE_30_DAYS and D-11 = NO_PUSH_PROVIDER_IN_A8_CORRECTNESS_PATH at their approved values, and implement the server-side session/installation identity, the per-session revoke surface and the account lifecycle state machine (ACTIVE / DISABLED / DELETION_PENDING / PURGED) with deletion_requested_at, purge_after = deletion_requested_at + 30 days, immediate session revocation on request, refusal of normal sync writes while pending, in-grace cancellation through the existing verified credential system, and a deterministic purge boundary invoked with an injected clock.
- Boundary: The server-side auth/account/sync/routes surface and its schema and tests only. The A3 session and refresh-rotation model is extended, never replaced; the A6 conflict policy and the A5 outbox policy are untouched.
- Depends: none
- Allowed Paths: `KeepLab-Relay/backend/src/main/kotlin/com/keeplab/backend/auth/`, `KeepLab-Relay/backend/src/main/kotlin/com/keeplab/backend/account/`, `KeepLab-Relay/backend/src/main/kotlin/com/keeplab/backend/sync/`, `KeepLab-Relay/backend/src/main/kotlin/com/keeplab/backend/routes/`, `KeepLab-Relay/backend/src/main/kotlin/com/keeplab/backend/Application.kt`, `KeepLab-Relay/backend/src/main/kotlin/com/keeplab/backend/BackendServices.kt`, `KeepLab-Relay/backend/src/main/resources/db/migration/`, `KeepLab-Relay/backend/src/test/`, `Google-Android-Agent-Development-Stack/reports/KEEPLAB-M5-HUMAN-DECISIONS.md`
- Acceptance: AC-M5-004, AC-M5-009, AC-M5-010, AC-M5-011, AC-M5-012, AC-M5-024, AC-M5-025
- Verification: deterministic backend tests for the session/installation identity, per-session revoke, disable, the fake-clock 30-day boundary, cancel-before-purge and purge-after-boundary
- Done When: the approved values are recorded verbatim; the server holds an installation-distinguishing session per login; revoke/disable/deletion-pending are refused on authenticated paths; the fake-clock boundary, cancellation and purge behave exactly as specified

### TASK-02 — Implement the Android installation/session representation and the session-list/revoke UX

- Goal: Generate and persist a KeepLab-owned, privacy-bounded installation identity app-privately, present it at login as the session's installation identity, and add the session list, the current-installation marker, the per-session revoke affordance and the non-destructive session-invalid state.
- Boundary: The Android auth/remote/local/UI surface for sessions only. No credential architecture change; no device fingerprinting or invasive identifier; no destructive sign-out; Room rows and outbox rows are never deleted here.
- Depends: TASK-01
- Allowed Paths: `KeepLab-Relay/app/src/main/java/com/keeplab/app/data/auth/`, `KeepLab-Relay/app/src/main/java/com/keeplab/app/data/remote/`, `KeepLab-Relay/app/src/main/java/com/keeplab/app/data/local/`, `KeepLab-Relay/app/src/main/java/com/keeplab/app/model/`, `KeepLab-Relay/app/src/main/java/com/keeplab/app/di/`, `KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/settings/`, `KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/auth/`, `KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/navigation/`, `KeepLab-Relay/app/src/main/java/com/keeplab/app/KeepLabApplication.kt`, `KeepLab-Relay/app/src/main/java/com/keeplab/app/MainActivity.kt`, `KeepLab-Relay/app/src/test/`, `KeepLab-Relay/app/src/androidTest/`
- Acceptance: AC-M5-004, AC-M5-005, AC-M5-025
- Verification: Android JVM tests for the installation identity generation/persistence, the session list mapping, the revoke request and the session-invalid state; the session-list and revoke selectors resolve
- Done When: two installations are distinguishable in the session list; the current installation is marked; another session can be revoked; the state is visible without deleting any local data

### TASK-03 — Prove bidirectional propagation between two independent clients

- Goal: Prove, with two independent authenticated clients on one account, that a write accepted from one client becomes visible to the other through its own pull, and the reverse, converging on the server-accepted representation.
- Boundary: The sync/repository and backend-sync surface, and its tests. The A4 pull/push semantics, the outbox and the checkpoint are consumed as frozen.
- Depends: TASK-01
- Allowed Paths: `KeepLab-Relay/backend/src/main/kotlin/com/keeplab/backend/sync/`, `KeepLab-Relay/backend/src/main/kotlin/com/keeplab/backend/routes/`, `KeepLab-Relay/backend/src/test/`, `KeepLab-Relay/app/src/main/java/com/keeplab/app/data/sync/`, `KeepLab-Relay/app/src/main/java/com/keeplab/app/data/remote/`, `KeepLab-Relay/app/src/main/java/com/keeplab/app/data/local/`, `KeepLab-Relay/app/src/main/java/com/keeplab/app/data/NoteRepository.kt`, `KeepLab-Relay/app/src/test/`
- Acceptance: AC-M5-001, AC-M5-002, AC-M5-022
- Verification: a deterministic backend integration test that drives two independent authenticated clients (distinct sessions, distinct installation identities, same account) and asserts A-to-B and B-to-A convergence on the server revision stream
- Done When: both directions converge deterministically in the two-client integration test, and no convergence depends on a client wall clock

### TASK-04 — Exercise the existing A6 conflict semantics under real two-client concurrency

- Goal: Drive two distinct authenticated clients from the same base revision and prove the frozen A6 policy holds: title/body never silently overwritten with KEEP_LOCAL/KEEP_SERVER/KEEP_BOTH, KEEP_BOTH producing a NEW logical note with a NEW client UUID enqueued as CREATE, concurrent checklist additions both surviving, a concurrent label removal not resurrected, delete-vs-edit explicit, and server revision/order as the only authority.
- Boundary: The conflict/sync surface and its tests only. The A6 policy is consumed as frozen and is not redesigned.
- Depends: TASK-03
- Allowed Paths: `KeepLab-Relay/backend/src/main/kotlin/com/keeplab/backend/sync/`, `KeepLab-Relay/backend/src/test/`, `KeepLab-Relay/app/src/main/java/com/keeplab/app/data/sync/`, `KeepLab-Relay/app/src/main/java/com/keeplab/app/data/local/`, `KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/conflict/`, `KeepLab-Relay/app/src/test/`
- Acceptance: AC-M5-003, AC-M5-023
- Verification: deterministic two-client concurrency tests for each A6 conflict class, asserting the observable outcome and that no resolution consults an unsynchronised client wall clock
- Done When: every named A6 conflict class is exercised under real two-client concurrency with the specified outcome and no silent overwrite

### TASK-05 — Implement remote session invalidation and non-destructive AUTH_REQUIRED behaviour

- Goal: Make a revoked or disabled remote session produce a session-invalid / AUTH_REQUIRED outcome on the next authenticated request, refresh or sync, while keeping the Room data, the conflicts and the durable outbox intact and allowing re-authentication.
- Boundary: The Android auth/sync surface and its tests, plus the backend refusal path. No destructive sign-out, no local deletion, no reassignment of local notes.
- Depends: TASK-01, TASK-02
- Allowed Paths: `KeepLab-Relay/app/src/main/java/com/keeplab/app/data/auth/`, `KeepLab-Relay/app/src/main/java/com/keeplab/app/data/sync/`, `KeepLab-Relay/app/src/main/java/com/keeplab/app/data/remote/`, `KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/settings/`, `KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/auth/`, `KeepLab-Relay/app/src/test/`, `KeepLab-Relay/backend/src/main/kotlin/com/keeplab/backend/auth/`, `KeepLab-Relay/backend/src/test/`
- Acceptance: AC-M5-006, AC-M5-007, AC-M5-008
- Verification: deterministic tests that revoke a session and assert the next authenticated call, refresh and sync are refused, that a revoked refresh token cannot rotate into a new valid chain, and that Room rows and outbox rows are unchanged
- Done When: a revoked remote session is refused everywhere, is non-destructive everywhere, and can authenticate again

### TASK-06 — Implement account disable and the D-05 30-day deletion state machine, cancel and purge

- Goal: Implement account disable (all sessions unusable, local notes intact) and the D-05 deletion lifecycle: request → DELETION_PENDING with immediate access disable and full session revocation, cancel inside the grace window through the existing credential system restoring ACTIVE, and the deterministic purge boundary after purge_after that permanently deletes the server account data.
- Boundary: The backend account/auth lifecycle surface and its tests. Account lifecycle stays separate from the Trash lifecycle and the sync tombstone; no production scheduler and no cloud resource.
- Depends: TASK-01
- Allowed Paths: `KeepLab-Relay/backend/src/main/kotlin/com/keeplab/backend/account/`, `KeepLab-Relay/backend/src/main/kotlin/com/keeplab/backend/auth/`, `KeepLab-Relay/backend/src/main/kotlin/com/keeplab/backend/routes/`, `KeepLab-Relay/backend/src/main/resources/db/migration/`, `KeepLab-Relay/backend/src/test/`, `KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/settings/`, `KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/auth/`, `KeepLab-Relay/app/src/main/java/com/keeplab/app/data/auth/`, `KeepLab-Relay/app/src/test/`
- Acceptance: AC-M5-009, AC-M5-010, AC-M5-011, AC-M5-012, AC-M5-024
- Verification: deterministic fake-clock tests for the disable path, request, no-new-write-while-pending, cancel-before-purge, the boundary at exactly purge_after, purge-after-boundary, and idempotent purge
- Done When: ACTIVE → DELETION_PENDING → ACTIVE-or-PURGED is deterministic under an injected clock, and Android local notes are untouched throughout

### TASK-07 — Run the real two-Android-device journey

- Goal: Run the final M5 device journey on two independent Android device/app instances on one account: session list, A↔B propagation, real concurrency conflict, per-session revoke, remote invalidation with local data and outbox survival, account disable and the deletion-grace states — all with PUSH_PROVIDER = NONE.
- Boundary: The existing bounded device/verification seam only. `adb devices` is inspected once; no broad host scan; no cloud provisioning; no `screenshot → LLM → tap` loop; deterministic selectors drive the journey and screenshots are failure evidence only.
- Depends: TASK-02, TASK-03, TASK-04, TASK-05, TASK-06
- Allowed Paths: `KeepLab-Relay/app/src/androidTest/`, `Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/keeplab-m5-a8/`
- Acceptance: AC-M5-001, AC-M5-002, AC-M5-018, AC-M5-019
- Verification: the two-device journey with deterministic assertions per step; on FAIL the evidence is screenshot + layout + logcat + the failed assertion, read once
- Done When: the journey completes on two real independent Android instances on one account, or the milestone returns A8_DEVICE_PAIR_UNAVAILABLE and is not reported PASS

### TASK-08 — Run one combined M5 verification and produce the M5 report

- Goal: Run the single combined M5 verification pass (all affected existing backend and Android tests plus the new A8 tests, the deterministic two-client backend integration, the real two-device journey, revoke, invalidation, Room survival, outbox survival, the D-05 fake-clock boundary, cancel-before-purge, purge-after-boundary, no cross-account leakage, PUSH_PROVIDER = NONE, no M4 attachment modification, no A9 work) and produce the M5 report.
- Boundary: Verification and the report only. No post-PASS exploration, no Auto-Finalizer inspection, no reopening of M4, no dependency change, no surface broadening.
- Depends: TASK-07
- Allowed Paths: `Google-Android-Agent-Development-Stack/reports/KEEPLAB-M5-A8-EXECUTION.md`, `Google-Android-Agent-Development-Stack/reports/KEEPLAB-M5-HUMAN-DECISIONS.md`, `Google-Android-Agent-Development-Stack/reports/KEEPLAB-AUTH-SYNC-HUMAN-DECISIONS.md`, `Google-Android-Agent-Development-Stack/reports/KEEPLAB-AUTH-SYNC-DECISION-REGISTER.md`, `Google-Android-Agent-Development-Stack/reports/KEEPLAB-AUTH-SYNC-IMPLEMENTATION-ROADMAP.md`, `Google-Android-Agent-Development-Stack/reports/KEEPLAB-MINOR-BACKLOG.md`, `Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/keeplab-m5-a8/`
- Acceptance: AC-M5-013, AC-M5-014, AC-M5-015, AC-M5-016, AC-M5-017, AC-M5-020, AC-M5-021, AC-M5-026
- Verification: run the backend gate and the Android gate once each, plus the deterministic A8 suites, and assert every A8 gate value, DEPENDENCY_CHANGE = NO, M4 NOT_REOPENED and A9 NOT_STARTED
- Done When: every A8 acceptance value is PASS or the milestone is BLOCKED/FAIL with evidence, and one M5 report exists
