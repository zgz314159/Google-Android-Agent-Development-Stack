# KEEPLAB-M4-ATTACHMENTS-EXECUTE

**The execution prompt for `KEEPLAB-M4-ATTACHMENTS-001`.**

Activate this contract and implement **M4 (A7 attachments) in ONE session**: the attachment
foundation, then the backend binary path, then the Android offline/upload/download path, then the
minimal UX, then **one** verification pass. `PASS = STOP`.

- **Milestone:** `M4 = A7_ATTACHMENTS`
- **Loop:** `PLAN ONCE → IMPLEMENT ATTACHMENT FOUNDATION → IMPLEMENT BACKEND BINARY PATH → IMPLEMENT ANDROID OFFLINE/UPLOAD/DOWNLOAD PATH → IMPLEMENT MINIMAL UX → VERIFY M4 ONCE → PASS = STOP`
- **Date (`D-13`):** 2026-10-06 (CST, UTC+08:00) · **Device:** `NOT_USED` · **Cloud:** `NOT_PROVISIONED`
- **Data stage:** `EXPERIMENTAL` — `DISPOSABLE_TEST_DATA`; `DEV_DATABASE_RESET_REQUIRED = YES`
- **Package:** `reports/contracts/KEEPLAB-M4-ATTACHMENTS-001/` — `READ_ONLY_INPUT`

---

## 0. What M4 is, and what it is not

**M4 IS:** A7 attachments end to end under D-13 — a server-configurable limit set; a portable
`ObjectStorage` abstraction with a filesystem development reference driver; a content-addressed,
append-only, account-authorized, deferred binary path; a durable app-private local attachment model
with streaming import, size enforcement, SHA-256 and signature-based MIME validation; a **separate**
resumable `attachment_sync` transfer pipeline so a pending binary never blocks note usability;
server-verified content addressing; same-account deduplication that never bypasses quota, count or
authorization; quota reservation inside one atomic boundary; safe removal and conservative orphan
handling; and a minimal attachment UX (attach an existing JPEG/PNG/WebP/PDF, show name/type/size/state,
Retry, Remove).

**M4 IS NOT:** a metadata contract; an upload contract; a download contract; a storage contract; an
Attachment/Storage/Upload Review; a post-PASS audit; a separate D-13 governance task; A8 multi-device;
A9 multi-account; collaboration; cloud deployment; release hardening; Tencent COS provisioning;
camera/drawing/voice/video capture; audio/video/octet-stream/executable/archive support; multipart or
cloud-presigned upload architecture; a production orphan scheduler; a push provider; Google Keep work;
Testapp or PowerAi.

```
ATTACHMENT METADATA IS NOT THE ATTACHMENT BINARY.
A PENDING UPLOAD NEVER BLOCKS THE NOTE (INVARIANT ATT-1).
DO NOT SPLIT METADATA/UPLOAD/DOWNLOAD INTO SEPARATE CONTRACTS OR REVIEWS.
```

## 1. Activation (do this before any write, then stop re-reading)

| # | Check | On failure |
|---|---|---|
| 1 | `HERMES_CONTRACT_PACKAGE` points at this package | set it (see `EXECUTOR-PROMPT.md`) |
| 2 | `sha256(contract_guard.py)` == `e418fc28b08ac7afe4fdd42ec44d572ddaa2f23f6200de300ecac211404b3746` | STOP — validated against a different guard |
| 3 | `pre_tool_call` hook wiring unchanged (`matcher write_file\|patch\|terminal`, `fail_closed: true`) | STOP |
| 4 | `load_contract(this package)` → `MANIFEST_OK`, `contract_id = KEEPLAB-M4-ATTACHMENTS-001` | STOP |
| 5 | Re-hash **every** `frozen_inputs` file **before the first write** | STOP — emit `STALE_M4_INPUT` |
| 6 | `KeepLab-Relay/backend/` present and buildable via `./gradlew -p backend` | STOP |
| 7 | The package must never be written: `reports/contracts/` is a forbidden path | STOP if a write is attempted |

