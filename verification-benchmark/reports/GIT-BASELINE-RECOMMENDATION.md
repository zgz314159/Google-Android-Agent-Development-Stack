# Git Baseline Recommendation

Status: advisory only. **No commit is created by this hardening task.**

## Current state (verified)

`KeepLab-Relay` has a `.git` directory in **unborn HEAD / zero-commit** state:

- `.git/HEAD` → `ref: refs/heads/master`, but `.git/refs/heads/` is empty;
- `.git/objects/pack/` is empty; no loose objects;
- `git log` fails (no commits);
- no remote configured;
- the benchmark recorded `git_commit = "NO_GIT"` and isolation `filesystem copy; NO_WORKTREE`
  for exactly this reason.

The same holds for the benchmark worktree copy derived from it.

## Risk

Because there is no first commit, "the repository" is only a working tree:

1. **No real worktree / no history.** `git worktree`, `git diff`, `git blame`, and
   commit-anchored rollback are unavailable. A bad edit has no tracked prior version to
   return to.
2. **No reliable baseline.** The frozen verification baseline is identified only by an APK
   sha256 plus a filesystem copy — not by `(commit, path)` provenance. Any future claim that a
   result was produced from a specific source revision cannot be independently reproduced.
3. **Weak provenance / diff / audit.** There is no object database to prove what changed
   between the pre-testTag build and the frozen build, or between the frozen build and future
   work.
4. **Harness isolation workarounds.** The benchmark had to copy the tree instead of using a
   git worktree (`NO_WORKTREE`), which is fragile and does not scale.

## Recommendation (next phase, requires user approval)

On explicit user approval, establish a **Phase B baseline**:

1. Create an initial commit of the current `KeepLab-Relay` tree.
2. Tag it (e.g. `phase-b-baseline`) and, if desired, tag the verification-benchmark tree with
   the frozen apk sha256 in the tag message.
3. Thereafter use real `git worktree` for verification runs, and record the commit SHA in
   `benchmark-run.json.git_commit` (replacing `NO_GIT`).

Dependencies to settle before committing:

- a `.gitignore` that excludes build output / SDK paths (a `.gitignore` already exists);
- a decision on whether `frozen/app-debug-frozen.apk` (binary, ~19 MB) is tracked, LFS'd, or
  referenced by hash only;
- an author/identity for the baseline commit.

## Do not do now

This task does **not** run `git init`, `git add`, `git commit`, or `git tag`. The baseline
frozen in `reports/FINAL-VERIFICATION-COMPRESSION-AUDIT.md` remains identified by APK sha256,
which is unchanged by hardening.
