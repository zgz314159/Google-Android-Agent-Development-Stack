# Acceptance Criteria — KeepLab M5 = A8 Multi-Device Hardening

## Acceptance Criteria

### AC-M5-001 — TWO_DEVICE_CONVERGENCE

- Given: two independent Android device/app instances on ONE KeepLab account, each with its own app process, Room database, secure/session store, installation identity and authenticated session
- When: one device writes and the other pulls
- Then: the second device converges to the server-accepted representation of that write
- Verification: deterministic two-client integration assertion plus the two-device journey assertion that the written content is present on the other instance
- PC1 Step: PC1-01

### AC-M5-002 — BIDIRECTIONAL_PROPAGATION

- Given: Device A and Device B, both authenticated on the same account
- When: A writes and then B writes
- Then: B converges to A's write and A converges to B's write, in both directions
- Verification: assert both directions in the deterministic two-client integration and in the two-device journey
- PC1 Step: PC1-02

### AC-M5-003 — REAL_CONCURRENCY_CONFLICT

- Given: two distinct authenticated clients holding the same base revision for one entity
- When: both push a change to the server
- Then: the second push is a server revision conflict answered with the authoritative 409 body, never a silent overwrite
- Verification: assert the 409 and the authoritative current revision/payload in the two-client integration test
- PC1 Step: PC1-03

### AC-M5-004 — SESSION_LIST

- Given: an account with two or more independent sessions
- When: the signed-in user inspects the server session list
- Then: every session of the account is listed, each distinguishable by its installation identity, with the current session identifiable
- Verification: assert the session-list payload contains one entry per session with the current flag set on exactly one
- PC1 Step: PC1-04

### AC-M5-005 — PER_SESSION_REVOKE

- Given: an account with Device A's and Device B's sessions
- When: Device A revokes Device B's session
- Then: the server marks Device B's session revoked and it is no longer valid
- Verification: assert the revoke outcome and the server session state
- PC1 Step: PC1-05

### AC-M5-006 — REMOTE_INVALIDATION

- Given: Device B holds access and refresh credentials for a session that has been revoked or disabled
- When: Device B performs its next authenticated API request, refresh or sync
- Then: the request is rejected, a revoked refresh token never rotates into a new valid refresh chain, and Device B enters the session-invalid / AUTH_REQUIRED state
- Verification: assert the refusal status on the API call, on refresh and on sync, and assert no new valid refresh chain is produced
- PC1 Step: PC1-06

### AC-M5-007 — LOCAL_NOTES_SURVIVE_REVOKE

- Given: Device B with local Room notes, including LOCAL_ONLY notes and account-scoped cached notes
- When: Device B discovers that its session was revoked or disabled
- Then: every local note is still present and no note was reassigned to another account
- Verification: compare the Room note set and its account scoping before and after the invalidation; assert equality
- PC1 Step: PC1-07

### AC-M5-008 — OUTBOX_SURVIVES_REVOKE

- Given: Device B with pending outbox mutations
- When: Device B discovers that its session was revoked or disabled
- Then: the durable outbox is intact and the pending work is retained
- Verification: compare the outbox row set before and after the invalidation; assert equality
- PC1 Step: PC1-08

### AC-M5-009 — ACCOUNT_DISABLE

- Given: an account with at least two sessions and a device with local notes
- When: the account is disabled
- Then: all sessions become unusable on authenticated requests, refresh and sync, and the local notes remain intact
- Verification: assert every session is refused and the local note set is unchanged
- PC1 Step: PC1-09

### AC-M5-010 — ACCOUNT_DELETE_GRACE_30D

- Given: an ACTIVE account and a deliberate authenticated deletion request
- When: the request is accepted
- Then: the account enters DELETION_PENDING, normal account access is disabled, all server sessions are revoked immediately, no new normal sync write is accepted while deletion is pending, and purge_after equals deletion_requested_at + 30 days under server clock authority
- Verification: assert the state transition, the immediate revocation of every session, the refused sync write, and the exact purge_after arithmetic against an injected clock
- PC1 Step: PC1-10

