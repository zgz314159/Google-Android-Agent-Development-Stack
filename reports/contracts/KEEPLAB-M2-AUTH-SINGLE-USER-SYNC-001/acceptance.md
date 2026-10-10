# Acceptance — KEEPLAB-M2-AUTH-SINGLE-USER-SYNC-001

**Contract:** `KEEPLAB-M2-AUTH-SINGLE-USER-SYNC-001`
**Milestone:** `M2` = `A3_AUTH_SESSION` + `A4_SINGLE_USER_SYNC` (one contract, one execution session, one verification pass)
**Date:** 2026-10-06 (CST, UTC+08:00)
**Human authorization:** `HUMAN_PROJECT_OWNER_APPROVAL` 2026-10-06 — D-01 `EMAIL_PASSWORD_VERIFIED` · D-04 `PRESERVE_LOCAL_CACHE` · D-10 `JWT_ACCESS_OPAQUE_ROTATING_REFRESH`
**Project data stage:** `EXPERIMENTAL` — `DISPOSABLE_TEST_DATA` (Android + backend), `OLD_TEST_DB_COMPATIBILITY = NOT_REQUIRED`, `DEV_DATABASE_RESET_REQUIRED = YES`
**Status:** READY (contract package validated; M2 itself is NOT executed)
**Phase state:** A0 READY · A1 PASS · A2 PASS · M2 AUTHORIZED_BY_HUMAN · A5+ NOT_STARTED

## 0. What this package is

A temporary execution contract that authorizes **one later, separate** session to implement the whole
M2 milestone — A3 (email/password auth + session) and then A4 (single-user note sync) — through the
**same unmodified Contract Guard**, inside a bounded write surface. It is **not** an implementation:
no backend code, no Android code and no device work happens in the contract-creation phase.

Execution model (frozen):

```
PLAN ONCE
  -> A3 EXECUTE
  -> A3 LIGHT CHECKPOINT  (records only; NOT a review; the session does NOT stop)
  -> A4 EXECUTE
  -> VERIFY M2 ONCE
  -> PASS = STOP
```

Forbidden inside M2: an A3 contract, an A4 contract, an A3 review, an A4 review, a post-PASS audit.

## 1. Machine-readable semantics

Recorded in `implementation-contract.json` (`milestone`, `frozen_human_decisions`, `a3_scope`,
`a4_scope`, `project_data_stage`, `allowed_paths`, `forbidden_paths`, `verification_intent`,
`stop_conditions`, `failure_rule`, `overhead_rule`) and mirrored here.

| Field | Value |
|---|---|
| `milestone` | `M2` = `A3` + `A4`, one contract, one session, one verification pass |
| `human_decisions` | D-01 / D-04 / D-10 (frozen 2026-10-06) |
| `pending_not_blocking` | D-05, D-06, D-11, D-12, D-13, D-14 |
| `project_data_stage` | `EXPERIMENTAL` (both sides), `DEV_DATABASE_RESET_REQUIRED = YES` |
| `backend_path` | `/mnt/AndroidDev/Projects/KeepLab-Relay/backend/` (PRESENT, created by A2) |
| `backend_build_model` | `INDEPENDENT_GRADLE_PROJECT` — `./gradlew -p backend` |
| `root_android_gradle_modified` | `NO` (required outcome) |
| `android_surface_policy` | `ENUMERATED_NOT_WHOLE_APP` |
| `identity_authority` | KeepLab backend |
| `room` | local SSOT; schema bumped by direct experimental bump; **no encryption claim** |
| `server_revision` | the only conflict authority |
| `mutation_dedupe` | claim + apply + revision + change-log = ONE transaction |
| `device` | `NOT_USED` (M2 is device-free) |
| `cloud` | `NOT_PROVISIONED` (no deployment) |

## 2. Frozen human decisions (do not reopen)

### D-01 — `EMAIL_PASSWORD_VERIFIED`

email + password registration; email verification required; password login; forgot/reset password
supported. Passkey may be added later. Phone login deferred. **Google login forbidden. Firebase Auth
forbidden.** No Google Identity, no Google private API, no OAuth social login.

