# EXECUTOR-PROMPT — KEEPLAB-M3-OFFLINE-CONFLICT-001

**The future execution prompt for this contract is:**

`Google-Android-Agent-Development-Stack/reports/contracts/KEEPLAB-M3-OFFLINE-CONFLICT-001/KEEPLAB-M3-OFFLINE-CONFLICT-EXECUTE.md`

**Execution status in this phase:** `NOT_EXECUTED`.

This contract-creation phase performed targeted discovery and authored the package. It did not
implement M3. Running it is a separate, explicitly-authorized task
(`KEEPLAB-M3-OFFLINE-CONFLICT-EXECUTE`) in a **fresh** Hermes session.

## How a future session activates this contract

The Contract Guard resolves its package as:

```
package_dir = os.environ.get("HERMES_CONTRACT_PACKAGE") or DEFAULT_PACKAGE
```

`DEFAULT_PACKAGE` is the frozen P0B-CLOSE package. The switch is therefore the guard's own
**`HERMES_CONTRACT_PACKAGE`** environment variable, inherited by the hook subprocess from the
Hermes process environment. Point the Hermes process at this package before starting the M3
execution session:

```
export HERMES_CONTRACT_PACKAGE=/mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack/reports/contracts/KEEPLAB-M3-OFFLINE-CONFLICT-001
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

If the guard sha256 differs when the M3 session starts, the contract was validated against a
different guard: STOP.

## Recorded before execution is allowed

| Field | Value |
|---|---|
| `MILESTONE` | `M3` = `A5_OFFLINE_HARDENING` + `A6_CONFLICT_HANDLING` |
| `EXECUTION_MODEL` | `PLAN ONCE → A5 EXECUTE → A5 LIGHT CHECKPOINT → A6 EXECUTE → VERIFY M3 ONCE → PASS = STOP` |
| `CONTRACTS` | exactly ONE (this one). No A5 contract, no A6 contract, no A5/A6 review, no post-PASS audit, no separate D-06 governance task. |
| `HUMAN_DECISION` | `D-06 = TRASH_RETENTION_7_DAYS` (`HUMAN_PROJECT_OWNER_APPROVAL`, 2026-10-06) |
| `TOMBSTONE_RETENTION` | `SEPARATE / NOT_7_DAYS / NOT_CHOSEN`; `TOMBSTONE_GC = DISABLED` |
| `PENDING_NOT_BLOCKING` | D-05, D-11, D-12, D-13, D-14 |
| `PROJECT_DATA_STAGE` | `EXPERIMENTAL` — `DISPOSABLE_TEST_DATA`; `DEV_DATABASE_RESET_REQUIRED = YES` |
| `BACKEND_PATH` | `/mnt/AndroidDev/Projects/KeepLab-Relay/backend/` — `PRESENT` |
| `BACKEND_BUILD_MODEL` | `INDEPENDENT_GRADLE_PROJECT` (reuse `./gradlew -p backend`) |
| `ROOT_ANDROID_GRADLE_CHANGE` | `NO` — required outcome; a needed root change is a STOP (`M3_ROOT_GRADLE_CHANGE_REQUIRED`) |
| `ANDROID_SURFACE` | `ENUMERATED_NOT_WHOLE_APP` (see `allowed_paths`, incl. the new `ui/conflict/`) |
| `GRADLE_MODULE_CHANGES` | `app/build.gradle.kts` + `gradle/libs.versions.toml` only, and only to add M3 dependencies |
| `A5_CHECKPOINT` | `LIGHT` — records only; the session does **not** stop and continues directly into A6 |
| `ERROR_CLASSES` | `AUTH_REQUIRED` · `CONFLICT` · `TEMPORARY_RETRYABLE` · `PERMANENT_VALIDATION_FAILURE` · `NOT_FOUND_NON_DESTRUCTIVE` · `SUCCESS` |
| `RETRY_CONSTANTS` | `AUTO_RETRY_MAX_ATTEMPTS = 5` · `BACKOFF_POLICY = EXPONENTIAL` · `BACKOFF_INITIAL_DELAY = 30s` · `BACKOFF_MAX_DELAY = 5h` (record final values; never remove the bound) |
| `LOST_WAKEUP` | mandatory; choose the smallest correct mechanism against the **actual** WorkManager version; `KEEP` is neither blindly kept nor blindly replaced; test `TRIGGER_DURING_ACTIVE_SYNC` |
| `SERVER_REVISION` | the only conflict authority; stale `baseRevision` → `409 REVISION_CONFLICT` carrying the current authoritative revision and server payload |
| `KEEP_BOTH` | NEW client UUID · same `accountId` · `SYNC_PENDING` · `CREATE` mutation; never reuse the original client UUID or revision identity |
| `TRASH_RETENTION` | `7 DAYS`; Trash ≠ tombstone; offline unacknowledged Trash is never prematurely final-deleted |
| `CRDT` / `AUTO_3WAY_MERGE` | `NOT_ADOPTED` |
| `WORKMANAGER` | one unique serialized `note_sync` pipeline; no parallel pipeline |
| `CLOUD_PROVISIONING` | `BLOCK` |
| `DEVICE` | `NOT_USED` (M3 is device-free: no adb, no Maestro, no UiAutomator, no APK install) |
| `LIVE_POSTGRES` | optional at most once; absence → `SKIPPED_TOOL_UNAVAILABLE`, never a blocker; never install infrastructure |
| `GATES` | `./gradlew -p backend test build` (once) and `./gradlew :app:testDebugUnitTest :app:assembleDebug` (once) |
| `STOPS_AFTER` | M3 (A5 + A6 verified once) |
| `MUST_NOT_START` | A7 attachments · A8 multi-device · A9 multi-account/collaboration |

## Forbidden behaviour

- no A5 contract, no A6 contract, no A5 review, no A6 review
- no stopping after A5 (A5 is a checkpoint, not a stop)
- no post-PASS review, no second audit
- no full repository scan
- no re-run of a passing task and no re-run of the already-passed gate side
- no re-opening A0, A1, A2 or M2
- no separate D-06 governance task
- no device, no cloud, no A7+ work
