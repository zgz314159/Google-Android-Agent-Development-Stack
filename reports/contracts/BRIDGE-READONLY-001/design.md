# Implementation Design — Bridge read-only acceptance task

## Architecture

One disposable task worktree under `/var/lib/aegl-model/tasks/BRIDGE-READONLY-001/project`,
owned by `aegl-ai`, is the contract source_root. The contract package is root-controlled under
the trusted Stack copy; the sandbox mounts it read-only so `EXECUTOR-PROMPT.md` is visible at
its real path. No formal project, compiler, guard, launcher or profile is modified.

## Data Flow

1. The root controller creates the disposable worktree and registers the task.
2. The wrapper passes the registered task and the contract prompt path to the installed
   `aegl-hermes-sandbox`.
3. Hermes runs the read-only commands in the worktree and writes `EVIDENCE.txt`.
4. The bridge reports the real execution outcome; no value is synthesized.

## File Structure Plan

- Task worktree: `/var/lib/aegl-model/tasks/BRIDGE-READONLY-001/project`
- Evidence: `EVIDENCE.txt` inside the worktree
- Contract package: trusted Stack `reports/contracts/BRIDGE-READONLY-001/`

## Selector Contract

```json
{
  "decisions": [
    {
      "id": "DEC-001",
      "statement": "The task worktree is the contract source_root; allowed_paths is exactly '.'.",
      "rationale": "The launcher checks the worktree against source_root/allowed_paths; a separate project-relative path would be unverified string matching."
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
    "selectors_added": ["bridge_readonly_evidence"],
    "surfaces": []
  },
  "selector_contract": [
    {
      "compose_test_tag": "bridge_readonly_evidence",
      "name": "bridge_readonly_evidence",
      "required": true,
      "state": "EVIDENCE.txt exists in the disposable worktree",
      "uiautomator": "By.res(\"bridge_readonly_evidence\")"
    }
  ],
  "stop_conditions": [
    "Any write outside the disposable worktree: STOP, CONTRACT_DEVIATION.",
    "Any synthesized or missing evidence: STOP, EVIDENCE_MISSING.",
    "Any formal source, contract, compiler, guard, launcher, profile or host change: STOP, ABSOLUTE_BLOCK_VIOLATION."
  ]
}
```

## Contract Metadata

- No visual or business surface.
