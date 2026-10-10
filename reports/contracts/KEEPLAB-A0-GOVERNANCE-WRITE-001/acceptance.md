# Acceptance — KEEPLAB-A0-GOVERNANCE-WRITE-001

**Contract:** `KEEPLAB-A0-GOVERNANCE-WRITE-001`
**Phase:** `A0_GOVERNANCE_WRITE` (temporary execution contract)
**Date:** 2026-10-06
**Human authorization:** D-15 `YES_BOUNDED_ACCOUNT_NETWORK_UNLOCK` (+ D-02/D-03/D-07/D-08/D-09)
**Status:** READY (contract package validated; the amendment itself is NOT applied)

## 0. What this package is

A narrow, human-approved governance-write contract. It authorizes a **later, separate**
apply session to perform the canonical A0 governance amendment through the **same
unmodified Contract Guard**. It performs no amendment itself and authorizes no
implementation.

## 1. Machine-readable authorization semantics

Recorded in `implementation-contract.json` under `authorization_semantics` (the guard
loader ignores unknown keys, so this cannot invalidate the contract) and mirrored here:

| Field | Value |
|---|---|
| `phase` | `A0_GOVERNANCE_WRITE` |
| `human_authorization` | `TRUE` |
| `human_decision` | `D-15 YES_BOUNDED_ACCOUNT_NETWORK_UNLOCK` |
| `mutation_scope` | the 3 governance files, exactly |
| `product_source_mutation` | `FORBIDDEN` |
| `implementation_mutation` | `FORBIDDEN` |
| `backend_mutation` | `FORBIDDEN` |
| `device_mutation` | `FORBIDDEN` |
| `historical_evidence_mutation` | `FORBIDDEN` |
| `guard_mutation` | `FORBIDDEN` |
| `implementation_authorization_model` | `PHASE_GATED` (not unrestricted) |

## 2. Allowed mutation scope (exhaustive)

1. `KeepLab-Relay/MISSION.md`
2. `KeepLab-Relay/FACTORY_RULES.md` — **conditional**; byte-identical expected
3. `KeepLab-Relay/specs/google-keep-parity/ROADMAP.md`

Evidence output:

- `Google-Android-Agent-Development-Stack/reports/`
- `Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/keeplab-a0-governance-write/`

## 3. Semantic acceptance criteria

**AC-A0GW-001 — MISSION.md bounded policy.** The absolute account/network prohibition
(hard invariant 1 and the "Sync and identity" out-of-scope entry) is superseded by
`BOUNDED_ACCOUNT_NETWORK_POLICY`, and the file still declares: LOCAL_FIRST mandatory;
account optional for local notes; network optional for local notes; offline read
mandatory; offline write mandatory; existing local notes protected; Room remains the
local SSOT; remote sync optional and never the canonical UI source; Google/Firebase auth
forbidden unless separately human-approved; network or auth failure cannot delete local
data.

**AC-A0GW-002 — no implementation detail.** The amendment introduces no A1/A2/A3
implementation content: no endpoints, no schema, no vendor sub-choices, no stack
specifics beyond the already-approved D-07/D-08/D-09 values.

**AC-A0GW-003 — FACTORY_RULES.md honesty.** FACTORY_RULES.md is changed **only if** its
current text categorically conflicts with the approved bounded policy. The reviewed text
(871 bytes, 2026-10-02) contains no such prohibition, so the expected result is
**byte-identical** (same sha256). Permission is not mandatory mutation.

**AC-A0GW-004 — ROADMAP.md minimal status update.** Only the RISK-GOV-001 /
account-network governance status changes, to `RESOLVED_BY_BOUNDED_HUMAN_UNLOCK`, with
D-15, 2026-10-06, scope = account/network architecture phases only, limits = phase-gated /
local-first / own-backend / no Google-Firebase by default, and an explicit residual
naming the still-gated items. No unrelated risk, phase, matrix ID or sequencing line is
closed, re-scoped or deleted.

**AC-A0GW-005 — nothing else changed.** After the amendment, every other tracked file is
byte-identical: `KeepLab-Relay/app/**`, `KeepLab-Relay/**/*.gradle*`, `KeepLab-Relay/.factory/**`,
`KeepLab-Relay/HANDOFF.md`, `KeepLab-Relay/AGENTS.md`, the frozen P0B packages, `Testapp/`,
`PowerAi/`, `KeepLab-Relay-evidence/`, the frozen `verification/**` subtrees, Hermes core
and `contract_guard.py`.

**AC-A0GW-006 — guard untouched and active.** The guard source, the hook configuration
and the active frozen P0B-CLOSE contract are unmodified; the guard remains the same
fail-closed `pre_tool_call` hook.

**AC-A0GW-007 — stale input fails closed.** Before mutating, the apply session re-hashes
all three files and fails closed with `STALE_GOVERNANCE_INPUT` on any drift.

**AC-A0GW-008 — self-protection.** The apply session verifies this package's sha256
manifest before touching any governance file and never rewrites the package or broadens
its own allowed paths.

**AC-A0GW-009 — phase discipline.** The apply session stops after A0. It does not start
A1 or A2 and grants no implementation authorization.

**AC-A0GW-010 — D-14 untouched.** D-14 remains `HUMAN_DECISION_PENDING`. This package is
a temporary execution contract and is not D-14's permanent formal spec-package decision.

## 4. Required guard classifications (validated in this phase, simulated)

| Write target | Required |
|---|---|
| `KeepLab-Relay/MISSION.md` | ALLOW |
| `KeepLab-Relay/FACTORY_RULES.md` | ALLOW |
| `KeepLab-Relay/specs/google-keep-parity/ROADMAP.md` | ALLOW |
| `KeepLab-Relay/app/src/main/...` | BLOCK |
| `KeepLab-Relay/HANDOFF.md` | BLOCK |
| `KeepLab-Relay/.factory/decisions.md` | BLOCK |
| `Testapp/...` | BLOCK |
| `PowerAi/...` | BLOCK |
| current P0B frozen contract | BLOCK |
| this contract package itself | BLOCK |
| allowed apply evidence output | ALLOW |

## 5. Readiness gates

| Gate | Result |
|---|---|
| acceptance | PASS |
| boundaries | PASS |
| hashes | PASS |
| schema | PASS |
| traceability | PASS |
