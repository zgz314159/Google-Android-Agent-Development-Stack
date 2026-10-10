# Verification Layer — Git Recommendation

No git action was performed this round. This document records what the operator is advised
to do **later, after approval**.

## Current state (observed, not changed)

- The Stack root `/mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack` is **not a
  git repository** (`git rev-parse` → *not a git repository*).
- `KeepLab-Relay` is a git repo; the verification worktree
  (`Worktrees/KeepLab-Verification-Compression`) is not.
- No `git add` / `git commit` / `git push` / `reset --hard` / `clean -fd` was run.

## Recommended future baseline

Once the operator approves, initialize the Stack as a repository and tag the promoted layer:

```bash
cd /mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack
git init
# add a .gitignore (below) BEFORE the first add
git add -A
git commit -m "Verification Layer v1.0.0 + Evaluation Layer v0.2.1"
git tag verification-layer-v1.0.0
```

Recommended `.gitignore` additions:

```gitignore
# Verification Layer run outputs / device scratch
verification/.runs/
verification/.state/
# Python bytecode
__pycache__/
*.pyc
```

## Why a single tag on the whole Stack

The promoted layer depends on the frozen benchmark only as *evidence*, and on the Evaluation
Core as an add-on. Versioning the layer at `verification-layer-v1.0.0` (while
`verification-benchmark/` continues to carry the historical **Harness v1.0** identity)
keeps the two responsibilities distinct.

## Do not

- Do not rewrite or delete `verification-benchmark/` frozen evidence.
- Do not force-push or reset any existing worktree.
- Do not commit `.runs/` (device outputs) or `_evaluation/` (generated reports).

## Status

```
GIT COMMIT CREATED: NO
```
