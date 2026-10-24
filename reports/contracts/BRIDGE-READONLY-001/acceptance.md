# Acceptance Criteria — Bridge read-only acceptance task

## Acceptance Criteria

### AC-BRIDGE-001 — Actual read-only evidence exists

- Given: the controlled sandbox executed TASK-01 in the disposable worktree
- When: the worktree is inspected
- Then: `EVIDENCE.txt` exists with the actual `id -un`, `pwd`, `git rev-parse HEAD` and `uname -s` values, and no other file was written
- Verification: read EVIDENCE.txt and compare it with the sandbox's actual worktree/path/HEAD/OS; reject any synthesized value
- PC1 Step: PC1-01
