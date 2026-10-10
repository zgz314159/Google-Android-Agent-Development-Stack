# KEEPLAB-M2 acceptance — AC-M2-001 … AC-M2-025

**Contract:** `KEEPLAB-M2-AUTH-SINGLE-USER-SYNC-001` (unmodified, `READ_ONLY_INPUT`)
**Milestone:** `M2` = `A3_AUTH_SESSION` + `A4_SINGLE_USER_SYNC` — one contract, one session, one verification pass
**Date:** 2026-10-06 · **Device:** NOT_USED · **Cloud:** NOT_PROVISIONED
**Data stage:** `EXPERIMENTAL`, `DISPOSABLE_TEST_DATA`, `DEV_DATABASE_RESET_REQUIRED = YES`

Evidence locations are given as paths; backend tests are in
`KeepLab-Relay/backend/src/test/kotlin/com/keeplab/backend/`, Android unit tests in
`KeepLab-Relay/app/src/test/java/com/keeplab/app/`.

---

## AC-M2-001 — D-01 honoured, no forbidden identity

`PASS`

- Backend: `auth/AuthService.kt` (register, required verification, password login, password reset),
  `routes/AuthRoutes.kt` (`/v1/auth/*`).
- Android: `ui/auth/AuthViewModel.kt` + `ui/auth/AuthScreen.kt` (sign in, register, verify email,
  forgot/reset password); `data/auth/AuthRepository.kt`.
- Scan: no `google`, `firebase`, `FirebaseAuth`, `GoogleSignIn`, `CredentialManager`,
  `google-services`, `play-services-auth` reference exists anywhere in backend or `app/src`. No
  phone auth, no OAuth social login, no passkey.
- Tests: `AuthServiceTest`, `AuthRoutesTest`, `M2AuthSessionTest`.

## AC-M2-002 — A3 backend schema exists

`PASS`

- `backend/src/main/resources/db/migration/V2__auth_schema.sql` (after V1): `users`,
  `email_verification_challenges`, `password_reset_challenges`, `sessions`, `refresh_states`.
- Nothing beyond A3: no notes, no sync tables, no account-deletion or retention structures.

## AC-M2-003 — password KDF and code verifiers

`PASS`

- `auth/crypto/PasswordHasher.kt`: **Argon2id** via BouncyCastle `bcprov-jdk18on:1.83` (maintained,
  vetted; no invented hashing). Parameters recorded in the M2 report: Argon2id v=19, t=3 iterations,
  m=64 MiB, p=1, 16-byte fresh random salt per password, 32-byte output, PHC-encoded.
  `PASSWORD_KDF_FALLBACK` not used.
- `auth/crypto/PepperedHasher.kt`: codes and refresh tokens stored only as peppered HMAC-SHA256
  verifiers, constant-time compare. TTL 600 s, max 5 attempts, 60 s resend cooldown
  (`AuthService.CODE_TTL_SECONDS` / `MAX_CODE_ATTEMPTS` / `RESEND_COOLDOWN_SECONDS`).
- `auth/EmailSender.kt`: `EmailSender` port, `RecordingEmailSender` (tests),
  `ConsoleDevelopmentEmailSender` (development only), `NoopEmailSender` (default/production).
- Tests: `AuthServiceTest` (`no plaintext password, code or refresh token is ever stored`, attempt
  bounding, cooldown).

## AC-M2-004 — A3 auth API works

`PASS`

- `routes/AuthRoutes.kt`: register, verify-email, login, refresh, logout, password-reset
  request/confirm, `GET /v1/auth/sessions`, `DELETE /v1/auth/sessions/{sessionId}`.
- Tests: `AuthServiceTest` (register/verify/unverified rejection/wrong password/reset/logout/
  per-session revoke/session list) and `AuthRoutesTest` (the same over real in-process HTTP).

## AC-M2-005 — JWT access token

`PASS`

- `auth/JwtService.kt`: HS256, signing key from configuration only.
- Claims `sub`, `sid`, `iat`, `exp`, `iss`, `aud` asserted in
  `AuthServiceTest.the access token carries the minimum claims and rejects tampering` (tampered
  signature, tampered payload, foreign key and foreign issuer are all refused).
