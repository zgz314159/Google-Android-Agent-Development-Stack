# KEEPLAB-M4-ATTACHMENTS-EXECUTION

**Task:** `KEEPLAB-M4-ATTACHMENTS-EXECUTE` (the execution prompt of `KEEPLAB-M4-ATTACHMENTS-001`)
**Milestone:** `M4 = A7_ATTACHMENTS`
**Date (`D-13`):** 2026-10-06 (CST, UTC+08:00)
**Device:** `NOT_USED` · **Cloud:** `NOT_PROVISIONED`
**Loop executed once:** PLAN ONCE → ATTACHMENT FOUNDATION → BACKEND BINARY PATH → ANDROID
OFFLINE/UPLOAD/DOWNLOAD PATH → MINIMAL UX → VERIFY M4 ONCE → `PASS = STOP`

---

## 1. Activation evidence (before the first write)

| # | Check | Result |
|---|---|---|
| 1 | `HERMES_CONTRACT_PACKAGE` | points at `…/reports/contracts/KEEPLAB-M4-ATTACHMENTS-001` |
| 2 | `sha256(contract_guard.py)` | `e418fc28b08ac7afe4fdd42ec44d572ddaa2f23f6200de300ecac211404b3746` — **MATCH** |
| 3 | `pre_tool_call` wiring | `matcher write_file\|patch\|terminal`, `fail_closed: true` — **unchanged** |
| 4 | `load_contract(this package)` | `MANIFEST_OK` (5/5 entries), `contract_id = KEEPLAB-M4-ATTACHMENTS-001` |
| 5 | `frozen_inputs` re-hashed **before the first write** | **122/122 byte-identical**, 0 drift, 0 missing → no `STALE_M4_INPUT` |
| 6 | `KeepLab-Relay/backend/` present | yes — independent Gradle project, `./gradlew -p backend` |
| 7 | `reports/contracts/` | never written (READ_ONLY_INPUT honoured; the guard would have blocked it) |

The plan was written once to
`orchestration/hermes/evidence/keeplab-m4-attachments/PLAN.md` and then executed in phase order.

## 2. D-13 as honoured (never reinterpreted)

```
D-13 = ATTACHMENT_LIMITS_V1 · HUMAN_PROJECT_OWNER_APPROVAL · 2026-10-06
MAX_SINGLE_ATTACHMENT_BYTES    = 26214400        (25 MiB)
MAX_ATTACHMENTS_PER_NOTE       = 20
ACCOUNT_ATTACHMENT_QUOTA_BYTES = 1073741824      (1 GiB)
ALLOWED_MIME_TYPES             = image/jpeg, image/png, image/webp, application/pdf
LIMIT_AUTHORITY                = SERVER_CONFIGURABLE
```

- All four limits are **server-configurable**; the backend enforces them and is authoritative.
- No D-13 value was changed and no fifth MIME type was added. `audio/*`, `video/*`,
  `application/octet-stream`, arbitrary binary, executables and archives are not supported anywhere.
- Quota is **logical bytes**: a duplicate content hash may share one binary but every logical
  attachment still counts in full, and a **pending upload reservation counts while it is active**.
- `reports/KEEPLAB-M4-HUMAN-DECISIONS.md` (authored with the contract) is the decision record; it was
  read and honoured, not rewritten.

## 3. Final configuration values

`KEEPLAB_ATTACHMENT_MAX_BYTES=26214400` · `KEEPLAB_ATTACHMENT_MAX_PER_NOTE=20` ·
`KEEPLAB_ATTACHMENT_ACCOUNT_QUOTA_BYTES=1073741824` ·
`KEEPLAB_ATTACHMENT_ALLOWED_MIME_TYPES=image/jpeg,image/png,image/webp,application/pdf` ·
`KEEPLAB_ATTACHMENT_CHUNK_BYTES=1048576` (IMPLEMENTATION_DEFAULT) ·
`KEEPLAB_ATTACHMENT_ORPHAN_GRACE_SECONDS=86400` (IMPLEMENTATION_DEFAULT) ·
`KEEPLAB_OBJECT_STORAGE_DRIVER=filesystem` · `KEEPLAB_OBJECT_STORAGE_ROOT=build/keeplab-object-storage`.

