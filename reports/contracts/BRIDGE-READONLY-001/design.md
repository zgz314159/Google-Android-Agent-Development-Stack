# Implementation Design — Bridge read-only acceptance task

## Architecture

The disposable task root is `/var/tmp/BRIDGE-READONLY-001`; its `project/` child is the
Git worktree owned by `aegl-ai`. The contract `source_root` is the task root, and
`allowed_paths` is exactly `project`, so the launcher, registration tool, Contract Guard
and validator all resolve the same source_root-relative paths. The contract package is
root-controlled under the trusted Stack copy; the sandbox mounts it read-only so
`EXECUTOR-PROMPT.md` is visible at its real path. The expected HEAD is bound by a
root-owned `PREP-BINDING.json` created after the task commit exists, so the contract does
not embed its own commit SHA. No formal project, compiler, guard, launcher or profile is
modified.

## Data Flow

1. The root controller creates `/var/tmp/BRIDGE-READONLY-001/project` from the fixed task
   bundle, verifies the explicit target ref/commit, registers `BRIDGE-READONLY-001`, and
   writes the root-owned `PREP-BINDING.json` with that exact worktree and commit.
2. The wrapper passes the registered task and the contract prompt path to the installed
   `aegl-hermes-sandbox`.
3. Hermes runs the read-only commands in the task worktree and writes exactly four labeled
   lines to `EVIDENCE.txt` there.
4. The bridge reports the real process outcome. A separate read-only acceptance check
   compares `EVIDENCE.txt` with `PREP-BINDING.json`, records its SHA-256, and reports
   `TASK_ACCEPTANCE` independently of process success; it never rewrites the evidence.

## File Structure Plan

- Task root / contract source_root: `/var/tmp/BRIDGE-READONLY-001`
- Task worktree: `/var/tmp/BRIDGE-READONLY-001/project`
- Evidence: `EVIDENCE.txt` inside the worktree (contract path `project/EVIDENCE.txt`)
- Evidence format: exactly four labeled lines, in order:
  `id -un: aegl-ai`, `pwd: /var/tmp/BRIDGE-READONLY-001/project`,
  `git rev-parse HEAD: <PREP-BINDING.json commit>`, `uname -s: Linux`
- Read first: `project/README.md` under the task root
- Contract package: trusted Stack `reports/contracts/BRIDGE-READONLY-001/`
- Trusted expected-value binding: trusted package `PREP-BINDING.json`

## Selector Contract

```json
{
  "decisions": [
    {
      "id": "DEC-001",
      "statement": "The disposable task root is the contract source_root; allowed_paths is exactly 'project'; the launcher, Guard, registration and validator all use that source_root-relative path.",
      "rationale": "A single task root/source_root keeps the worktree, registration, Guard and validator aligned without relaxing the Guard to '.' or relying on string-only matching."
    },
    {
      "id": "DEC-002",
      "statement": "The expected task commit is bound after the task commit by a root-owned PREP-BINDING.json under the trusted contract package; the contract does not embed its own commit SHA.",
      "rationale": "Binding the expected HEAD outside the contract content avoids a self-referential commit hash cycle while keeping the acceptance expected value trusted."
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
