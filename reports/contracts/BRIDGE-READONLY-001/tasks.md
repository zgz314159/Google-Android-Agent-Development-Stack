# Tasks — Bridge read-only acceptance task

## Tasks

### TASK-01 — Run the read-only check and write EVIDENCE.txt

- Goal: Run `id -un`, `pwd`, `git rev-parse HEAD` and `uname -s` in `/var/tmp/BRIDGE-READONLY-001/project`; write their raw output to `EVIDENCE.txt` in that worktree; do not modify any other file.
_Boundary:_ Read-only inspection and one evidence file only. No formal source or host change.
_Depends:_ none
- Allowed Paths: `project`
- Acceptance: AC-BRIDGE-001
- Verification: `EVIDENCE.txt` in the worktree contains the actual username, worktree path, git HEAD and OS name; compare it with the actual command results; no other file changed.
- Done When: EVIDENCE.txt is present in the worktree with the raw output and the sandbox reports its real execution outcome.
