# Tasks — Bridge read-only acceptance task

## Tasks

### TASK-01 — Run the read-only check and write EVIDENCE.txt

- Goal: Run `id -un`, `pwd`, `git rev-parse HEAD` and `uname -s` in the disposable worktree; write their raw output to `project/EVIDENCE.txt`; do not modify any other file.
_Boundary:_ Read-only inspection and one evidence file only. No formal source or host change.
_Depends:_ none
- Allowed Paths: `project`
- Acceptance: AC-BRIDGE-001
- Verification: `project/EVIDENCE.txt` exists and contains the actual username, worktree path, git HEAD and OS name; no other file changed.
- Done When: project/EVIDENCE.txt is present with the raw output and the sandbox reports its real execution outcome.
