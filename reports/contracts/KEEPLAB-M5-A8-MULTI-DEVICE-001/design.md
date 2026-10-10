# Implementation Design — KeepLab M5 = A8 Multi-Device Hardening

## Architecture

M5 adds no new product architecture and no new dependency. It extends the existing seams:

- **Backend auth/session seam (A3).** `auth/AuthService.kt` already owns register/login/refresh
  rotation/revoke and derives identity only from the signed access JWT
  (`authenticate(accessToken)` checks the token, resolves the session, and refuses a revoked
  session). `auth/AuthStore.kt` is the persistence port with `sessionsForUser`, `revokeSession`,
  `revokeAllSessions`; `auth/AuthModels.kt` already models `SessionRecord`, `RefreshState`,
  `AuthenticatedPrincipal`, `SessionView`. `routes/AuthRoutes.kt` already exposes
  `GET /v1/auth/sessions`, `DELETE /v1/auth/sessions/{sessionId}` and
  `POST /v1/auth/sessions/{sessionId}/revoke`. M5 extends these seams with an
  installation-distinguishing session identity and the account lifecycle state; it does not replace
  them.
- **Backend account seam (new, `auth/` + `account/`).** A new account-lifecycle component owned by
  the `account/` package expresses `ACTIVE`, `DISABLED`, `DELETION_PENDING` and `PURGED`, with
  `deletion_requested_at` and `purge_after`, and it is consulted by the same `authenticate` seam so
  every authenticated path (sync, attachment, session list, revoke) observes disable/deletion.
- **Backend sync seam (A4/A6).** `sync/SyncService.kt` authorizes through
  `auth.authenticate(accessToken)` and applies mutations against the server revision authority in
  `sync/SyncStore.kt`; `routes/SyncRoutes.kt` already returns the authoritative `409` conflict body.
  M5 only requires that a revoked/disabled account is refused here.
- **Android auth seam (A3).** `data/auth/SessionManager.kt` owns the one active account and its
  encrypted credentials via `data/auth/SecureSessionStore.kt`; `AuthRepository.requireAccessToken`
  already yields a non-destructive `AccessTokenOutcome.AuthRequired`.
  `data/auth/DeviceLabelProvider.kt` is the existing label seam. M5 adds a KeepLab-generated
  installation identity persisted app-privately, and a session-list/revoke surface.
- **Android sync seam (A4/A5/A6).** `data/sync/SyncEngine.kt` already returns
  `SyncRunResult.AUTH_REQUIRED` without touching Room or the outbox, and
  `data/sync/ConflictResolver.kt` owns A6 resolution. M5 consumes these as frozen.
- **UI seam (A3/A6).** `ui/settings/SettingsScreen.kt` is the account area and `ui/conflict/` the
  A6 surface; `ui/auth/` the credential surface.

What is REUSED and must not be rebuilt: the A3 session/refresh-rotation model, the A4 sync
engine + outbox + checkpoint, the A5 retry policy, the A6 per-field conflict policy, the A7
attachment architecture, the Room SSOT invariant and the `AUTH_REQUIRED` non-destructive rule.

**D-11 boundary.** Correctness is pull/delta based. No provider abstraction implementation is
required in M5; only the guarantee that A8 passes with `PUSH_PROVIDER = NONE`.

**D-05 boundary.** Account lifecycle is strictly separate from the Trash lifecycle (D-06) and from
the sync tombstone. Purge is a deterministic service boundary invoked with an injected clock; no
production scheduler is built.

## Data Flow

1. **Installation identity.** On first run a KeepLab-owned installation identity is generated and
   persisted app-privately (never IMEI/serial/Android ID-as-global-identity/advertising ID/phone
   number). It is presented at login as the session's installation identity and returned in the
   session list.
2. **Two devices, one account.** Device A and Device B each authenticate independently and each
   hold their own session (own installation identity, own Room database, own secure session store,
   own app process).
