# KEEPLAB-M2-AUTH-SINGLE-USER-SYNC-EXECUTION

**Contract:** `KEEPLAB-M2-AUTH-SINGLE-USER-SYNC-001` — `CONTRACT_PACKAGE: READ_ONLY_INPUT`, unmodified
**Milestone:** `M2` = `A3_AUTH_SESSION` + `A4_SINGLE_USER_SYNC` — **one** contract, **one** session, **one** verification pass
**Execution model:** `PLAN ONCE → A3 EXECUTE → A3 LIGHT CHECKPOINT → A4 EXECUTE → VERIFY M2 ONCE → PASS = STOP`
**Date:** 2026-10-06 (CST, UTC+08:00) · **Device:** `NOT_USED` · **Cloud:** `NOT_PROVISIONED`
**Data stage:** `EXPERIMENTAL` — `DISPOSABLE_TEST_DATA`, `DEV_DATABASE_RESET_REQUIRED = YES`
**Result:** `PASS` — both gates green, one pass, no re-runs. **PASS = STOP.**

---

## 1. Activation

| Check | Result |
|---|---|
| `sha256(contract_guard.py)` | `e418fc28b08ac7afe4fdd42ec44d572ddaa2f23f6200de300ecac211404b3746` — **matches** |
| `pre_tool_call` hook wiring | unchanged (`matcher write_file|patch|terminal`, `fail_closed: true`, timeout 20) |
| `load_contract(M2 package)` | `MANIFEST_OK`, `contract_id = KEEPLAB-M2-AUTH-SINGLE-USER-SYNC-001` |
| `frozen_inputs.files` re-hash **before the first write** | 41/41 byte-identical, `mismatches = []` |
| Package role | `READ_ONLY_INPUT` — never written, re-hashed or extended |
| `KeepLab-Relay/backend/` | PRESENT, independent Gradle project, built via `./gradlew -p backend` |

The plan was written once (`evidence/…/M2-PLAN.md`) and executed in order.

## 2. Environment (facts and accommodations)

- Maven Central reachable; **`dl.google.com` unreachable** on this host and `androidx.work` absent from
  the Gradle cache. Fix: a user-level Gradle init script
  (`~/.gradle/init.d/00-keeplab-google-mirror.gradle`, **outside the project root**) repoints
  dependency resolution at reachable mirrors. **No project file was touched for this**, and the
  project's root Gradle files are byte-identical (proven below).
- `ktor-client-okhttp` was rejected: it pulls `com.squareup.okhttp3:okhttp-android:5.5.0`, which
  demands `compileSdk 37`. Rather than bump the compile SDK, the M2 dependency uses **Ktor CIO**
  (pure Kotlin, no added HTTP stack). `compileSdk`/`targetSdk`/`minSdk` are unchanged.
- No container runtime and no `psql` on this host → `LIVE_POSTGRES_INTEGRATION = SKIPPED_TOOL_UNAVAILABLE`
  and `LIVE_POSTGRES_CRASH_INJECTION = SKIPPED_TOOL_UNAVAILABLE`. Neither the transaction design nor
  the revision/dedupe semantics were weakened because of it.

## 3. A3 — backend auth

- `config/AppConfig.kt`: `AuthConfig` (JWT key, refresh pepper, code pepper, access/refresh TTLs,
  replay window, email mode) + `EmailDeliveryMode`; no secret has a compiled-in default.
- `auth/SecretMaterial.kt`: an absent secret becomes an ephemeral in-memory development value with a
  start-up warning; nothing ephemeral is committed, persisted or logged.
- **Password KDF:** `auth/crypto/PasswordHasher.kt` — **Argon2id via BouncyCastle `bcprov-jdk18on:1.83`**
  (maintained, vetted; no invented hashing). **Recorded parameters:** Argon2id, `v=19`,
  `t=3` iterations, `m=64 MiB`, `p=1`, a fresh 16-byte random salt per password, 32-byte output,
  stored as a PHC string. `PASSWORD_KDF_FALLBACK` **not** used.
