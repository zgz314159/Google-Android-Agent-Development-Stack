# EXECUTOR-PROMPT — KEEPLAB-A0-GOVERNANCE-WRITE-001

**The future execution prompt for this contract is:**

`Google-Android-Agent-Development-Stack/reports/contracts/KEEPLAB-A0-GOVERNANCE-WRITE-001/KEEPLAB-A0-GOVERNANCE-WRITE-APPLY.md`

**Execution status in this phase:** `NOT_EXECUTED`.

This contract-creation phase authored the apply prompt. It did not run it. Running it is
a separate, explicitly-authorized task (`KEEPLAB-A0-GOVERNANCE-WRITE-APPLY`).

## How a future session activates this contract

The Contract Guard resolves its package as:

```
package_dir = os.environ.get("HERMES_CONTRACT_PACKAGE") or DEFAULT_PACKAGE
```

`DEFAULT_PACKAGE` is the frozen P0B-CLOSE package. The switch is therefore the guard's own
**`HERMES_CONTRACT_PACKAGE`** environment variable, inherited by the hook subprocess from
the Hermes process environment. Point the Hermes process at this package before starting
the apply session:

```
export HERMES_CONTRACT_PACKAGE=/mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack/reports/contracts/KEEPLAB-A0-GOVERNANCE-WRITE-001
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

If the guard sha256 differs when the apply session starts, the contract was validated
against a different guard: STOP.