3. **Propagation.** A writes → the server accepts and advances the entity revision → B's pull
   (`GET /v1/sync/changes?since=<cursor>`) returns the change → B applies it into Room in one
   transaction and advances its checkpoint. The reverse holds identically.
4. **Real concurrency.** A and B both hold base revision N; both push. The first is applied and the
   revision advances; the second is answered `409 REVISION_CONFLICT` with the authoritative body,
   and the client records a persisted conflict whose resolution follows the frozen A6 policy.
5. **Session list / revoke.** A lists sessions, revokes B's session; the server marks B's session
   revoked. B's next authenticated request, refresh or sync is refused (access token session check,
   refresh rotation refused, sync `AUTH_REQUIRED`); B's Room rows, conflicts and outbox are
   untouched and B can authenticate again.
6. **Account disable / delete.** A disable makes every session unusable and leaves local data
   intact. A deletion request moves `ACTIVE → DELETION_PENDING`, revokes all sessions immediately
   and blocks normal sync writes; cancellation inside the grace window re-authenticates with the
   existing credential system and restores `ACTIVE`; after `purge_after = deletion_requested_at +
   30 days` the deterministic purge boundary permanently deletes the server account data.
7. **Verification.** One combined deterministic verification pass (backend tests, Android JVM
   tests, two-client backend integration, the real two-device journey) then one M5 report.

## File Structure Plan

**MUST TOUCH (enumerated surface)**

| Area | Path | Expected change |
| --- | --- | --- |
| backend auth | `KeepLab-Relay/backend/src/main/kotlin/com/keeplab/backend/auth/` | session/device/installation identity; disabled-state refusal in the authenticate seam |
| backend account | `KeepLab-Relay/backend/src/main/kotlin/com/keeplab/backend/account/` | account lifecycle state machine, deletion grace, cancellation, purge boundary |
| backend sync | `KeepLab-Relay/backend/src/main/kotlin/com/keeplab/backend/sync/` | refuse writes while disabled/deletion-pending |
| backend routes | `KeepLab-Relay/backend/src/main/kotlin/com/keeplab/backend/routes/` | session list/revoke/account lifecycle endpoints |
| backend wiring | `.../backend/Application.kt`, `.../backend/BackendServices.kt` | wire the account component |
| backend schema | `KeepLab-Relay/backend/src/main/resources/db/migration/` | new Flyway migration(s) after V4 |
| backend tests | `KeepLab-Relay/backend/src/test/` | new A8 tests |
| android auth | `KeepLab-Relay/app/src/main/java/com/keeplab/app/data/auth/` | installation identity, session list/revoke, session-invalid state |
| android sync/remote/local | `.../data/sync/`, `.../data/remote/`, `.../data/local/` | session/account API client, local lifecycle state, Room schema bump |
| android repo/model/di | `.../data/NoteRepository.kt`, `.../model/`, `.../di/` | wiring only where genuinely required |
| android UI | `.../ui/settings/`, `.../ui/auth/`, `.../ui/navigation/`, `.../ui/conflict/` | session list, revoke, account lifecycle, session-invalid state |
| android entry points | `.../KeepLabApplication.kt`, `.../MainActivity.kt` | only if genuinely required |
| android tests | `KeepLab-Relay/app/src/test/`, `KeepLab-Relay/app/src/androidTest/` | new A8 tests |
| reports | `Google-Android-Agent-Development-Stack/reports/KEEPLAB-M5-A8-EXECUTION.md` etc. | the M5 report and decision records |
| evidence | `Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/keeplab-m5-a8/` | M5 evidence |

**MUST NOT TOUCH**

- `KeepLab-Relay/app/src/main/java/com/keeplab/app/data/attachment/` and `.../ui/attachment/` — M4 is
  CLOSED and is not modified.