- `auth/crypto/PepperedHasher.kt`: verification codes, reset codes and refresh tokens are stored
  **only** as peppered HMAC-SHA256 verifiers with constant-time comparison; deterministic child
  derivation for retry-safe rotation. Code TTL 600 s, max 5 failed attempts, 60 s resend cooldown.
- `auth/EmailSender.kt`: `EmailSender` port; `NoopEmailSender` (default/production — delivers nothing,
  prints nothing), `ConsoleDevelopmentEmailSender` (**only** under explicit
  `KEEPLAB_EMAIL_MODE=development`, with an unmissable development banner), `RecordingEmailSender`
  (tests). No cloud email service is started, no SMTP is deployed.
- `auth/JwtService.kt`: HS256, claims `sub`, `sid`, `iat`, `exp`, `iss`, `aud`; signing key from
  configuration only.
- API (`routes/AuthRoutes.kt`): `POST /v1/auth/register|verify-email|login|refresh|logout`,
  `POST /v1/auth/password-reset/request|confirm`, `GET /v1/auth/sessions`,
  `DELETE /v1/auth/sessions/{sessionId}` (and `POST …/revoke`).
- Schema: `V2__auth_schema.sql` — `users`, `email_verification_challenges`,
  `password_reset_challenges`, `sessions`, `refresh_states`.
- Password reset revokes every existing session of the account.
- **No account deletion** (D-05 pending, untouched).

### D-10 refresh rotation, as implemented

`refresh_request_id` retry-safety is achieved by **safely re-deriving** the child credential:
`child = base64url(HMAC-SHA256(pepper, "child|" + presentedParentToken + "|" + requestId))`. Because
derivation is deterministic in the *presented* credential, the replay record retains **no secret** —
only the previous verifier, the request id and the window end. Behaviour: current token → rotate; the
same old token with the same request id inside the bounded window → the **same** child and expiry
recovered; the same old token with a **different** request id after rotation → reuse → reject and
revoke that one session, with no second child ever minted and no account access destroyed.

## 4. A3 — Android session and auth UX

- `data/auth/SecureSessionStore.kt` + `data/auth/AndroidKeystoreSecretCipher.kt`: **AES-GCM under a
  key held in the Android Keystore**; only ciphertext is written to app-private storage; there is no
  plaintext fallback and no claim anywhere that the Room database is encrypted.
- `data/auth/SessionManager.kt`: single active account; sign-out clears the credential blob and the
  active account and touches **no** Room table.
- `data/auth/AuthRepository.kt`: register/verify/login/refresh/logout/reset; `requireAccessToken`
  refreshes with a `refresh_request_id` when the access token is near expiry and returns
  `AUTH_REQUIRED` rather than deleting anything when it cannot.
- `data/remote/*`: Ktor CIO client, `AuthApi`/`SyncApi` ports and implementations.
- UI: `ui/auth/*` (sign in, register, verify email, forgot/reset password) and `ui/settings/*` (the
  smallest account area), reached from the Home overflow menu via two additive navigation keys. No
  pre-existing navigation was refactored, and the app stays fully usable with no account.
- Credential Manager is **not** integrated; a plain email/password form satisfies A3.

## 5. A3 light checkpoint

Recorded in `evidence/…/A3-CHECKPOINT.md` → `A3_CHECKPOINT: READY_FOR_A4`. Records only; the session
continued directly into A4.

## 6. A4 — backend sync

- `V3__sync_schema.sql`: `server_entities` (notes, checklist items, labels, note-label relations),
  `account_revisions`, `sync_tombstones`, `change_log` (cursor), `mutation_dedupe`.
- `sync/SyncStore.kt` + `sync/SyncService.kt` + `routes/SyncRoutes.kt`:
  `POST /v1/sync/mutations`, `GET /v1/sync/changes?since=`, `GET /v1/sync/checkpoint`.
- **Atomic apply.** One atomic operation performs: dedupe claim, `baseRevision` check, revision bump,
  entity upsert, tombstone write, change-log append and the dedupe record. In `JdbcSyncStore` that is
  one transaction with rollback on conflict (so a conflicted mutation leaves **no** claim behind and a
  duplicate can never apply twice); `InMemorySyncStore` performs the identical logic under one lock.