- Identity is server-derived: `SyncRoutesTest.a request account id is never authority` sends a
  foreign `accountId` and proves it changes nothing.

## AC-M2-006 — opaque retry-safe rotating refresh token

`PASS`

- Opaque 32-byte token (`PepperedHasher.randomToken`), stored only as a verifier.
- Rotation re-derives the child deterministically
  (`PepperedHasher.deriveChildToken(parent, requestId)`), so no rotated secret is retained in the
  replay record.
- Tests (`AuthServiceTest`): normal refresh rotates; same old token + same `refresh_request_id`
  returns the same child and the same expiry with `generation == 1`; the same old token with a
  **different** request id is reuse → the single affected session is revoked and no second child is
  minted; revoked session and expired refresh are rejected; a fresh log-in still works afterwards
  (no destructive account loss). No plaintext token is stored (`no plaintext … is ever stored`).

## AC-M2-007 — Android session support and secure storage

`PASS`

- `data/auth/SecureSessionStore.kt` + `data/auth/AndroidKeystoreSecretCipher.kt`: AES-GCM under a key
  held in the **Android Keystore**, ciphertext-only blob in app-private storage, no plaintext
  fallback.
- `data/auth/AuthRepository.kt` + `SessionManager`: register/verify/login/refresh/logout/session state.
- Tests: `M2AuthSessionTest` — round-trip, on-disk bytes contain no token/email, an invalidated key
  degrades to "signed out" instead of crashing, `clear()` removes the file.
- Credential Manager is **not** integrated; a plain email/password form satisfies A3.
- No database-encryption claim anywhere; no SQLCipher-style dependency.

## AC-M2-008 — auth UX reachable and login-optional app

`PASS`

- `ui/settings/SettingsScreen.kt` + `SettingsViewModel` ("Account" area), reachable from the Home
  overflow menu (`HomeScreen` → `NavigationKeys.Settings`); `ui/auth/AuthScreen.kt` covers sign in /
  register / verify email / forgot / reset; signed-in state and Sign out live in the same area.
- No pre-existing navigation was refactored: the new entries are additive and Home keeps its
  existing callbacks.
- The app remains fully usable without an account (nothing gates note creation).

## AC-M2-009 — D-04 sign-out behaviour

`PASS`

- `SessionManager.onSignedOut()` clears credentials + active account and touches no Room table;
  `AuthRepository.logout()` attempts the remote revoke and clears locally regardless.
- Tests: `M2LocalModelTest.sign-out clears credentials and the active account but preserves Room rows
  and the outbox`; `M2AuthSessionTest.sign-out revokes the session remotely and always clears the
  local credentials` (including a transport failure).
- `AUTH_REQUIRED` deletes nothing: `M2SyncEngineTest.AUTH_REQUIRED is a signal, never a delete`.

## AC-M2-010 — LOCAL_ONLY safety

`PASS`

- Tests (`M2LocalModelTest`): a pre-login note stays `LOCAL_ONLY`/`accountId = NULL` after login and
  is never uploaded or reassigned; a note created signed out is `LOCAL_ONLY` with no outbox row; a
  note created signed in is account-scoped `SYNC_PENDING` with exactly one mutation.
- `M2SyncEngineTest.a signed-out sync is a no-op that never pushes a LOCAL_ONLY note`.

## AC-M2-011 — local Room model for one-account sync

`PASS`

- `KeepLabDatabase` version 3 → **4** by direct experimental bump; `exportSchema` stays false (no
  `app/schemas`); no migration chain authored; `DEV_DATABASE_RESET_REQUIRED = YES` recorded.
- `OutboxEntity`, `ClientCheckpointEntity`; stable `clientUuid` on checklist items and labels
  (UNIQUE, fresh-row default) alongside the retained Long primary keys; account/state columns and the
  indexes that A4 needs.
- A1 properties preserved: `clientUuid` UNIQUE with a fresh-row default, nullable `accountId`, the
  seven `SyncState` values, and Trash ≠ tombstone structurally.

## AC-M2-012 — persistent outbox in the mutation transaction

