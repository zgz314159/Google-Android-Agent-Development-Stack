# Auto-Finalizer operational activation

Makes the Evaluation Core v0.2.1 Auto-Finalizer actually run during daily use — without
entering the observed task's timing path and without modifying Command Code internals.

## What runs

```
systemd --user timer (every 2 min, persistent)
   -> oneshot service:
      python3 evaluation/commandcode/auto_finalize.py scan
          --projects-root ~/.commandcode/projects
          --output-root <_evaluation>
          --stable-seconds 60
```

`scan` is cheap: it stats each session JSONL (mtime + size) and only runs the full
deterministic core for a session that is stable and not already finalized. Zero LLM calls,
zero network calls, raw JSONL read-only.

## Why a timer + oneshot scan (not a long-running watcher)

- **Crash-safe**: the timer re-fires; no daemon to supervise.
- **Bounded logs**: journald rotates automatically.
- **Idle-friendly**: `Nice=10` + `IOSchedulingClass=idle`; the work is a stat when nothing
  changed.
- A long-running `auto_finalize.py watch` is still available for ad-hoc use; the timer is the
  production activation.

## Install (user-scoped, non-root)

```bash
verification/integration/autofinalizer/install.sh install   # render units into ~/.config/systemd/user
verification/integration/autofinalizer/install.sh enable    # enable --now the timer
verification/integration/autofinalizer/install.sh status    # service + timer state
verification/integration/autofinalizer/install.sh start     # run one scan immediately
verification/integration/autofinalizer/install.sh disable   # stop + disable
verification/integration/autofinalizer/install.sh uninstall # remove units
```

Override the evaluation output root with `AUTOFINALIZER_OUTPUT_ROOT`.

## Non-goals

- Never writes to `/etc/systemd/...`.
- Never installs a Command Code `Stop` hook (it fires inside the observed turn and would add
  a process spawn to the observed timing path).
- Never modifies, copies, or re-runs the raw session.
