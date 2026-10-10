# KEEPLAB-M2-AUTH-SINGLE-USER-SYNC-EXECUTE

**Contract:** `KEEPLAB-M2-AUTH-SINGLE-USER-SYNC-001` (`CONTRACT_PACKAGE: READ_ONLY_INPUT`, unmodified)
**Milestone:** `M2` = `A3_AUTH_SESSION` + `A4_SINGLE_USER_SYNC`
**Mode:** `PLAN ONCE → A3 EXECUTE → A3 LIGHT CHECKPOINT → A4 EXECUTE → VERIFY M2 ONCE → PASS = STOP`
**Date:** 2026-10-06 (CST, UTC+08:00)
**Authorization:** `HUMAN_PROJECT_OWNER_APPROVAL` — D-01 `EMAIL_PASSWORD_VERIFIED` · D-04 `PRESERVE_LOCAL_CACHE` · D-10 `JWT_ACCESS_OPAQUE_ROTATING_REFRESH`
**Data stage:** `EXPERIMENTAL` — `DISPOSABLE_TEST_DATA`, `DEV_DATABASE_RESET_REQUIRED = YES`, `CLEAN_TARGET_ARCHITECTURE > OLD_TEST_DATA_COMPATIBILITY`
**Device:** `NOT_USED` · **Cloud:** `NOT_PROVISIONED` · **This milestone's status if you are reading it as the executor:** `NOT_EXECUTED until you run it`

---

## 0. What M2 is, and what it is not

M2 contains two logically separate checkpoints executed in ONE session:

```
A3 = AUTH / SESSION
then
A4 = SINGLE-USER SYNC
```

They share **one contract, one execution session, one final verification pass**.

Required flow, unchanged for the whole run:

```
PLAN ONCE
  → A3 EXECUTE
  → A3 LIGHT CHECKPOINT      (records only; NOT a review; DO NOT stop the session)
  → CONTINUE DIRECTLY TO A4
  → A4 EXECUTE
  → VERIFY M2 ONCE
  → PASS = STOP
```

**Do NOT** create an A3 Contract, stop after A3, create an A4 Contract, create an A3 Review, create an
A4 Review, or perform a post-PASS audit. Phases are checkpoints, not bureaucratic stops.

Not in M2: A5 offline hardening, A6 conflict-resolution UI, attachments, object storage, push/FCM,
multi-device hardening, multi-account, collaboration/sharing, account deletion, automatic Trash
retention/purge, CRDT, Google login, Firebase Auth, phone login, passkeys, cloud deployment, device
work, Google Keep work, Testapp, PowerAi.

---

## 1. Activation (do this before any write, then stop re-reading)

1. Confirm the guard identity: `sha256(contract_guard.py)` must equal
   `e418fc28b08ac7afe4fdd42ec44d572ddaa2f23f6200de300ecac211404b3746`, and the `pre_tool_call` hook
   must still be the same fail-closed wiring. If either differs: STOP.
2. Load the package with `load_contract(package_dir)`; require `MANIFEST_OK` and the expected
   `contract_id`. A `CONTRACT_HASH_MISMATCH` is a STOP.
3. Re-hash every `frozen_inputs.files` entry BEFORE your first write. Any drift → `STALE_M2_INPUT` STOP.
   Never re-baseline an expected hash to match the filesystem.
4. Confirm the package is READ_ONLY_INPUT: you must never write into `reports/contracts/**`.
5. Confirm `KeepLab-Relay/backend/` is PRESENT and is the A2 independent Gradle project.

Then write the plan **once** (A3 tasks, A4 tasks, worker policy decision, test list, gate commands) and
execute it in order. Do not re-plan after that.

**Overhead rule.** After activation and the stale-input check, begin implementation. Do not spend long
periods rewriting governance docs, reviewing old phases, re-validating PASS work, creating evidence
before product work, or re-reading the same architecture files. If more than ~30 tool calls occur before
meaningful product writes without a real blocker:`PROCESS_OVERHEAD_TOO_HIGH` — simplify and execute.

