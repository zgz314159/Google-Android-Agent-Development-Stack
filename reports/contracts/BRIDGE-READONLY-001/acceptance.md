# Acceptance Criteria — Bridge read-only acceptance task

## Acceptance Criteria

### AC-BRIDGE-001 — Actual read-only evidence exists

- Given: the controlled sandbox executed TASK-01 in the disposable worktree
- When: the worktree is inspected read-only
- Then: `EVIDENCE.txt` exists with exactly four labeled lines, in order: `id -un: aegl-ai`, `pwd: /var/tmp/BRIDGE-READONLY-001/project`, `git rev-parse HEAD: <PREP-BINDING.json commit>`, `uname -s: Linux`; no other line or file was written
- Verification: a deterministic read-only check compares the exact lines with the root-owned trusted `PREP-BINDING.json` and records the SHA-256 of EVIDENCE.txt; missing, extra or mismatched lines fail task acceptance; the check never rewrites, repairs or beautifies the evidence
- PC1 Step: PC1-01
