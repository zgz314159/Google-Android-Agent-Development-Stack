# KEEPLAB-A0-GOVERNANCE-WRITE-APPLY

**Canonical A0 governance amendment — APPLIED and verified through the same unmodified Contract Guard**

- Contract: `KEEPLAB-A0-GOVERNANCE-WRITE-001`
- Package: `reports/contracts/KEEPLAB-A0-GOVERNANCE-WRITE-001` (`CONTRACT_PACKAGE: READ_ONLY_INPUT`)
- Phase: `A0_GOVERNANCE_WRITE`
- Date: **2026-10-06 (CST)**
- Human authorization: `D-15 = YES_BOUNDED_ACCOUNT_NETWORK_UNLOCK` (+ D-02/D-03/D-07/D-08/D-09)
- Result: **A0 = READY**
- Stops after A0. A1 and A2 not started.

---

## 1. How the contract was activated (same guard, different package)

```
HERMES_CONTRACT_PACKAGE=/mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack/reports/contracts/KEEPLAB-A0-GOVERNANCE-WRITE-001
```

The guard resolves its package as `os.environ.get("HERMES_CONTRACT_PACKAGE") or DEFAULT_PACKAGE`,
and the `pre_tool_call` hook subprocess inherits that from the Hermes process environment.

| Activation check | Result |
| --- | --- |
| `load_contract(package_dir).contract_id` | `KEEPLAB-A0-GOVERNANCE-WRITE-001` — PASS |
| `load_contract(package_dir).integrity` | `MANIFEST_OK` — PASS |
| `sha256(contract_guard.py)` | `e418fc28…b3746` (matches the contract's frozen value) — PASS |
| hook config still fail-closed `pre_tool_call` | `write_file\|patch\|terminal`, `fail_closed: true`, sha256 `7ac5c4cb…` unchanged since 2026-10-05 — PASS |

**No guard patch, no hook edit, no config edit, no file rename, no out-of-project write-and-copy.**

Control case proved the point: with `HERMES_CONTRACT_PACKAGE` pointing back at the frozen
P0B-CLOSE package, `KeepLab-Relay/MISSION.md` is **BLOCKed** again (`PRODUCTION_IMMUTABLE`).
The unlock comes from the package switch, never from a weakened guard.

## 2. Package and input integrity (before any mutation)

- **Package manifest:** all 5 entries (`implementation-contract.json`, `project-context.json`,
  `acceptance.md`, `EXECUTOR-PROMPT.md`, `KEEPLAB-A0-GOVERNANCE-WRITE-APPLY.md`) re-hashed
  on disk → **5/5 match**, sizes match. Package not repaired, not rewritten.
- **Governance inputs:** all three `expected_before_hashes` matched live →
  **no `STALE_GOVERNANCE_INPUT`**, hashes never re-baselined.

| File | sha256 before | size | mtime |
| --- | --- | --- | --- |
| `KeepLab-Relay/MISSION.md` | `9e9107b1…6b06a` | 5959 | 2026-10-03T11:30:01 |
| `KeepLab-Relay/FACTORY_RULES.md` | `7e6c4897…268d1` | 871 | 2026-10-02T23:43:45 |
| `KeepLab-Relay/specs/google-keep-parity/ROADMAP.md` | `58d6505b…cb0d47` | 12738 | 2026-10-04T20:19:31 |

## 3. Guard-level preflight (25/25 verdicts as required)

The **unmodified** guard was invoked exactly as the hook invokes it.

| Case group | Result |
| --- | --- |
| `MISSION.md` / `FACTORY_RULES.md` / `ROADMAP.md` via `write_file` and `patch` | ALLOW ✔ |
| `reports/` and this phase's evidence directory | ALLOW ✔ |
| `KeepLab-Relay/app/**`, `HANDOFF.md`, `AGENTS.md`, `.factory/**`, gradle, frozen P0B packages | BLOCK ✔ |
| `Testapp/`, `PowerAi/`, `KeepLab-Relay-evidence/`, frozen `verification/**`, `.hermes.md` | BLOCK ✔ |
| `contract_guard.py`, this contract package, unlisted sibling `specs/google-keep-parity/PARITY-MATRIX.md` | BLOCK ✔ |
| terminal redirect / `cp` into a protected path | BLOCK ✔ |
| control: `MISSION.md` under the frozen default package | BLOCK ✔ |

## 4. Amendments applied (exactly the approved text)

### 4.1 `KeepLab-Relay/MISSION.md` — seq 1..4 applied

- **Invariant 1** — the absolute *"Local-first, no network"* wording is superseded by
  `BOUNDED_ACCOUNT_NETWORK_POLICY` (invariant **v2, 2026-10-06**). It now declares:
  LOCAL_FIRST mandatory · account optional · network optional · offline read mandatory ·
  offline write mandatory · existing local notes protected (never silently assigned,
  uploaded, deleted or merged into an account) · **Room remains the local SSOT** · remote
  sync optional and never the canonical UI data source · the device stays the source of
  truth for the UI · **network or authentication failure must never delete local data** ·
  Google/Firebase identity forbidden unless separately human-approved.
- **Out-of-scope "Sync and identity"** — narrowed to account/sign-in/sync/reconciliation
  *outside an explicitly human-approved, phase-gated contract*.
- **Allowed evolutions** — bounded account/network phases appended.
- **Governance note** — changing invariant 1 now requires a human commit carrying the
  approved bounded scope and limits.

`9e9107b1…6b06a` → **`f857295d…d128cd`** (5959 → 7400 bytes)

### 4.2 `KeepLab-Relay/FACTORY_RULES.md` — **byte-identical**

`FACTORY_RULES_AMENDMENT_REQUIRED: false`. The current text (871 bytes, 2026-10-02) contains
**no categorical account/network prohibition** — it covers scope, tests, security invariants,
secrets, truthful reporting, protected paths, migration requirements and Archon gates. No
categorical conflict therefore no amendment; permission is not obligation. sha256 and mtime
unchanged: `7e6c4897…268d1`, 2026-10-02T23:43:45.

### 4.3 `KeepLab-Relay/specs/google-keep-parity/ROADMAP.md` — one status update (seq 6)

```
## RISK-GOV-001 — Governance reconciliation — RESOLVED_BY_BOUNDED_HUMAN_UNLOCK

Date:              2026-10-06
Approved decision: D-15 = YES_BOUNDED_ACCOUNT_NETWORK_UNLOCK
Scope:             account/network architecture phases only
Limits:            phase-gated · local-first · own-backend · no Google/Firebase by default
Residual:          P3-large-screen, P4-rich-text, P5-attachments/link and P7-ecosystem remain
                   gated by their own items; this resolution covers the account/network
                   prohibition only.
```

The pre-existing RISK-GOV-001 paragraph and its three bullets (`Governance scope`,
`Does not block`, `Risk: HIGH.`) are **untouched**, so RISK-GOV-001's remaining
non-account/network governance scope stays open. No other risk, phase section, matrix-ID
list, sequencing line or P-item was closed, re-scoped or deleted.

`58d6505b…cb0d47` → **`5ab14973…14aef2`** (12738 → 13161 bytes)

### 4.4 Proposal seq 7 — not applied

`KeepLab-Relay/.factory/decisions.md` is outside the contract's mutation scope, is listed in
`forbidden_paths`, and the guard returns `BLOCK (FORBIDDEN)`. Excluded; no broadening attempted.

## 5. Result

| File | sha256 after | size | mtime after |
| --- | --- | --- | --- |
| `KeepLab-Relay/MISSION.md` | `f857295d…d128cd` | 7400 | 2026-10-06T07:15:35 |
| `KeepLab-Relay/FACTORY_RULES.md` | `7e6c4897…268d1` (unchanged) | 871 | 2026-10-02T23:43:45 (unchanged) |
| `KeepLab-Relay/specs/google-keep-parity/ROADMAP.md` | `5ab14973…14aef2` | 13161 | 2026-10-06T07:15:43 |

**Nothing else changed.** 21/21 protected scopes clean: `KeepLab-Relay/app/**` (4279 files),
gradle (11), `.factory` (5), `harness` (10), frozen P0B packages (40), `Testapp`/`PowerAi`
(absent), `KeepLab-Relay-evidence` (24), frozen `verification/**` (388),
`verification-benchmark` (399), `specification` (39), `evaluation` (37), `references` (4013),
the guard adapter dir (25), `.hermes.md`, and this contract package (7 files, all still
matching their manifest).

Three pre-existing harness artefacts also moved during the window and are recorded
transparently in `unchanged-scope-scan.json`: this phase's own `terminal.log` (pinned-Hermes
session transcript), the guard's append-only `contract-guard-decisions.jsonl` audit log, and
`_evaluation/.auto_finalize_index.json` (Auto-Finalizer index). None is a governance,
product, Gradle, schema or backend file and none was authored by this phase.