**Guard-practical note (MB-A1-003 / MB-A2-008).** The frozen guard treats a literal `>` anywhere in a
terminal command as a redirect. Drive it with files and read-only commands; never inline heredocs,
payload-bearing shell text or pipes into interpreters. Write source files with `write_file`, not with
shell redirection.

---

## 2. Frozen human decisions — honour them, never reinterpret them

### D-01 `EMAIL_PASSWORD_VERIFIED`

email + password registration · email verification required · password login · forgot/reset password
supported · passkey may be added **later** · phone login deferred · **Google login forbidden** ·
**Firebase Auth forbidden**.

### D-04 `PRESERVE_LOCAL_CACHE`

On sign-out: revoke/clear current session credentials · remove active-account state · stop account sync ·
**preserve** Room data · **preserve** account-scoped cached notes · **preserve** the outbox ·
**preserve** `LOCAL_ONLY` notes.

Signed-out UI keeps showing `LOCAL_ONLY` data. Account-scoped rows of a signed-out account remain stored
but are not treated as another account's data and must not sync. Re-login to the same account may resume
them.

```
DO NOT CLAIM FULL ROOM DATABASE ENCRYPTION.
No database-encryption feature is authorized here.
```

### D-10 `JWT_ACCESS_OPAQUE_ROTATING_REFRESH`

Access token: **JWT**, short-lived, default target ≈ 15 minutes, configurable.
Refresh token: **opaque**, high-entropy, default target ≈ 30 days, configurable.
Refresh secrets are **never** stored plaintext at rest — the server stores a secure verifier/hash form.
Rotation is required and **retry-safe** via `refresh_request_id`: a lost successful response retried
with the **same** old refresh token and the **same** request id inside a bounded replay window must
recover the **same** rotated result. Never mint multiple child sessions, never treat the request
immediately as theft, never destroy account access. Use the **smallest safe implementation**. If replay
state must retain a secret result it must be encrypted at rest or safely re-derived. **Never write token
plaintext to reports, evidence or logs.**

## 3. Decisions that stay pending and do NOT block M2

D-05 account deletion retention (do not implement account deletion) · D-06 Trash automatic retention
(do not implement automatic Trash expiration/purge; an explicit final deletion may create a tombstone,
M2 never auto-purges it) · D-11 push provider (none in M2) · D-12 collaboration (out of scope) ·
D-13 attachment limits (attachments out of scope) · D-14 formal spec package location (pending, does
not block M2). Do not ask again; do not pre-empt them.

---

## 4. Write surface

**Allowed — backend**

```
KeepLab-Relay/backend/**            (existing + new source, resources, new Flyway migrations,
                                     backend-local Gradle files, tests, Dockerfile,
                                     docker-compose.yml, .dockerignore, .env.example)
```

**Allowed — Android (enumerated; NOT the whole app)**

```
KeepLab-Relay/app/build.gradle.kts
KeepLab-Relay/gradle/libs.versions.toml
KeepLab-Relay/app/src/main/AndroidManifest.xml
KeepLab-Relay/app/src/main/java/com/keeplab/app/KeepLabApplication.kt
KeepLab-Relay/app/src/main/java/com/keeplab/app/MainActivity.kt
KeepLab-Relay/app/src/main/java/com/keeplab/app/data/
KeepLab-Relay/app/src/main/java/com/keeplab/app/model/
KeepLab-Relay/app/src/main/java/com/keeplab/app/di/
KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/auth/
KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/settings/
KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/navigation/
KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/home/
KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/editor/
KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/archive/
KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/labels/
KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/trash/
KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/note/
KeepLab-Relay/app/src/test/
```

**Allowed — reporting / evidence**

```
Google-Android-Agent-Development-Stack/reports/
Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/keeplab-m2-auth-single-user-sync/
```

**Blocked explicitly** (and everything else inside the project root is blocked by fail-closed
classification):

