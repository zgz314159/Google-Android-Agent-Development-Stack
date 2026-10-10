# EXECUTOR PROMPT — KEEPLAB-M5-A8-MULTI-DEVICE

You are the execution agent for a FROZEN Implementation Contract. Work from the contract
and the listed `read_first` files. Do not re-do reconnaissance, re-choose architecture, or
re-plan decisions this contract has already frozen.

## 0. Verify the frozen contract
- Contract: `implementation-contract.json` (contract_id `KEEPLAB-M5-A8-MULTI-DEVICE-001`, version `0.1.0`)
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
- Read only these 26 `read_first` files:
  1. Google-Android-Agent-Development-Stack/reports/KEEPLAB-AUTH-SYNC-IMPLEMENTATION-ROADMAP.md
  2. Google-Android-Agent-Development-Stack/reports/KEEPLAB-AUTH-SYNC-HUMAN-DECISIONS.md
  3. Google-Android-Agent-Development-Stack/reports/KEEPLAB-AUTH-SYNC-DECISION-REGISTER.md
  4. Google-Android-Agent-Development-Stack/reports/KEEPLAB-AUTH-SYNC-API-CONTRACT.md
  5. Google-Android-Agent-Development-Stack/reports/KEEPLAB-M4-ATTACHMENTS-EXECUTION.md
  6. KeepLab-Relay/backend/src/main/kotlin/com/keeplab/backend/auth/AuthService.kt
  7. KeepLab-Relay/backend/src/main/kotlin/com/keeplab/backend/auth/AuthStore.kt
  8. KeepLab-Relay/backend/src/main/kotlin/com/keeplab/backend/auth/AuthModels.kt
  9. KeepLab-Relay/backend/src/main/kotlin/com/keeplab/backend/auth/JwtService.kt
  10. KeepLab-Relay/backend/src/main/kotlin/com/keeplab/backend/auth/Clock.kt
  11. KeepLab-Relay/backend/src/main/kotlin/com/keeplab/backend/routes/AuthRoutes.kt
  12. KeepLab-Relay/backend/src/main/kotlin/com/keeplab/backend/routes/SyncRoutes.kt
  13. KeepLab-Relay/backend/src/main/kotlin/com/keeplab/backend/sync/SyncService.kt
  14. KeepLab-Relay/backend/src/main/kotlin/com/keeplab/backend/sync/SyncStore.kt
  15. KeepLab-Relay/backend/src/main/kotlin/com/keeplab/backend/Application.kt
  16. KeepLab-Relay/backend/src/main/kotlin/com/keeplab/backend/BackendServices.kt
  17. KeepLab-Relay/backend/src/main/resources/db/migration/V2__auth_schema.sql
  18. KeepLab-Relay/backend/src/main/resources/db/migration/V3__sync_schema.sql
  19. KeepLab-Relay/app/src/main/java/com/keeplab/app/data/auth/SessionManager.kt
  20. KeepLab-Relay/app/src/main/java/com/keeplab/app/data/auth/SecureSessionStore.kt
  21. KeepLab-Relay/app/src/main/java/com/keeplab/app/data/auth/AuthRepository.kt
  22. KeepLab-Relay/app/src/main/java/com/keeplab/app/data/auth/DeviceLabelProvider.kt
  23. KeepLab-Relay/app/src/main/java/com/keeplab/app/data/sync/SyncEngine.kt
  24. KeepLab-Relay/app/src/main/java/com/keeplab/app/data/local/KeepLabDatabase.kt
  25. KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/settings/SettingsScreen.kt
  26. KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/conflict/ConflictScreen.kt
- Extend to a targeted search ONLY for `CONTRACT_GAP`, `CONTRACT_CONTRADICTION`, a missing
  dependency, or compile evidence that requires one extra file. Record `EXTRA_RECON_REASON`
  (file + why) for every extension.

