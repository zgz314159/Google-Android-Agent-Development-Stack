# Acceptance — KEEPLAB-M4-ATTACHMENTS-001

**Contract:** `KEEPLAB-M4-ATTACHMENTS-001`
**Milestone:** `M4` = `A7_ATTACHMENTS` — **one** contract, **one** session, **one** verification pass
**Execution model:** `PLAN ONCE → IMPLEMENT ATTACHMENT FOUNDATION → IMPLEMENT BACKEND BINARY PATH → IMPLEMENT ANDROID OFFLINE/UPLOAD/DOWNLOAD PATH → IMPLEMENT MINIMAL UX → VERIFY M4 ONCE → PASS = STOP`
**Date:** 2026-10-06 (CST, UTC+08:00) · **Device:** `NOT_USED` · **Cloud:** `NOT_PROVISIONED`
**Data stage:** `EXPERIMENTAL` — `DISPOSABLE_TEST_DATA`; `DEV_DATABASE_RESET_REQUIRED = YES`
**Frozen human decision:** `D-13 = ATTACHMENT_LIMITS_V1` (`HUMAN_PROJECT_OWNER_APPROVAL`, 2026-10-06)

---

## What this package is

This package is a **TEMPORARY EXECUTION CONTRACT**. It exists so that a later **fresh** Hermes
session can implement A7 attachments through the **same unmodified Contract Guard**, under an
explicit and bounded write surface, with attachment metadata, the backend binary path and the
Android offline/upload/download path kept inside **one contract**, **one session** and **one**
final verification pass.

- `package_role`: `TEMPORARY_EXECUTION_CONTRACT`
- `package_access`: `READ_ONLY_INPUT` (enforced by `reports/contracts/` being a forbidden path)
- `implementation_authorization`: `GRANTED_TO_M4_EXECUTION_TASK_ONLY`
- This contract-creation task performed targeted discovery and authored the package. It did **not**
  implement M4, and it did **not** create a metadata contract, an upload contract, a download
  contract, a storage contract, an Attachment/Storage/Upload Review, a post-PASS audit or a
  separate D-13 governance task.

## Machine-readable semantics

| Key | Value |
|---|---|
| `contract_id` | `KEEPLAB-M4-ATTACHMENTS-001` |
| `milestone` | `M4 = A7 attachments` |
| `execution_model` | `PLAN ONCE → FOUNDATION → BACKEND BINARY PATH → ANDROID PATH → MINIMAL UX → VERIFY M4 ONCE → PASS = STOP` |
| `contracts_in_milestone` | `1` |
| `execution_sessions` | `1` |
| `verification_passes` | `1` |
| `metadata_upload_download_split` | `FORBIDDEN` |
| `root_gradle_change_required` | `NO` |
| `expected_dependency_change` | `NO` (the two Gradle files are conditionally authorized only) |
| `android_surface_policy` | `ENUMERATED_NOT_WHOLE_APP` |
| `object_storage` | `PORTABLE_ABSTRACTION` + `FILESYSTEM_DEV_TEST` reference driver |
| `tencent_cloud_provisioned` | `NO` |
| `device` | `NOT_USED` |
| `cloud` | `NOT_PROVISIONED` |
| `LIVE_POSTGRES_INTEGRATION` | `SKIPPED_TOOL_UNAVAILABLE` (no docker, no podman, no psql on this host) |
| `transfer_pipeline` | one durable `attachment_sync` pipeline beside the existing `note_sync` pipeline |
| `push_provider` | `FORBIDDEN` |

## Frozen human decision — `D-13` (do not reopen, do not reinterpret)

```
D-13 = ATTACHMENT_LIMITS_V1
SOURCE = HUMAN_PROJECT_OWNER_APPROVAL
DATE = 2026-10-06
RECORD = reports/KEEPLAB-M4-HUMAN-DECISIONS.md
```

| Key | Value |
|---|---|
| `MAX_SINGLE_ATTACHMENT_BYTES` | `26214400` (25 MiB) |
| `MAX_ATTACHMENTS_PER_NOTE` | `20` |
| `ACCOUNT_ATTACHMENT_QUOTA_BYTES` | `1073741824` (1 GiB) |
| `ALLOWED_MIME_TYPES` | `image/jpeg`, `image/png`, `image/webp`, `application/pdf` |
| `LIMIT_AUTHORITY` | `SERVER_CONFIGURABLE` — the backend is authoritative |