```
KeepLab-Relay/app/src/main/res/**, ui/theme/**, ui/common/**, app/src/androidTest/**,
app/src/benchmark/**, app/src/debug/**, app/src/release/**, app/schemas/**, app/proguard-rules.pro,
KeepLab-Relay/benchmark/**, KeepLab-Relay/settings.gradle.kts, KeepLab-Relay/build.gradle.kts,
KeepLab-Relay/gradle.properties, KeepLab-Relay/gradle/wrapper/**, KeepLab-Relay/gradlew,
KeepLab-Relay/local.properties, KeepLab-Relay/specs/**, KeepLab-Relay/verification/**,
KeepLab-Relay/harness/**, KeepLab-Relay/docs/**, KeepLab-Relay/factory/**, KeepLab-Relay/.factory/**,
KeepLab-Relay/MISSION.md, KeepLab-Relay/FACTORY_RULES.md, KeepLab-Relay/{Dockerfile,docker-compose.yml},
Google-Android-Agent-Development-Stack/.hermes.md, /specification/**, /verification/**,
/verification-benchmark/**, /references/**, /orchestration/hermes/evaluation_adapter/**,
/orchestration/hermes/HERMES-LOCK.json, /evaluation/**, /reports/contracts/**,
KeepLab-Relay/specs/p0b-*/**, Testapp/**, PowerAi/**, KeepLab-Relay-evidence/**
```

**Surface limit.** If A3/A4 would need a blocked Android file (a resource, a theme, a shared UI widget,
an instrumentation test, a schema export), STOP with `M2_SURFACE_BROADENING_REQUIRED` naming the exact
file and reason. Never broaden silently.

**Root Gradle.** `settings.gradle.kts`, `build.gradle.kts`, `gradle.properties`, `gradle/wrapper/**` and
`gradlew` stay byte-identical. Only `app/build.gradle.kts` and `gradle/libs.versions.toml` may change,
and only to add M2 dependencies — do not remove or gratuitously bump unrelated entries. A needed root
change is a STOP with `M2_ROOT_GRADLE_CHANGE_REQUIRED`.

---

## 5. A3 — backend auth

Extend the existing Ktor backend. Add PostgreSQL/Flyway **development** migrations after V1 for:

- `users` — server-generated UUID identity, normalized unique email, password verifier
- email verification challenges
- password reset challenges
- `sessions` — revocable, device-labelled
- refresh-token / refresh-rotation state
- **only** structures truly required for A3

**Password hashing.** A modern password KDF. **Argon2id preferred.** Do **not** invent custom password
hashing — use a maintained, vetted implementation and record the library, parameters and salt strategy
in the report. If Argon2id genuinely cannot be resolved as a maintained dependency, use another vetted
modern KDF from a maintained library and record `PASSWORD_KDF_FALLBACK` with the reason.

**Email verification.** A small deterministic service abstraction. Recommended experimental defaults:
6-digit random code · TTL 10 minutes · maximum failed attempts 5 · resend cooldown 60 seconds. Store
**only** a secure verifier/hash for verification and reset codes. No production email provider is chosen
in M2: provide a delivery abstraction, use a **fake sender** in tests, and allow a
`ConsoleDevelopmentEmailSender` **only** when explicitly configured as development. Production/default
mode must never rely on it and must never silently print verification secrets. Do not start a cloud
email service and do not deploy SMTP.

### 5.1 A3 API

One consistent versioned namespace. Recommended:

| Route | Behaviour |
|---|---|
| `POST /v1/auth/register` | create an account (email + password) |
| `POST /v1/auth/verify-email` | confirm the verification code |
| `POST /v1/auth/login` | password exchange → session; unverified accounts are rejected |
| `POST /v1/auth/refresh` | rotate the refresh credential (retry-safe) |
| `POST /v1/auth/logout` | revoke the current session |
| `POST /v1/auth/password-reset/request` | start a password reset |
| `POST /v1/auth/password-reset/confirm` | complete a password reset |
| `GET /v1/auth/sessions` | list the account's sessions |
| `DELETE` or `POST` revoke `/v1/auth/sessions/{sessionId}` | revoke one session |

Required behaviours: register · verify email · login · refresh · logout · list sessions · per-session
revoke · request password reset · complete password reset.

Password reset should revoke existing sessions unless a clearly safer minimal design is already present.

**Do NOT implement account deletion.**

The final exact HTTP method may follow the existing Ktor style if the behaviour is equivalent.

