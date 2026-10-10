# KEEPLAB-A0-OPEN-GOVERNANCE-WRITE-CONTRACT

**Phase:** contract creation + validation. **Not** a governance mutation, **not** implementation.
**Date:** 2026-10-06 (CST) · **Task:** open the narrow human-approved governance-write Contract that unblocks A0.

## 1. Result in one paragraph

The Contract Guard already supports a package override: it resolves its package as
`os.environ.get("HERMES_CONTRACT_PACKAGE") or DEFAULT_PACKAGE`. Because the hook subprocess
inherits the Hermes process environment, a future session can point the **same unmodified
guard** at a **different, narrowly scoped contract** by exporting that variable. A new
temporary execution contract — `KEEPLAB-A0-GOVERNANCE-WRITE-001` — was authored and
validated under an already-authorized Stack reports location. It authorizes exactly the
three canonical governance files plus two evidence locations, blocks everything else
(including itself), freezes the expected before hashes, and ships an APPLY prompt that was
**not** executed. **No governance file, no product source, no guard, no hook config and no
existing contract was modified.** A0 remains BLOCKED today only because the apply step has
not been run yet.

## 2. Why A0 was blocked

The active frozen contract `KEEPLAB-P0B-CLOSE-001` is a benchmark-closure contract. Its
`allowed_paths` cover benchmark surfaces and Stack reports/evidence; its `forbidden_paths`
list `KeepLab-Relay/MISSION.md` and `KeepLab-Relay/FACTORY_RULES.md`; and
`KeepLab-Relay/specs/google-keep-parity/ROADMAP.md` is listed nowhere. The guard tests
forbidden first, allows second, and **fails closed on anything unlisted**, so all three
governance writes are blocked by design. The A0 phase correctly stopped rather than
weakening the boundary.

## 3. Supported switch mechanism (from source, not memory)

| Question | Answer |
|---|---|
| Does a supported package override exist? | **YES** |
| Exact mechanism | `HERMES_CONTRACT_PACKAGE` environment variable |
| Guard code | `contract_guard.py:475` — `package_dir = os.environ.get("HERMES_CONTRACT_PACKAGE") or DEFAULT_PACKAGE` |
| Default package | `/mnt/AndroidDev/Projects/KeepLab-Relay/specs/p0b-close-benchmarkability` |
| CLI flag? | none — `argv` is unused |
| Per-hook `env:` key in `hooks:` config? | **not supported** — `ShellHookSpec` has no `env` field |
| How the hook sees the variable | `shell_hooks._spawn` → `build_subprocess_env(...)`, which snapshots `os.environ`; the hook subprocess inherits the Hermes process environment |
| Guard source modified | **NO** (`e418fc28…b3746`) |
| Hook config modified | **NO** |

Activation for the future apply session:

```bash
export HERMES_CONTRACT_PACKAGE=/mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack/reports/contracts/KEEPLAB-A0-GOVERNANCE-WRITE-001
```

Same guard, same fail-closed hook, different contract. No patch, no hook removal, no config
edit, no rename-to-evade-classification, no out-of-project write-and-copy.

## 4. The new contract

**Package:** `Google-Android-Agent-Development-Stack/reports/contracts/KEEPLAB-A0-GOVERNANCE-WRITE-001/`
(chosen because `reports/` is already authorized today — the protected KeepLab spec locations are not).

| File | Role |
|---|---|
| `implementation-contract.json` | the machine contract (`allowed_paths`, `forbidden_paths`, `authorization_semantics`, frozen hashes) |
| `project-context.json` | `source_root` + `path_classes` |
| `manifest.json` | sha256 of the 5 authored artifacts; the guard's integrity gate |
| `acceptance.md` | AC-A0GW-001..010 |
| `EXECUTOR-PROMPT.md` | pointer + activation recipe |
| `KEEPLAB-A0-GOVERNANCE-WRITE-APPLY.md` | the future execution prompt (not executed) |
| `READY.json` | readiness marker |

**Allowed (5):** the three governance files, `reports/`, and
`orchestration/hermes/evidence/keeplab-a0-governance-write/`.
**Forbidden (47):** every unrelated forbidden path of the frozen P0B-CLOSE contract, kept
verbatim, plus new prohibitions for the surfaces this narrow contract must not reach —
`KeepLab-Relay/app/**`, root/app Gradle files, the frozen P0B package, the guard adapter —
and the package itself.

