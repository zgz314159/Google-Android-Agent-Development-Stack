# PRODUCT — Phase-45 thin bounded Campaign Supervisor contract

## Product

`Google-Android-Agent-Development-Stack` compiles a change request into a frozen Implementation
Contract, implements it, verifies it on a physical device, and evaluates it. Around that pipeline
the stack carries its own orchestration infrastructure under `orchestration/hermes/`, including
the **GPT <-> Hermes control bridge** (`orchestration/hermes/bridge/`): a stdlib-only kernel that
consumes exactly one `HERMES_TASK_V1` envelope per round, validates it against a frozen contract
package, executes it under the Contract Guard and reports one compact `HERMES_RESULT_V1` back.

The bridge is deliberately ONE ROUND per invocation and deliberately not a loop. What is missing
is the layer that decides *when* a round should run for a bounded milestone. This package is the
compiler-owned contract for that layer: a thin, bounded **Campaign Supervisor** that sits AROUND
the already-PASS one-round bridge and wakes it only when a new, valid control response arrives.

Architecture this contract authorizes (Supervisor added; Bridge unchanged):

    GPT-5.6  <->  Campaign Supervisor  <->  existing bridge_cli.py ONE ROUND  <->  Hermes / DeepSeek

The Supervisor does not replace, redesign or duplicate the Bridge. The Bridge remains the ONLY
authority for HERMES task schema validation, nonce / sequence / in_reply_to, replay, risk,
contract validation, the self-modification gate, Contract Guard execution, the durable result
transaction and the browser result send.

## Change Request

Authorize a single compiler-owned contract package whose only project write surface is
`orchestration/hermes/supervisor/` plus the campaign evidence directory
`orchestration/hermes/evidence/campaign-supervisor/`, and whose tasks produce a stdlib-only
Campaign Supervisor that:

- acquires exactly one campaign lock;
- snapshots the initial Bridge challenge;
- polls the LATEST COMPLETED ChatGPT assistant response and computes its sha256;
- never processes the same assistant response twice;
- invokes the EXISTING `bridge_cli.py round` exactly once when a NEW response contains exactly
  one valid Bridge task envelope for the expected sequence / nonce / in_reply_to;
- waits for Bridge to send its result and for the next NEW assistant response;
- repeats under hard bounds;
- and terminates the campaign on a valid campaign-terminal envelope, or pauses fail-closed
  otherwise.

This package authorizes the Supervisor contract; it implements nothing itself.

## Scope

- Write authorization for `Google-Android-Agent-Development-Stack/orchestration/hermes/supervisor/` only.
- Write authorization for `Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/campaign-supervisor/` only.
- A stdlib-only package: `campaign_protocol.py`, `campaign_state.py`, `campaign_supervisor.py`,
  `campaign_cli.py`, `tests/test_campaign_supervisor.py` and `__init__.py`.
- Read-only reuse of the existing Bridge interfaces and the existing ChatGPT adapter READ seam.
- Deterministic tests driven entirely by injected fakes, plus one combined Supervisor verification
  writing compact evidence under the campaign evidence directory.

## Non-Goals

- Replacing, redesigning, refactoring or copying the Bridge or any Bridge authority.
- Implementing a second task-authorization layer, a second protocol layer, a second Chrome/CDP
  stack, or any message sender in the Supervisor.
- Executing a Hermes contract directly, or sending anything to ChatGPT, from the Supervisor.
- An unbounded `while true: bridge_cli round` loop, or any autonomy without hard round and wall
  limits.
- Modifying the Bridge, the Specification Compiler, the Contract Guard / evaluation adapter,
  `HERMES-LOCK.json`, the KeepLab product, `Testapp`, `PowerAi`, or any other repository.
- Touching the Android device `87296ada`, the browser, or any network surface during verification.

## Contract Metadata

```json
{
  "experiment": {
    "experiment_id": "PHASE45-CAMPAIGN-SUPERVISOR",
    "experiment_type": "SPEC_FIRST_BROWNFIELD",
    "matched_control_available": false,
    "contract_id": "PHASE45-CAMPAIGN-SUPERVISOR-001",
    "mode": "brownfield"
  },
  "feature": {
    "feature_id": "PHASE45-CAMPAIGN-SUPERVISOR",
    "title": "Phase-45 thin bounded Campaign Supervisor contract",
    "summary": "Authorize a compiler-owned contract for a stdlib-only Campaign Supervisor that schedules bounded, one-round-at-a-time wake-ups of the already-PASS GPT<->Hermes bridge for a single milestone: one campaign lock, a sha256 new-assistant-response guard, exactly one bridge round per new valid task envelope, a separate strict campaign-terminal envelope, fail-closed pausing on any malformed control or bridge safety state, hard round and wall limits, and durable per-campaign state; the Bridge remains the sole authority and is reused read-only."
  },
  "scope": [
    "Write authorization for Google-Android-Agent-Development-Stack/orchestration/hermes/supervisor/",
    "Write authorization for Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/campaign-supervisor/",
    "Stdlib-only Supervisor package with the exact declared module set",
    "Read-only reuse of the existing Bridge interfaces and the ChatGPT adapter READ seam",
    "Deterministic fake-driven tests plus one combined Supervisor verification"
  ],
  "non_goals": [
    "Replacing, redesigning or duplicating the Bridge or any Bridge authority",
    "A second task-authorization, protocol or Chrome/CDP layer",
    "Direct Hermes contract execution or any ChatGPT send from the Supervisor",
    "Unbounded autonomy or an infinite while-true bridge replay",
    "Modifying the Bridge, the compiler, the guard, HERMES-LOCK.json, KeepLab, Testapp or PowerAi",
    "Device, browser or network interaction during verification"
  ],
  "unresolved_questions": []
}
```