Write the plan once, then execute it in order. Do not re-read the same architecture files
repeatedly. Do not perform a full repository scan.

## 2. Frozen human decision — `D-13` (honour it; never reinterpret it)

Record: `reports/KEEPLAB-M4-HUMAN-DECISIONS.md`.

```
D-13 = ATTACHMENT_LIMITS_V1
SOURCE = HUMAN_PROJECT_OWNER_APPROVAL
DATE = 2026-10-06

MAX_SINGLE_ATTACHMENT_BYTES    = 26214400        (25 MiB)
MAX_ATTACHMENTS_PER_NOTE       = 20
ACCOUNT_ATTACHMENT_QUOTA_BYTES = 1073741824      (1 GiB)
ALLOWED_MIME_TYPES             = image/jpeg, image/png, image/webp, application/pdf
LIMIT_AUTHORITY                = SERVER_CONFIGURABLE
```

- These limits **MUST be server-configurable**. The backend is authoritative.
- Android may pre-validate for UX using cached server limits or these D-13 defaults. Server
  enforcement is authoritative even when a cached client value is stale.
- **Out of scope, never add:** `audio/*`, `video/*`, `application/octet-stream`, arbitrary binary
  files, executables, archives (unless separately approved later).
- Never change a D-13 value and never add a fifth MIME type. That needs a new human decision.

### Quota semantics (frozen)

```
ACCOUNT_ATTACHMENT_QUOTA_BYTES = LOGICAL attachment bytes owned by the account
DUPLICATE FILES DO NOT BYPASS QUOTA
```

- If the same content hash is attached twice, storage **may** deduplicate the binary, but **both**
  logical attachment sizes count toward the 1 GiB account quota.
- **Pending upload reservations count while active**, so concurrent uploads cannot race past quota.
- Release the reservation safely on abort, expiry, or a failed initiation before commitment.

## 3. Decisions that stay pending and do NOT block M4

`D-05` account-deletion retention · `D-11` push provider · `D-12` collaboration ·
`D-14` formal spec package location. `SYNC_TOMBSTONE_RETENTION_OR_COMPACTION` remains a separate
`IMPLEMENTATION_DECISION_PENDING` concern and `TOMBSTONE_GC` stays `DISABLED`.

Do **not** implement account deletion, a push provider, collaboration, a formal spec relocation, a
tombstone retention duration or tombstone GC. Do **not** reopen A0/A1/A2/M2/M3 without new explicit
failure evidence.

## 4. Write surface

`allowed_paths` (project-relative to `/mnt/AndroidDev/Projects`):

```
KeepLab-Relay/backend/                                            <-- the whole backend directory
KeepLab-Relay/app/build.gradle.kts                                (only if a dependency change is proven required)
KeepLab-Relay/gradle/libs.versions.toml                           (only if a dependency change is proven required)
KeepLab-Relay/app/src/main/AndroidManifest.xml                    (only if genuinely needed)
KeepLab-Relay/app/src/main/java/com/keeplab/app/KeepLabApplication.kt
KeepLab-Relay/app/src/main/java/com/keeplab/app/MainActivity.kt
KeepLab-Relay/app/src/main/java/com/keeplab/app/data/             (incl. new data/attachment/)
KeepLab-Relay/app/src/main/java/com/keeplab/app/model/
KeepLab-Relay/app/src/main/java/com/keeplab/app/di/
KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/attachment/    <-- NEW; the minimal attachment surface
KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/settings/
KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/auth/
KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/navigation/
KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/trash/
KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/note/
KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/editor/
KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/home/
KeepLab-Relay/app/src/main/res/xml/                               (narrow carve-out; a FileProvider is NOT expected to be needed)
KeepLab-Relay/app/src/test/
Google-Android-Agent-Development-Stack/reports/
Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/keeplab-m4-attachments/
```

