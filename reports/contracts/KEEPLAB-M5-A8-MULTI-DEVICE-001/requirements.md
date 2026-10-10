# Requirements — KeepLab M5 = A8 Multi-Device Hardening

## Requirements

### REQ-M5-001 — Independent device/session identities and an inspectable session list

- Statement: Two or more independent installations must be able to hold a valid session on ONE KeepLab account, and the session representation must let a user tell them apart without device fingerprinting or invasive identifiers.
- Conditions: Two independent Android app instances (independent app process, Room database, secure session store, installation identity and authenticated session) use the same account.
- Expected: The server holds one session per installation; `GET /v1/auth/sessions` reports every session of the account with the current one identifiable; each session carries a KeepLab-generated installation/device identity. IMEI, hardware serial, Android ID as a global tracking identity, advertising ID and phone number are never used.
- Edge case: A session whose installation identity is absent or unreadable must still be representable (a stable non-identifying fallback label), never rejectable in a way that breaks sign-in.
- Acceptance: AC-M5-004, AC-M5-025
- Tasks: TASK-01, TASK-02

### REQ-M5-002 — Bidirectional propagation and convergence across two clients

- Statement: A write accepted from one client must become visible to the other client through its own pull, and the reverse must hold too, converging without user intervention.
- Conditions: Two independent authenticated clients share one account and one server revision stream.
- Expected: Device A writes → server accepts → Device B pulls and converges to the server state; Device B writes → Device A converges. Convergence is on the server-accepted representation, not on a client wall clock.
- Edge case: A client that is offline at write time still converges after reconnect; a change that the client already applied at a revision greater than or equal to the incoming one is not re-applied destructively.
- Acceptance: AC-M5-001, AC-M5-002, AC-M5-022
- Tasks: TASK-03, TASK-07

### REQ-M5-003 — Existing A6 conflict semantics hold under real two-client concurrency

- Statement: The A6 conflict rules must be exercised and preserved under real server concurrency: two distinct authenticated clients acting from the same base revision.
- Conditions: Client A and client B both hold the same base revision for an entity and both push a change.
- Expected: The second write is a server revision conflict, never a silent overwrite: title/body is user-resolved with KEEP_LOCAL, KEEP_SERVER and KEEP_BOTH; `KEEP_BOTH` creates a NEW logical note with a NEW client-generated UUID enqueued as `CREATE` in the same account scope, never reusing the original entity id; concurrent checklist additions both survive; a concurrent label removal is not resurrected by a union; delete-vs-edit is explicit; the server revision/order is the only authority and no unsynchronised client wall clock is used. The A6 policy is consumed as frozen and is not redesigned.
- Edge case: A duplicate `mutation_id` retry returns the recorded result once and applies nothing twice.
- Acceptance: AC-M5-003, AC-M5-023
- Tasks: TASK-04

### REQ-M5-004 — Per-session revoke, remote invalidation and non-destructive recovery

- Statement: Device A must be able to revoke Device B's session without destroying B's local data; B's next authenticated request, refresh or sync must be rejected and B must be able to authenticate again.
- Conditions: A revokes B's session from the session list; B then performs an authenticated API call, a refresh, or a sync.
- Expected: The server marks/revokes B's session; B's access and refresh capability become invalid; a revoked refresh token never rotates into a new valid refresh chain; B enters `AUTH_REQUIRED`/session-invalid state; B's Room data and durable outbox remain intact; there is no destructive sign-out and no silent reassignment of B's local notes to another account; the user may authenticate again. Refresh tokens, password verifiers, access-token content and secret material are never exposed.
- Edge case: A revoke issued while B is mid-sync must not delete B's local rows; the in-flight push is refused, not applied to a foreign account.
- Acceptance: AC-M5-005, AC-M5-006, AC-M5-007, AC-M5-008
- Tasks: TASK-02, TASK-05

### REQ-M5-005 — Account disable makes every session unusable without local data loss

- Statement: Disabling an account must make all of its sessions unusable while leaving the Android local notes intact.
- Conditions: The account enters the disabled state.
- Expected: Every session of the account is refused on authenticated requests, refresh and sync; the Android local notes, account-scoped cached notes and `LOCAL_ONLY` notes all survive.
- Edge case: A client that only discovers the disable on a later pull must record the auth failure non-destructively rather than deleting anything.
- Acceptance: AC-M5-009
- Tasks: TASK-06

### REQ-M5-006 — D-05 account deletion grace state machine, cancellation and deterministic purge boundary

- Statement: Account deletion must be a deliberate, authenticated act that is strictly distinct from the Trash lifecycle and must follow the human-approved D-05 `ACCOUNT_DELETE_GRACE_30_DAYS` semantics.
- Conditions: An authenticated owner requests deletion, or cancels inside the grace window, or the grace window elapses.
- Expected: `ACTIVE → DELETION_PENDING` immediately on request; normal account access becomes disabled and all server sessions are revoked immediately; no new normal sync write is accepted while deletion is pending; `purge_after = deletion_requested_at + 30 days` with server clock authority; within the window the owner may cancel through re-authentication using the EXISTING verified credential system (no new token family invented for recovery) restoring `ACTIVE` without resurrecting deleted data because purge has not occurred; after expiry a deterministic purge boundary permanently deletes the server account data. No client wall clock decides purge eligibility; tests use an injected/fake clock and no 30-real-day test and no production scheduler is required.
- Edge case: A cancellation attempt exactly at or after `purge_after` is refused; a purge is idempotent and cannot purge a cancelled (ACTIVE) account.
- Acceptance: AC-M5-010, AC-M5-011, AC-M5-012, AC-M5-024
- Tasks: TASK-01, TASK-06

