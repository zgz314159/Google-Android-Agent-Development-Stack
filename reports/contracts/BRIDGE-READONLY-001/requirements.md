# Requirements — Bridge read-only acceptance task

## Requirements

### REQ-BRIDGE-001 — Read-only sandbox evidence

- Statement: The task must run only read-only identity, path, git and OS commands in the disposable worktree and write their raw output to `EVIDENCE.txt`.
- Conditions: When the controlled Hermes sandbox executes this contract.
- Expected: `EVIDENCE.txt` contains the actual username, worktree path, git HEAD and OS name; no other file is written.
- Edge case: Any missing command or sandbox failure must be reported as a real failure, never filled in by the bridge.
- Acceptance: AC-BRIDGE-001
- Tasks: TASK-01