**Backend write surface: `KeepLab-Relay/backend/` (whole directory).** `ROOT_GRADLE_CHANGE: NO`.
The expected dependency change is **NO**: SHA-256 is `java.security.MessageDigest`, signature
validation is a byte comparison, the picker is `androidx.activity` (already pinned), and the server
needs only `ktor-server-core` plus JDK APIs. If a dependency addition is genuinely required, record
exactly what and why in the M4 report.

Blocked (do not write, do not "fix"): `app/src/main/res/drawable/`, `res/mipmap-anydpi/`,
`res/mipmap-anydpi-v26/`, `res/values/`, `res/values-night/`, `ui/theme/`, `ui/common/`,
`ui/conflict/`, `app/src/androidTest/`, `app/src/benchmark/`, `app/schemas/`, `proguard-rules.pro`,
the root Gradle files, the wrapper, `gradlew`, `specs/`, `verification/`, `harness/`, the governance
markdown, `Dockerfile`, `docker-compose.yml`, `server/`, `infra/`, `cloud/`, `firebase/`, `Testapp/`,
`PowerAi/`, the Stack's `specification/`, `verification/`, `verification-benchmark/`, `references/`,
`orchestration/hermes/evaluation_adapter/`, `evaluation/`, and **`reports/contracts/`**.

`KeepLab-Relay/app/**` is **not** broadly authorized — the surface is enumerated. A needed file
outside it is a STOP (`M4_SURFACE_BROADENING_REQUIRED`), never a silent broadening.

## 5. Phase 1 — attachment foundation (backend)

1. **Limits.** Add the server-configurable keys with the D-13 defaults, following the existing
   `ConfigKeys` + `fromEnvironment(env)` pattern (injectable env reader, tested deterministically):

   ```
   KEEPLAB_ATTACHMENT_MAX_BYTES            = 26214400
   KEEPLAB_ATTACHMENT_MAX_PER_NOTE         = 20
   KEEPLAB_ATTACHMENT_ACCOUNT_QUOTA_BYTES  = 1073741824
   KEEPLAB_ATTACHMENT_ALLOWED_MIME_TYPES   = image/jpeg,image/png,image/webp,application/pdf
   KEEPLAB_ATTACHMENT_CHUNK_BYTES          = 1048576
   KEEPLAB_ATTACHMENT_ORPHAN_GRACE_SECONDS = 86400
   ```

   `CHUNK_BYTES` and `ORPHAN_GRACE_SECONDS` are `IMPLEMENTATION_DEFAULTS`, not D-13 product
   decisions — but they must be configurable. A malformed value must fail loudly rather than
   silently defaulting.

2. **`.env.example`.** Document every new key with placeholders/defaults. **Never create
   `backend/.env`. Never commit a secret.**

3. **Config API.** `GET /v1/attachments/config` returns exactly `maxBytes`, `maxPerNote`,
   `accountQuotaBytes`, `allowedMimeTypes`, `preferredChunkBytes`. Expose **no** internal storage
   path. The Android client may cache it; the server stays authoritative.

4. **`ObjectStorage` abstraction.** A small port for the operations the domain needs (write/append
   at an offset, read a range, size, delete, exists). `FilesystemObjectStorage` is the
   development/test reference driver, configured by `KEEPLAB_OBJECT_STORAGE_DRIVER=filesystem` and
   `KEEPLAB_OBJECT_STORAGE_ROOT=<path>`. Attachment domain logic depends on `ObjectStorage` only —
   never on a cloud SDK and never on filesystem APIs directly. A `TencentObjectStorage` adapter is
   **not** written in M4.

5. **Persistence model + migrations.** Add only what A7 needs, after `V3`: attachment metadata
   (account-scoped: `account_id` + note identity + attachment UUID), the upload session / resume
   state, content objects for content addressing, quota reservation state, and orphan/abandoned
   state. Every attachment is scoped by account + note identity + attachment UUID.

## 6. Phase 2 — backend binary path