Out of scope and never to be added by M4: `audio/*`, `video/*`, `application/octet-stream`,
arbitrary binary files, executables, and archives unless separately approved later.

Android may pre-validate for UX using cached server limits or these D-13 defaults. **Server
enforcement remains authoritative** even when a cached client value is stale.

### Quota semantics (frozen)

```
ACCOUNT_ATTACHMENT_QUOTA_BYTES = LOGICAL_ATTACHMENT_BYTES_OWNED_BY_THE_ACCOUNT
```

- Duplicate files do **not** bypass the quota. If the same content hash is attached twice, storage
  **may** deduplicate the binary, but **both** logical attachment sizes count toward the 1 GiB
  account quota.
- A **pending upload reservation counts while active**, so concurrent uploads cannot race past the
  quota.
- On abort, expiry or a failed initiation before commitment, the reservation is released safely.

## What M4 must add — attachment foundation

| Area | Required behaviour |
|---|---|
| D-13 limits | exactly `26214400` / `20` / `1073741824` / JPEG+PNG+WebP+PDF, all `SERVER_CONFIGURABLE`, backend authoritative |
| Configuration keys | `KEEPLAB_ATTACHMENT_MAX_BYTES`, `KEEPLAB_ATTACHMENT_MAX_PER_NOTE`, `KEEPLAB_ATTACHMENT_ACCOUNT_QUOTA_BYTES`, `KEEPLAB_ATTACHMENT_ALLOWED_MIME_TYPES`, `KEEPLAB_ATTACHMENT_CHUNK_BYTES`, `KEEPLAB_ATTACHMENT_ORPHAN_GRACE_SECONDS` with the D-13 defaults and the recorded implementation defaults `CHUNK_BYTES = 1048576`, `ORPHAN_GRACE_SECONDS = 86400` |
| `backend/.env.example` | placeholders/default documentation for every new key; a real `backend/.env` is never created and no secret is committed |
| Config API | `GET /v1/attachments/config` returns `maxBytes`, `maxPerNote`, `accountQuotaBytes`, `allowedMimeTypes`, `preferredChunkBytes`; no internal storage path is exposed; the Android client may cache it |
| Object storage | a portable `ObjectStorage` abstraction; production business logic depends on it and never directly on a Tencent COS SDK, an AWS SDK or filesystem APIs; `FilesystemObjectStorage` is the development/test reference driver configured by `KEEPLAB_OBJECT_STORAGE_DRIVER` and `KEEPLAB_OBJECT_STORAGE_ROOT` |
| Cloud | no Tencent COS, no Tencent CVM, no load balancer, no managed PostgreSQL, no cloud credential, no cloud provisioning |

## What M4 must add — backend binary path

| Area | Required behaviour |
|---|---|
| Content addressing | SHA-256; the server verifies the **actual uploaded bytes** and never trusts only the client hash, the filename or the `Content-Type` header; object identity = account scope + verified hash (recommended key shape `accounts/<accountId>/sha256/<hash>`) |
| Path safety | the user filename is never the object key; no `../`, no path traversal and no absolute path from user metadata may influence a filesystem path |
| Persistence model | attachment metadata scoped by `accountId` + note identity + attachment UUID, upload-session state, content objects for content addressing, quota reservation state and orphan/abandoned state; new Flyway migrations after `V3` only as genuinely required |
| Initiate | `POST /v1/attachments/uploads` with `attachmentId`, `noteClientUuid`, `contentHash`, `sizeBytes`, `mimeType`, `displayName` → `uploadId`, `chunkBytes`, `acceptedOffset`, `deduplicated`/`uploadRequired` |
| Append | `PUT /v1/attachments/uploads/{uploadId}` with `offset` + binary body (or an equivalent clean Ktor route) |
| Status / resume | `GET /v1/attachments/uploads/{uploadId}` reports the accepted offset and whether further bytes are required |
| Complete | `POST /v1/attachments/uploads/{uploadId}/complete` verifies total byte count, SHA-256, MIME, quota reservation and note/account authorization; a hash mismatch is rejected |
| Configuration | the limits are read from server configuration at request time; a malformed value fails loudly instead of silently defaulting |
| Deduplication | within the same account verified identical content may reuse the stored binary, but independent metadata is still created and every logical attachment still counts against quota and the per-note limit; dedupe never bypasses quota, the 20-attachment limit or authorization; cross-account hash existence is never revealed |
| Download | `GET /v1/attachments/{attachmentId}/content` requires the authenticated account to own/access the parent note; no public anonymous object URL |
| Remove | removing an attachment never deletes or corrupts the note; an unreferenced object becomes `ORPHAN_CANDIDATE` and is not unsafely deleted inside the same metadata mutation unless transactional correctness is proven |
| Orphans | `findOrphanCandidates()` / `cleanupEligibleOrphans()`; a binary is deletable only when no metadata references it, no active upload owns it and the orphan grace has elapsed; cleanup never corrupts a live note; a full production scheduler is **not** built |
| Quota concurrency | reserve/check quota inside one atomic persistence boundary (never check-then-race-then-insert); concurrent initiation cannot exceed the 1 GiB logical account quota; `MAX_ATTACHMENTS_PER_NOTE = 20` is server enforced |
| Authorization | the account is derived from the authenticated JWT subject only; a client-supplied `accountId` is never authority |
| Overbuild guard | no multipart and no cloud-presigned architecture |