### 5.2 Access token

JWT. Server-derived identity only. Minimum claims: `sub` = user/account UUID, `sid` = session UUID,
`iat`, `exp`, `iss`, `aud`. Do **not** trust a client-supplied `accountId` as authorization authority —
use the authenticated subject. The signing key comes from environment/config; no source-code secret.

### 5.3 Refresh token

Opaque, high-entropy. The server stores only a safe verifier/hash form. Rotation is required and
retry-safe through `refresh_request_id`.

Implementation approach (choose the smallest that is safe and record it):

- preferred: **safely re-derive** the child credential deterministically from server-side secret
  material plus the presented parent credential plus `refresh_request_id`, so no secret result is
  retained in the replay record;
- alternative: store the rotated result **encrypted at rest** under a server key.

Required deterministic tests: normal refresh · same request retry · old token + same request id ·
old token + different request id after rotation · revoked session · expired refresh token.

Behaviour: same old token + same request id inside the bounded window → the same rotated result. Old
token + a **different** request id after a successful rotation → treated as reuse (reject and apply the
session-family policy) but **never** multiple simultaneously-valid children, never destructive account
loss. **Never** a retry system that can accidentally create more than one valid child rotation.

### 5.4 A3 light checkpoint

Record, in the report/evidence, only: A3 backend auth structures authored · Android auth/session
structures authored · human D-01/D-04/D-10 honoured · no Google/Firebase auth · local data still
non-destructive. Emit `A3_CHECKPOINT: READY_FOR_A4`. Then **continue immediately into A4** — do not run
the Milestone gate here, do not stop, do not create another contract.

---

## 6. A3 — Android session and auth UX

Implement client support for: register · verify · login · refresh · logout · session state.

**Secure storage.** Access and refresh tokens must **NOT** be stored as ordinary plaintext preference
values. Use an app-private, **Android Keystore-backed** secure session store (for example an AES-GCM key
held in the Android Keystore encrypting the token payload written into app-private storage). Keep the
implementation small. **Do not claim the Room database is encrypted** and do not add a database
encryption dependency.

**Credential Manager.** Allowed **only** as Android credential **UX** for **password** credentials. No
Google ID credential, no Firebase, and it does not become the identity authority. If adding it would
require a Google-identity-only path, a plain email/password form satisfies A3.

**Auth UX.** KeepLab must remain usable **without login**. Add the smallest sensible account surface.
At minimum users must be able to reach: Sign in · Register · Verify email · Forgot/reset password ·
signed-in account state · Sign out. Prefer integrating this through a settings/account area rather than
redesigning the whole UI — **there is no settings screen today**, so add the smallest one and expose it
from the existing Home overflow menu / app bar rather than refactoring unrelated navigation.

`AUTH_REQUIRED` must **not** delete local data.

**Sign-out (D-04).**

```
On sign-out: backend session revoked when possible · local tokens cleared · active account cleared ·
             sync stops · Room rows remain · outbox remains.
Signed out:  LOCAL_ONLY notes remain usable.
Previous account's rows: remain cached, never sync, never reassigned, never treated as another
             account's rows.
UI filtering if needed: signed out → LOCAL_ONLY only;
                        signed in  → LOCAL_ONLY + rows matching activeAccountId;
                        another old account's rows → retained locally, hidden from the active surface.
Phase-1:     SINGLE_ACTIVE_ACCOUNT.
```

---

## 7. A4 — local Room model

Current DB version after A1 is **3**. Because project data is experimental, M2 may move **directly** to
the next clean schema version by a **direct experimental bump**. No old-development-data migration is
required and **no migration chain is authored**. Record `DEV_DATABASE_RESET_REQUIRED = YES`.

Expected new local persistence concepts:

- a stable UUID for **independently synced checklist items** (stable across edits)
- a stable UUID for **labels** if independently synced
- an **outbox** table
- a **client sync checkpoint** table
- any minimum indexing required

**Keep local Long PKs where they remain useful.** Stable UUIDs are **sync identities**; do not replace
good local PKs merely because UUIDs exist. Preserve the A1 properties: `clientUuid` stays UNIQUE with a
fresh-row default, `accountId` stays nullable, `syncState` keeps its seven values, and **Trash ≠
tombstone** stays structural (no write statement may set `deletedAt` for a trashed row).

