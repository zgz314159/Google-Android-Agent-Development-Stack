# EXECUTOR-PROMPT — KEEPLAB-M4-ATTACHMENTS-001

**The future execution prompt for this contract is:**

`Google-Android-Agent-Development-Stack/reports/contracts/KEEPLAB-M4-ATTACHMENTS-001/KEEPLAB-M4-ATTACHMENTS-EXECUTE.md`

**Execution status in this phase:** `NOT_EXECUTED`.

This contract-creation phase performed targeted discovery and authored the package. It did not
implement M4. Running it is a separate, explicitly-authorized task
(`KEEPLAB-M4-ATTACHMENTS-EXECUTE`) in a **fresh** Hermes session.

## How a future session activates this contract

The Contract Guard resolves its package as:

```
package_dir = os.environ.get("HERMES_CONTRACT_PACKAGE") or DEFAULT_PACKAGE
```

`DEFAULT_PACKAGE` is the frozen P0B-CLOSE package. The switch is therefore the guard's own
**`HERMES_CONTRACT_PACKAGE`** environment variable, inherited by the hook subprocess from the
Hermes process environment. Point the Hermes process at this package before starting the M4
execution session:

```
export HERMES_CONTRACT_PACKAGE=/mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack/reports/contracts/KEEPLAB-M4-ATTACHMENTS-001
```

That is the whole mechanism: **same guard, same fail-closed hook, different package.** No guard
patch, no hook edit, no config edit, no file rename, no out-of-project write-and-copy. Unsetting
the variable returns the guard to the frozen P0B-CLOSE contract.

## Guard identity this contract was validated against

| Item | Value |
|---|---|
| guard source | `orchestration/hermes/evaluation_adapter/contract_guard.py` |
| guard version | `p0b-close-1` |
| guard sha256 | `e418fc28b08ac7afe4fdd42ec44d572ddaa2f23f6200de300ecac211404b3746` |
| hook event | `pre_tool_call` |
| matcher | `write_file\|patch\|terminal` |
| fail_closed | `true` |
| hook config modified | NO |

If the guard sha256 differs when the M4 session starts, the contract was validated against a
different guard: STOP.

## Recorded before execution is allowed