### D-04 — `PRESERVE_LOCAL_CACHE`

On sign-out: revoke/clear session credentials, remove active-account state, stop account sync,
**preserve** Room data, account-scoped cached notes, the outbox and `LOCAL_ONLY` notes. Signed-out UI
must keep showing `LOCAL_ONLY` data. Rows of a signed-out account stay stored, are never treated as
another account's data and never sync; re-login to the same account may resume them.

```
DO NOT CLAIM FULL ROOM DATABASE ENCRYPTION.
No database-encryption feature is authorized.
```

### D-10 — `JWT_ACCESS_OPAQUE_ROTATING_REFRESH`

Access token: JWT, short-lived, default target ≈ 15 minutes, configurable.
Refresh token: opaque, high-entropy, default target ≈ 30 days, configurable.
Refresh secrets are **never** stored plaintext at rest — the server stores a secure verifier/hash form.
Rotation is required and **retry-safe** through `refresh_request_id`: a lost response followed by the
same retry must recover the same rotated result inside a bounded replay window. Never: mint multiple
child sessions, treat the request immediately as theft, or destroy account access. If replay state
must retain a secret result, it is encrypted at rest or safely re-derived. Token plaintext never
reaches reports, evidence or logs.

## 3. A3 — backend auth

New PostgreSQL/Flyway development schema for `users`, email verification challenges, password reset
challenges, `sessions`, refresh-token/refresh-rotation state, and only what A3 truly requires.

- identity: server-generated UUID; email normalized and unique
- password hashing: a modern password KDF, **Argon2id preferred**, from a maintained vetted library —
  no invented/custom hashing (a documented fallback KDF is allowed only if Argon2id cannot be resolved)
- email verification: a small deterministic service abstraction; recommended experimental defaults
  6-digit code, TTL 10 minutes, max 5 failed attempts, resend cooldown 60 seconds; only a secure
  verifier/hash is stored
- delivery: an `EmailSender`/`VerificationSender` abstraction, a fake sender in tests, and a
  development-only console sender that is **never** used in production/default mode and never prints a
  verification secret silently; no cloud email service is started

Versioned API namespace `/v1`:

| Route | Behaviour |
|---|---|
| `POST /v1/auth/register` | create an account (email + password) |
| `POST /v1/auth/verify-email` | confirm the email verification code |
| `POST /v1/auth/login` | password credential exchange → session |
| `POST /v1/auth/refresh` | rotate the refresh credential (retry-safe) |
| `POST /v1/auth/logout` | revoke the current session |
| `POST /v1/auth/password-reset/request` | start a password reset |
| `POST /v1/auth/password-reset/confirm` | complete a password reset |
| `GET /v1/auth/sessions` | list sessions |
| `DELETE`/`POST` revoke `/v1/auth/sessions/{sessionId}` | revoke one session |

Password reset revokes existing sessions unless a clearly safer minimal design is already present.
**Account deletion is not implemented.** The final exact HTTP method may follow the existing Ktor
style where behaviour is equivalent.

Access token JWT claims (minimum): `sub` = user/account UUID, `sid` = session UUID, `iat`, `exp`,
`iss`, `aud`. Identity is server-derived; a client-supplied `accountId` is **never** authorization
authority. The signing key comes from environment/config — no source-code secret.

## 4. A3 — Android session and auth UX

- register / verify / login / refresh / logout / session state implemented in the client
- access and refresh material stored **only** in an app-private, **Android Keystore-backed** secure
  session store — never as ordinary plaintext preference values; the Room database is **not** claimed
  to be encrypted
- Credential Manager, if used at all, is **password credential UX only** — no Google ID credential, no
  Firebase, and it is not the identity authority
- KeepLab stays usable **without login**
- the smallest sensible account surface is reachable: Sign in, Register, Verify email,
  Forgot/reset password, signed-in account state, Sign out — integrated through a settings/account
  area (there is no settings screen today; the smallest one is added) rather than redesigning the UI
- unrelated navigation is not refactored
- `AUTH_REQUIRED` must **not** delete local data