- Authorization is the JWT subject **only**. A request-body `accountId` is accepted for wire
  compatibility and is never consulted — proven over HTTP.
- `baseRevision` is the revision the client last saw; a stale value → `409 REVISION_CONFLICT`.

## 7. A4 — Android local model, outbox, sync engine

- Room **version 3 → 4 by direct experimental bump**; no migration chain authored; `exportSchema`
  stays `false`; `DEV_DATABASE_RESET_REQUIRED = YES`.
- New: `outbox` and `client_sync_checkpoint` tables; stable `clientUuid` (UNIQUE, fresh-row default)
  plus account/state columns on checklist items and labels. Local Long primary keys are retained;
  `clientUuid` stays UNIQUE, `accountId` stays nullable, `SyncState` keeps its seven values, and
  Trash ≠ tombstone stays structural.
- Outbox rows carry `mutationId` (idempotency key), `accountId`, target client UUID, entity type,
  kind, `baseRevision`, the **captured** payload and `createdAt`, plus only `attemptCount`/
  `lastErrorCode`.
- `LocalStore.writeAtomically` (`RoomLocalStore` = one Room transaction) wraps every mutation, so the
  entity write and its outbox row land together or not at all.
- **LOCAL_ONLY safety:** signed out → `accountId = null`, `LOCAL_ONLY`, no outbox row, never uploaded
  and never adopted after login. Signed in → `accountId = active account`, `SYNC_PENDING`, enqueued.
- Engine flow: ensure a valid session → refresh if necessary → push oldest-first → handle each
  response → pull changes after the checkpoint → apply the page **and** advance the checkpoint in one
  transaction. Room remains the local SSOT; the UI never reads remote state.
- Error mapping: 401 → one refresh then retry; refresh unavailable → `AUTH_REQUIRED` (outbox intact);
  409 → `CONFLICT` with no destructive overwrite; 404 → `SYNC_FAILED`, the live local note is kept and
  the mutation is retained; 5xx/transport → `RETRY_LATER` (never marked permanent). A remote final
  deletion becomes a local tombstone and is never resurrected.
- Coverage: note create, title/body edit, archive, pin, colour, Trash state, checklist changes, label
  changes and note-label links.

### Worker policy decision (chosen, not frozen)

ONE unique pipeline `note_sync`; `ExistingWorkPolicy.KEEP`; `NetworkType.CONNECTED`. `KEEP` is the
smallest policy that cannot create parallel duplicate pipelines — an already enqueued/running run is
left alone and a repeat request is dropped rather than queued behind it. A deterministic test asserts
the single unique name, the policy and the network constraint through an injectable enqueuer seam, so
the property holds without a WorkManager runtime. No push provider, no FCM, no background push
architecture.

## 8. Secrets and configuration

- `backend/.env.example` gained **placeholders only**; `backend/.env` is **absent** (verified).
- `application.conf` declares `KEEPLAB_JWT_SIGNING_KEY`, `KEEPLAB_REFRESH_TOKEN_PEPPER`,
  `KEEPLAB_AUTH_CODE_PEPPER`, `KEEPLAB_ACCESS_TOKEN_TTL_SECONDS`,
  `KEEPLAB_REFRESH_TOKEN_TTL_SECONDS`, `KEEPLAB_REFRESH_REPLAY_WINDOW_SECONDS` (and
  `KEEPLAB_EMAIL_MODE`) with `${?VAR}` substitution and no secret default.
- The backend builds and starts with no secret present (ephemeral in-memory development values plus a
  warning). No password, access token, refresh token, verification/reset secret, signing key or pepper
  is logged or written into any report, evidence file or log — the secret scan is clean.

## 9. Verification — ONE pass

| # | Command | Result |
|---|---|---|
| 1 | `cd /mnt/AndroidDev/Projects/KeepLab-Relay && ./gradlew -p backend test build` | **BUILD SUCCESSFUL** (`evidence/…/gate-backend.log`) |
| 2 | `cd /mnt/AndroidDev/Projects/KeepLab-Relay && ./gradlew :app:testDebugUnitTest :app:assembleDebug` | **BUILD SUCCESSFUL** (`evidence/…/gate-android.log`); debug APK produced |