A malformed value **fails loudly** (`IllegalArgumentException`) instead of silently defaulting —
proven by a test. `ConfigKeys` + `AppConfig.fromEnvironment(env)` follow the existing pattern with an
injectable env reader; `application.conf` and `backend/.env.example` mirror the same keys with
placeholders/defaults. **No real `backend/.env` was created and no secret was written anywhere.**

## 4. Object storage

- **Port:** `ObjectStorage` (`exists` / `size` / `append(offset)` / `read(offset,len)` / `delete`).
  Attachment domain logic depends on this port only — no cloud SDK, no filesystem API.
- **Driver used:** `FilesystemObjectStorage` — the development/test reference driver
  (`KEEPLAB_OBJECT_STORAGE_DRIVER=filesystem`). `InMemoryObjectStorage` is the deterministic-test
  driver. An unknown driver name fails loudly.
- **Keys:** server-shaped only, `accounts/<accountId>/sha256/<hash>`; `ObjectKeys.requireSafe` refuses
  an absolute path, a backslash, `.`/`..` and any unsafe segment, and the object key is never derived
  from a user filename.
- **A `TencentObjectStorage` adapter was NOT written.** No cloud resource, credential or SDK exists in
  the change set; `CLOUD = NOT_PROVISIONED`.

## 5. Persistence and migration facts

- Backend: **Flyway `V4__attachment_schema.sql`** (after `V3`). Tables:
  `attachment_quota(account_id, reserved_bytes, committed_bytes)`,
  `attachment_objects(account_id, object_key, content_hash, size_bytes, created_at)`,
  `attachments(account_id, attachment_id, note_client_uuid, …, state, created_at)`,
  `attachment_uploads(account_id, upload_id, …, accepted_offset, state, reserved_bytes)`,
  `attachment_orphans(account_id, object_key, created_at)`.
  `DEV_DATABASE_RESET_REQUIRED = YES`; no production migration complexity was built.
- Android: Room **schema 5 → 6 by a direct experimental bump** (attachments were absent). No migration
  chain was authored; `exportSchema` stays `false`; `MB-M3-009` remains a non-blocking backlog item.
  New `attachments` table (FK to `notes`, unique `attachmentId`) with `attachmentId`, `noteId`,
  `noteClientUuid`, nullable `accountId`, app-private `localPath`, `contentHash`, `sizeBytes`,
  `mimeType`, `displayName`, `uploadState`, nullable `remoteObjectId`, `uploadId`, `uploadedBytes`,
  nullable `lastErrorCode`, `attemptCount`, `createdAt`.
- Stores mirror the existing split: `AttachmentStore` port + `InMemoryAttachmentStore` (the executable
  specification) + `JdbcAttachmentStore` (production, one transaction with the account-usage row
  locked). `ParentNoteLookup` / `JdbcParentNoteLookup` supplies the parent-note authorization check.

## 6. Upload-protocol facts

| Step | Route | Behaviour |
|---|---|---|
| Config | `GET /v1/attachments/config` | exactly `maxBytes`, `maxPerNote`, `accountQuotaBytes`, `allowedMimeTypes`, `preferredChunkBytes` — no storage path, no driver, no root |
| Initiate | `POST /v1/attachments/uploads` | validates MIME/size, authorizes the account **from the JWT subject only** and the parent note as live, then **reserves quota, checks the per-note count and records the session in ONE atomic boundary**; returns `uploadId`, `chunkBytes`, `acceptedOffset`, `deduplicated`, `uploadRequired` |
| Append | `PUT /v1/attachments/uploads/{uploadId}?offset=` | owning account only, exact-offset append (gap/overrun refused), size enforced while streaming, `off`→offset advance |
| Status | `GET /v1/attachments/uploads/{uploadId}` | the durable resume point and whether more bytes are required |
| Complete | `POST /v1/attachments/uploads/{uploadId}/complete` | server recomputes SHA-256 over the stored bytes and re-validates the MIME signature and the byte count; a mismatch aborts, releases the reservation and **never becomes `UPLOADED`** |
| Download | `GET /v1/attachments/{attachmentId}/content` | authenticated + parent-note authorized; no anonymous URL and no object-path exposure |
| Remove | `DELETE /v1/attachments/{attachmentId}` | metadata only; an unreferenced object becomes an `ORPHAN_CANDIDATE`, never an unsafe inline delete |
| Orphans | service boundary | `findOrphanCandidates()` / `cleanupEligibleOrphans()` + `expireStaleUploads(ttl)`: deletable only when unreferenced, no active upload owns it and the grace elapsed. **No scheduler.** |