Implement one `AttachmentService` (or equivalent) over a store port with an in-memory implementation
for deterministic tests and a JDBC implementation for production, mirroring the existing
`SyncStore` / `InMemorySyncStore` / `JdbcSyncStore` split.

| Step | Required behaviour |
|---|---|
| Authorize | Resolve the account from the authenticated JWT subject only. A body `accountId` is never authority. The parent note (`noteClientUuid`, entity type `NOTE`) must belong to the authenticated account and not be tombstoned. |
| Initiate | `POST /v1/attachments/uploads` with `attachmentId`, `noteClientUuid`, `contentHash`, `sizeBytes`, `mimeType`, `displayName`. Reject a disallowed MIME, an oversize `sizeBytes`, the 21st attachment on the note and an over-quota logical total. **Reserve quota atomically in the same boundary that records the session.** Return `uploadId`, `chunkBytes`, `acceptedOffset`, and `deduplicated`/`uploadRequired`. |
| Append | `PUT /v1/attachments/uploads/{uploadId}` with `offset` + binary body. Only the owning account may append. The streamed bytes must be appended at the declared offset; a gap or an overrun is rejected. Enforce the size limit while streaming. |
| Status | `GET /v1/attachments/uploads/{uploadId}` returns the accepted offset and whether further bytes are required (a resumed client must be able to continue from the accepted offset). |
| Complete | `POST /v1/attachments/uploads/{uploadId}/complete` verifies the total byte count, the **server-computed SHA-256** against the declared hash, the MIME signature and the quota reservation. A mismatch is rejected and never becomes `UPLOADED`. |
| Content addressing | Object identity = account scope + verified hash; use a key shape like `accounts/<accountId>/sha256/<hash>`. The user filename is **never** the key and never a path component. Never accept `../`, a traversal or an absolute path from user metadata. |
| Dedupe | Within the same account, verified identical content may reuse the stored binary, but create independent attachment metadata and keep counting every logical attachment against quota and the per-note limit. Never leak whether another account has the same hash. |
| Download | `GET /v1/attachments/{attachmentId}/content` requires the authenticated account to own/access the parent note. No public anonymous object URL. |
| Remove | Remove attachment metadata for the owning account. An object with no remaining references becomes `ORPHAN_CANDIDATE`. Do **not** delete the binary unsafely inside the same metadata mutation unless transactional correctness is proven. |
| Orphans | `findOrphanCandidates()` and `cleanupEligibleOrphans()`. A binary is deletable only when no attachment metadata references it, no active upload owns it, and `KEEPLAB_ATTACHMENT_ORPHAN_GRACE_SECONDS` has elapsed. Cleanup must never corrupt a live note. No production scheduler. |
| Quota release | Release the reservation on abort, on expiry, and on a failed initiation before commitment. |

**Do not overbuild.** No multipart upload, no cloud-presigned URLs, no Tencent SDK dependency, no
production scheduler.

## 7. Phase 3 — Android local attachment model

1. **Room entity + DAO** with a **direct experimental schema bump** (current 5 → 6). No migration
   chain is authored; `exportSchema` stays false (MB-M3-009 stays a non-blocking backlog item).
   Minimum fields: stable client `attachmentId`, parent `noteId`/`noteClientUuid`, nullable
   `accountId`, app-private `localPath`, SHA-256 `contentHash`, `sizeBytes`, `mimeType`,
   `displayName`, `uploadState`, nullable `remoteObjectId`, `uploadedBytes`, nullable
   `lastErrorCode`, `createdAt`, and a removed state if required.

2. **Durable import.** When the user selects an allowed attachment, import the bytes into KeepLab
   app-private storage: stream, enforce the 25 MiB limit (including when the source size is
   unknown), compute SHA-256, verify the basic MIME signature, store safely. Do **not** depend
   permanently on the transient external content URI. An import failure must not corrupt note state
   and must not leave a partially-created usable row unless the state explicitly represents failure.