## 5. Validation

Two independent checks were run against the **unmodified** guard:

1. **Hook-path simulation** — 30 payloads through `contract_guard.py` as a subprocess with
   `HERMES_CONTRACT_PACKAGE` selecting the package. **30/30 matched expectation**
   (8 ALLOW / 22 BLOCK against the new contract, plus 4 control cases against the current
   contract confirming MISSION/FACTORY_RULES/ROADMAP are blocked **today** and `reports/` is
   allowed today). No protected file was written.
2. **Loader validation** — the new package imported through the guard's own `load_contract`
   and `classify`: `contract_id` correct, `integrity = MANIFEST_OK`, `source_root` correct,
   14 required classifications correct, and all 7 protected reference files byte-identical.

Representative labels: `MISSION.md → ALLOW/GOVERNANCE_WRITE_TARGET`,
`app/src/main/... → BLOCK/PRODUCTION_IMMUTABLE`, `.factory/decisions.md → BLOCK/FORBIDDEN`,
the package itself → `BLOCK/CONTRACT_PACKAGE_READ_ONLY`.

## 6. Frozen governance inputs

| File | sha256 | State |
|---|---|---|
| `KeepLab-Relay/MISSION.md` | `9e9107b1…b06a` | FROZEN, mtime 2026-10-03 |
| `KeepLab-Relay/FACTORY_RULES.md` | `7e6c4897…68d1` | FROZEN, mtime 2026-10-02 |
| `KeepLab-Relay/specs/google-keep-parity/ROADMAP.md` | `58d6505b…0d47` | FROZEN, mtime 2026-10-04 |

All three match the A0 evidence exactly. The apply session must fail closed with
`STALE_GOVERNANCE_INPUT` on any drift.

## 7. FACTORY_RULES conditional

`FACTORY_RULES.md` (871 bytes, 2026-10-02) contains no categorical account/network
prohibition — it is workflow guidance about shared gates, irreversible actions, truthfully
reporting failed checks and not bypassing an Archon gate. **No amendment is required**, so
the apply session must leave it **byte-identical**. Permission is not mandatory mutation.

## 8. What the amendment will do (for the apply session)

- **MISSION.md** — supersede hard invariant 1's absolute "no network" with the versioned
  `BOUNDED_ACCOUNT_NETWORK_POLICY`, narrow the out-of-scope "Sync and identity" entry to
  phases outside an explicitly human-approved, phase-gated contract, add the allowed-evolution
  entry and the human-commit note. Preserved: local-first mandatory, account/network optional
  for local use, offline read+write mandatory, existing local notes protected, Room as local
  SSOT, remote sync optional and never the canonical UI source, Google/Firebase auth forbidden
  unless separately human-approved, no local data loss on network/auth failure.
- **ROADMAP.md** — one status update: RISK-GOV-001 **account/network** →
  `RESOLVED_BY_BOUNDED_HUMAN_UNLOCK` (D-15, 2026-10-06, phase-gated · local-first ·
  own-backend · no Google/Firebase by default) with an explicit residual. No unrelated risk,
  phase or matrix ID is closed.

## 9. Boundaries held

No governance file, product source, Gradle file, Room schema, `.factory/**`, `HANDOFF.md`,
`AGENTS.md`, frozen P0B contract, guard source, hook configuration or Hermes core was
modified. No backend, Dockerfile, PostgreSQL or cloud resource was created. The Android
device was not touched and `adb` was not run. D-14 remains `HUMAN_DECISION_PENDING` — this
is a temporary execution contract, not D-14's permanent spec-package decision.

## 10. Evidence

`orchestration/hermes/evidence/keeplab-open-governance-write-contract/` —
`current-contract.json`, `guard-loader-analysis.json`, `contract-package-manifest.json`,
`before-protected-hashes.json`, `guard-simulation.json`, `apply-prompt-manifest.json`,
`verification.json` (+ the raw `terminal.log`).

## 11. Next

Run `KEEPLAB-A0-GOVERNANCE-WRITE-APPLY` (the authored-but-unexecuted prompt). It stops
after A0. It must not start A1 or A2.
