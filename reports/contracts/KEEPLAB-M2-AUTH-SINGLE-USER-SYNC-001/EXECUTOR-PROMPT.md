# EXECUTOR-PROMPT — KEEPLAB-M2-AUTH-SINGLE-USER-SYNC-001

**The future execution prompt for this contract is:**

`Google-Android-Agent-Development-Stack/reports/contracts/KEEPLAB-M2-AUTH-SINGLE-USER-SYNC-001/KEEPLAB-M2-AUTH-SINGLE-USER-SYNC-EXECUTE.md`

**Execution status in this phase:** `NOT_EXECUTED`.

This contract-creation phase performed targeted discovery and authored the package. It did not
implement M2. Running it is a separate, explicitly-authorized task
(`KEEPLAB-M2-AUTH-SINGLE-USER-SYNC-EXECUTE`) in a **fresh** Hermes session.

## How a future session activates this contract

The Contract Guard resolves its package as:

```
package_dir = os.environ.get("HERMES_CONTRACT_PACKAGE") or DEFAULT_PACKAGE
```

`DEFAULT_PACKAGE` is the frozen P0B-CLOSE package. The switch is therefore the guard's own
**`HERMES_CONTRACT_PACKAGE`** environment variable, inherited by the hook subprocess from the
Hermes process environment. Point the Hermes process at this package before starting the M2
execution session:

```
export HERMES_CONTRACT_PACKAGE=/mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack/reports/contracts/KEEPLAB-M2-AUTH-SINGLE-USER-SYNC-001
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

If the guard sha256 differs when the M2 session starts, the contract was validated against a
different guard: STOP.

## Recorded before execution is allowed

| Field | Value |
|---|---|
| `MILESTONE` | `M2` = `A3_AUTH_SESSION` + `A4_SINGLE_USER_SYNC` |
| `EXECUTION_MODEL` | `PLAN ONCE → A3 EXECUTE → A3 LIGHT CHECKPOINT → A4 EXECUTE → VERIFY M2 ONCE → PASS = STOP` |
| `CONTRACTS` | exactly ONE (this one). No A3 contract, no A4 contract, no A3/A4 review, no post-PASS audit. |
| `HUMAN_DECISIONS` | D-01 `EMAIL_PASSWORD_VERIFIED` · D-04 `PRESERVE_LOCAL_CACHE` · D-10 `JWT_ACCESS_OPAQUE_ROTATING_REFRESH` (frozen 2026-10-06) |
| `PENDING_NOT_BLOCKING` | D-05, D-06, D-11, D-12, D-13, D-14 |
| `PROJECT_DATA_STAGE` | `EXPERIMENTAL` — `DISPOSABLE_TEST_DATA`; `DEV_DATABASE_RESET_REQUIRED = YES` |
| `BACKEND_PATH` | `/mnt/AndroidDev/Projects/KeepLab-Relay/backend/` — `PRESENT` |
| `BACKEND_BUILD_MODEL` | `INDEPENDENT_GRADLE_PROJECT` (reuse `./gradlew -p backend`) |
| `ROOT_ANDROID_GRADLE_MODIFIED` | `NO` — required outcome; a needed root change is a STOP |
| `ANDROID_SURFACE` | `ENUMERATED_NOT_WHOLE_APP` (see `allowed_paths`) |
| `GRADLE_MODULE_CHANGES` | `app/build.gradle.kts` + `gradle/libs.versions.toml` only, and only to add M2 dependencies |
| `A3_CHECKPOINT` | `LIGHT` — records only; the session does **not** stop |
| `SERVER_REVISION` | the only conflict authority; stale `baseRevision` → `409 REVISION_CONFLICT` |
| `TRASH_VS_TOMBSTONE` | distinct; no automatic Trash retention, no automatic tombstone purge |
| `WORKMANAGER` | one unique `note_sync` pipeline; `ExistingWorkPolicy` = `A4_IMPLEMENTATION_DECISION` |
| `IDENTITY` | KeepLab backend only — no Google, no Firebase, no phone, no OAuth social, no passkey |
| `ROOM_ENCRYPTION_CLAIM` | `FORBIDDEN` |
| `ACCOUNT_DELETION` | `NOT_IMPLEMENTED` |
| `ATTACHMENTS` / `COLLABORATION` / `MULTI_ACCOUNT` / `PUSH` | `OUT_OF_SCOPE` |
| `CLOUD_PROVISIONING` | `BLOCK` |
| `DEVICE` | `NOT_USED` (M2 is device-free) |
| `GATES` | `./gradlew -p backend test build` (once) and `./gradlew :app:testDebugUnitTest :app:assembleDebug` (once) |
| `LIVE_POSTGRES` | optional at most once; absence → `SKIPPED_TOOL_UNAVAILABLE`, never a blocker |
