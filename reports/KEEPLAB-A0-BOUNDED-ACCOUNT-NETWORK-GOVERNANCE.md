# KEEPLAB-A0-BOUNDED-ACCOUNT-NETWORK-GOVERNANCE

**Bounded account/network governance policy + exact governance amendment proposal (NOT APPLIED)**

- Task: `KEEPLAB-HUMAN-ARCHITECTURE-DECISIONS-A0`
- Date: **2026-10-06 (CST)**
- Status: **PROPOSED_NOT_APPLIED · NON_IMPLEMENTATION_AUTHORIZING**
- Basis: human approval of `D-15 = YES_BOUNDED_ACCOUNT_NETWORK_UNLOCK` (plus D-02, D-03, D-07, D-08, D-09).
- Companion: `reports/KEEPLAB-A0-HUMAN-ARCHITECTURE-DECISIONS.md`.

> This document defines the bounded policy that D-15 authorizes, and carries the **exact** minimal
> amendment text that would need to be written into the protected governance files. The amendment
> was **not applied**: the active frozen Contract Guard blocks writes to those files
> (`BLOCKED_BY_CONTRACT_GUARD`). Nothing here authorizes implementation.

---

## 1. BOUNDED_ACCOUNT_NETWORK_POLICY (normative)

The former absolute constraint

```
NO ACCOUNT
NO NETWORK
```

is superseded — **only to the extent of the human approval** — by the bounded policy below. It is
superseded at the *decision* level now, and at the *invariant* level only once the canonical
governance write is authorized and applied (see §5).

### 1.1 Local-first guarantees (unchanged, strengthened as explicit)

| Key | Value |
| --- | --- |
| `LOCAL_FIRST` | `MANDATORY` |
| `LOCAL_NOTES_BEFORE_SIGNIN` | `ALLOWED` |
| `OFFLINE_READ` | `MANDATORY` |
| `OFFLINE_WRITE` | `MANDATORY` |
| `NETWORK_REQUIRED_TO_OPEN_EXISTING_NOTE` | `FORBIDDEN` |
| `ROOM` | `LOCAL_SSOT` |
| `OUTBOX` | `REQUIRED_FOR_OFFLINE_MUTATIONS` |
| `REMOTE_SYNC_AS_CANONICAL_UI_SOURCE` | `FORBIDDEN` |

### 1.2 Identity / network boundaries

| Key | Value |
| --- | --- |
| `KEEPLAB_IDENTITY_AUTHORITY` | `OWN_BACKEND` |
| `REMOTE_TRANSPORT` | `HTTPS_ONLY` |
| `GOOGLE_AUTH` | `FORBIDDEN_UNLESS_HUMAN_APPROVED` |
| `FIREBASE_AUTH` | `FORBIDDEN_UNLESS_HUMAN_APPROVED` |
| `GOOGLE_PRIVATE_API` | `FORBIDDEN` |

### 1.3 Non-destructiveness guarantees

| Key | Value |
| --- | --- |
| `AUTH_FAILURE_DELETES_LOCAL_DATA` | `NO` |
| `NETWORK_FAILURE_DELETES_LOCAL_DATA` | `NO` |
| `AUTH_REQUIRED_DELETES_OUTBOX` | `NO` |
| `EXISTING_LOCAL_NOTES_MAY_BE_DROPPED` | `NO` |

### 1.4 Gate

| Key | Value |
| --- | --- |
| `IMPLEMENTATION` | `PHASE_GATED` |
| `ACCOUNT_NETWORK_FEATURES` | `ALLOWED_ONLY_INSIDE_EXPLICIT_APPROVED_PHASES` |

---

## 2. What D-15 does NOT authorize

Explicitly **not** authorized by D-15:

```
UNLIMITED_NETWORK_PERMISSION
UNLIMITED_ACCOUNT_IMPLEMENTATION
IGNORE_FACTORY_RULES
IGNORE_CONTRACT_GUARD
START_ALL_PHASES
```

- No phase starts automatically; each later phase needs its own contract, acceptance criteria,
  verification, rollback and guard authorization.
