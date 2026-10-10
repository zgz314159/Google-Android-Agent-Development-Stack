# EXECUTOR-PROMPT — KEEPLAB-A2-BACKEND-FOUNDATION-001

**The future execution prompt for this contract is:**

`Google-Android-Agent-Development-Stack/reports/contracts/KEEPLAB-A2-BACKEND-FOUNDATION-001/KEEPLAB-A2-BACKEND-FOUNDATION-EXECUTE.md`

**Execution status in this phase:** `NOT_EXECUTED`.

This contract-creation phase performed targeted discovery and authored the package. It did not
create the backend. Running it is a separate, explicitly-authorized task
(`KEEPLAB-A2-BACKEND-FOUNDATION-EXECUTE`).

## How a future session activates this contract

The Contract Guard resolves its package as:

```
package_dir = os.environ.get("HERMES_CONTRACT_PACKAGE") or DEFAULT_PACKAGE
```

`DEFAULT_PACKAGE` is the frozen P0B-CLOSE package. The switch is therefore the guard's own
**`HERMES_CONTRACT_PACKAGE`** environment variable, inherited by the hook subprocess from the
Hermes process environment. Point the Hermes process at this package before starting the A2
execution session:

```
export HERMES_CONTRACT_PACKAGE=/mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack/reports/contracts/KEEPLAB-A2-BACKEND-FOUNDATION-001
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

If the guard sha256 differs when the A2 session starts, the contract was validated against a
different guard: STOP.

## Recorded before execution is allowed

| Field | Value |
|---|---|
| `BACKEND_PATH` | `/mnt/AndroidDev/Projects/KeepLab-Relay/backend/` |
| `BACKEND_PATH_STATE` | `ABSENT` — the directory does not exist; nothing may be overwritten |
| `BACKEND_BUILD_MODEL` | `INDEPENDENT_GRADLE_PROJECT` (own `settings.gradle.kts` + `build.gradle.kts`) |
| `WRAPPER` | reuse the existing repository wrapper: `cd /mnt/AndroidDev/Projects/KeepLab-Relay && ./gradlew -p backend <tasks>` |
| `ROOT_ANDROID_GRADLE_MODIFIED` | `NO` — required outcome; a needed root change is a STOP |
| `FROZEN_TECHNOLOGY` | `KOTLIN + KTOR` · `POSTGRESQL` · `PORTABLE_DOCKER` · future cloud `TENCENT_CLOUD` (not provisioned) |
| `MIGRATION` | `FLYWAY`, exactly one foundation-only initial migration |
| `POOL` | `HIKARICP` + PostgreSQL JDBC driver, `SELECT 1` probe behind an injectable abstraction |
| `PROJECT_DATA_STAGE` | `EXPERIMENTAL` — `CLEAN_FOUNDATION > BACKWARD_COMPATIBILITY` |
| `ANDROID` | `BLOCK` — `KeepLab-Relay/app/**` and every Android Gradle file are read-only |
| `AUTH` | `BLOCK` (D-01/D-04/D-10 unresolved) |
| `SYNC` | `BLOCK` |
| `CLOUD_PROVISIONING` | `BLOCK` |
| `DEVICE` | `NOT_USED` |
| `DOCKER_RUNTIME_SMOKE` | optional; `SKIPPED_TOOL_UNAVAILABLE` when no container runtime exists (never a blocker) |
