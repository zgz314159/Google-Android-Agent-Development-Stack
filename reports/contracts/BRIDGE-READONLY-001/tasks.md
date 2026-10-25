# Tasks — Bridge read-only acceptance task

## Tasks

### TASK-01 — Run the read-only check and write EVIDENCE.txt

- Goal: Run `id -un`, `pwd`, `git rev-parse HEAD` and `uname -s` in `/var/tmp/BRIDGE-READONLY-001/project`; write exactly four labeled lines to `EVIDENCE.txt` in this order: `id -un: <actual>`, `pwd: <actual>`, `git rev-parse HEAD: <actual>`, `uname -s: <actual>`; no other lines or files.
_Boundary:_ Read-only inspection and one evidence file only. No formal source or host change.
_Depends:_ none
- Allowed Paths: `project`
- Acceptance: AC-BRIDGE-001
- Verification: `EVIDENCE.txt` in the worktree contains exactly four labeled lines whose values are `aegl-ai`, `/var/tmp/BRIDGE-READONLY-001/project`, the commit in the trusted `PREP-BINDING.json`, and `Linux`; compare with the actual command results; no other file changed.
- Done When: EVIDENCE.txt is present in the worktree with exactly the four labeled actual values and the bridge reports its real process outcome; process exit does not by itself prove task acceptance.