`PASS`

- `OutboxEntity` carries `mutationId`, `accountId`, target client UUID, entity type, mutation kind,
  `baseRevision`, captured payload and `createdAt`, plus only `attemptCount`/`lastErrorCode`.
- `DefaultNoteRepository` performs every mutation through `LocalStore.writeAtomically`
  (`RoomLocalStore` = one Room transaction).
- Tests: `M2LocalModelTest.the entity write and its outbox row are one transaction` (an outbox write
  failure leaves no entity row); `an outbox row is removed only on a confirmed push`;
  `AUTH_REQUIRED` leaves the outbox intact (`M2SyncEngineTest`).
- Push sends the captured payload: `M2SyncEngineTest.push sends the captured payload rather than the
  current row`, `M2LocalModelTest.cover of every product edit produces the matching mutation kind`.

## AC-M2-013 — A4 backend sync schema

`PASS`

- `V3__sync_schema.sql`: `server_entities` (notes/checklist items/labels/note-label relations),
  `account_revisions`, `sync_tombstones`, `change_log` (cursor), `mutation_dedupe`.
- Source inspection: no attachment, object-storage, collaboration, multi-account or CRDT code
  exists in the backend.

## AC-M2-014 — sync API authenticated by JWT only

`PASS`

- `routes/SyncRoutes.kt`: `POST /v1/sync/mutations`, `GET /v1/sync/changes?since=…`,
  `GET /v1/sync/checkpoint`.
- `SyncService` derives the account from the authenticated subject only.
- Tests: `SyncRoutesTest.every sync endpoint requires a bearer token and answers 401 without one`;
  `a request account id is never authority`; `an account only ever reads its own change log`;
  `SyncServiceTest.accounts are isolated, so one account never sees or changes another account's
  data`.

## AC-M2-015 — atomic mutation dedupe

`PASS`

- `SyncStore.applyMutation` performs the dedupe claim, revision check, revision bump, entity upsert,
  tombstone write, change-log append and dedupe record as **one atomic operation**
  (`InMemorySyncStore` under one lock; `JdbcSyncStore` in one transaction with rollback on conflict).
- Tests: `SyncServiceTest.a duplicate mutation id returns the recorded result and never applies
  twice` (one apply, one revision increment, one change-log entry: asserted via
  `changeCount`/`dedupeCount`/`checkpoint`); `SyncRoutesTest` proves the same over HTTP.
- `LIVE_POSTGRES_CRASH_INJECTION = SKIPPED_TOOL_UNAVAILABLE` — no container runtime and no `psql` on
  this host; the transaction design was not weakened.

## AC-M2-016 — revision authority and conflict state

`PASS`

- Every accepted mutation advances the per-account server revision
  (`SyncServiceTest.an authenticated mutation applies once and advances the server revision`).
- A stale `baseRevision` yields `409 REVISION_CONFLICT` and leaves **no claim and no change entry**
  (`SyncServiceTest.a stale base revision is a 409 conflict and leaves no claim or change behind`,
  `SyncRoutesTest` over HTTP).
- The client maps 409 to `CONFLICT` and stops destructive overwrite
  (`M2SyncEngineTest.a stale revision marks the entity CONFLICT and never overwrites destructively`).
- No client wall clock participates in ordering; no conflict-resolution UI exists.

## AC-M2-017 — Trash is not a tombstone and nothing resurrects

`PASS`

- Trashing writes product state only: `M2LocalModelTest.trashing an account-scoped note never writes
  the tombstone and queues ordinary state` (`deletedAt` stays null).
- A remote final deletion becomes a local tombstone and is not resurrected:
  `M2SyncEngineTest.a remote deletion tombstones locally and never resurrects` (including a stale
  older change for the same note).
- No automatic Trash expiration or tombstone purge exists; D-06 stays pending.

## AC-M2-018 — checkpoint discipline

`PASS`

- `SyncDao`/`ClientCheckpointEntity` store the client checkpoint; `GET /v1/sync/checkpoint` reports
  the server cursor — different authorities.
- The page apply and the checkpoint advance happen in one transaction
  (`SyncEngine.pullChanges`).