No multipart upload, no cloud-presigned URL, no Tencent SDK, no production orphan scheduler.

## 7. Android model / pipeline / UX facts

- **Local model.** `attachments` table + `AttachmentDao`; states `LOCAL_ONLY`, `UPLOAD_PENDING`,
  `UPLOADING`, `UPLOADED`, `DOWNLOAD_PENDING`, `DOWNLOADING`, `FAILED`, `REMOVED`. Metadata mutations go
  through `LocalStore.writeAtomically` together with a parent-note touch, so an attachment can never be
  recorded without its change. `requireAccountForAttachmentState` mirrors the M3 invariant: only
  `LOCAL_ONLY` may exist without an account.
- **Durable import.** `AttachmentImporter` streams the selected bytes into app-private
  `filesDir/keeplab-attachments`, enforces 25 MiB *while streaming* (an unknown source size cannot
  evade it), computes SHA-256 over exactly the bytes written, validates the real signature and only
  then renames the temporary file. The transient picker URI is never persisted, and every rejection
  path deletes its partial file.
- **MIME validation.** Signature-based (JPEG `FF D8 FF`, PNG signature + `IHDR`, WebP `RIFF….WEBP`,
  PDF `%PDF-`); a mismatch with the declared/selected type is a `VALIDATION_ERROR` and is never
  uploaded.
- **Transfer pipeline.** A **separate** durable `attachment_sync` pipeline (its own unique work name,
  own network preference, own persisted `uploadId` / `uploadedBytes` / `attemptCount` / `lastErrorCode`)
  beside the untouched `note_sync` pipeline. Background transfer prefers `UNMETERED`; a manual Retry or
  a user download may use `CONNECTED`. Retry reuses the M3 constants and classification
  (`AUTO_RETRY_MAX_ATTEMPTS = 5`, exponential backoff) — there is no second notion of retryability and
  no infinite loop. `AUTH_REQUIRED` retains the local file, the metadata and the pending transfer.
- **Download.** Streamed to a temporary file, SHA-256 verified, and only then atomically renamed over
  the local file; a bad hash is `FAILED` and never replaces known-good data.
- **UX.** `ui/attachment/AttachmentSection` inside the editor: attach an **existing** file through
  `ActivityResultContracts.OpenDocument` restricted to the four D-13 types, showing display name, type,
  size and transfer state, with **Retry** when failed and **Remove**. Picker filtering is explicitly not
  treated as validation. No camera/drawing/voice/video capture, no editor redesign, **no storage
  permission** (`AndroidManifest.xml` was not modified and no FileProvider was added — neither was
  needed), no cloud key in the APK.
- **ATT-1.** Attachment state lives entirely outside the note's own state; a pending, offline, failed
  or resuming transfer never blocks opening/editing the note, the checklist, labels, archive, pin or
  Trash — proven by a test that does all of those with a pending attachment.

## 8. Test counts

| Suite | Tests | Failures | Errors | Skipped |
|---|---|---|---|---|
| Backend (`backend/build/test-results/test`) | **95** | 0 | 0 | 0 |
| Android (`app/build/test-results/testDebugUnitTest`) | **183** | 0 | 0 | 0 |

New in M4: **33 backend** attachment tests (`AttachmentServiceTest`, `AttachmentRoutesTest`) and
**24 Android** attachment tests (`AttachmentModelTest`, `AttachmentTransferTest`). No giant test
framework; no live PostgreSQL, no cloud, no device, no network.