- `KeepLab-Relay/app/src/main/res/`, `.../app/src/benchmark/`, `.../app/schemas/` — unchanged.
- `KeepLab-Relay/app/build.gradle.kts`, `KeepLab-Relay/build.gradle.kts`,
  `KeepLab-Relay/settings.gradle.kts`, `KeepLab-Relay/gradle/`, `gradle.properties`, `gradlew`,
  `gradlew.bat` — no dependency change is authorized and none is expected.
- `KeepLab-Relay/MISSION.md`, `FACTORY_RULES.md`, `specs/`, `verification/`, `harness/`,
  `firebase/`, `cloud/`, `infra/` — unchanged.
- `Google-Android-Agent-Development-Stack/specification/`, `verification/`,
  `verification-benchmark/`, `evaluation/`, `orchestration/hermes/bridge/`,
  `orchestration/hermes/evaluation_adapter/`, `orchestration/hermes/HERMES-LOCK.json`,
  `.hermes.md`, `reports/contracts/` — unchanged.
- `KeepLab-Relay-evidence/`, `Testapp/`, `PowerAi/` — out of scope.
- `~/.hermes` profile and configuration — never touched.

## Selector Contract

| name | state it identifies |
| --- | --- |
| `m5_session_list` | the account session list is rendered |
| `m5_session_row_current` | the session list marks the current installation |
| `m5_session_revoke_action` | a per-session revoke affordance is available |
| `m5_auth_required_banner` | the client is in the non-destructive session-invalid / AUTH_REQUIRED state |
| `m5_note_list` | the note list renders local Room state |
| `m5_note_editor_title` | the note title field of the editor |
| `m5_conflict_banner` | a persisted conflict is surfaced for resolution |
| `m5_account_delete_request` | the deliberate deletion-request affordance |
| `m5_account_delete_pending` | the account is shown as DELETION_PENDING with the grace window |
| `m5_account_delete_cancel` | the in-grace cancellation affordance |
| `m5_sync_status` | the manual sync / sync-status affordance |

## Contract Metadata