Sign-out behaviour (D-04) and the LOCAL_ONLY safety rule are as described in §2 and §5.

## 5. A4 — local model, outbox, sync core

**Room.** Current version 3 → the next clean version by a **direct experimental bump**. No old
development-data migration is required and no migration chain is authored. New/required concepts:
stable UUID for independently synced checklist items, stable UUID for labels if independently synced,
an **outbox** table, a **client sync checkpoint** table, and the minimum indexing required. Local Long
primary keys are **kept** where they remain useful; stable UUIDs are sync identities, not PK
replacements.

**Outbox.** Each mutation carries `mutationId`, `accountId`, the target client UUID, the mutation
kind, `baseRevision`, a payload or deterministic mutation data, and `createdAt`, plus only the minimal
A4 status fields. The entity write and its outbox insert happen in **one local transaction**. A5
machinery (advanced bounded retry, manual retry UX, coalescing, process-death hardening, lost-wakeup
hardening) is **not** built. `AUTH_REQUIRED` leaves the outbox intact.

**Backend sync data.** Notes, checklist items, labels, note-label relations, server revision, sync
tombstone, server change log/cursor and mutation-id dedupe — as new Flyway migrations after V1. No
attachments, no collaboration, no multi-account, no CRDT, no automatic conflict resolution.

**Sync API.** `POST /v1/sync/mutations`, `GET /v1/sync/changes?since=<cursor>`, `GET /v1/sync/checkpoint`.
Authentication comes only from the access JWT; a request `accountId` is never authority.

**Atomic apply.** A duplicate `mutation_id` never applies twice; the dedupe claim and the mutation
application are atomic in the same transaction. First mutation: apply once, record the result, append
the change log. Duplicate: return/recover the already-applied result. A deterministic test is required;
if no live PostgreSQL is available, test the transaction/service boundary as strongly as possible and
record `LIVE_POSTGRES_CRASH_INJECTION = SKIPPED_TOOL_UNAVAILABLE`.

**Revision.** The server is the revision authority; each accepted mutation advances the server
revision; the client sends `baseRevision`; a stale value yields `409 REVISION_CONFLICT`; the client
marks the entity `CONFLICT` and stops destructive overwrite. No A6 conflict-resolution UI.

**Server clock.** Client wall clock is never conflict authority. `updatedAt` may remain product
metadata; ordering/conflict authority is the server revision and the server-accepted change order.

**Trash ≠ tombstone.** `trashed` stays reversible product Trash and syncs as ordinary note state; a
final deletion uses `deletedAt`/tombstone. M2 does **not** implement automatic Trash retention and does
**not** auto-purge tombstones (D-06 stays pending). Deleted remote notes must not resurrect.

**Cursor / checkpoint.** The server cursor is the change-log position; the client checkpoint is the
last fully-applied server cursor. They are not the same stored authority. Pull: request changes after
the checkpoint → apply the full returned page transactionally → advance the checkpoint only after a
successful apply. A failed delta leaves the checkpoint unchanged (deterministic test required).

**404.** A 404 must not silently delete a live local note; it maps to a non-destructive sync/error
state (test required).

**accountId invariant.** `LOCAL_ONLY` may have `accountId = NULL`; any entity in `SYNC_PENDING`,
`SYNCING`, `SYNCED`, `SYNC_FAILED`, `CONFLICT` or `DELETE_PENDING` must have `accountId != NULL`.
Enforced at creation/update boundaries and by deterministic tests.

**WorkManager.** One unique pipeline named `note_sync`. The exact `ExistingWorkPolicy` is an
**A4 implementation decision** chosen by deterministic tests against the actual WorkManager version —
not frozen speculatively — and it must not create parallel duplicate pipelines. A5 later owns
lost-wakeup and reconnect hardening.

**Triggers.** After an account-scoped local mutation; after a successful login; on app start / a
suitable foreground entry; a manual/requested synchronization entry. No push provider, no FCM, no
background push architecture.

**Worker flow.** ensure a valid session → refresh if necessary → push pending mutations → handle
mutation responses → pull changes after the checkpoint → apply remote changes into Room → advance the
checkpoint only after success → finish. **Room remains the local SSOT; the UI never reads remote state
directly as canonical state.**

