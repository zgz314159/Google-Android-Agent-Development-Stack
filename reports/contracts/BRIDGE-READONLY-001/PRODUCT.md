# PRODUCT — Bridge read-only acceptance task

## Product

`Google-Android-Agent-Development-Stack` orchestration bridge. This package authorizes a
single disposable task worktree for a deterministic, read-only acceptance check; it does not
authorize any formal project change.

## Change Request

Run one read-only check inside the controlled Hermes sandbox and write its raw output only to
`EVIDENCE.txt` in the disposable task worktree.

## Scope

- Read the disposable task worktree.
- Run `id -un`, `pwd`, `git rev-parse HEAD`, `uname -s` only.
- Write the raw output to `EVIDENCE.txt` in the disposable task worktree.
- Return the real Hermes execution outcome to the bridge.

## Non-Goals

- No Microcourse project.
- No formal source, contract, compiler, guard, launcher, profile, or host change.
- No promotion, no push, no model/API call beyond the existing controlled sandbox.
- No business write.

## Contract Metadata

```json
{
  "experiment": {
    "experiment_id": "BRIDGE-READONLY",
    "experiment_type": "SPEC_FIRST_BROWNFIELD",
    "matched_control_available": false,
    "contract_id": "BRIDGE-READONLY-001",
    "mode": "brownfield"
  },
  "feature": {
    "feature_id": "BRIDGE-READONLY",
    "title": "Bridge read-only acceptance task",
    "summary": "Authorize one disposable worktree and its EVIDENCE.txt for a deterministic read-only sandbox check."
  },
  "scope": [
    "Read-only inspection of the disposable task worktree",
    "Write only EVIDENCE.txt inside that worktree",
    "Return the real sandbox execution outcome"
  ],
  "non_goals": [
    "Microcourse project",
    "Formal source or host change",
    "Promotion or push",
    "Business write"
  ],
  "unresolved_questions": []
}
```