```json
{
  "decisions": [
    {
      "id": "DEC-001",
      "statement": "D-05 = ACCOUNT_DELETE_GRACE_30_DAYS is frozen exactly as approved on 2026-10-07: request enters DELETION_PENDING, access is disabled, all sessions are revoked immediately, no new normal sync write is accepted, purge_after = deletion_requested_at + 30 days under server clock authority, cancellation inside the grace window uses the EXISTING verified credential system and restores ACTIVE without resurrecting purged data, and expiry reaches an explicit deterministic purge boundary.",
      "rationale": "This is a human project-owner decision, not a model choice. Re-asking or reinterpreting it would reopen a frozen decision; consuming it as stated keeps the account lifecycle distinct from the Trash lifecycle (D-06) and from the sync tombstone."
    },
    {
      "id": "DEC-002",
      "statement": "D-11 = NO_PUSH_PROVIDER_IN_A8_CORRECTNESS_PATH is frozen: no FCM, Firebase, Google services or vendor push dependency; correctness stays pull/delta based; any future push must sit behind a provider abstraction; A8 PASS must be possible with PUSH_PROVIDER = NONE.",
      "rationale": "The approved decision makes push a future latency optimization only. Making correctness depend on push would invert the approved posture and would add a forbidden dependency."
    },
    {
      "id": "DEC-003",
      "statement": "M5 consumes the existing A6 conflict semantics unchanged and never redesigns them; it only exercises them under real two-client concurrency.",
      "rationale": "A6 is frozen and closed. Redesigning the conflict policy inside a multi-device milestone would invalidate M3 evidence and reopen a completed milestone."
    },
    {
      "id": "DEC-004",
      "statement": "The final M5 journey must use two real, independently addressable Android device instances on one account; backend two-client integration tests never replace it, and an unavailable pair yields A8_DEVICE_PAIR_UNAVAILABLE with no PASS.",
      "rationale": "Multi-device correctness is exactly the property under test; a single-object mock would silently downgrade the milestone and produce a false PASS."
    },
    {
      "id": "DEC-005",
      "statement": "A privacy-bounded installation identity generated and persisted by KeepLab itself is used to distinguish independent installations; IMEI, hardware serial, Android ID as a global tracking identity, advertising ID and phone number are never used.",
      "rationale": "Sessions must be distinguishable without device fingerprinting or invasive identifiers, and without changing the credential architecture."
    },
    {
      "id": "DEC-006",
      "statement": "Purge is a deterministic service boundary exercised with an injected/fake clock; no production scheduler and no cloud infrastructure is built or provisioned in M5.",
      "rationale": "A 30-real-day test is not runnable and a production scheduler is out of scope, so the boundary is proven deterministically against the existing development backend/test environment."
    },
    {
      "id": "DEC-007",
      "statement": "No Gradle dependency change is authorized; the existing implementation seams are used, and a genuinely indispensable dependency is STOP = M5_DEPENDENCY_DECISION_REQUIRED.",
      "rationale": "Every needed capability (JWT session auth, Room, WorkManager, Ktor client, Flyway) already exists; a new dependency would enlarge the change set and require a separate human decision."
    },
    {
      "id": "DEC-008",
      "statement": "The authorized write surface is exactly the enumerated M5 backend, Android, report and evidence paths, with no broad prefix; a file genuinely outside it is STOP = M5_SURFACE_BROADENING_REQUIRED.",
      "rationale": "The Contract Guard fails closed on unclassified paths, and a broad prefix would re-authorize frozen areas such as the compiler, the verification layer and the contract packages."
    }
  ],
  "assumptions": [
    {
      "id": "ASM-001",
      "statement": "The existing development backend/test environment is sufficient to run the two-client integration and the two-device journey; no cloud provisioning is needed."
    },
    {
      "id": "ASM-002",
      "statement": "The existing one unique WorkManager `note_sync` pipeline and the existing `attachment_sync` separation remain the only sync executors; M5 adds no second pipeline concept."
    },
    {
      "id": "ASM-003",
      "statement": "Two independent Android device instances can be obtained from the existing bounded project tooling (two ADB-visible emulators, one physical device plus one emulator, or two physical devices)."
    },
    {
      "id": "ASM-004",
      "statement": "The A3 refresh-rotation model (single-use, retry-safe, reuse detection) is reused as-is for session validity so that revocation invalidates both access and refresh capability."
    }
  ],
  "data_change": {
    "schema_version_current": 6,
    "schema_version_target": 7,
    "migration_required": false,
    "notes": "Android Room moves 6 -> 7 by a direct experimental bump (project data is disposable; DEV_DATABASE_RESET_REQUIRED = YES; exportSchema stays false; no migration chain is authored), adding only the local installation/session identity and account lifecycle state M5 needs. On the backend, new Flyway migrations after V4 add the session installation identity and the account lifecycle (state, deletion_requested_at, purge_after); no production compatibility chain is authored."
  },
  "ui_change": {
    "surfaces": [
      "ui/settings (session list, per-session revoke, account disable/deletion affordances)",
      "ui/auth (re-authentication used for in-grace cancellation)",
      "ui/navigation (routes for the session list and the account lifecycle states)",
      "ui/conflict (consumed unchanged; entry point only)"
    ],
    "selectors_added": [
      "m5_session_list",
      "m5_session_row_current",
      "m5_session_revoke_action",
      "m5_auth_required_banner",
      "m5_note_list",
      "m5_note_editor_title",
      "m5_conflict_banner",
      "m5_account_delete_request",
      "m5_account_delete_pending",
      "m5_account_delete_cancel",
      "m5_sync_status"
    ]
  },
  "selector_contract": [
    {
      "name": "m5_session_list",
      "compose_test_tag": "m5_session_list",
      "uiautomator": "By.res(\"m5_session_list\")",
      "state": "the account session list is rendered for the signed-in account",
      "required": true
    },
    {
      "name": "m5_session_row_current",
      "compose_test_tag": "m5_session_row_current",
      "uiautomator": "By.res(\"m5_session_row_current\")",
      "state": "the session list marks the session of the current installation",
      "required": true
    },
    {
      "name": "m5_session_revoke_action",
      "compose_test_tag": "m5_session_revoke_action",
      "uiautomator": "By.res(\"m5_session_revoke_action\")",
      "state": "a per-session revoke affordance is available for another session",
      "required": true
    },
    {
      "name": "m5_auth_required_banner",
      "compose_test_tag": "m5_auth_required_banner",
      "uiautomator": "By.res(\"m5_auth_required_banner\")",
      "state": "the client is in the non-destructive session-invalid / AUTH_REQUIRED state",
      "required": true
    },
    {
      "name": "m5_note_list",
      "compose_test_tag": "m5_note_list",
      "uiautomator": "By.res(\"m5_note_list\")",
      "state": "the note list renders local Room state",
      "required": true
    },
    {
      "name": "m5_note_editor_title",
      "compose_test_tag": "m5_note_editor_title",
      "uiautomator": "By.res(\"m5_note_editor_title\")",
      "state": "the note title field of the editor",
      "required": true
    },
    {
      "name": "m5_conflict_banner",
      "compose_test_tag": "m5_conflict_banner",
      "uiautomator": "By.res(\"m5_conflict_banner\")",
      "state": "a persisted conflict is surfaced for resolution",
      "required": true
    },
    {
      "name": "m5_account_delete_request",
      "compose_test_tag": "m5_account_delete_request",
      "uiautomator": "By.res(\"m5_account_delete_request\")",
      "state": "the deliberate authenticated deletion-request affordance",
      "required": true
    },
    {
      "name": "m5_account_delete_pending",
      "compose_test_tag": "m5_account_delete_pending",
      "uiautomator": "By.res(\"m5_account_delete_pending\")",
      "state": "the account is shown as DELETION_PENDING with the grace window",
      "required": true
    },
    {
      "name": "m5_account_delete_cancel",
      "compose_test_tag": "m5_account_delete_cancel",
      "uiautomator": "By.res(\"m5_account_delete_cancel\")",
      "state": "the in-grace cancellation affordance",
      "required": true
    },
    {
      "name": "m5_sync_status",
      "compose_test_tag": "m5_sync_status",
      "uiautomator": "By.res(\"m5_sync_status\")",
      "state": "the manual sync / sync-status affordance",
      "required": true
    }
  ],
  "stop_conditions": [
    "A required write falls outside the enumerated allowed_paths or targets a forbidden path: STOP, CONTRACT_DEVIATION.",
    "Implementation genuinely requires a file outside the enumerated surface: STOP, M5_SURFACE_BROADENING_REQUIRED.",
    "A genuinely indispensable new dependency is discovered: STOP, M5_DEPENDENCY_DECISION_REQUIRED.",
    "Fewer than two usable independent Android device instances exist and no second isolated emulator instance can be supplied: STOP, A8_DEVICE_PAIR_UNAVAILABLE; M5 is NOT reported PASS.",
    "Any push provider, FCM, Firebase, Google services or vendor push dependency would be required: STOP, D11_VIOLATION.",
    "Satisfying M5 would require redesigning the A6 conflict policy, the A5 retry/outbox policy, the A7 attachment architecture or any frozen decision: STOP, CONTRACT_DEVIATION (frozen decision reopening is forbidden).",
    "Any step would delete, reset or reassign Android local Room data or the durable outbox because of a remote revoke, disable, deletion-pending or purge: STOP, LOCAL_DATA_DESTRUCTION_FORBIDDEN.",
    "Satisfying M5 would require modifying specification/, verification/, evaluation/, orchestration/hermes/bridge/, orchestration/hermes/evaluation_adapter/, HERMES-LOCK.json, .hermes.md, reports/contracts/, or the ~/.hermes profile: STOP, ABSOLUTE_BLOCK_VIOLATION."
  ]
}
```