## What M4 must add — Android local model, transfer path and minimal UX

| Area | Required behaviour |
|---|---|
| Local model | stable client `attachmentId`, parent `noteId`/`noteClientUuid`, nullable `accountId`, app-private `localPath`, SHA-256 `contentHash`, `sizeBytes`, `mimeType`, `displayName`, `uploadState`, nullable `remoteObjectId`, `uploadedBytes`, nullable `lastErrorCode`, `createdAt`, removed state if required; the user filename is never the storage identity |
| Durable import | import/copy the selected bytes into app-private storage by **streaming**; never depend permanently on a transient external content URI; enforce the 25 MiB limit while streaming when the source size is unknown; compute SHA-256; verify the basic MIME signature; an import failure never corrupts note state and never leaves a partially-created usable row unless the state explicitly represents failure |
| MIME validation | signature-based on the real bytes: JPEG `FF D8 FF`, the PNG signature, WebP `RIFF....WEBP`, PDF `%PDF-`; a mismatch is a `VALIDATION_ERROR` and is not uploaded; no executable-detection framework and no archive support |
| `LOCAL_ONLY` | a `LOCAL_ONLY` note may hold fully local `LOCAL_ONLY` attachments; a `LOCAL_ONLY` attachment is never silently adopted into an account and stays `LOCAL_ONLY` while its parent note does |
| Account-scoped | a new valid attachment becomes `UPLOAD_PENDING` and is eligible for deferred upload; the note stays immediately usable; a network failure does not roll back note data and an upload failure does not mark the note unusable |
| States | a small explicit set: `LOCAL_ONLY`, `UPLOAD_PENDING`, `UPLOADING`, `UPLOADED`, `DOWNLOAD_PENDING`, `DOWNLOADING`, `FAILED`, `REMOVED` (or project-style equivalents) — not dozens of states |
| Transfer pipeline | one separate durable **`attachment_sync`** pipeline, distinct from the existing `note_sync` pipeline, persisting the resume offset/upload id; never a parallel duplicate upload for the same attachment |
| Network policy | background upload prefers `UNMETERED` where practical without making correctness depend forever on Wi-Fi; a manual Retry/Upload may use `CONNECTED`; a user-triggered download may use `CONNECTED`; no FCM, no push provider |
| Retry | bounded on the recorded M3 constants (`AUTO_RETRY_MAX_ATTEMPTS = 5`, exponential backoff); network/429/5xx retryable; bad MIME/oversize/quota-exceeded/too-many permanent; `AUTH_REQUIRED` retains the local file, the metadata and the pending transfer |
| Download | stream to a temporary app-private file, verify SHA-256, then atomically replace/finalize; a hash mismatch is `FAILED` and never replaces known-good local data |
| Note usability | `INVARIANT ATT-1`: a pending, offline, failed or resuming upload never blocks opening or editing the note, editing its checklist, labelling, archiving, pinning or trashing it |
| UX | attach an **existing** JPEG/PNG/WebP/PDF through the Android system document/file picker restricted to the D-13 types; show display name, type, size and transfer state; Retry when failed; Remove; content is re-validated after selection because picker filtering is not security validation |
| Not implemented | camera capture, drawing capture, voice recording, video capture, an editor redesign, a thumbnail that needs large unrelated work |
| Permissions | no `MANAGE_EXTERNAL_STORAGE` and no legacy storage permission |