## 3. Execute tasks in dependency order
  TASK-01  Record D-05 = ACCOUNT_DELETE_GRACE_30_DAYS and D-11 = NO_PUSH_PROVIDER_IN_A8_CORRECTNESS_PATH at their approved values, and implement the server-side session/installation identity, the per-session revoke surface and the account lifecycle state machine (ACTIVE / DISABLED / DELETION_PENDING / PURGED) with deletion_requested_at, purge_after = deletion_requested_at + 30 days, immediate session revocation on request, refusal of normal sync writes while pending, in-grace cancellation through the existing verified credential system, and a deterministic purge boundary invoked with an injected clock.  (depends: none)
  TASK-02  Generate and persist a KeepLab-owned, privacy-bounded installation identity app-privately, present it at login as the session's installation identity, and add the session list, the current-installation marker, the per-session revoke affordance and the non-destructive session-invalid state.  (depends: TASK-01)
  TASK-03  Prove, with two independent authenticated clients on one account, that a write accepted from one client becomes visible to the other through its own pull, and the reverse, converging on the server-accepted representation.  (depends: TASK-01)
  TASK-04  Drive two distinct authenticated clients from the same base revision and prove the frozen A6 policy holds: title/body never silently overwritten with KEEP_LOCAL/KEEP_SERVER/KEEP_BOTH, KEEP_BOTH producing a NEW logical note with a NEW client UUID enqueued as CREATE, concurrent checklist additions both surviving, a concurrent label removal not resurrected, delete-vs-edit explicit, and server revision/order as the only authority.  (depends: TASK-03)
  TASK-05  Make a revoked or disabled remote session produce a session-invalid / AUTH_REQUIRED outcome on the next authenticated request, refresh or sync, while keeping the Room data, the conflicts and the durable outbox intact and allowing re-authentication.  (depends: TASK-01, TASK-02)
  TASK-06  Implement account disable (all sessions unusable, local notes intact) and the D-05 deletion lifecycle: request → DELETION_PENDING with immediate access disable and full session revocation, cancel inside the grace window through the existing credential system restoring ACTIVE, and the deterministic purge boundary after purge_after that permanently deletes the server account data.  (depends: TASK-01)
  TASK-07  Run the final M5 device journey on two independent Android device/app instances on one account: session list, A↔B propagation, real concurrency conflict, per-session revoke, remote invalidation with local data and outbox survival, account disable and the deletion-grace states — all with PUSH_PROVIDER = NONE.  (depends: TASK-02, TASK-03, TASK-04, TASK-05, TASK-06)
  TASK-08  Run the single combined M5 verification pass (all affected existing backend and Android tests plus the new A8 tests, the deterministic two-client backend integration, the real two-device journey, revoke, invalidation, Room survival, outbox survival, the D-05 fake-clock boundary, cancel-before-purge, purge-after-boundary, no cross-account leakage, PUSH_PROVIDER = NONE, no M4 attachment modification, no A9 work) and produce the M5 report.  (depends: TASK-07)

## 4. Boundaries
Allowed paths:
  - KeepLab-Relay/backend/src/main/kotlin/com/keeplab/backend/auth/
  - KeepLab-Relay/backend/src/main/kotlin/com/keeplab/backend/account/
  - KeepLab-Relay/backend/src/main/kotlin/com/keeplab/backend/sync/
  - KeepLab-Relay/backend/src/main/kotlin/com/keeplab/backend/routes/
  - KeepLab-Relay/backend/src/main/kotlin/com/keeplab/backend/Application.kt
  - KeepLab-Relay/backend/src/main/kotlin/com/keeplab/backend/BackendServices.kt
  - KeepLab-Relay/backend/src/main/resources/db/migration/
  - KeepLab-Relay/backend/src/test/
  - KeepLab-Relay/app/src/main/java/com/keeplab/app/data/auth/
  - KeepLab-Relay/app/src/main/java/com/keeplab/app/data/sync/
  - KeepLab-Relay/app/src/main/java/com/keeplab/app/data/remote/
  - KeepLab-Relay/app/src/main/java/com/keeplab/app/data/local/
  - KeepLab-Relay/app/src/main/java/com/keeplab/app/data/NoteRepository.kt
  - KeepLab-Relay/app/src/main/java/com/keeplab/app/model/
  - KeepLab-Relay/app/src/main/java/com/keeplab/app/di/
  - KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/settings/
  - KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/auth/
  - KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/navigation/
  - KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/conflict/
  - KeepLab-Relay/app/src/main/java/com/keeplab/app/KeepLabApplication.kt
  - KeepLab-Relay/app/src/main/java/com/keeplab/app/MainActivity.kt
  - KeepLab-Relay/app/src/test/
  - KeepLab-Relay/app/src/androidTest/
  - Google-Android-Agent-Development-Stack/reports/KEEPLAB-M5-A8-EXECUTION.md
  - Google-Android-Agent-Development-Stack/reports/KEEPLAB-M5-HUMAN-DECISIONS.md
  - Google-Android-Agent-Development-Stack/reports/KEEPLAB-AUTH-SYNC-HUMAN-DECISIONS.md
  - Google-Android-Agent-Development-Stack/reports/KEEPLAB-AUTH-SYNC-DECISION-REGISTER.md
  - Google-Android-Agent-Development-Stack/reports/KEEPLAB-AUTH-SYNC-IMPLEMENTATION-ROADMAP.md
  - Google-Android-Agent-Development-Stack/reports/KEEPLAB-MINOR-BACKLOG.md
  - Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/keeplab-m5-a8/