**Coverage.** note create; title/body edit; archive; pin; colour; Trash state; checklist changes;
label changes. No attachments, no collaboration.

**Error mapping.** 401/expired → attempt refresh if valid; refresh unavailable → `AUTH_REQUIRED`;
409 stale revision → `CONFLICT`; 404 → do not delete the local note; network/server temporary → retain
outbox and local data; generic 5xx → **not** permanent by default. No local data loss from auth
failure, network failure or a temporary server failure.

## 6. LOCAL_ONLY safety (frozen)

Pre-existing notes with `accountId = NULL` and `syncState = LOCAL_ONLY` are **never** silently
assigned, uploaded, deleted or merged into the signed-in account. M2 needs no bulk-link feature; old
LOCAL_ONLY notes are left LOCAL_ONLY. A new note created while signed out is `LOCAL_ONLY`. A new note
created while signed in gets `accountId = active account` + `SYNC_PENDING` and is enqueued for sync.

## 7. Secrets and configuration

`KEEPLAB_JWT_SIGNING_KEY`, `KEEPLAB_REFRESH_TOKEN_PEPPER`, `KEEPLAB_AUTH_CODE_PEPPER`,
`KEEPLAB_ACCESS_TOKEN_TTL_SECONDS`, `KEEPLAB_REFRESH_TOKEN_TTL_SECONDS`,
`KEEPLAB_REFRESH_REPLAY_WINDOW_SECONDS`. No real value is hard-coded; `backend/.env.example` gets
placeholders only; `backend/.env` is **not** created; nothing secret is logged or written into
evidence. The backend must still build and start with no secret present.

## 8. Allowed write surface (exhaustive)

**Backend**
1. `KeepLab-Relay/backend/` — the whole backend project (existing and new source, resources, new
   Flyway migrations, backend-local Gradle files, tests, `Dockerfile`, `docker-compose.yml`,
   `.dockerignore`, `.env.example`)

**Android (enumerated, NOT the whole app)**
2. `KeepLab-Relay/app/build.gradle.kts`
3. `KeepLab-Relay/gradle/libs.versions.toml`
4. `KeepLab-Relay/app/src/main/AndroidManifest.xml`
5. `KeepLab-Relay/app/src/main/java/com/keeplab/app/KeepLabApplication.kt`
6. `KeepLab-Relay/app/src/main/java/com/keeplab/app/MainActivity.kt`
7. `KeepLab-Relay/app/src/main/java/com/keeplab/app/data/`
8. `KeepLab-Relay/app/src/main/java/com/keeplab/app/model/`
9. `KeepLab-Relay/app/src/main/java/com/keeplab/app/di/`
10. `KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/auth/`
11. `KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/settings/`
12. `KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/navigation/`
13. `KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/home/`
14. `KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/editor/`
15. `KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/archive/`
16. `KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/labels/`
17. `KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/trash/`
18. `KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/note/`
19. `KeepLab-Relay/app/src/test/`

**Reporting / evidence**
20. `Google-Android-Agent-Development-Stack/reports/`
21. `Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/keeplab-m2-auth-single-user-sync/`

Everything else inside the project root is **BLOCKED** (fail-closed), including every file under
`KeepLab-Relay/app/src/main/res/` (resources), `ui/theme/`, `ui/common/`, `androidTest/`,
`benchmark/`, `app/schemas/`, `proguard-rules.pro`, the `benchmark/` module, `settings.gradle.kts`,
`build.gradle.kts`, `gradle.properties`, `gradle/wrapper/`, `gradlew`, `local.properties`, `specs/`,
`verification/`, `harness/`, `docs/`, `factory/`, the product governance files, the frozen P0B
packages, `reports/contracts/` (this package and every earlier package), `Testapp/`, `PowerAi/` and
`KeepLab-Relay-evidence/`.

**Explicit surface limit:** if A3/A4 would need a forbidden Android file (a resource, a theme, a shared
UI widget, an instrumentation test, a schema export), that is a **STOP** with
`M2_SURFACE_BROADENING_REQUIRED`, not a silent broadening.