- Tests: `M2SyncEngineTest.a failed delta leaves the checkpoint exactly where it was` (the same page
  is then applied from the same checkpoint); `a checkpoint written by one account never advances
  another account`.

## AC-M2-019 — 404 is non-destructive

`PASS`

- `SyncEngine.pushPending` maps 404 to `SYNC_FAILED` and keeps the outbox row; the local note stays.
- Test: `M2SyncEngineTest.a 404 never deletes a live local note`.

## AC-M2-020 — accountId invariant

`PASS`

- `requireAccountForNonLocalState` enforces it at every creation boundary; the outbox builder calls it
  before recording a mutation.
- Tests: `M2LocalModelTest.the accountId invariant holds for every non-local sync state` (all six
  non-local states reject a null account) and `M2SyncEngineTest.an entity is never left in a non-local
  state without an account`.
- Remote-sync rows always carry the account: `M2SyncEngineTest.a pulled page is applied with a
  non-null account`.

## AC-M2-021 — one unique note_sync pipeline

`PASS`

- `data/sync/NoteSyncWork.kt`: one unique name `note_sync`, one policy `ExistingWorkPolicy.KEEP`
  (recorded as the **A4 implementation decision**), `NetworkType.CONNECTED`.
- Tests (`M2SyncPipelineTest`): the name/policy/constraint constants; five triggers all land on the
  same unique name and policy; no `REPLACE`/`APPEND` is ever used.
- No push provider, no FCM, no background push architecture.

## AC-M2-022 — worker flow and error mapping

`PASS`

- `SyncEngine`: ensure a valid session → refresh if necessary → push → handle responses → pull →
  apply → advance the checkpoint on success.
- Tests (`M2SyncEngineTest`): push success; pull success; 409 → `CONFLICT`; 404 keeps the note; a
  generic 5xx is `RETRY_LATER`, never permanent; a transport failure retains everything; one 401 is
  recovered by a refresh; `AUTH_REQUIRED` retains the outbox. Raw server exceptions never reach the
  UI (the engine returns an enum, and `SyncWorker` maps it to a WorkManager result).

## AC-M2-023 — product-data coverage with Room as SSOT

`PASS`

- Covered: note create, title/body edit, archive, pin, colour, Trash state, checklist changes, label
  changes (`M2LocalModelTest.cover of every product edit produces the matching mutation kind`,
  `checklist and label changes are covered and queued for an account-scoped note`).
- The UI reads Room only: `DefaultNoteRepository` observes Room flows, and
  `M2SyncEngineTest.the engine reads and writes Room only, never remote state directly`.
- M2 does not implement automatic Trash retention or account deletion.

## AC-M2-024 — one verification pass, both gates run once

`PASS`

Each gate ran **once**, in one pass, and no re-run followed:

| # | Command | Result |
|---|---|---|
| 1 | `cd /mnt/AndroidDev/Projects/KeepLab-Relay && ./gradlew -p backend test build` | **BUILD SUCCESSFUL** — `evidence/keeplab-m2-auth-single-user-sync/gate-backend.log` |
| 2 | `cd /mnt/AndroidDev/Projects/KeepLab-Relay && ./gradlew :app:testDebugUnitTest :app:assembleDebug` | **BUILD SUCCESSFUL**, debug APK produced — `evidence/keeplab-m2-auth-single-user-sync/gate-android.log` |

No gate failed, so there was no fix, no re-run of a failed task and no re-run of the other side.
Totals for the recorded pass: backend **53 tests / 0 failures / 0 errors**; Android JVM
**116 tests / 0 failures / 0 errors**.

After PASS: no further gate run, no post-PASS review, no second audit.

## AC-M2-025 — boundaries held honestly

`PASS` — see `post-run-proof.json` in the evidence directory: frozen-input before/after hashes, the
scope scan (every changed source file inside `allowed_paths`; nothing touched under
`app/src/main/res/**`, `ui/theme/**`, `ui/common/**`, `androidTest/**`, `benchmark/**`, the root
Gradle files or `reports/contracts/**`), the secret scan, and `backend/.env` absent.