---

## 8. A4 — outbox

Create a persistent Room outbox. Each mutation must have:

`mutationId` · `accountId` · target client UUID · mutation kind · `baseRevision` · payload or
deterministic mutation data · `createdAt`

plus **only minimal** status fields needed for A4.

Rules:

- the entity mutation and its outbox row are written in **ONE local transaction**
- `mutationId` is the idempotency key
- the outbox row is removed only on confirmed success or explicit permanent-failure handling
- push the **captured** payload, not the live DB row
- `AUTH_REQUIRED` must leave the outbox intact

**Do NOT overbuild.** A5 owns advanced bounded retry, manual retry UX, coalescing, process-death
hardening and lost-wakeup hardening. A4 needs only a sound durable core.

---

## 9. A4 — backend sync data

Extend backend PostgreSQL with **only** the data needed for: single-account notes · checklist items ·
labels · note-label relations · server revision · sync tombstone · server change log / cursor ·
mutation-id dedupe. Use **new Flyway migrations after the existing A2 V1**.

No attachments. No collaboration. No multi-account. No CRDT. No automatic conflict resolution.

### 9.1 Sync API

```
POST /v1/sync/mutations
GET  /v1/sync/changes?since=<cursor>
GET  /v1/sync/checkpoint
```

Exact small route details may follow the architecture API contract. Authentication comes **only** from
the access JWT. Never trust a request `accountId` as authority.

### 9.2 Atomic mutation apply

A duplicate `mutation_id` must not apply twice. The **dedupe claim and the mutation application must be
atomic in the same transaction**.

- first mutation: apply once · record the result · append the change log
- duplicate mutation: return/recover the already-applied result **without** applying twice

Provide a deterministic test. If true crash injection is impractical without live PostgreSQL on this
host, test the transaction/service boundary as strongly as available and record
`LIVE_POSTGRES_CRASH_INJECTION = SKIPPED_TOOL_UNAVAILABLE`. Do not block M2 solely because Docker or
PostgreSQL is absent, and **do not weaken the transaction design** because of it.

### 9.3 Revision rule

The **server is the revision authority**. Each accepted mutation advances the server revision. The
client sends `baseRevision`. If stale: **HTTP 409 `REVISION_CONFLICT`**. In M2 the client marks the
entity `CONFLICT` and stops destructive overwrite. **Do NOT build an A6 conflict-resolution UI.**

### 9.4 Server clock rule

Client wall clock must **NOT** be conflict authority. `updatedAt` may remain product metadata.
Ordering/conflict authority: the **server revision** and the **server-accepted change order**.

### 9.5 Trash ≠ tombstone

Keep `trashed` as reversible product Trash and sync it as ordinary note state. Final deletion uses
`deletedAt` / tombstone. M2 does **not** implement automatic Trash retention and does **not** purge
tombstones automatically (D-06 stays pending). Deleted remote notes must not resurrect.

### 9.6 Cursor / checkpoint

The **server cursor** is the server change-log position; the **client checkpoint** is the last
fully-applied server cursor. They are **not** the same stored authority.

Pull flow: request changes after the client checkpoint → apply the full returned page transactionally →
**only after successful apply** advance the local checkpoint. If delta application fails, the checkpoint
must remain unchanged. Provide a deterministic test.

### 9.7 404 rule

A server 404 must **NOT** silently delete a live local note. Map it to a non-destructive sync/error
state. Provide a test.

### 9.8 accountId invariant

`LOCAL_ONLY` may have `accountId = NULL`. Any entity in `SYNC_PENDING` · `SYNCING` · `SYNCED` ·
`SYNC_FAILED` · `CONFLICT` · `DELETE_PENDING` **must** have `accountId != NULL`. Enforce this at
creation/update boundaries and with deterministic tests.

---

## 10. A4 — Android sync engine

### 10.1 WorkManager