## 9. Acceptance criteria

### AC-M2-001 — D-01 honoured, no forbidden identity

Evidence: backend and Android source inspection plus tests show email+password registration, required
email verification, password login and password reset, and show that no Google login, Google Identity,
Firebase Auth, Google private API, phone auth or OAuth social login exists anywhere.

### AC-M2-002 — A3 backend schema exists

Evidence: new Flyway migrations after V1 create users, email verification challenges, password reset
challenges, sessions and refresh-rotation state, and nothing beyond what A3 requires.

### AC-M2-003 — password KDF and code verifiers

Evidence: passwords are hashed with a maintained vetted modern KDF (Argon2id preferred, or a documented
fallback); verification and reset codes are stored only as secure verifiers with TTL/attempt/cooldown
limits; the delivery abstraction has a fake sender and a development-only console sender.

### AC-M2-004 — A3 auth API works

Evidence: deterministic backend tests cover register, verify-email, unverified login rejection, verified
login, wrong password, password reset, logout and per-session revoke; `GET /v1/auth/sessions` lists
sessions.

### AC-M2-005 — JWT access token

Evidence: a test validates the token signature and asserts the minimum claims `sub`, `sid`, `iat`,
`exp`, `iss`, `aud`; identity is taken from the authenticated subject and a client-supplied `accountId`
grants nothing; the signing key comes from configuration.

### AC-M2-006 — opaque retry-safe rotating refresh token

Evidence: the refresh token is opaque and high-entropy; only a verifier/hash is stored; deterministic
tests cover normal refresh, same old token + same `refresh_request_id` returning the same rotated
result, old token + different request id after rotation, revoked session and expired refresh token; no
path can create two simultaneously-valid child rotations; no plaintext token is stored or logged.

### AC-M2-007 — Android session support and secure storage

Evidence: register/verify/login/refresh/logout/session state exist in the client; access and refresh
material is written only through an app-private Android Keystore-backed store (tests exercise the store
boundary); the Room database is not claimed encrypted; Credential Manager, if present, is used only for
password credential UX.

### AC-M2-008 — auth UX reachable and login-optional app

Evidence: Sign in, Register, Verify email, Forgot/reset password, signed-in account state and Sign out
are reachable through a settings/account area; the app still works with no account; unrelated
navigation is not refactored.

### AC-M2-009 — D-04 sign-out behaviour

Evidence: a JVM test asserts that sign-out clears session credentials and active-account state, stops
sync, and leaves Room data, account-scoped cached notes and the outbox present; another test asserts
`AUTH_REQUIRED` deletes nothing.

### AC-M2-010 — LOCAL_ONLY safety

Evidence: tests assert a pre-login note stays `LOCAL_ONLY` with `accountId = NULL` and is never
uploaded or reassigned; a note created while signed out is `LOCAL_ONLY`; a note created while signed in
is account-scoped `SYNC_PENDING`.

### AC-M2-011 — local Room model for one-account sync

Evidence: the database version moved by a direct experimental bump (`DEV_DATABASE_RESET_REQUIRED = YES`);
checklist items and labels each carry a stable unique client UUID; an outbox table and a client
checkpoint table exist with the required columns; local Long PKs are retained where used; no migration
chain was authored.

### AC-M2-012 — persistent outbox in the mutation transaction

Evidence: outbox rows carry `mutationId`, `accountId`, target client UUID, mutation kind,
`baseRevision`, payload and `createdAt` plus minimal status; a test proves the entity write and the
outbox insert share one transaction (a failed write leaves neither); a test proves `AUTH_REQUIRED`
leaves the outbox intact.

### AC-M2-013 — A4 backend sync schema

Evidence: new migrations after V1 create only notes, checklist items, labels, note-label relations,
server revision, sync tombstones, the change log/cursor and mutation-id dedupe; source inspection shows
no attachment, collaboration, multi-account or CRDT code.

### AC-M2-014 — sync API authenticated by JWT only

Evidence: `/v1/sync/mutations`, `/v1/sync/changes` and `/v1/sync/checkpoint` exist; tests show they
reject a missing/invalid access token and that a request `accountId` for another account returns no
other account's data.