## 9. Gate results (each run once)

| Gate | Command | Runs | Result |
|---|---|---|---|
| BACKEND | `cd /mnt/AndroidDev/Projects/KeepLab-Relay && ./gradlew -p backend test build` | **1** | `BUILD SUCCESSFUL` |
| ANDROID | `cd /mnt/AndroidDev/Projects/KeepLab-Relay && ./gradlew :app:testDebugUnitTest :app:assembleDebug` | **1** | `BUILD SUCCESSFUL` (`app-debug.apk` built) |

`LIVE_POSTGRES_INTEGRATION = SKIPPED_TOOL_UNAVAILABLE` (no docker, no podman, no psql). No
infrastructure was installed and the transactional quota semantics were not weakened. The JDBC store
was developed against the same executable specification as the in-memory store and was never used to
justify weakening a check.

## 10. Post-run proof

- **Frozen inputs re-hashed after the run:** 122 total, 110 unchanged, 12 changed — and **every
  changed file lies inside `allowed_paths`** (the M3 baselines the contract explicitly permits the
  execution session to edit). No `frozen_inputs` file outside the write surface drifted.
- **Scope scan:** 43 files touched since the session start; **42 inside `allowed_paths`**; **no
  forbidden path written**. The single outside entry is
  `orchestration/hermes/evidence/p0b-close/contract-guard-decisions.jsonl` — the **guard's own audit
  log**, appended by the frozen `pre_tool_call` hook on every write-class call, not an M4 write
  (recorded as `MB-M4-007`).
- **Secret scan:** 42 session files scanned, **0 high-signal hits** (no AWS/Tencent key, no private
  key, no JWT literal, no long secret literal), **0 attachment-byte-logging sites**, no real
  `backend/.env`, no cloud credential.
- **Files created/modified** (all inside the enumerated surface):
  backend `attachment/` package (9 files) + `V4__attachment_schema.sql`,
  `config/AppConfig.kt`, `BackendServices.kt`, `Application.kt`, `routes/Routes.kt`,
  `application.conf`, `.env.example`, 3 backend test files;
  Android `data/local/AttachmentEntity.kt`, `AttachmentDao.kt`, `KeepLabDatabase.kt`, `NoteDao.kt`,
  `data/attachment/` (5 files), `data/remote/AttachmentApi.kt`, `data/sync/AttachmentSyncWork.kt`,
  `di/AttachmentModule.kt`, `ui/attachment/AttachmentSection.kt`, `ui/editor/{EditorScreen,EditorViewModel}.kt`,
  `MainActivity.kt`, test `Fakes.kt` + 4 test files.
- **Dependency change: NONE.** `app/build.gradle.kts` and `gradle/libs.versions.toml` were **not
  modified** — SHA-256 is `java.security.MessageDigest`, the MIME check is a byte comparison, the picker
  is `androidx.activity` (already pinned) and the server uses only `ktor-server-core` plus JDK APIs.
  `ROOT_GRADLE_CHANGE: NO`.
- **Device:** `NOT_USED` — no adb, no Maestro, no UiAutomator, no instrumentation, no APK install.
- **Cloud:** `NOT_PROVISIONED` — no Tencent COS, no CVM, no load balancer, no managed PostgreSQL, no
  cloud credential.

## 11. Minor findings

Appended to `reports/KEEPLAB-MINOR-BACKLOG.md` as `MB-M4-006` … `MB-M4-011` (HOCON mirror refreshed
by hand; the guard's own audit log sits outside `allowed_paths`; the `ObjectStorage` port returns
whole ranges; the client limits cache refreshes on demand; local-first removal of a never-uploaded
account-scoped attachment; the single-directory import with no startup `.part` sweep). All are
**non-blocking**; none was turned into a contract, review or audit.

## 12. Result

```
M4 RESULT: PASS = STOP.
```

No post-PASS review. No second audit. No metadata/upload/download sub-contract. No A8. No re-run of a
passed gate side. No re-opening of A0/A1/A2/M2/M3.