One **unique** pipeline named `note_sync`. Exact `ExistingWorkPolicy` is an **A4 implementation
decision** — do **not** freeze it blindly. Choose the simplest policy supported by the actual
WorkManager version that deterministic tests show does not create parallel duplicate pipelines.
`NetworkType.CONNECTED`. No multiple simultaneous sync workers, no per-keystroke unique work, no
unbounded unique-work names, no treating `getWorkInfosByTagFlow()` as an event stream.

A5 later handles lost-wakeup and reconnect hardening; M2 does not need full A5 resilience.

### 10.2 Triggers

At minimum: after an account-scoped local mutation · after a successful login · on app start or a
suitable foreground entry · a manual/requested synchronization entry.

**No push provider. No FCM. No background push architecture.**

### 10.3 Worker flow

ensure a valid session → refresh if necessary → push pending mutations → handle mutation responses →
pull changes after the checkpoint → apply remote changes into Room → advance the checkpoint only after
success → finish.

**Room remains the LOCAL SSOT.** The UI must never read remote state directly as canonical state.

### 10.4 Coverage

note create · title/body edit · archive · pin · colour · Trash state · checklist changes · label
changes. No attachments, no collaboration.

### 10.5 Error mapping

| Condition | Behaviour |
|---|---|
| 401 / expired | attempt a session refresh if valid |
| refresh unavailable | `AUTH_REQUIRED` |
| 409 stale revision | `CONFLICT` |
| 404 | do not delete the local note |
| network / server temporary | retain the outbox and local data |
| generic 5xx | do **NOT** mark permanent by default |

No local data loss from auth failure, network failure or a temporary server failure. Raw server
exceptions never reach the UI.

---

## 11. LOCAL_ONLY safety

Pre-existing notes with `accountId = NULL` and `syncState = LOCAL_ONLY` must **NEVER** be silently
assigned, uploaded, deleted or merged into the signed-in account. M2 does **not** need a bulk-link
feature — leave old LOCAL_ONLY notes LOCAL_ONLY.

- new note created while **signed out** → `LOCAL_ONLY`
- new note created while **signed in** → `accountId = active account`, `SYNC_STATE = SYNC_PENDING`,
  enqueued for sync

This provides M2 sync functionality without unsafe automatic adoption of pre-login notes.

---

## 12. Secrets, configuration, security boundaries

Extend the backend environment config as needed, for example:

```
KEEPLAB_JWT_SIGNING_KEY
KEEPLAB_REFRESH_TOKEN_PEPPER
KEEPLAB_AUTH_CODE_PEPPER
KEEPLAB_ACCESS_TOKEN_TTL_SECONDS
KEEPLAB_REFRESH_TOKEN_TTL_SECONDS
KEEPLAB_REFRESH_REPLAY_WINDOW_SECONDS
```

Do not hard-code real values. Update `backend/.env.example` with **placeholders only**.
Do **NOT** create `backend/.env` with real secrets. The backend must still build and start with no
secret present — an absent signing key may fall back to an ephemeral in-memory development-only value
with a clear startup warning, never a committed or persisted one.

**Never add** Google login · Google Identity · Firebase Auth · a Google private API · phone auth ·
OAuth social login. Credential Manager is password credential UX only and is **not** the identity
authority — KeepLab backend remains `IDENTITY_AUTHORITY`.

**Never log** a password · access token · refresh token · email verification secret · password-reset
secret · JWT signing secret · refresh pepper. No real credentials in source or evidence.

---

## 13. Test strategy (deterministic; no giant framework)

**Backend A3:** register · verify-email · unverified login rejection · verified login · wrong password ·
password reset · access token validation · refresh rotation · retry-safe same `refresh_request_id` ·
logout · per-session revoke.

**Backend A4:** authenticated mutation · atomic duplicate mutation dedupe · stale `baseRevision` → 409 ·
change cursor · tombstone · account isolation · failed apply does not advance the checkpoint where
applicable.

**Android JVM:** LOCAL_ONLY before login · sign-out preserves local data · sign-out preserves the
outbox · inactive-account rows not reassigned · signed-in new note becomes account scoped · outbox
creation · push success · pull success · 409 → `CONFLICT` · 404 does not delete · failed delta leaves the
checkpoint · remote-sync `accountId` non-null · refresh/session repository behaviour.