### AC-M2-015 — atomic mutation dedupe

Evidence: a deterministic backend test applies the same `mutation_id` twice and asserts one apply, one
revision increment and one change-log entry, with the second call returning the already-applied result;
the dedupe claim and the apply are in one transaction. If no live PostgreSQL exists,
`LIVE_POSTGRES_CRASH_INJECTION = SKIPPED_TOOL_UNAVAILABLE` is recorded and the boundary is tested as
strongly as available.

### AC-M2-016 — revision authority and conflict state

Evidence: an accepted mutation advances the server revision; a stale `baseRevision` yields
`409 REVISION_CONFLICT`; the client marks the entity `CONFLICT` and stops destructive overwrite; no
client wall clock participates in ordering; no conflict-resolution UI exists.

### AC-M2-017 — Trash is not a tombstone and nothing resurrects

Evidence: trashing writes product Trash state only and never `deletedAt`; a deleted remote note does
not reappear locally; no automatic Trash expiration or tombstone purge exists.

### AC-M2-018 — checkpoint discipline

Evidence: the client checkpoint advances only after a clean transactional apply; a test asserts a failed
delta leaves the checkpoint unchanged; the server cursor and the client checkpoint are stored
separately.

### AC-M2-019 — 404 is non-destructive

Evidence: a test returns 404 for a live local note and asserts the local row still exists and the entity
entered a non-destructive sync/error state.

### AC-M2-020 — accountId invariant

Evidence: deterministic tests assert that any entity entering `SYNC_PENDING`, `SYNCING`, `SYNCED`,
`SYNC_FAILED`, `CONFLICT` or `DELETE_PENDING` has a non-null `accountId`, and that `LOCAL_ONLY` is the
only state that may have a null one.

### AC-M2-021 — one unique note_sync pipeline

Evidence: exactly one unique WorkManager pipeline named `note_sync` exists with a `CONNECTED`
constraint; the chosen `ExistingWorkPolicy` is recorded as an A4 implementation decision and a
deterministic test shows repeated triggers do not create parallel duplicate pipelines; no push
provider, FCM or background push architecture exists.

### AC-M2-022 — worker flow and error mapping

Evidence: the worker performs ensure-session → refresh-if-needed → push → handle responses → pull →
apply → advance-checkpoint-on-success; tests cover push success, pull success, 409 → `CONFLICT`, 404
does not delete, a generic 5xx is not marked permanent, and auth/network/temporary failures retain
local data and the outbox.

### AC-M2-023 — product-data coverage with Room as SSOT

Evidence: create, title/body edit, archive, pin, colour, Trash state, checklist changes and label
changes round-trip; the UI reads only from Room.

### AC-M2-024 — one verification pass, both gates run once

Evidence: the report records `cd /mnt/AndroidDev/Projects/KeepLab-Relay && ./gradlew -p backend test
build` and `cd /mnt/AndroidDev/Projects/KeepLab-Relay && ./gradlew :app:testDebugUnitTest
:app:assembleDebug`, each run **once**; after a deterministic failure only the failed task was re-run
and the already-passing side was not re-run.

### AC-M2-025 — boundaries held honestly

Evidence: frozen inputs re-hash byte-identical; the scope scan shows every created/modified file inside
`allowed_paths` and no change under a forbidden path (including `app/src/main/res/**`, `ui/theme/**`,
`ui/common/**`, `androidTest/**`, `benchmark/**`, the root Gradle files and
`reports/contracts/**`); the secret scan is clean and no token plaintext appears in reports, evidence
or logs; no device, no cloud, no Google/Firebase, no account deletion, no automatic Trash retention,
no attachments, no collaboration.

## 10. Required guard classifications (validated in this phase, simulated)

