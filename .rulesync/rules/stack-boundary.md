---
targets:
  - cursor
root: true
description: "Google Stack Cursor project boundary — thin; OS sandbox and broker remain authoritative."
cursor:
  alwaysApply: true
---

# Google Stack Cursor project boundary

Central policy (readable sibling system project):
`/home/zhong/Projects/AI-Engineering-Governance-Layer/governance/global-agent-policy.md`

Controlled task entry (AEGL-owned):
`/home/zhong/Projects/AI-Engineering-Governance-Layer/bin/aegl-task`
(`task start Google-Android-Agent-Development-Stack <name>`, then verify/register/record/promote)

## Binding rules

- Treat the formal Stack checkout as read-only for AI-assisted work. Edit only in an approved disposable worktree or independent checkout outside the formal tree, then use the trusted promotion path (`aegl-task` + broker).
- Keep authoritative Stack source, tests, fixtures, schemas, locks, build scripts, and Stack-specific policy in this owning project. Do not depend on undeclared source under a tool install or AEGL internals beyond declared entrypoints.
- Keep generated builds, test results, caches, logs, screenshots, APKs, temporary databases, and task state out of the formal project tree and out of `/home/zhong/Projects`. Prefer declared external task directories (for example under `$XDG_STATE_HOME/aegl/tasks`).
- Do not bypass a failed path, sandbox, or promotion gate. Report the exact blocker; do not claim PASS or completion from a partial run.
- Never overwrite existing agent instruction files (`AGENTS.md`, `CLAUDE.md`, or non-generated rules) during rule sync without an explicit conflict resolution.

## Scope notes

- These Cursor project rules are defense in depth. They are not an OS isolation substitute and do not replace entry-bind, sandbox, or broker gates.
- Cursor **global** RuleSync deploy is unsupported on pinned RuleSync v25.0.0; this file is **project-level only**.
- Do not copy AEGL gate implementations into this project; invoke the declared AEGL entry and keep Stack-owned source here.