Use fakes and `MockEngine` where appropriate. Follow the existing test conventions
(`app/src/test/java/com/keeplab/app/Fakes.kt`, `MainDispatcherRule`, the backend's `ktor-server-test-host`
and injectable-probe pattern). No live network, no live PostgreSQL, no device, no instrumentation test.

**No live PostgreSQL blocker.** If this host has no Docker runtime and no `psql`, do not spend the
milestone installing infrastructure. Use deterministic backend/service tests. If a lightweight existing
mechanism can run real PostgreSQL cheaply it may be used **once**. Otherwise record
`LIVE_POSTGRES_INTEGRATION = SKIPPED_TOOL_UNAVAILABLE`. This does not block experimental M2 and does not
excuse a weaker transaction design.

Do not build a giant test framework.

---

## 14. Final verification — ONCE

After A3 and A4 are implemented, perform **ONE** Milestone verification pass:

**Backend**

```
cd /mnt/AndroidDev/Projects/KeepLab-Relay
./gradlew -p backend test build
```

**Android**

```
cd /mnt/AndroidDev/Projects/KeepLab-Relay
./gradlew :app:testDebugUnitTest :app:assembleDebug
```

Run each final gate **once**. Do **NOT** run them again after PASS.

If one fails: read the failure **once**, fix the **failed path only**, rerun **only the failed task**.
Do **NOT** rerun the already-passed side — a backend failure never justifies re-running the Android gate
and vice versa. Same failure after two genuine fixes: `REPEATED_FAILURE` and perform **ONE** root-cause
analysis.

Optional, at most once and only if genuinely cheap: a live PostgreSQL integration / crash-injection
check. Absent runtime → record the two `SKIPPED_TOOL_UNAVAILABLE` values.

### 14.1 Post-run proof

| Check | Requirement |
|---|---|
| `frozen_inputs` re-hashed | all byte-identical, `mismatches = []` |
| scope scan | every created/modified file inside `allowed_paths`; nothing under a forbidden path; `app/src/main/res/**`, `ui/theme/**`, `ui/common/**`, `androidTest/**`, `benchmark/**`, the root Gradle files and `reports/contracts/**` unchanged |
| secret scan | CLEAN; no real credential; no token/password/OTP plaintext anywhere in reports, evidence or logs |
| `backend/.env` | ABSENT |
| guard, hook config, allowlist, contract packages | byte-identical; this package not rewritten, re-hashed or extended |

---

## 15. Acceptance checklist (M2 PASS requires all of these)

D-01 honoured · D-04 honoured · D-10 honoured · registration works · email verification works
deterministically · login works · password reset works · JWT access token works · opaque refresh token
works · retry-safe refresh rotation works · logout works · per-session revoke works · `AUTH_REQUIRED`
does not delete local data · pre-login `LOCAL_ONLY` data is not silently adopted · Room remains the
local SSOT · outbox exists · single-account sync core exists · create/edit/archive/pin/colour/trash sync ·
checklist sync · label sync · atomic mutation dedupe · stale `baseRevision` → 409 · failed delta does not
advance the checkpoint · deleted note does not resurrect · 404 does not delete a live local row ·
remote-sync `accountId` is non-null · unique `note_sync` pipeline exists · Android app builds · backend
builds · relevant tests pass · no Google/Firebase auth · no cloud deployment · no device work.

Map each item to `AC-M2-001 … AC-M2-025` in `acceptance.md` and record the evidence.

---

## 16. Minor backlog

`MINOR_BACKLOG` no longer triggers cleanup by count. Do **not** stop because the backlog is 5, 10, 20 or
30 items. Only fix a backlog item if it blocks M2, breaks the build/tests, repeatedly slows development,
or is almost free inside an already-touched file. Otherwise append it compactly to
`reports/KEEPLAB-MINOR-BACKLOG.md` and continue.

## 17. Stop

`PASS = STOP.` After PASS: no post-PASS review, no second audit, no additional contract, no A5, no A6,
no A0/A1/A2 re-opened, no re-run of a passing task. Report the result and stop.