Each command was run **once**. No fix was needed, so nothing was re-run: a failed-then-fixed task, a
re-run of a passed side and a post-PASS re-run all did not occur.

Test totals for the recorded pass: **backend 53 tests, 0 failures, 0 errors**; **Android JVM 116 tests,
0 failures, 0 errors** (169 total).

Honest detail: at the recorded gate run, `:backend:test` and `:app:testDebugUnitTest` were reported
`UP-TO-DATE` (their inputs were unchanged since the identical tasks had already executed green during
implementation) while `:backend:build` (distribution archives) and the whole `:app:assembleDebug`
chain executed. Gradle's up-to-date check is itself the assertion that no test input changed, so the
recorded green result is valid for the final sources; the concrete failure counts above come from
those task's own recorded results.

Optional live PostgreSQL check: **not run** — no container runtime and no `psql` on this host.
`LIVE_POSTGRES_INTEGRATION = SKIPPED_TOOL_UNAVAILABLE`, `LIVE_POSTGRES_CRASH_INJECTION = SKIPPED_TOOL_UNAVAILABLE`.

## 10. Post-run proof

`evidence/…/post-run-proof.json`.

| Check | Result |
|---|---|
| `frozen_inputs` re-hashed | 41 files: **24 byte-identical**, 17 changed — every changed file is inside `allowed_paths` and is an authorized M2 write |
| Protected files byte-identical | `settings.gradle.kts`, `build.gradle.kts`, `gradle.properties`, `gradlew` — all identical. `app/src/main/res/**`, `ui/theme/**`, `ui/common/**`, `androidTest/**`, `benchmark/**`, `app/schemas/**` — **0 files touched** |
| Scope scan | 86 changed paths inside `allowed_paths`; **0** inside a forbidden path; `reports/contracts/**` untouched (this package and all earlier ones); root Gradle files untouched |
| Guard / hook config / allowlist / contract packages | byte-identical; this package neither rewritten, re-hashed nor extended |
| Secret scan | **CLEAN** (no bearer literal, no JWT literal, no non-placeholder secret assignment in reports, evidence, backend or app sources) |
| `backend/.env` | **ABSENT** |
| Device / cloud / Google-Firebase | no `adb`/Maestro/UiAutomator/instrumentation run; no cloud provisioning; no Google/Firebase/Google-Identity dependency or call |

Two changed paths are outside `allowed_paths` and are **not** M2 writes — they are produced by the
frozen tooling itself and are reported here rather than hidden:
`orchestration/hermes/evidence/p0b-close/contract-guard-decisions.jsonl` (the guard's own best-effort
audit trail, appended by the hook on every write-class call) and
`_evaluation/.auto_finalize_index.json` (the Hermes `on_session_finalize` autofinalizer, outside the
project root). No M2 code or configuration wrote either.

## 11. Acceptance

`reports/KEEPLAB-M2-ACCEPTANCE.md` maps **AC-M2-001 … AC-M2-025** to concrete code and test evidence.
All 25 are `PASS`.

## 12. Notes recorded honestly (no contract deviation)

- **Phase ordering.** The A4 *backend* sync schema/service/routes were authored immediately after the
  A3 backend code they extend rather than at a separate A4 phase boundary; the A3 checkpoint file
  states this explicitly. One contract, one session, one verification pass were preserved.
- **Unused-but-harmless leftovers** (see `reports/KEEPLAB-MINOR-BACKLOG.md`): `SyncDao.nextOutboxEntry`
  is now unused by the engine (the push loop selects from `pendingMutations` with an attempted set);
  a handful of now-unused test imports; the legacy `MIGRATION_1_2` is still registered alongside the
  direct-bump destructive fallback.
- **D-05 / D-06 / D-11 / D-12 / D-13 / D-14** were not pre-empted: no account deletion, no automatic
  Trash retention or tombstone purge, no push provider, no collaboration, no attachments, no
  spec-package relocation.

**PASS = STOP.** No post-PASS review, no second audit, no additional contract, no A5, no A6, no
re-opening of A0/A1/A2, no re-run of a passing task.