- The Contract Guard is untouched and remains fail-closed.
- Google/Firebase identity remains forbidden unless separately human-approved.

---

## 3. Phase eligibility (PHASE_GATED)

| Phase | Intended eligibility after A0 | Actual (canonical A0 write blocked) |
| --- | --- | --- |
| A1_LOCAL_DATA_PREPARATION | ELIGIBLE | decision-ready · execution BLOCKED |
| A2_BACKEND_FOUNDATION | ELIGIBLE | decision-ready · execution BLOCKED |
| A3_AUTH_IMPLEMENTATION | NOT_YET_ELIGIBLE | `BLOCKED_BY_HUMAN_DECISIONS` (D-01, D-04, D-10) |
| A4_SYNC | NOT_YET_ELIGIBLE | `NOT_YET_ELIGIBLE` |
| A5+ | NOT_YET_ELIGIBLE | `NOT_YET_ELIGIBLE` |

---

## 4. Canonical route and why the write is blocked

The canonical governance mechanism was inspected, not invented (see
`KEEPLAB-A0-HUMAN-ARCHITECTURE-DECISIONS.md` §11). Two authorized/unauthorized layers:

| Layer | Location | Authorization |
| --- | --- | --- |
| governance **record** (the decision) | `reports/**` (Stack's canonical record mechanism) | **AUTHORIZED** — written by this A0 |
| product **constitution** (invariant text) | `KeepLab-Relay/MISSION.md`, `KeepLab-Relay/FACTORY_RULES.md`, `KeepLab-Relay/specs/google-keep-parity/ROADMAP.md` (`RISK-GOV-001`) | **NOT AUTHORIZED** — guard BLOCKs |

Guard verdicts (real execution of the unmodified guard; full table in
`KEEPLAB-A0-HUMAN-ARCHITECTURE-DECISIONS.md` §12):

```
KeepLab-Relay/MISSION.md                              BLOCK  PRODUCTION_IMMUTABLE
KeepLab-Relay/FACTORY_RULES.md                        BLOCK  PRODUCTION_IMMUTABLE
KeepLab-Relay/specs/google-keep-parity/ROADMAP.md     BLOCK  UNCLASSIFIED_FAIL_CLOSED
KeepLab-Relay/.factory/decisions.md                   BLOCK  FORBIDDEN
reports/**                                            ALLOW  EVIDENCE_OUTPUT
orchestration/hermes/evidence/**                      ALLOW  EVIDENCE_OUTPUT
```

The guard was not modified, not weakened, and the frozen implementation contract was not edited.

---

## 5. Governance amendment proposal — EXACT TEXT (PROPOSED, NOT APPLIED)

Each block below is the exact minimal replacement/addition. Do not treat any of it as applied.

### 5.1 `KeepLab-Relay/MISSION.md` — supersede the absolute constraint (minimal)

Replace hard invariant 1:

```text
1. **Local-first, no network.** No note content or metadata leaves the device. The
   app performs no network I/O for product function.
```

with the versioned bounded invariant:

```text
1. **Local-first; account and network are optional, phase-gated extensions.**
   KeepLab remains local-first. Account is optional for local use. Network is optional for
   local use. Account/network features are allowed only inside explicit human-approved
   phases, each with its own contract, acceptance criteria, verification and rollback.
   Offline operation remains mandatory: reading and writing existing local notes must
   never require the network. Existing local notes are protected: no local note may be
   silently assigned, uploaded, deleted or merged into an account. Remote sync may never
   become the canonical UI data source. Google/Firebase identity remains forbidden
   unless separately human-approved. The device stays the source of truth for the UI.
   (Invariant version: v2, 2026-10-06, supersedes v1's absolute "no network".)
```

Replace the out-of-scope entry:

```text
**Sync and identity**
- Any account, sign-in, cloud sync or multi-device reconciliation
- Sharing a note with another person or app
```

with:

```text
**Sync and identity**
- Any account, sign-in, cloud sync or multi-device reconciliation *outside an explicitly
  human-approved, phase-gated contract* (optional extension; never required for local use)
- Sharing a note with another person or app
```

Add to the "Allowed evolutions" list:

```text
- Bounded account/network phases explicitly approved by the human owner, provided the
  local-first, offline-mandatory and no-silent-data-loss invariants above still hold
```

Governance-file note to add:

```text
Changing invariant 1 now requires a human commit recording the approved bounded scope
(D-15 = YES_BOUNDED_ACCOUNT_NETWORK_UNLOCK, scope: account/network architecture phases only;
limits: phase-gated, local-first, own-backend, no Google/Firebase by default).
```

**Do NOT** add any A1/A2/A3 implementation detail (no schema, no endpoints, no stack, no vendor).

### 5.2 `KeepLab-Relay/FACTORY_RULES.md` — narrow only the categorical prohibition (minimal)

If, and only if, a clause categorically forbids account/network work, replace that clause with:

```text
Account/network work is permitted only inside an explicitly human-approved, phase-gated
contract that carries its own scope, acceptance criteria, verification and rollback.
Preserve unchanged: irreversible-change protection, human-approval requirements, the
fail-closed guard, the no-silent-data-loss rule, and the phase/contract gates.
```

No general safety rule is weakened. If no such categorical clause exists, **FACTORY_RULES.md is
left untouched**.

### 5.3 `KeepLab-Relay/specs/google-keep-parity/ROADMAP.md` — resolve `RISK-GOV-001` (minimal)

Replace the `RISK-GOV-001` block body's resolution state with:

```text
## RISK-GOV-001 — Governance reconciliation — RESOLVED_BY_BOUNDED_HUMAN_UNLOCK

Date:              2026-10-06
Approved decision: D-15 = YES_BOUNDED_ACCOUNT_NETWORK_UNLOCK
Scope:             account/network architecture phases only
Limits:            phase-gated · local-first · own-backend · no Google/Firebase by default
Residual:          P3-large-screen, P4-rich-text, P5-attachments/link and P7-ecosystem remain
                   gated by their own items; this resolution covers the account/network
                   prohibition only.
```

Do **not** close unrelated risks.

### 5.4 `KeepLab-Relay/.factory/decisions.md` — record the answered decisions (only if the project convention requires it)

```text
- D-02 DECIDED 2026-10-06: YES_LOCAL_ONLY_BEFORE_SIGNIN
- D-03 DECIDED 2026-10-06: SINGLE_ACTIVE_ACCOUNT_PHASE1
- D-07 DECIDED 2026-10-06: KOTLIN_KTOR
- D-08 DECIDED 2026-10-06: TENCENT_CLOUD + PORTABLE_DOCKER
- D-09 DECIDED 2026-10-06: POSTGRESQL
- D-15 DECIDED 2026-10-06: YES_BOUNDED_ACCOUNT_NETWORK_UNLOCK
```

This file does not currently exist and its location is `FORBIDDEN` to the guard.

---

## 6. To unblock

```
NEXT: OPEN_GOVERNANCE_WRITE_CONTRACT
```

A governance-write contract must explicitly authorize (at minimum) agent writes to
`KeepLab-Relay/MISSION.md`, `KeepLab-Relay/FACTORY_RULES.md` and
`KeepLab-Relay/specs/google-keep-parity/ROADMAP.md`, then the §5 amendment text can be applied
verbatim and A0 re-run to completion. Until then the gate stays closed to execution.

---

## 7. Status

```
BOUNDED_ACCOUNT_NETWORK_POLICY:  RECORDED (decision level)
CANONICAL MISSION AMENDMENT:     NOT APPLIED
RISK-GOV-001 CANONICAL RESOLUTION: NOT APPLIED
IMPLEMENTATION AUTHORIZED:       NO
CONTRACT GUARD:                  ACTIVE (unmodified)
STATUS:                          BLOCKED_BY_CONTRACT_GUARD
NEXT:                            OPEN_GOVERNANCE_WRITE_CONTRACT
```
