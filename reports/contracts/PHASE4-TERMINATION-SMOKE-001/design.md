# Implementation Design — Phase-4 evidence-only termination smoke

## Architecture

No architecture is added or changed. This package is a single, deliberately trivial,
evidence-only task on top of the existing stack:

- `orchestration/hermes/bridge/` is the GPT <-> Hermes control kernel that consumes a task,
  validates its contract package, executes it under the Contract Guard and reports one result. It
  is READ-ONLY here: this package must not be able to write into it.
- `orchestration/hermes/evidence/phase4-termination-smoke/` is the one directory this package is
  allowed to write. Everything the smoke produces lives there.
- The Contract Guard resolves the write allow-list from this package's
  `implementation-contract.json`, so the smoke's whole capability is the union of one directory.

The smoke exercises termination semantics, not features: it proves a live task can run to PASS and
then stop, with the Phase C report delivered in the final assistant response and no post-PASS tool
call. That makes it the safe final live sequence-4 smoke: its worst-case failure mode is a stray
marker file in an isolated evidence directory.

What is REUSED and must not be rebuilt: the protocol envelope, the contract gate, the Contract
Guard, the risk gate, the replay journal and the compiler pipeline. Nothing is re-implemented.

## Data Flow

1. The bridge consumes the task and validates this package through the normal contract gate.
2. The task executes under the Contract Guard, which permits writes only inside the smoke evidence
   directory.
3. The executor creates exactly one marker file there.
4. The executor verifies the marker once and runs the normal verification layer exactly once.
5. On PASS the executor makes no further tool call, search, read, audit, repeated verification or
   exploratory check, produces the Phase C report in the final assistant response, emits a compact
   final result and stops.
6. No Auto-Finalizer is invoked, inspected or awaited in-session; it is a POST-SESSION observer.

## File Structure Plan

**MUST TOUCH**

| File | Role | Expected change |
| --- | --- | --- |
| `orchestration/hermes/evidence/phase4-termination-smoke/TERMINATION-SMOKE-OK.json` | evidence-only marker | created once, recording the smoke identity |

**MAY TOUCH**

| File | Role | Expected change |
| --- | --- | --- |
| `orchestration/hermes/evidence/phase4-termination-smoke/__pycache__/` | bytecode cache | regenerated only if a helper module is imported from that directory |

**MUST NOT TOUCH**

- `orchestration/hermes/bridge/` — the control kernel.
- `orchestration/hermes/evaluation_adapter/` — the Contract Guard and its hooks.
- `orchestration/hermes/HERMES-LOCK.json` — the pinned Hermes revision.
- `specification/` — the compiler.
- `.hermes.md` — project governance context.
- `verification/`, `verification-benchmark/`, `evaluation/` — frozen layers.
- `reports/contracts/` — every contract package, this one included.
- KeepLab product code, `Testapp/`, `PowerAi/` — out of scope.

## Selector Contract

No Android UI is touched. The compiler schema requires a selector contract regardless, so these
entries are **deterministic filesystem identity markers**, not on-screen widgets. The smoke
performs zero device interaction and zero visual judgment.

| name | state it identifies |
| --- | --- |
| `phase4_termination_smoke_dir_present` | the isolated smoke evidence directory exists under orchestration/hermes/evidence/phase4-termination-smoke/ |
| `phase4_termination_smoke_marker_present` | the single evidence-only marker file exists inside that directory |

## Contract Metadata

```json
{
  "decisions": [
    {
      "id": "DEC-001",
      "statement": "The smoke's entire write surface is orchestration/hermes/evidence/phase4-termination-smoke/ and nothing else.",
      "rationale": "The smoke's only job is to prove termination semantics; isolating it to one evidence directory makes its worst-case effect a single stray marker and keeps the control plane unreachable by construction."
    },
    {
      "id": "DEC-002",
      "statement": "The smoke is a single deterministic marker plus one verification-layer pass; PASS -> FINAL RESPONSE -> STOP, with no repeated verification.",
      "rationale": "Termination semantics can only be observed on a task small enough that the only thing left to do after PASS is stop. A larger task would make 'no post-PASS tool call' untestable."
    },
    {
      "id": "DEC-003",
      "statement": "Auto-Finalizer is a POST-SESSION observer and is never invoked, inspected or awaited inside this session.",
      "rationale": "Auto-Finalizer runs after the session exits; treating it as an in-session acceptance criterion invites exactly the post-PASS tool calls this smoke exists to forbid."
    }
  ],
  "assumptions": [
    {
      "id": "ASM-001",
      "statement": "The bridge contract gate accepts a READY, compiler-generated, project-local package whose allowed surface is a single evidence directory."
    },
    {
      "id": "ASM-002",
      "statement": "Creating one small JSON marker file and reading it back is fully deterministic and offline."
    }
  ],
  "data_change": {
    "schema_version_current": 0,
    "schema_version_target": 0,
    "migration_required": false,
    "notes": "No persisted schema is touched. The only durable artifact is one new evidence-only marker file in an isolated directory."
  },
  "ui_change": {
    "surfaces": [],
    "selectors_added": [
      "phase4_termination_smoke_dir_present",
      "phase4_termination_smoke_marker_present"
    ]
  },
  "selector_contract": [
    {
      "name": "phase4_termination_smoke_dir_present",
      "compose_test_tag": "phase4_termination_smoke_dir_present",
      "uiautomator": "By.res(\"phase4_termination_smoke_dir_present\")",
      "state": "isolated smoke evidence directory present under orchestration/hermes/evidence/phase4-termination-smoke/",
      "required": true
    },
    {
      "name": "phase4_termination_smoke_marker_present",
      "compose_test_tag": "phase4_termination_smoke_marker_present",
      "uiautomator": "By.res(\"phase4_termination_smoke_marker_present\")",
      "state": "single evidence-only marker file present inside that directory",
      "required": true
    }
  ],
  "stop_conditions": [
    "A required write falls outside the smoke evidence directory: STOP, CONTRACT_DEVIATION.",
    "Satisfying the smoke would require touching bridge/, evaluation_adapter/, specification/, HERMES-LOCK.json, .hermes.md, KeepLab, Testapp or PowerAi: STOP, ABSOLUTE_BLOCK_VIOLATION.",
    "The smoke is asked to do anything beyond one marker and one verification-layer pass: STOP, SCOPE_WIDENING.",
    "A post-PASS tool call, search, read, audit or repeated verification appears necessary: STOP, TERMINATION_SEMANTICS_VIOLATION.",
    "Auto-Finalizer would have to be invoked, inspected or awaited in-session: STOP, POST_SESSION_ONLY_VIOLATION."
  ]
}
```
