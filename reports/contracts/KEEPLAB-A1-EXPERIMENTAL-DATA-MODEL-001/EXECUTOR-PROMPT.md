# EXECUTOR-PROMPT — KEEPLAB-A1-EXPERIMENTAL-DATA-MODEL-001

**The future execution prompt for this contract is:**

`Google-Android-Agent-Development-Stack/reports/contracts/KEEPLAB-A1-EXPERIMENTAL-DATA-MODEL-001/KEEPLAB-A1-EXPERIMENTAL-DATA-MODEL-EXECUTE.md`

**Execution status in this phase:** `NOT_EXECUTED`.

This contract-creation phase performed targeted discovery and authored the package. It did
not implement A1. Running it is a separate, explicitly-authorized task
(`KEEPLAB-A1-EXPERIMENTAL-DATA-MODEL-EXECUTE`).

## How a future session activates this contract

The Contract Guard resolves its package as:

```
package_dir = os.environ.get("HERMES_CONTRACT_PACKAGE") or DEFAULT_PACKAGE
```

`DEFAULT_PACKAGE` is the frozen P0B-CLOSE package. The switch is therefore the guard's own
**`HERMES_CONTRACT_PACKAGE`** environment variable, inherited by the hook subprocess from
the Hermes process environment. Point the Hermes process at this package before starting
the A1 execution session:

```
export HERMES_CONTRACT_PACKAGE=/mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack/reports/contracts/KEEPLAB-A1-EXPERIMENTAL-DATA-MODEL-001
```

That is the whole mechanism: **same guard, same fail-closed hook, different package.**
No guard patch, no hook edit, no config edit, no file rename, no out-of-project
write-and-copy. Unsetting the variable returns the guard to the frozen P0B-CLOSE contract.

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

If the guard sha256 differs when the A1 session starts, the contract was validated against a
different guard: STOP.

## Recorded before execution is allowed

| Field | Value |
|---|---|
| `PRIMARY_KEY_STRATEGY` | `KEEP_LONG_LOCAL_PK_ADD_UNIQUE_CLIENT_UUID` |
| reason | the existing `Long` rowid key is clean and already referenced by two child foreign keys and the whole id surface; the stable client UUID is added beside it. Replacing the local key is a SEPARATE later decision (KEEPLAB-AUTH-SYNC-DATA-MODEL MIG-1/MIG-2) and is forbidden here. |
| `DEV_DATABASE_RESET_REQUIRED` | `YES` — schema version 2 -> 3 with no migration authored; an installed development database may need app-data clearing or a reinstall. Accepted for the `EXPERIMENTAL` data stage. |
| `GRADLE` | `BLOCK` |
| `DEVICE` | `NOT_USED` |