3. **MIME validation.** Signatures: JPEG `FF D8 FF`; PNG `89 50 4E 47 0D 0A 1A 0A` + `IHDR`; WebP
   `RIFF....WEBP`; PDF `%PDF-`. A mismatch with the declared/selected type is a `VALIDATION_ERROR`
   and is never uploaded. No executable-detection framework, no archives.

4. **States.** One small explicit set: `LOCAL_ONLY`, `UPLOAD_PENDING`, `UPLOADING`, `UPLOADED`,
   `DOWNLOAD_PENDING`, `DOWNLOADING`, `FAILED`, `REMOVED` (or project-style equivalents). Do not
   create dozens of states.

5. **Scope rules.** A `LOCAL_ONLY` note may hold `LOCAL_ONLY` attachments that stay fully local; a
   `LOCAL_ONLY` attachment is **never** silently adopted into an account and stays `LOCAL_ONLY` while
   its note does. An attachment on an account-scoped note becomes `UPLOAD_PENDING` and is eligible
   for deferred upload while the note stays immediately usable.

6. **Write path.** Attachment metadata mutations go through the existing single local write boundary
   (`LocalStore.writeAtomically`) with the parent-note context, so an attachment can never be
   recorded without its change (or the reverse). Preserve the existing `requireAccountForNonLocalState`
   style invariant: only `LOCAL_ONLY` may exist without an account.

## 8. Phase 4 — Android offline / upload / download path

1. **`attachment_sync` pipeline.** A durable attachment transfer pipeline **separate** from
   `note_sync`, with its own unique work name, network constraint and backoff, and its own persisted
   state (resume offset, `uploadId`, attempt count, last error). Never create a parallel duplicate
   upload for the same attachment. Do not change the `note_sync` pipeline's uniqueness or semantics.

2. **Upload.** Initiate (or resume) the session, append chunks from the persisted offset, and
   complete. Persist `uploadedBytes`/`uploadId`/`acceptedOffset` so a resumed run continues rather
   than restarts. On success set `UPLOADED` and record `remoteObjectId`.

3. **Download.** Stream to a temporary app-private file, verify SHA-256, and only then atomically
   replace/finalize the local attachment file. A hash mismatch is `FAILED` and must not replace
   known-good local data.

4. **Retry.** Reuse the M3 bounded-retry constants and classification; do not invent a second notion
   of retryability and do not create an infinite loop. Network, `429`, `5xx` → retryable. Bad MIME,
   oversize, quota exceeded, too many attachments → permanent, not retried forever. `AUTH_REQUIRED`
   → retain the local file, the metadata and the pending transfer.

5. **Network policy.** Background binary upload prefers `UNMETERED` where practical without making
   correctness depend forever on Wi-Fi. A manual Retry/Upload may request transfer under
   `CONNECTED`; a user-triggered download may use `CONNECTED`. No FCM, no push provider, no permanent
   background socket.

6. **Note usability.** Nothing in the attachment path may block the note: opening, editing
   title/body, editing the checklist, labelling, archiving, pinning and Trash must all still work
   while an attachment is pending, offline, failed or resuming.

7. **Remove.** Remove the attachment without deleting or corrupting the note; for a `LOCAL_ONLY`
   attachment remove the metadata and the app-private file safely; for an account-scoped uploaded
   attachment use the authenticated backend removal.

## 9. Phase 5 — minimal attachment UX

- Attach an **existing** file with Android `OpenDocument`/SAF (or another standard system picker)
  restricted to the D-13 MIME types. **Picker filtering is not security validation** — re-validate
  the content after selection.
- Show at minimum: display name, type, size, transfer state. Offer **Retry** when failed and
  **Remove**.
- Put the listing inside the editor/detail surface with tiny integration points; the new
  `ui/attachment/` package holds the attachment surface. Do not redesign the note editor, Home, the
  theme or the navigation architecture.
- A simple image thumbnail is allowed **only** if it requires no large unrelated UI or dependency
  work. When in doubt, skip it.