| Field | Value |
|---|---|
| `MILESTONE` | `M4` = `A7_ATTACHMENTS` |
| `EXECUTION_MODEL` | `PLAN ONCE → IMPLEMENT ATTACHMENT FOUNDATION → IMPLEMENT BACKEND BINARY PATH → IMPLEMENT ANDROID OFFLINE/UPLOAD/DOWNLOAD PATH → IMPLEMENT MINIMAL UX → VERIFY M4 ONCE → PASS = STOP` |
| `CONTRACTS` | exactly ONE (this one). No metadata contract, no upload contract, no download contract, no storage contract, no Attachment/Storage/Upload Review, no post-PASS audit, no separate D-13 governance task. |
| `HUMAN_DECISION` | `D-13 = ATTACHMENT_LIMITS_V1` (`HUMAN_PROJECT_OWNER_APPROVAL`, 2026-10-06) |
| `ATTACHMENT_LIMITS` | `MAX_SINGLE = 26214400` · `MAX_PER_NOTE = 20` · `ACCOUNT_QUOTA = 1073741824` · `ALLOWED_MIME = image/jpeg,image/png,image/webp,application/pdf` · `LIMIT_AUTHORITY = SERVER_CONFIGURABLE` |
| `QUOTA_SEMANTICS` | LOGICAL bytes; duplicates do not bypass; a pending reservation counts while active and is released on abort/expiry/failed initiation |
| `OUT_OF_SCOPE_MIME` | `audio/*`, `video/*`, `application/octet-stream`, arbitrary binary, executables, archives |
| `OBJECT_STORAGE` | `PORTABLE_ABSTRACTION` (`ObjectStorage`) + `FILESYSTEM_DEV_TEST` reference driver (`KEEPLAB_OBJECT_STORAGE_DRIVER`, `KEEPLAB_OBJECT_STORAGE_ROOT`) |
| `TENCENT_CLOUD_PROVISIONED` | `NO` — no cloud resource, no cloud credential, no Tencent COS adapter |
| `PROJECT_DATA_STAGE` | `EXPERIMENTAL` — `DISPOSABLE_TEST_DATA`; `DEV_DATABASE_RESET_REQUIRED = YES` |
| `ROOM_SCHEMA` | current 5 → next clean version by direct experimental bump; no migration chain; `exportSchema` stays false |
| `BACKEND_SCHEMA` | new Flyway migrations after `V3` only as genuinely required |
| `BACKEND_PATH` | `/mnt/AndroidDev/Projects/KeepLab-Relay/backend/` — `PRESENT` |
| `BACKEND_BUILD_MODEL` | `INDEPENDENT_GRADLE_PROJECT` (reuse `./gradlew -p backend`) |
| `ROOT_ANDROID_GRADLE_CHANGE` | `NO` — required outcome; a needed root change is a STOP (`M4_ROOT_GRADLE_CHANGE_REQUIRED`) |
| `EXPECTED_GRADLE_CHANGE` | `NO` dependency change expected; `app/build.gradle.kts` + `gradle/libs.versions.toml` are conditionally authorized only, and any addition must be recorded |
| `ANDROID_SURFACE` | `ENUMERATED_NOT_WHOLE_APP` (see `allowed_paths`, incl. the new `ui/attachment/` and a narrow `res/xml/` carve-out) |
| `CONTENT_ADDRESSING` | SHA-256; the server verifies the uploaded bytes; object key = account scope + verified hash; the filename is never a path component |
| `DEDUPE` | same-account binary reuse allowed; independent metadata always created; quota/count/authorization never bypassed; cross-account hash existence never revealed |
| `UPLOAD_PROTOCOL` | initiate → append(offset) → status/resume → complete; no multipart, no cloud-presigned architecture |
| `DOWNLOAD` | authenticated, parent-note authorized, no anonymous URL; Android verifies SHA-256 then atomically replaces |
| `QUOTA_CONCURRENCY` | reserve/check inside ONE atomic persistence boundary; never check-then-race-then-insert |
| `ORPHANS` | conservative; `findOrphanCandidates()` / `cleanupEligibleOrphans()`; deletable only when unreferenced + no active upload + grace elapsed; no production scheduler |
| `NOTE_USABILITY` | `INVARIANT ATT-1` — a pending/offline/failed/resuming upload never blocks note use |
| `TRANSFER_PIPELINE` | one durable `attachment_sync` pipeline beside the existing `note_sync` pipeline; never a duplicate upload for the same attachment |
| `MIME_VALIDATION` | signature-based (JPEG `FF D8 FF`, PNG signature, WebP `RIFF....WEBP`, PDF `%PDF-`); mismatch = `VALIDATION_ERROR`; extension alone is never trusted |
| `RETRY` | bounded on the M3 constants (`AUTO_RETRY_MAX_ATTEMPTS = 5`, exponential backoff); no infinite loop; `AUTH_REQUIRED` retains local file + metadata + pending transfer |
| `NETWORK` | background prefers `UNMETERED`; manual retry and user download may use `CONNECTED`; no FCM, no push |
| `UX` | system picker restricted to the D-13 types; show name/type/size/state; Retry; Remove; no capture UX; no editor redesign |
| `PERMISSIONS` | no `MANAGE_EXTERNAL_STORAGE`, no legacy storage permission |
| `CLOUD_PROVISIONING` | `BLOCK` |
| `DEVICE` | `NOT_USED` (M4 is device-free: no adb, no Maestro, no UiAutomator, no APK install) |
| `LIVE_POSTGRES` | optional at most once; absence → `SKIPPED_TOOL_UNAVAILABLE`, never a blocker; never install infrastructure |
| `GATES` | `./gradlew -p backend test build` (once) and `./gradlew :app:testDebugUnitTest :app:assembleDebug` (once) |
| `STOPS_AFTER` | M4 (A7 attachments verified once) |
| `MUST_NOT_START` | A8 multi-device · A9 multi-account · collaboration · cloud deployment · release hardening |

## Forbidden behaviour

- no metadata contract, no upload contract, no download contract, no storage contract
- no Attachment Review, no Storage Review, no Upload Review, no post-PASS audit
- no splitting metadata/upload/download by phase or by media type
- no post-PASS review, no second audit
- no full repository scan
- no re-run of a passing task and no re-run of the already-passed gate side
- no re-opening A0, A1, A2, M2 or M3
- no separate D-13 governance task
- no device, no cloud, no A8+ work
- no broad storage permission, no capture UX, no editor redesign
- no archive/executable/audio/video/arbitrary-binary support