## Allowed write surface (exhaustive)

Project-relative to `/mnt/AndroidDev/Projects` (the Contract Guard's `source_root`). A path matching
neither list is BLOCKED (`UNCLASSIFIED_FAIL_CLOSED`); `forbidden_paths` is tested first.

```
KeepLab-Relay/backend/                                        <-- the whole backend directory
KeepLab-Relay/app/build.gradle.kts                            (only if a dependency change is proven required)
KeepLab-Relay/gradle/libs.versions.toml                       (only if a dependency change is proven required)
KeepLab-Relay/app/src/main/AndroidManifest.xml                (only if genuinely needed)
KeepLab-Relay/app/src/main/java/com/keeplab/app/KeepLabApplication.kt   (only if genuinely needed)
KeepLab-Relay/app/src/main/java/com/keeplab/app/MainActivity.kt         (only if genuinely needed)
KeepLab-Relay/app/src/main/java/com/keeplab/app/data/         (incl. new data/attachment/)
KeepLab-Relay/app/src/main/java/com/keeplab/app/model/
KeepLab-Relay/app/src/main/java/com/keeplab/app/di/
KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/attachment/   <-- NEW; the minimal attachment surface
KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/settings/
KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/auth/
KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/navigation/
KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/trash/
KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/note/
KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/editor/
KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/home/
KeepLab-Relay/app/src/main/res/xml/                           (narrow carve-out; a FileProvider is NOT expected to be needed)
KeepLab-Relay/app/src/test/
Google-Android-Agent-Development-Stack/reports/
Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/keeplab-m4-attachments/
```

**Backend write surface: `KeepLab-Relay/backend/` (whole directory).** `ROOT_GRADLE_CHANGE: NO`.

Blocked (do not write, do not "fix"): `app/src/main/res/drawable/`, `res/mipmap-anydpi/`,
`res/mipmap-anydpi-v26/`, `res/values/`, `res/values-night/`, `ui/theme/`, `ui/common/`,
`ui/conflict/` (M3's surface), `app/src/androidTest/`, `app/src/benchmark/`, `app/schemas/`,
`proguard-rules.pro`, the root Gradle files, the wrapper, `gradlew`, `specs/`, `verification/`,
`harness/`, the governance markdown, `Dockerfile`, `docker-compose.yml`, `server/`, `infra/`,
`cloud/`, `firebase/`, `Testapp/`, `PowerAi/`, the Stack's `specification/`, `verification/`,
`verification-benchmark/`, `references/`, `orchestration/hermes/evaluation_adapter/`,
`evaluation/`, and **`reports/contracts/`** (so this package is a read-only input to its own
execution session).

`KeepLab-Relay/app/**` is **not** authorized as a whole. Themes, shared widgets, the other resource
directories, the M3 conflict surface, `androidTest`, `benchmark` and schema exports are blocked. A
needed change there is a STOP (`M4_SURFACE_BROADENING_REQUIRED`), not a silent broadening.

## Acceptance Criteria

### AC-M4-001 — D-13 honoured exactly and configurable

`PASS` requires the D-13 values (`26214400` / `20` / `1073741824` / JPEG+PNG+WebP+PDF) to be the
server defaults and every one of them to be overridable through the documented configuration keys
with the backend authoritative. Evidence: the backend configuration and its deterministic tests.

### AC-M4-002 — 25 MiB single-attachment enforcement

`PASS` requires the server to reject a single attachment larger than `26214400` bytes, using configured
limits rather than a client claim, proven by a deterministic test.

### AC-M4-003 — 20 attachments per note enforced

`PASS` requires the server to reject the 21st attachment on one note, proven by a deterministic test.

### AC-M4-004 — 1 GiB logical account quota enforced

`PASS` requires the `1073741824` logical account quota to be enforced, with duplicate content still
counting twice and a pending upload reservation counting while active.

### AC-M4-005 — allowed MIME exactly JPEG/PNG/WebP/PDF

`PASS` requires exactly `image/jpeg`, `image/png`, `image/webp` and `application/pdf` to be allowed,
and audio, video, `application/octet-stream`, arbitrary binary, executable and archive content to be
rejected.

### AC-M4-006 — server-configurable limits and `.env.example`

`PASS` requires every attachment limit to be configurable through the documented environment keys,
`backend/.env.example` to carry placeholders/default documentation for them, no real `backend/.env`
to exist, and no secret to be committed.

### AC-M4-007 — attachment configuration endpoint

`PASS` requires `GET /v1/attachments/config` to return `maxBytes`, `maxPerNote`,
`accountQuotaBytes`, `allowedMimeTypes` and `preferredChunkBytes` and to expose no internal storage
path; the Android client may cache it and the server stays authoritative.

### AC-M4-008 — portable object-storage abstraction

`PASS` requires an `ObjectStorage` abstraction that the attachment domain logic depends on, a
`FilesystemObjectStorage` development/test reference driver configured by
`KEEPLAB_OBJECT_STORAGE_DRIVER` and `KEEPLAB_OBJECT_STORAGE_ROOT`, and **no** direct dependency of
the domain logic on a cloud SDK or on filesystem APIs.

### AC-M4-009 — no cloud provisioning

`PASS` requires that no cloud resource is provisioned (no Tencent COS, no Tencent CVM, no load
balancer, no managed PostgreSQL, no cloud credential) and that M4 passes without any of them.

### AC-M4-010 — verified content addressing and path safety

`PASS` requires SHA-256 content addressing with the object identity derived from account scope plus
the **server-verified** hash; the server must verify the actual uploaded bytes rather than trusting
only the client hash, the filename or the `Content-Type` header; the user filename must never be the
object key; and no `../`, path traversal or absolute path from user metadata may influence a
filesystem path.

### AC-M4-011 — resumable upload session protocol

`PASS` requires initiate (`POST /v1/attachments/uploads` returning `uploadId`, `chunkBytes`,
`acceptedOffset` and `deduplicated`/`uploadRequired`), chunk append (`PUT` with `offset` and a binary
body), status (`GET`) and complete (`POST .../complete`), with no multipart or cloud-presigned
architecture.

### AC-M4-012 — complete verifies everything

`PASS` requires `complete` to verify the total byte count, the SHA-256, the MIME, the quota
reservation and note/account authorization, and a hash mismatch to be rejected so that it can never
become an `UPLOADED` attachment.

### AC-M4-013 — resume works

`PASS` requires the accepted offset and `uploadId` to be persisted and reported, so a resuming client
resumes from the accepted offset, and a fully-uploaded or deduplicated object to report that no
further bytes are required.

### AC-M4-014 — dedupe without bypass

`PASS` requires that within one account verified identical content may reuse the stored binary while
independent attachment metadata is still created and every logical attachment still counts against
the account quota and the per-note limit, and that deduplication cannot bypass quota, the 20-attachment
limit or authorization.

### AC-M4-015 — cross-account hash non-disclosure

`PASS` requires the service never to reveal whether another account already has an identical content
hash.

### AC-M4-016 — authorized download

`PASS` requires `GET /v1/attachments/{attachmentId}/content` to serve only an authenticated account
that owns or can access the attachment's parent note, to reject a cross-account download, and to
expose no public anonymous object URL.

### AC-M4-017 — quota race protected

`PASS` requires the quota to be reserved and checked inside one atomic persistence boundary rather
than check-then-race-then-insert, concurrent upload initiation not to exceed the 1 GiB logical
account quota, and a reservation to be released on abort, expiry or a failed initiation before
commitment. A deterministic concurrency/service test proves it or records the limit of what the
current backend test architecture can prove.

### AC-M4-018 — conservative orphan handling

`PASS` requires abandoned uploads, failed metadata finalization, removal and still-referenced
deduplicated binaries to be handled conservatively: a binary is deletable only when no attachment
metadata references it, no active upload owns it and the orphan grace has elapsed;
`findOrphanCandidates()` and `cleanupEligibleOrphans()` are the service boundary; cleanup never
corrupts a live note; no production scheduler is required.

### AC-M4-019 — safe removal

`PASS` requires removing an attachment never to delete or corrupt the note, an account-scoped
uploaded attachment to be removed through authenticated backend semantics, an unreferenced object to
become `ORPHAN_CANDIDATE` rather than being deleted unsafely inside the same metadata mutation (unless
transactional correctness is proven), and a `LOCAL_ONLY` attachment to remove its metadata and its
app-private file safely.

### AC-M4-020 — server-derived authorization

`PASS` requires the account to be derived from the authenticated JWT subject only, a client-supplied
`accountId` never to be authority, and upload/download additionally to require ownership of the
parent note.

### AC-M4-021 — note usability invariant

`PASS` requires that while an attachment upload is pending, offline, failed or resuming the user can
still open the note and edit title/body/checklist, label, archive, pin and Trash it, with attachment
failure staying attachment-local.

### AC-M4-022 — durable app-private import

`PASS` requires the selected bytes to be imported into app-private storage by streaming, without a
permanent dependency on a transient external content URI; the 25 MiB limit to be enforced while
streaming when the source size is unknown; SHA-256 to be computed; the basic MIME signature to be
verified; and an import failure neither to corrupt note state nor to leave a partially-created usable
attachment row unless the state explicitly represents failure.

### AC-M4-023 — signature-based MIME validation

`PASS` requires magic/signature validation of the real bytes (JPEG `FF D8 FF`, the PNG signature,
WebP `RIFF....WEBP`, PDF `%PDF-`), a MIME/header mismatch to be a `VALIDATION_ERROR` that is not
uploaded, and no executable-detection framework or archive support to be added.

### AC-M4-024 — clean local attachment model

`PASS` requires a local attachment model with the minimum concepts (stable client `attachmentId`,
parent note identity, nullable `accountId`, app-private `localPath`, SHA-256 `contentHash`,
`sizeBytes`, `mimeType`, `displayName`, `uploadState`, nullable `remoteObjectId`, `uploadedBytes`
resume state, nullable `lastErrorCode`, `createdAt`, removed state if required) and the user filename
never used as the storage identity.

### AC-M4-025 — LOCAL_ONLY attachments stay local

`PASS` requires a `LOCAL_ONLY` note's attachments to remain fully local with no account and no
upload, no silent adoption of a `LOCAL_ONLY` attachment into an account, and the attachment to stay
`LOCAL_ONLY` while its parent note does.

### AC-M4-026 — account-scoped attachment is deferred, not blocking

`PASS` requires a new valid attachment on an account-scoped note to become `UPLOAD_PENDING` and be
eligible for deferred upload while the note remains immediately usable, a network failure not to roll
back note data, and an upload failure not to mark the note unusable.

### AC-M4-027 — small explicit state model, persisted

`PASS` requires the small explicit state set (`LOCAL_ONLY`, `UPLOAD_PENDING`, `UPLOADING`,
`UPLOADED`, `DOWNLOAD_PENDING`, `DOWNLOADING`, `FAILED`, `REMOVED` or project-style equivalents) and
the state to survive repository reconstruction because it is persisted.

### AC-M4-028 — separate `attachment_sync` pipeline

`PASS` requires binary transfer to use its own durable `attachment_sync` pipeline, distinct from the
existing `note_sync` pipeline, persisting the resume offset/upload id, and never creating a parallel
duplicate upload for the same attachment.

### AC-M4-029 — network policy, no push

`PASS` requires background upload to prefer `UNMETERED` where practical without making correctness
depend forever on Wi-Fi, a manual Retry/Upload to be able to use `CONNECTED`, a user-triggered
download to be able to use `CONNECTED`, and no FCM or push provider of any kind.

### AC-M4-030 — bounded attachment retry, non-destructive auth failure

`PASS` requires bounded retry on the recorded M3 constants with no new infinite loop; network, 429
and 5xx to stay retryable; bad MIME, oversize, quota-exceeded and too-many-attachments not to be
retried forever; and `AUTH_REQUIRED` to retain the local file, the metadata and the pending transfer.

### AC-M4-031 — minimal attachment UX

`PASS` requires the user to be able to attach an **existing** JPEG/PNG/WebP/PDF through the Android
system document/file picker restricted to the D-13 types, to see display name, type, size and
transfer state, to Retry a failed attachment and to Remove it, with the selected content re-validated
after selection. Camera, drawing, voice and video capture must not exist and the note editor must not
be redesigned.

### AC-M4-032 — no broad storage permission

`PASS` requires that no `MANAGE_EXTERNAL_STORAGE` and no legacy storage permission is requested for
attachments.

### AC-M4-033 — verified download, atomic replace

`PASS` requires the Android download to stream to a temporary app-private file, verify SHA-256, and
only then atomically replace/finalize the local attachment file, and a failed hash validation to
become `FAILED` without replacing known-good local data.

### AC-M4-034 — backend test matrix

`PASS` requires deterministic backend tests covering: default D-13 config; server-configurable
override; allowed MIME; blocked MIME; magic/signature mismatch; a single attachment over 25 MiB
rejected; the 21st attachment rejected; the 1 GiB quota enforced; a pending reservation participating
in quota; a quota reservation released safely; same-account content dedupe; dedupe not bypassing
quota; cross-account object/hash not exposed; upload initiate; chunk upload; resume offset; complete
verifying SHA-256; hash mismatch rejected; authorized download; cross-account download rejected;
removal not corrupting the note; a shared content object retained while referenced; an abandoned
upload becoming an orphan candidate; and orphan cleanup never removing a referenced binary.

### AC-M4-035 — Android test matrix

`PASS` requires deterministic Android tests covering: allowed attachment import; disallowed MIME
rejected; oversize streaming import rejected; the app-private copy surviving loss of the source
abstraction; SHA-256 computed; a `LOCAL_ONLY` attachment not uploading; an account-scoped attachment
becoming `UPLOAD_PENDING`; the note usable while an upload is pending; the upload state surviving
repository reconstruction; resume using the persisted offset/`uploadId`; a temporary failure
retaining the local file; `AUTH_REQUIRED` retaining the local attachment; retry resuming; a
successful upload becoming `UPLOADED`; download hash verification; a bad downloaded hash not
replacing local data; removal leaving the parent note intact; and the server config overriding a
client default.

### AC-M4-036 — device-free

`PASS` requires that no adb, no Maestro, no UiAutomator, no instrumentation run and no APK
installation was used: `DEVICE = NOT_USED`.

### AC-M4-037 — one verification pass, PASS = STOP

`PASS` requires each final gate to run exactly once, a failure to fix the failed path only and re-run
only the failed task, the already-passed side never to be re-run, and `PASS` to mean `STOP` with no
post-PASS review and no second audit.

### AC-M4-038 — no A8/A9 and no out-of-scope work

`PASS` requires that no A8 multi-device, no A9 multi-account, no collaboration, no cloud deployment,
no release hardening and no Google Keep work was started, and that `Testapp` and `PowerAi` were never
touched.

### AC-M4-039 — contract, guard and prior phases untouched

`PASS` requires this package to remain `READ_ONLY_INPUT`, the Contract Guard and the hook wiring to
be unmodified, Hermes core not to be patched, the frozen `P0B-CLOSE` contract and the A0/A1/A2/M2/M3
packages to be byte-identical, and no prior phase to be reopened without new explicit failure
evidence.

### AC-M4-040 — no secrets, no logged attachment bytes

`PASS` requires no cloud credential, no real `backend/.env`, no committed secret, no token plaintext
and no logged attachment byte range in source, evidence or logs, and that object-storage credentials
(when production exists later) belong only to backend infrastructure and never to the APK.

## Verification

| Gate | Command | Runs |
|---|---|---|
| BACKEND | `cd /mnt/AndroidDev/Projects/KeepLab-Relay && ./gradlew -p backend test build` | 1 |
| ANDROID | `cd /mnt/AndroidDev/Projects/KeepLab-Relay && ./gradlew :app:testDebugUnitTest :app:assembleDebug` | 1 |

`LIVE_POSTGRES_INTEGRATION = SKIPPED_TOOL_UNAVAILABLE` on this host (no docker, no podman, no psql);
absence is never a blocker, no infrastructure is installed inside M4, and the transactional quota
semantics are not weakened.

Post-run proof: re-hashed frozen inputs (byte-identical), a scope scan (changes only inside
`allowed_paths`), a secret scan, the two gate results and the M4 report under
`Google-Android-Agent-Development-Stack/reports/` and
`Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/keeplab-m4-attachments/`.

## Out of scope (must not start)

```
A8 multi-device · A9 multi-account · collaboration and sharing · cloud deployment ·
release hardening · Tencent COS provisioning · camera/drawing/voice/video capture ·
audio/video/application-octet-stream/executable/archive support ·
multipart or cloud-presigned upload architecture · a production orphan scheduler ·
FCM or any push provider · a permanent background socket · account deletion ·
production email · Google/Firebase identity · room encryption claims · tombstone GC ·
Google Keep work · Testapp · PowerAi
```

```
M4 RESULT EXPECTATION: PASS = STOP.
No post-PASS review. No second audit. No metadata/upload/download sub-contract. No A8.
No re-run of a passed gate side. No re-opening of A0/A1/A2/M2/M3.
```