- **No** camera capture, drawing capture, voice recording or video capture.
- **No** broad storage permission: no `MANAGE_EXTERNAL_STORAGE`, no legacy storage permission.
- Add a navigation route only if the attachment surface genuinely needs one; a `FileProvider` is
  **not** expected to be needed (never add one speculatively).

## 10. Security rules (never violate)

```
NEVER trust a client accountId, a filename as a path, or Content-Type alone.
NEVER expose a filesystem object path.
NEVER serve an attachment anonymously.
NEVER log attachment bytes.
NEVER store cloud credentials on Android or embed a cloud key in the APK.
NEVER write a real backend/.env or a real credential into source, evidence or logs.
```

## 11. Test strategy

**Backend (deterministic, JUnit 5 + the in-process Ktor test host + the in-memory store, no live
PostgreSQL):** default D-13 config; server-configurable override; a malformed limit value failing
loudly; allowed MIME; blocked MIME; magic/signature mismatch; a single attachment over 25 MiB
rejected; the 21st attachment rejected; the 1 GiB quota enforced; a pending reservation participating
in quota; a reservation released safely; same-account content dedupe; dedupe not bypassing quota;
cross-account object/hash not exposed; upload initiate; chunk upload; resume offset; complete
verifying SHA-256; hash mismatch rejected; authorized download; cross-account download rejected;
removal not corrupting the note; a shared content object retained while referenced; an abandoned
upload becoming an orphan candidate; orphan cleanup never removing a referenced binary.

**Android (deterministic JVM, fakes / Ktor MockEngine, a temporary app-private directory, no
device):** allowed attachment import; disallowed MIME rejected; oversize streaming import rejected;
the app-private copy surviving loss of the source abstraction; SHA-256 computed; a `LOCAL_ONLY`
attachment not uploading; an account-scoped attachment → `UPLOAD_PENDING`; the note usable while an
upload is pending; the upload state surviving repository reconstruction; resume using the persisted
offset/`uploadId`; a temporary failure retaining the local file; `AUTH_REQUIRED` retaining the local
attachment; retry resuming; a successful upload → `UPLOADED`; download hash verification; a bad
downloaded hash not replacing local data; removal leaving the parent note intact; the server config
overriding a client default.

No giant test framework. No live PostgreSQL, no cloud, no device, no network.

## 12. Verification — ONCE

| Gate | Command | Runs |
|---|---|---|
| BACKEND | `cd /mnt/AndroidDev/Projects/KeepLab-Relay && ./gradlew -p backend test build` | **1** |
| ANDROID | `cd /mnt/AndroidDev/Projects/KeepLab-Relay && ./gradlew :app:testDebugUnitTest :app:assembleDebug` | **1** |

- On failure: read the failure once, fix the **failed path only**, re-run **only the failed task**.
- Never re-run the already-passed side.
- The same failure surviving two genuine fixes → `REPEATED_FAILURE` + **ONE** root-cause analysis.
- `LIVE_POSTGRES_INTEGRATION = SKIPPED_TOOL_UNAVAILABLE` (no docker, no podman, no psql). Never
  install infrastructure inside M4; never weaken the transactional quota semantics because of it.

**Post-run proof:** re-hash every `frozen_inputs` file (byte-identical), a scope scan (every
created/modified file inside `allowed_paths`, no forbidden path changed), a secret scan (no real
credential, no token plaintext, no attachment bytes), the two gate results, and the M4 report.

## 13. M4 acceptance checklist