Forbidden paths:
  - Google-Android-Agent-Development-Stack/specification/
  - Google-Android-Agent-Development-Stack/verification/
  - Google-Android-Agent-Development-Stack/verification-benchmark/
  - Google-Android-Agent-Development-Stack/evaluation/
  - Google-Android-Agent-Development-Stack/orchestration/hermes/bridge/
  - Google-Android-Agent-Development-Stack/orchestration/hermes/evaluation_adapter/
  - Google-Android-Agent-Development-Stack/orchestration/hermes/HERMES-LOCK.json
  - Google-Android-Agent-Development-Stack/.hermes.md
  - Google-Android-Agent-Development-Stack/reports/contracts/
  - KeepLab-Relay/MISSION.md
  - KeepLab-Relay/FACTORY_RULES.md
  - KeepLab-Relay/specs/
  - KeepLab-Relay/verification/
  - KeepLab-Relay/harness/
  - KeepLab-Relay/app/src/main/java/com/keeplab/app/data/attachment/
  - KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/attachment/
  - KeepLab-Relay/app/src/main/res/
  - KeepLab-Relay/app/src/benchmark/
  - KeepLab-Relay/app/schemas/
  - KeepLab-Relay/app/build.gradle.kts
  - KeepLab-Relay/build.gradle.kts
  - KeepLab-Relay/settings.gradle.kts
  - KeepLab-Relay/gradle/
  - KeepLab-Relay/gradle.properties
  - KeepLab-Relay/gradlew
  - KeepLab-Relay/gradlew.bat
  - KeepLab-Relay/firebase/
  - KeepLab-Relay/cloud/
  - KeepLab-Relay/infra/
  - KeepLab-Relay-evidence/
  - Testapp/
  - PowerAi/
Frozen decisions (do not reopen): DEC-001, DEC-002, DEC-003, DEC-004, DEC-005, DEC-006, DEC-007, DEC-008.

## 5. If the contract is wrong
If a contract fact contradicts the source, a required file is missing, an assumption is
wrong, an acceptance is impossible, or a boundary is unsafe:
  STOP → emit `CONTRACT_DEVIATION` with evidence. Do NOT silently redesign.

## 6. Verify and hand off
1. Run the targeted tests named in `tasks.md`.
2. Build the Verification Plan (engine `maestro`,
   journey `M5-A8-TWO-DEVICE-JOURNEY`).
3. Run the deterministic Verification Layer exactly once.
4. On PASS: make NO further tool call, search, read, audit, repeated verification or
   exploratory check. Produce the Phase C report in the FINAL ASSISTANT RESPONSE using only
   evidence already collected in this session, emit the compact final task result, and STOP
   immediately.
5. On FAIL: repair only the failed contract item and re-run only the work that repair
   invalidated. Do not repeat unaffected PASS work.

After this session (POST-SESSION observers, not in-session steps):
- `on_session_finalize` / Auto-Finalizer are POST-SESSION observers.
- Do NOT invoke, inspect, wait for, or verify Auto-Finalizer from inside this Hermes session.
- Auto-Finalizer runs only AFTER this Hermes session exits and is NOT an in-session acceptance
  criterion.

## Stop conditions
  - A required write falls outside the enumerated allowed_paths or targets a forbidden path: STOP, CONTRACT_DEVIATION.
  - Implementation genuinely requires a file outside the enumerated surface: STOP, M5_SURFACE_BROADENING_REQUIRED.
  - A genuinely indispensable new dependency is discovered: STOP, M5_DEPENDENCY_DECISION_REQUIRED.
  - Fewer than two usable independent Android device instances exist and no second isolated emulator instance can be supplied: STOP, A8_DEVICE_PAIR_UNAVAILABLE; M5 is NOT reported PASS.
  - Any push provider, FCM, Firebase, Google services or vendor push dependency would be required: STOP, D11_VIOLATION.
  - Satisfying M5 would require redesigning the A6 conflict policy, the A5 retry/outbox policy, the A7 attachment architecture or any frozen decision: STOP, CONTRACT_DEVIATION (frozen decision reopening is forbidden).
  - Any step would delete, reset or reassign Android local Room data or the durable outbox because of a remote revoke, disable, deletion-pending or purge: STOP, LOCAL_DATA_DESTRUCTION_FORBIDDEN.
  - Satisfying M5 would require modifying specification/, verification/, evaluation/, orchestration/hermes/bridge/, orchestration/hermes/evaluation_adapter/, HERMES-LOCK.json, .hermes.md, reports/contracts/, or the ~/.hermes profile: STOP, ABSOLUTE_BLOCK_VIOLATION.