### AC-M5-011 — DELETE_CANCEL_RECOVERY

- Given: an account in DELETION_PENDING inside its 30-day grace window
- When: the owner cancels through re-authentication using the EXISTING verified credential system
- Then: the account returns to ACTIVE with no data loss and no purged data resurrected, and no new token family was invented for recovery
- Verification: assert the ACTIVE restoration after re-authentication and assert that the credential seam used is the existing one
- PC1 Step: PC1-11

### AC-M5-012 — PURGE_BOUNDARY

- Given: an account in DELETION_PENDING and a fake clock advanced to or beyond purge_after
- When: the deterministic purge boundary runs
- Then: the server account data is permanently deleted, the purge is idempotent, and a cancelled (ACTIVE) account is never purged
- Verification: assert purge at/after the boundary, assert a repeat purge is a no-op, and assert an ACTIVE account is not purged; no 30-real-day wait and no production scheduler
- PC1 Step: PC1-12

### AC-M5-013 — ROOM_SSOT_PRESERVED

- Given: any remote revoke, disable, deletion-pending or purge event
- When: the Android client observes it
- Then: Room remains the local source of truth and no local Room data is silently deleted, and the UI still reads from Room
- Verification: assert the Room row set is unchanged by the remote event and that no network response is returned directly to the UI
- PC1 Step: PC1-13

### AC-M5-014 — SERVER_REVISION_AUTHORITY_PRESERVED

- Given: a multi-device conflict or a concurrent write
- When: the outcome is decided
- Then: the server revision/order is the only authority and no unsynchronised client wall clock participates in any resolution
- Verification: assert the resolved revision equals the server-assigned revision and that no client timestamp is consulted
- PC1 Step: PC1-14

### AC-M5-015 — CROSS_ACCOUNT_LEAK_NONE

- Given: two accounts and a client supplying a foreign account identifier
- When: any authenticated request is made
- Then: no other account's data is readable or writable; the effective scope is derived from the authenticated session only; local notes are never transferred into another account
- Verification: assert a foreign-account request exposes no foreign data and changes nothing, and assert local note account scoping is unchanged
- PC1 Step: PC1-15

### AC-M5-016 — PUSH_PROVIDER_NONE

- Given: the M5 change set and build configuration
- When: the deliverable is inspected
- Then: PUSH_PROVIDER equals NONE, no FCM/Firebase/Google-services/vendor push dependency exists, and A8 pass was achieved with push disabled
- Verification: assert no push dependency in the build files and assert PUSH_REQUIRED_FOR_CORRECTNESS = NO
- PC1 Step: PC1-16

### AC-M5-017 — NO_GRADLE_DEPENDENCY_CHANGE

- Given: the M5 change set
- When: the Gradle build files are inspected
- Then: no new dependency was added and the root/Android Gradle files are unmodified
- Verification: assert DEPENDENCY_CHANGE = NO and that app/build.gradle.kts, gradle/libs.versions.toml and the root Gradle files are unchanged
- PC1 Step: PC1-17

### AC-M5-018 — TWO_REAL_ANDROID_DEVICES

- Given: the existing bounded device/verification seam and `adb devices` inspected once
- When: the final M5 journey runs
- Then: it runs on two real, independently addressable Android device/app instances (two emulators, one physical device plus one emulator, or two physical devices) on one account
- Verification: assert two distinct device serials/instances with two independent app processes, Room databases, session stores and sessions
- PC1 Step: PC1-18

### AC-M5-019 — DEVICE_PAIR_UNAVAILABLE_BLOCKS_PASS