| Write target | Required |
|---|---|
| `KeepLab-Relay/backend/src/main/kotlin/.../auth/...kt` | ALLOW |
| `KeepLab-Relay/backend/src/main/resources/db/migration/V2__*.sql` | ALLOW |
| `KeepLab-Relay/backend/src/test/kotlin/...` | ALLOW |
| `KeepLab-Relay/app/src/main/java/com/keeplab/app/data/sync/...kt` | ALLOW |
| `KeepLab-Relay/app/src/main/java/com/keeplab/app/data/local/OutboxEntity.kt` | ALLOW |
| `KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/auth/...kt` | ALLOW |
| `KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/settings/...kt` | ALLOW |
| `KeepLab-Relay/app/src/test/java/com/keeplab/app/...` | ALLOW |
| `KeepLab-Relay/app/build.gradle.kts` | ALLOW |
| `KeepLab-Relay/gradle/libs.versions.toml` | ALLOW |
| `KeepLab-Relay/app/src/main/AndroidManifest.xml` | ALLOW |
| `Google-Android-Agent-Development-Stack/reports/...` | ALLOW |
| `.../orchestration/hermes/evidence/keeplab-m2-auth-single-user-sync/...` | ALLOW |
| `KeepLab-Relay/app/src/main/res/values/strings.xml` | BLOCK |
| `KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/theme/Theme.kt` | BLOCK |
| `KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/common/SearchTopBar.kt` | BLOCK |
| `KeepLab-Relay/app/src/androidTest/java/...` | BLOCK |
| `KeepLab-Relay/app/src/benchmark/java/...` | BLOCK |
| `KeepLab-Relay/app/schemas/...` | BLOCK |
| `KeepLab-Relay/benchmark/build.gradle.kts` | BLOCK |
| `KeepLab-Relay/settings.gradle.kts`, `build.gradle.kts`, `gradle.properties` | BLOCK |
| `KeepLab-Relay/gradle/wrapper/...`, `gradlew` | BLOCK |
| `KeepLab-Relay/specs/...`, `verification/...`, `MISSION.md` | BLOCK |
| `Testapp/...`, `PowerAi/...`, `KeepLab-Relay-evidence/...` | BLOCK |
| `.../evaluation_adapter/contract_guard.py` | BLOCK |
| this contract package itself | BLOCK |
| every earlier A0/A1/A2 contract package | BLOCK |

**Guard scope, stated plainly.** The frozen guard classifies write *targets*, not tool choice. `adb`,
`./gradlew`, `docker run` and Hermes config/core paths (outside the project root) are not blocked by any
path list, so the device prohibition, the cloud prohibitions, the Google/Firebase prohibition and the
Hermes-core prohibition are enforced by this contract's stop conditions. They are not weaker for that:
violating one is a `CONTRACT_DEVIATION`.

## 11. Verification (one pass)

```
cd /mnt/AndroidDev/Projects/KeepLab-Relay && ./gradlew -p backend test build          # ONCE
cd /mnt/AndroidDev/Projects/KeepLab-Relay && ./gradlew :app:testDebugUnitTest :app:assembleDebug   # ONCE
```

On failure: read the failure once, fix the failed path only, rerun only the failed task. Never re-run
the already-passed side. Same failure after two genuine fixes → `REPEATED_FAILURE` plus one root-cause
analysis. After PASS: stop. No post-PASS review, no second audit, no A5.

Optional at most once: a live PostgreSQL integration / crash-injection check **if** a container runtime
or local PostgreSQL is genuinely available and cheap. Otherwise record
`LIVE_POSTGRES_INTEGRATION = SKIPPED_TOOL_UNAVAILABLE` and
`LIVE_POSTGRES_CRASH_INJECTION = SKIPPED_TOOL_UNAVAILABLE`. Neither absence blocks M2 and neither
justifies installing infrastructure or weakening the transaction design.

Not verified here: production deployment, live PostgreSQL behaviour beyond the optional single check,
push notifications, attachments, collaboration, multi-device convergence, conflict-resolution UX, and
any Android device behaviour.

## 12. Readiness gates

| Gate | Result |
|---|---|
| acceptance | PASS |
| boundaries | PASS |
| hashes | PASS |
| backend_path | PASS (PRESENT, independent Gradle project, owned by M2) |
| android_surface | PASS (enumerated, not whole-app) |
| traceability | PASS |
| guard_simulation | PASS |
