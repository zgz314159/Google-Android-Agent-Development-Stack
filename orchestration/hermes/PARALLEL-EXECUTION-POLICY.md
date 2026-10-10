# PARALLEL-EXECUTION-POLICY

Applies to Hermes orchestration over this Stack.

## Defaults

- **Read-only work** (audit, exploration, summarisation, search): parallel delegation is
  allowed and encouraged. Independent read-only tasks carry no shared mutable state.
- **Write work** (implementation, edits): **single writer by default**. One writer owns a
  file boundary at a time.

## Parallel implementation

- Two writers must never edit the same file/`allowed_paths` set concurrently.
- When parallel implementation is genuinely required, each writer runs in an isolated
  **git worktree** (worktree-per-writer). Merges are explicit and reviewed.
- The frozen contract's `tasks[].depends` defines the allowed concurrency: a task may
  start only after all its dependencies complete.

## Shared exclusive resources

- Any resource with `capacity = 1` (the physical Android device `87296ada`, a build
  directory, a single APK) must be serialized through a host lock before use.
- The device lock is `verification/core/device_lock.sh` (`flock`, resource
  `device:<serial>`). A second concurrent run fails closed with `DEVICE_BUSY`.

## Observability

- Subagent/delegation execution must be recorded (child ids, start/end, concurrency) so
  the Evaluation layer can attribute wall time. Unprovable overlap is reported
  `NOT_AVAILABLE`, never guessed.

## Anti-patterns (forbidden)

- Fan-out write storms over the same file boundary.
- Concurrent device access from two workers.
- Re-exploring a target that already has a frozen replay flow.
