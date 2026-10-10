# PRODUCT — Phase-4 Hermes Task V1 Control Kernel Install

## Product

`Google-Android-Agent-Development-Stack` is an Android AI software-factory system: a change
request is compiled into a frozen Implementation Contract, then implemented, verified on a
physical device, and evaluated. Around that pipeline the stack carries its own orchestration
infrastructure under `orchestration/hermes/`.

One part of that infrastructure is the **GPT <-> Hermes control kernel** ("the bridge"): a small
stdlib-only Python package that lets an external GPT-driven control loop hand exactly one
`HERMES_TASK_V1` envelope per round to Hermes, validates it against a frozen contract package,
executes it under the Contract Guard, and reports one compact `HERMES_RESULT_V1` back.

Every change to the stack is gated by the **Contract Guard**: a fail-closed `pre_tool_call` hook
that permits a write only when the target path is listed in the `allowed_paths` of the active
compiler-owned contract package. A path that is inside the project but listed in no active
contract is `UNCLASSIFIED_FAIL_CLOSED`. This is why installing a new kernel requires its own
contract package, even though the kernel itself is already written and tested.

## Change Request

Authorize, by a single compiler-owned Phase-4 contract package, the write surface required to
install the already-implemented and already-tested Phase-4 bridge kernel from its staging location
`orchestration/hermes/evidence/phase4-hermes-task-v1-kernel/bridge/` into its production location
`orchestration/hermes/bridge/`. This package creates the authorization only; it does not perform
the install.

## Scope

- Authorize writes under `Google-Android-Agent-Development-Stack/orchestration/hermes/bridge/`.
- Authorize writes under the existing Phase-4 evidence directory
  `Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/phase4-hermes-task-v1-kernel/`
  for the install-parity report only.
- Authorize the verbatim copy of the staged kernel modules
  (`protocol.py`, `bridge_state.py`, `contract_executor.py`, `bridge_cli.py`, `chatgpt_adapter.py`)
  into `orchestration/hermes/bridge/`.
- Authorize running the bridge's own deterministic test suite and a staged-vs-installed byte-parity
  check.

## Non-Goals

- Redesigning, refactoring or rewriting any Phase-4 kernel module. The implementation is frozen.
- Re-planning the Phase-4 task graph or reopening any decision recorded during the Phase-4 run.
- Modifying KeepLab product code, the Specification Compiler, the Contract Guard, the Hermes
  profile configuration, or the pinned Hermes source.
- Authorizing any broad `/mnt/AndroidDev/Projects` write surface.
- Touching `Testapp`, `PowerAi`, or any unrelated repository.
- Enabling the bridge in a live loop, wiring it into the profile hooks, or running it against a
  device.

## Contract Metadata

```json
{
  "experiment": {
    "experiment_id": "PHASE4-HERMES-TASK-V1-KERNEL",
    "experiment_type": "SPEC_FIRST_BROWNFIELD",
    "matched_control_available": false,
    "contract_id": "PHASE4-HERMES-TASK-V1-KERNEL-001",
    "mode": "brownfield"
  },
  "feature": {
    "feature_id": "PHASE4-BRIDGE-INSTALL",
    "title": "Phase-4 Hermes Task V1 control kernel install",
    "summary": "Authorize the write surface that installs the already-tested Phase-4 bridge kernel from its evidence staging tree into orchestration/hermes/bridge/, with a deterministic install, a test run and a byte-parity proof."
  },
  "scope": [
    "Write authorization for Google-Android-Agent-Development-Stack/orchestration/hermes/bridge/",
    "Write authorization for the Phase-4 evidence directory for the install-parity report",
    "Verbatim copy of the staged Phase-4 kernel modules",
    "Deterministic bridge test run and staged-vs-installed parity proof"
  ],
  "non_goals": [
    "Phase-4 redesign or re-implementation",
    "KeepLab product code",
    "Specification Compiler source modification",
    "Contract Guard source modification",
    "Hermes profile configuration modification",
    "Live bridge enablement or device execution",
    "Any unrelated repository"
  ],
  "unresolved_questions": []
}
```