### REQ-M5-007 — No push provider in the A8 correctness path

- Statement: A8 correctness must hold with `PUSH_PROVIDER = NONE`, and no push provider may be introduced by this milestone.
- Conditions: All multi-device, revoke, invalidation, disable and deletion-grace behaviour is verified.
- Expected: Correctness remains pull/delta based; WorkManager, foreground or manual sync detect remote state; authenticated API and refresh paths detect revoked/disabled state; no FCM/Firebase/vendor push dependency exists; pass is possible with `PUSH_PROVIDER = NONE`; any future push must sit behind a provider abstraction and is a latency optimization only.
- Edge case: A design that only works with push is not acceptable as A8 evidence.
- Acceptance: AC-M5-016
- Tasks: TASK-08

### REQ-M5-008 — The final M5 journey uses two real, independently addressable Android device instances

- Statement: The final M5 device journey must run against two independent Android device/app instances on one KeepLab account, and multi-device may never be silently downgraded to a single-object mock and reported PASS.
- Conditions: `adb devices` and the existing bounded device/verification seam are inspected once before the journey; two usable independent Android instances are available (two emulators, one physical plus one emulator, or two physical devices), each with its own app process, Room database, secure/session store, installation identity and authenticated session.
- Expected: The journey runs on the real pair; backend integration tests with two independent clients are mandatory but do not by themselves replace it.
- Edge case: If fewer than two usable independent Android instances exist and the existing project tooling cannot supply a second isolated emulator instance, the milestone returns `A8_DEVICE_PAIR_UNAVAILABLE` and M5 MUST NOT be reported PASS. No cloud infrastructure is provisioned to satisfy the test; the existing development backend/test environment is used.
- Acceptance: AC-M5-018, AC-M5-019
- Tasks: TASK-07

### REQ-M5-009 — The authorized write surface is bounded and frozen work is not reopened

- Statement: The contract must authorize only the enumerated M5 surfaces and must not authorize any broad prefix.
- Conditions: The generated contract is read and the guard activates this package.
- Expected: `allowed_paths` contains the enumerated M5 backend, Android, report and evidence paths; it does not contain `KeepLab-Relay/`, `KeepLab-Relay/app/`, or `Google-Android-Agent-Development-Stack/reports/` as broad prefixes; no allowed path is equal to, inside, or a parent of any forbidden path; frozen milestone work is never reopened.
- Edge case: A required file genuinely outside the enumerated surface is `STOP → M5_SURFACE_BROADENING_REQUIRED`, never a silent widening.
- Acceptance: AC-M5-020, AC-M5-021
- Tasks: TASK-08

### REQ-M5-010 — No Gradle dependency change

- Statement: M5 must be implemented with the existing implementation seams and must not add a dependency.
- Conditions: The Android and backend build files are inspected after the M5 change set.
- Expected: `app/build.gradle.kts`, `gradle/libs.versions.toml`, the root Gradle files: no Firebase, FCM, Google services, vendor push SDK, new networking stack or CRDT library is added; `DEPENDENCY_CHANGE: NO`.
- Edge case: A genuinely indispensable dependency is `STOP → M5_DEPENDENCY_DECISION_REQUIRED`, never an automatic addition.
- Acceptance: AC-M5-017
- Tasks: TASK-08

### REQ-M5-011 — Room stays the local source of truth and the server keeps revision authority

- Statement: Local Room remains the single source of truth for the Android UI and the server remains the only revision/order authority; local data is never silently destroyed or reassigned.
- Conditions: Any remote disable, deletion-pending, purge, revoke or invalidation occurs.
- Expected: Android local Room data is never silently deleted because the remote account was disabled, deletion-pending or purged; local notes are never silently reassigned to another account; `LOCAL_ONLY` notes stay local; account-scoped cached notes stay local and simply cannot sync while unauthorized; the A6 server-revision authority is preserved; there is no cross-account leakage; existing attachments, outbox, conflicts and local notes remain intact.
- Edge case: An authenticated request answered with a revocation or disable status must be non-destructive at every call site.
- Acceptance: AC-M5-013, AC-M5-014, AC-M5-015
- Tasks: TASK-08

### REQ-M5-012 — One combined M5 verification pass and one M5 report

- Statement: M5 is planned once, implemented fully, and verified once, producing one M5 report.
- Conditions: All M5 work is complete.
- Expected: The verification covers all affected existing backend and Android tests plus the new A8 tests, the deterministic two-client backend integration, the real two-device journey, session revoke, remote invalidation, local Room survival, outbox survival, the D-05 fake-clock 30-day boundary, cancel-before-purge, purge-after-boundary, no cross-account leakage and `PUSH_PROVIDER = NONE`, with deterministic assertions and screenshots not as the primary oracle. `PASS = STOP`: the final Phase C report is produced from already-collected evidence, with no post-PASS exploration.
- Edge case: On FAIL, only the failed M5 item is repaired and only the work invalidated by that repair is re-run.
- Acceptance: AC-M5-026
- Tasks: TASK-08
