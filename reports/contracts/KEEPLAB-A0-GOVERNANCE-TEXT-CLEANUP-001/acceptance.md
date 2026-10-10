# Acceptance — KEEPLAB-A0-GOVERNANCE-TEXT-CLEANUP-001

**Contract:** `KEEPLAB-A0-GOVERNANCE-TEXT-CLEANUP-001`
**Phase:** `A0_GOVERNANCE_TEXT_CLEANUP` (temporary execution contract)
**Date:** 2026-10-06
**Human authorization:** D-15 `YES_BOUNDED_ACCOUNT_NETWORK_UNLOCK` (already recorded; the cleanup is semantically authorized and must not change D-15's meaning)
**Observation closed:** `OBS-1` — residual pre-D-15 descriptive sentence in `MISSION.md`
**Status:** READY (contract package validated; the replacement itself is NOT applied)

## 0. What this package is

A narrow, human-authorized governance **text-consistency** contract. It authorizes a
**later, separate** apply session to replace exactly one descriptive sentence inside
`KeepLab-Relay/MISSION.md` through the **same unmodified Contract Guard**. It performs no
replacement itself and authorizes no implementation.

## 1. Machine-readable authorization semantics

Recorded in `implementation-contract.json` under `authorization_semantics` and
`mutation_spec` (the guard loader ignores unknown keys, so these cannot invalidate the
contract) and mirrored here:

| Field | Value |
|---|---|
| `phase` | `A0_GOVERNANCE_TEXT_CLEANUP` |
| `human_authorization` | `TRUE` |
| `human_decision` | `D-15 YES_BOUNDED_ACCOUNT_NETWORK_UNLOCK` |
| `mutation_scope` | exactly `KeepLab-Relay/MISSION.md` |
| `mutation_unit` | `ONE_SEMANTIC_SENTENCE` |
| `product_source_mutation` | `FORBIDDEN` |
| `implementation_mutation` | `FORBIDDEN` |
| `backend_mutation` | `FORBIDDEN` |
| `device_mutation` | `FORBIDDEN` |
| `historical_evidence_mutation` | `FORBIDDEN` |
| `guard_mutation` | `FORBIDDEN` |
| `contract_mutation` | `FORBIDDEN` |
| `implementation_authorization_model` | `PHASE_GATED` (not unrestricted) |

## 2. The exact mutation (exhaustive)

**File:** `KeepLab-Relay/MISSION.md`

**Old sentence (must occur exactly once):**

```
Everything lives on the device: no account, no sync, no network.
```

**New sentence (must not already occur):**

```
KeepLab remains local-first: local notes require no account or network; optional account and sync capabilities are allowed only inside an explicitly human-approved, phase-gated contract.
```

**Rules that make it provably minimal:**

- The replacement is **inline** — the new sentence replaces the old sentence in place,
  inside the same line. The line is **not** re-flowed and **no** other line is touched
  or re-wrapped.
- The resulting file must satisfy:
  `resulting_text == original_text.replace(old_sentence, new_sentence, 1)`.
- After the edit, the old sentence occurs **0** times, the new sentence occurs **exactly
  1** time, and `BOUNDED_ACCOUNT_NETWORK_POLICY` is still present.
- **No semantic expansion.** No other sentence, in MISSION.md or anywhere else, is in
  scope.

## 3. Allowed write surface (exhaustive)

1. `KeepLab-Relay/MISSION.md`

Evidence output:

- `Google-Android-Agent-Development-Stack/reports/`
- `Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/keeplab-a0-governance-text-cleanup/`

## 4. Semantic acceptance criteria

**AC-A0TC-001 — OBS-1 corrected.** The old sentence no longer exists in `MISSION.md`; the
new sentence exists exactly once, at the same position in the same line.

**AC-A0TC-002 — minimal diff.** The only byte difference in `MISSION.md` is the substring
replacement described in §2. Every other line is byte-identical.

**AC-A0TC-003 — bounded policy still authoritative.** `BOUNDED_ACCOUNT_NETWORK_POLICY`
is still present and unchanged in `MISSION.md`; D-15's meaning is unchanged.

**AC-A0TC-004 — no semantic expansion.** No endpoint, schema, vendor sub-choice, stack
detail or any other prose change is introduced.

**AC-A0TC-005 — nothing else changed.** After the cleanup, every protected file is
byte-identical: `KeepLab-Relay/FACTORY_RULES.md` (→ `7e6c4897…68d1`),
`KeepLab-Relay/specs/google-keep-parity/ROADMAP.md` (→ `5ab14973…4aef2`),
`KeepLab-Relay/app/**`, `KeepLab-Relay/**/*.gradle*`, `KeepLab-Relay/.factory/**`,
`KeepLab-Relay/HANDOFF.md`, `KeepLab-Relay/AGENTS.md`, `KeepLab-Relay/FACTORY.md`, the
frozen P0B packages, the earlier A0 governance-write contract package, `Testapp/`,
`PowerAi/`, `KeepLab-Relay-evidence/`, the frozen `verification/**` subtrees, Hermes core
and `contract_guard.py`.

**AC-A0TC-006 — guard untouched and active.** The guard source, the hook configuration and
the active frozen P0B-CLOSE contract are unmodified; the guard remains the same
fail-closed `pre_tool_call` hook.

**AC-A0TC-007 — stale input fails closed.** Before mutating, the apply session re-hashes
`MISSION.md` and fails closed with `STALE_GOVERNANCE_INPUT` on any drift. It never
re-baselines.

**AC-A0TC-008 — self-protection.** The apply session verifies this package's sha256
manifest before touching `MISSION.md` and never rewrites the package or broadens its own
allowed paths.

**AC-A0TC-009 — phase discipline.** The apply session stops after the cleanup. It does not
start A1 or A2 and grants no implementation authorization. A0 remains READY.

**AC-A0TC-010 — D-14 untouched.** D-14 remains `HUMAN_DECISION_PENDING`. This package is a
temporary execution contract and is not D-14's permanent formal spec-package decision.

## 5. Required guard classifications (validated in this phase, simulated)

| Write target | Required |
|---|---|
| `KeepLab-Relay/MISSION.md` | ALLOW |
| `Google-Android-Agent-Development-Stack/reports/...` | ALLOW |
| `.../orchestration/hermes/evidence/keeplab-a0-governance-text-cleanup/...` | ALLOW |
| `KeepLab-Relay/FACTORY_RULES.md` | BLOCK |
| `KeepLab-Relay/specs/google-keep-parity/ROADMAP.md` | BLOCK |
| `KeepLab-Relay/app/src/main/...` | BLOCK |
| `KeepLab-Relay/app/schemas/...` (Room schema) | BLOCK |
| `KeepLab-Relay/.factory/...` | BLOCK |
| `KeepLab-Relay/HANDOFF.md` | BLOCK |
| `Testapp/...` | BLOCK |
| `PowerAi/...` | BLOCK |
| `.../evaluation_adapter/contract_guard.py` | BLOCK |
| this contract package itself | BLOCK |
| the earlier A0 governance-write package | BLOCK |

## 6. Readiness gates

| Gate | Result |
|---|---|
| acceptance | PASS |
| boundaries | PASS |
| hashes | PASS |
| schema | PASS |
| traceability | PASS |