No implementation content: 0 endpoints, 0 schema changes, 0 vendor sub-choices, no stack
detail beyond the already-approved D-07/D-08/D-09 values. The guard audit log records every
project write of this phase as `GOVERNANCE_WRITE_TARGET` or `EVIDENCE_OUTPUT` = **ALLOW**.

## 6. Evidence

`orchestration/hermes/evidence/keeplab-a0-governance-write/`

- `pre-apply-hashes.json`
- `package-integrity.json`
- `guard-activation.json` (activation, guard identity, hook config, 25-case preflight)
- `governance-diff-applied.json`
- `post-apply-hashes.json`
- `unchanged-scope-scan.json`
- `verification.json` (21/21 checks PASS, 0 stop conditions, 2 informational observations)

## 7. Status

```
A0: READY
A1: READY_FOR_SEPARATE_CONTRACT
A2: READY_FOR_SEPARATE_CONTRACT
A3: BLOCKED_BY_HUMAN_DECISIONS
D-01 / D-04 / D-10: PENDING
D-14: HUMAN_DECISION_PENDING
IMPLEMENTATION_AUTHORIZATION_MODEL: PHASE_GATED
IMPLEMENTATION_AUTHORIZATION: NOT_GRANTED
```

The Android device `87296ada` was never opened. No adb, Maestro or UiAutomator run. No
product source, Gradle, Room, backend, Docker, PostgreSQL or cloud resource was touched.