- Given: fewer than two usable independent Android device instances and no way to supply a second isolated one
- When: the milestone is evaluated
- Then: the result is A8_DEVICE_PAIR_UNAVAILABLE and M5 is NOT reported PASS, and no mock-only evidence is accepted as PASS
- Verification: assert the BLOCKED result with the blocker named and assert no PASS was emitted from mocks alone
- PC1 Step: PC1-19

### AC-M5-020 — WRITE_SURFACE_BOUNDED

- Given: the generated implementation contract
- When: allowed_paths and forbidden_paths are read
- Then: only the enumerated M5 paths are allowed, no broad KeepLab-Relay/ or KeepLab-Relay/app/ or reports/ prefix is authorized, and no allowed path overlaps a forbidden path
- Verification: assert the enumerated entries are present and that the compiler reports zero E_PATH_CONFLICT and zero E_PROJECT_ESCAPE errors
- PC1 Step: PC1-20

### AC-M5-021 — FROZEN_MILESTONES_NOT_REOPENED

- Given: the M5 change set
- When: it is inspected
- Then: A0/A1/A2/M2/M3/M4 and every frozen decision (D-01, D-04, D-06, D-07, D-08, D-09, D-10, D-13, D-15) are untouched, the A6 conflict policy and the A7 attachment architecture are not modified, and A9 is not started
- Verification: assert M4 = NOT_REOPENED, A9 = NOT_STARTED, no attachment module was modified, and TOMBSTONE_GC stays DISABLED
- PC1 Step: PC1-21

### AC-M5-022 — BACKEND_INTEGRATION_TWO_CLIENTS

- Given: the existing development backend/test environment
- When: the A8 integration tests run
- Then: they drive two independent authenticated clients (distinct sessions and installation identities, same account) and are mandatory, while not by themselves replacing the two-device journey
- Verification: assert the integration suite uses two distinct authenticated sessions and that the journey is separately reported
- PC1 Step: PC1-22

### AC-M5-023 — A6_CONFLICT_SEMANTICS_EXERCISED

- Given: real two-client concurrency from the same base revision
- When: each A6 conflict class occurs
- Then: title/body is never silently overwritten and offers KEEP_LOCAL/KEEP_SERVER/KEEP_BOTH; KEEP_BOTH creates a NEW logical note with a NEW client-generated UUID enqueued as CREATE in the same account scope and never reuses the original entity id; concurrent checklist additions both survive; a concurrent label removal is not resurrected; delete-vs-edit is explicit
- Verification: assert each named class outcome in the deterministic two-client tests, including the new UUID and the CREATE enqueue for KEEP_BOTH
- PC1 Step: PC1-23

### AC-M5-024 — D05_STATE_MACHINE

- Given: the D-05 account lifecycle
- When: the deletion lifecycle is driven
- Then: ACTIVE → DELETION_PENDING → either ACTIVE again by in-grace cancellation or PURGED after the deterministic 30-day boundary, with no state reachable outside that machine
- Verification: assert the reachable state sequence and assert DELETION_PENDING cannot be skipped or reversed outside cancellation
- PC1 Step: PC1-24

### AC-M5-025 — SESSION_REPRESENTATION_PRIVACY

- Given: the session/installation identity implementation
- When: the identifiers used are inspected
- Then: IMEI, hardware serial, Android ID as a global tracking identity, advertising ID and phone number are never used, and the installation identity is one generated and persisted by KeepLab itself
- Verification: assert no such identifier is read or transmitted and that the installation identity is KeepLab-generated and app-private
- PC1 Step: PC1-25

### AC-M5-026 — VERIFICATION_ONCE_AND_REPORT

- Given: all M5 work complete
- When: verification runs
- Then: it runs once and produces one M5 report; screenshots are not the primary oracle; on PASS no post-PASS exploration occurs; on FAIL only the failed item is repaired and only invalidated work is re-run
- Verification: assert one combined verification pass, deterministic assertions as the oracle, and a single M5 report
- PC1 Step: PC1-26
