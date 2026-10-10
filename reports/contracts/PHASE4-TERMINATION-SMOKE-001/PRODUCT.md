# PRODUCT — Phase-4 evidence-only termination smoke

## Product

`Google-Android-Agent-Development-Stack` compiles a change request into a frozen Implementation
Contract, implements it, verifies it on a physical device, and evaluates it. Around that pipeline
the stack carries its own orchestration infrastructure under `orchestration/hermes/`, including a
stdlib-only GPT <-> Hermes control bridge that executes exactly one `HERMES_TASK_V1` envelope per
round and reports one compact `HERMES_RESULT_V1` back.

This package is the **single safe termination smoke** for the hardened bridge. It exists to prove,
once, end to end and with no possibility of touching the control plane, that a live task can be
consumed, executed, verified once and terminated cleanly under the hardened termination semantics
(PASS -> FINAL ASSISTANCE report -> STOP), while writing nothing except one evidence marker.

It is deliberately trivial and completely deterministic: no Android app, no device, no UI, no
network. Its entire write surface is one isolated evidence directory.

## Change Request

Authorize a bounded, evidence-only contract package whose only authorized project write surface is
`orchestration/hermes/evidence/phase4-termination-smoke/`, whose task creates exactly one marker
file, verifies it once, runs the normal verification layer exactly once, and then obeys PASS ->
FINAL RESPONSE -> STOP.

This package authorizes a task; it performs nothing itself.

## Scope

- Authorize writes under `Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/phase4-termination-smoke/` only.
- Create exactly one evidence-only marker file there.
- Verify that marker once, deterministically.
- Run the normal verification layer exactly once.
- Terminate on PASS with the Phase C report in the final assistant response and STOP.

## Non-Goals

- Touching `orchestration/hermes/bridge/`, the Contract Guard, the Specification Compiler, the
  pinned Hermes revision, `.hermes.md`, KeepLab product code, `Testapp` or `PowerAi`.
- Any Android device interaction, any browser interaction, any network access.
- Any second writer, any retry loop, any exploratory or repeated verification after PASS.
- Executing Auto-Finalizer, or treating it as an in-session acceptance criterion.

## Contract Metadata

```json
{
  "experiment": {
    "experiment_id": "PHASE4-TERMINATION-SMOKE",
    "experiment_type": "SPEC_FIRST_BROWNFIELD",
    "matched_control_available": false,
    "contract_id": "PHASE4-TERMINATION-SMOKE-001",
    "mode": "brownfield"
  },
  "feature": {
    "feature_id": "PHASE4-TERMINATION-SMOKE",
    "title": "Phase-4 evidence-only termination smoke",
    "summary": "One tiny deterministic live task that writes a single evidence marker under an isolated evidence directory, verifies it once, runs the normal verification layer once, and terminates on PASS with the Phase C report in the final assistant response, without any capability to touch the bridge, the guard, the compiler or any product code."
  },
  "scope": [
    "Write authorization for orchestration/hermes/evidence/phase4-termination-smoke/ only",
    "One evidence-only marker file",
    "One deterministic verification",
    "One normal verification-layer pass",
    "PASS -> final response -> STOP"
  ],
  "non_goals": [
    "Control-plane modification",
    "Device or browser interaction",
    "Network access",
    "Repeated or exploratory verification",
    "Auto-Finalizer invocation",
    "Any broader project write surface"
  ],
  "unresolved_questions": []
}
```
