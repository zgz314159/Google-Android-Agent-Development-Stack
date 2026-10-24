# Implementation Design — Bridge read-only acceptance task

## Architecture

The disposable task root is `/var/tmp/BRIDGE-READONLY-001`; its `project/` child is the
Git worktree owned by `aegl-ai`. The contract `source_root` is the task root, and
`allowed_paths` is exactly `project`, so the launcher, registration tool, Contract Guard
and validator all resolve the same source_root-relative paths. The contract package is
root-controlled under the trusted Stack copy; the sandbox mounts it read-only so
`EXECUTOR-PROMPT.md` is visible at its real path. No formal project, compiler, guard,
launcher or profile is modified.

## Data Flow

1. The root controller creates `/var/tmp/BRIDGE-READONLY-001/project` from the fixed task
   bundle and registers `BRIDGE-READONLY-001`.
2. The wrapper passes the registered task and the contract prompt path to the installed
   `aegl-hermes-sandbox`.
3. Hermes runs the read-only commands in the task worktree and writes `EVIDENCE.txt` there.
4. The bridge reports the real execution outcome; no value is synthesized.

## File Structure Plan

- Task root / contract source_root: `/var/tmp/BRIDGE-READONLY-001`
- Task worktree: `/var/tmp/BRIDGE-READONLY-001/project`
- Evidence: `EVIDENCE.txt` inside the worktree (contract path `project/EVIDENCE.txt`)
- Read first: `project/README.md` under the task root
- Contract package: trusted Stack `reports/contracts/BRIDGE-READONLY-001/`

## Selector Contract

```json
{
  "decisions": [
    {
      "id": "DEC-001",
      "statement": "The disposable task root is the contract source_root; allowed_paths is exactly 'project'; the launcher, Guard, registration and validator all use that source_root-relative path.",
      "rationale": "A single task root/source_root keeps the worktree, registration, Guard and validator aligned without relaxing the Guard to '.' or relying on string-only matching."
    }
  ],
  "assumptions": [],
  "data_change": {
    "migration_required": false,
    "notes": "No persisted schema.",
    "schema_version_current": 0,
    "schema_version_target": 0
  },
  "ui_change": {
    "selectors_added": [],
    "surfaces": []
  },
  "selector_contract": [],
  "stop_conditions": [
    "Any write outside the disposable worktree: STOP, CONTRACT_DEVIATION.",
    "Any synthesized or missing evidence: STOP, EVIDENCE_MISSING.",
    "Any formal source, contract, compiler, guard, launcher, profile or host change: STOP, ABSOLUTE_BLOCK_VIOLATION."
  ]
}
```

## Contract Metadata

- No visual or business surface.