```
[x] D-13 honoured exactly (25 MiB / 20 / 1 GiB / JPEG+PNG+WebP+PDF)
[x] limits server-configurable, backend authoritative
[x] 25 MiB server enforcement
[x] 20 attachments per note enforcement
[x] 1 GiB logical account quota enforcement
[x] pending reservation participates in quota and is released safely
[x] allowed MIME exactly JPEG/PNG/WebP/PDF
[x] audio / video / arbitrary binary not supported
[x] app-private durable local copy (independent of the picker URI)
[x] SHA-256 content addressing
[x] server verifies the uploaded hash
[x] portable ObjectStorage abstraction
[x] filesystem reference driver (development/test)
[x] tencent cloud NOT provisioned
[x] note remains usable during a pending upload
[x] LOCAL_ONLY attachment remains local
[x] deferred upload
[x] resumable upload (persisted offset / uploadId)
[x] download authorization
[x] cross-account download blocked
[x] download hash verification with atomic replace
[x] safe remove
[x] orphan handling (conservative, explicit service boundary)
[x] quota race protection (one atomic boundary)
[x] bounded attachment retry, no infinite loop
[x] AUTH_REQUIRED non-destructive
[x] minimal attachment UI
[x] no broad storage permission
[x] no Tencent/cloud credentials in the APK
[x] BACKEND gate PASS
[x] ANDROID gate PASS
[x] relevant tests PASS
[x] no device
[x] no A8, no cloud provisioning, no collaboration
```

## 14. Stop conditions

Stop and report rather than improvising when:

- a write would fall outside `allowed_paths` or inside a forbidden path (`CONTRACT_DEVIATION`);
- a `frozen_inputs` file has drifted (`STALE_M4_INPUT`);
- a root Gradle change would be needed (`M4_ROOT_GRADLE_CHANGE_REQUIRED`);
- an Android file outside the enumerated surface would be needed (`M4_SURFACE_BROADENING_REQUIRED`);
- a metadata/upload/download/storage contract, a review or a post-PASS audit is being created;
- the milestone is being split by phase or by media type;
- cloud provisioning, a cloud credential or a Tencent COS adapter would be needed;
- an object-storage SDK would have to become a production dependency of the domain logic;
- the device, adb, Maestro, UiAutomator, an instrumentation run or an APK install would be needed;
- Docker/podman/PostgreSQL would have to be installed;
- a real secret, a real `backend/.env` or a logged attachment byte range would have to be written;
- a quota check would have to leave the atomic boundary;
- the server would have to trust a client hash/filename/Content-Type;
- user metadata would have to influence a filesystem path;
- a cross-account download or hash disclosure would be possible;
- an attachment failure would have to block or roll back the note, or a `LOCAL_ONLY` attachment
  would have to be silently adopted into an account;
- orphan cleanup would have to delete a referenced binary or corrupt a live note;
- an unbounded retry loop or a forever-retried permanent failure would have to be introduced;
- a storage permission, a capture UX, or archive/executable/audio/video support would have to be
  added;
- a D-13 limit would have to change;
- Hermes config, the hook allowlist, Hermes core, `contract_guard.py`, the frozen P0B-CLOSE
  contract, an A0/A1/A2/M2/M3 package or this package would have to be modified;
- A0/A1/A2/M2/M3 would have to be reopened;
- a gate fix would have to reach outside `allowed_paths`;
- the same failure survived two genuine fixes (perform ONE RCA, do not restart M4);
- more than roughly 30 tool calls passed before meaningful product writes without a real blocker
  (`PROCESS_OVERHEAD_TOO_HIGH`);
- a minor wording/naming/warning issue is being turned into a contract (append it to
  `reports/KEEPLAB-MINOR-BACKLOG.md` instead);
- A8, A9, collaboration, cloud deployment or release hardening is being started.

## 15. Report

Write `reports/KEEPLAB-M4-ATTACHMENTS-EXECUTION.md` with: activation evidence; D-13 as honoured; the
final configuration values; the object-storage driver used; the persistence/migration facts; the
upload-protocol facts; the Android model/pipeline/UX facts; the test counts; the two gate results
(each once); the scope/secret scan results; `DEVICE = NOT_USED`; `CLOUD = NOT_PROVISIONED`; any
minor findings appended to `reports/KEEPLAB-MINOR-BACKLOG.md`; and the explicit statement that
`PASS = STOP`.

```
M4 RESULT: PASS = STOP.
No post-PASS review. No second audit. No metadata/upload/download sub-contract. No A8.
No re-run of a passed gate side. No re-opening of A0/A1/A2/M2/M3.
```
