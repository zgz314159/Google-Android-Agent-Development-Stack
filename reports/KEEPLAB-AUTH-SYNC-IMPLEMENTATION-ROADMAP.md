# KEEPLAB-AUTH-SYNC-IMPLEMENTATION-ROADMAP

**Future phased implementation plan for KeepLab account / offline / sync (NOT executed)**

- Task: `KEEPLAB-AUTH-SYNC-ARCHITECTURE-SPEC`
- Date: 2026-10-05 (CST) · Status: **CANONICAL_ARCHITECTURE_DRAFT · NON_IMPLEMENTATION_AUTHORIZING**
- **Nothing in this document was executed.** All phases are future work and are governance-blocked
  until the human opens the account/network gate (spec §1.2/§1.3).
- A0 update (2026-10-06): the human decision layer of A0 is **resolved**
  (D-02/D-03/D-07/D-08/D-09/D-15 approved); the canonical governance **file** amendment is
  `BLOCKED_BY_CONTRACT_GUARD`, so A1/A2 remain **BLOCKED** from execution. See the "A0 attempt"
  table above.
- Basis: `KEEPLAB-AUTH-SYNC-ARCHITECTURE-SPEC.md`; `KEEP-OFFLINE-SYNC-BLUEPRINT.md`.

The phase names below are **evaluated, not blindly adopted** from the task's example. A0/A1 are
required. A2–A8 are ordered by dependency. A9 is explicitly optional.

---

## Phase A0 — Governance unlock

| | |
| --- | --- |
| **Scope** | A human amendment of `MISSION.md` / `FACTORY_RULES.md` (via the project governance route) to permit an account/network phase; resolution of `RISK-GOV-001` scope for account/sync. |
| **Prerequisites** | none |
| **Deliverable** | an amended governance invariant set authorizing an account/network phase (human-authored) |
| **Acceptance gate** | the Mission no longer forbids account/network; the account/network gate is recorded resolved; this spec's `IMPLEMENTATION_AUTHORIZATION` flips only if the human says so |
| **Rollback** | revert the governance amendment (no code to roll back — nothing built) |
| **Must NOT bundle** | any product code; any backend; any dependency |

### A0 attempt — `KEEPLAB-HUMAN-ARCHITECTURE-DECISIONS-A0` (2026-10-06)

| Step | Result |
| --- | --- |
| Human decisions D-02/D-03/D-07/D-08/D-09/D-15 approved and recorded under `reports/**` | **DONE** |
| Bounded account/network policy recorded (`KEEPLAB-A0-BOUNDED-ACCOUNT-NETWORK-GOVERNANCE.md`) | **DONE** |
| Canonical governance amendment (`MISSION.md`, `FACTORY_RULES.md`) | **BLOCKED_BY_CONTRACT_GUARD** |
| `RISK-GOV-001` canonical resolution in `specs/google-keep-parity/ROADMAP.md` | **BLOCKED_BY_CONTRACT_GUARD** |
| A0 acceptance gate met (Mission no longer forbids account/network) | **NO** |

```
A0 STATUS:                          INCOMPLETE · BLOCKED_BY_CONTRACT_GUARD
IMPLEMENTATION_AUTHORIZATION_MODEL: PHASE_GATED
CURRENT_IMPLEMENTATION_AUTHORIZATION: NOT_GRANTED
NEXT:                               OPEN_GOVERNANCE_WRITE_CONTRACT
```

A0's decision layer is resolved; its canonical governance write is not. A1/A2 are decision-ready but
their execution remains blocked until the governance-write contract exists.

> **Blocking relationship:** A0 blocks **every** phase below. No phase may start while
> `CURRENT_IMPLEMENTATION_AUTHORIZATION: NOT_GRANTED`.

---

## Phase A1 — Local data-model preparation (still offline)

| | |
| --- | --- |
| **Scope** | Prepare the local model for a future account: add `account_id` (**nullable** — NULL is legal only while `LOCAL_ONLY`), stable client UUIDs (**additive**), a sync-tombstone column (`deleted_at`), a Trash timestamp (`trashed_at`) and sync metadata columns — **additively**, preserving every existing note. No network. |
| **Prerequisites** | A0 — decision layer resolved (D-02, D-03); canonical governance write `BLOCKED_BY_CONTRACT_GUARD`, so execution is **BLOCKED** |
| **Key tasks** | design the additive migration; add a stable client UUID column and backfill it for existing rows; keep the existing local primary key as an **implementation-local identity** (primary-key replacement is a separate migration decision, never required for first network enablement); keep `trashed` as **product Trash** (never map it to `deleted_at`); export schema (`enableSchema`) if not already on |
| **Acceptance gate** | all existing notes preserved; every row has a stable client UUID; the existing primary key and all existing FKs/references survive; `trashed` rows remain recoverable product Trash and are NOT tombstones; the migration is additive; existing test suites green |
| **Rollback** | a reverse migration is *not* required (additive); keep the DB version gate; existing data untouched |
| **Must NOT bundle** | any network call; any auth; any sync worker; any server; a primary-key replacement or an encrypted-database dependency |
| **Why first** | migration risk is lowest before auth exists; and `MISSION.md`'s irreversible list forbids dropping existing notes — this phase proves the tooling honors it |

```
CRITICAL: existing local data MUST NEVER be silently deleted when future auth is introduced.
```

---

## Phase A2 — Backend foundation

| | |
| --- | --- |
| **Scope** | stand up the KeepLab backend skeleton: API edge, primary DB, object storage, service skeletons, TLS, environment config. **Provider/language/DB vendor must be human-decided first.** |
| **Prerequisites** | A0; human decisions: cloud provider = `TENCENT_CLOUD` + `DEPLOYMENT_PORTABILITY: PORTABLE_DOCKER`, backend language = `KOTLIN` + `KTOR`, database vendor = `POSTGRESQL` — **all resolved 2026-10-06** (D-07/D-08/D-09); execution still **BLOCKED** on the canonical A0 governance write |
| **Acceptance gate** | a health endpoint answers over TLS; DB reachable; object storage writable; no product identity data yet |
| **Rollback** | tear down the environment (infrastructure-only) |
| **Must NOT bundle** | any Android client code; any auth method; any notes data model tied to a specific auth method |

---

## Phase A3 — Registration / login / session

| | |
| --- | --- |
| **Scope** | the chosen auth method end-to-end against the KeepLab backend; Credential Manager as UX layer; session issue/rotate/revoke; the auth UX state machine (STATE-MODEL §1). |
| **Prerequisites** | A0, A2; human decisions **still pending**: final auth method (AUTH-DEC-004 / D-01), token format (AUTH-DEC-005 / D-10), sign-out local-data policy (AUTH-DEC-011 / D-04) → `BLOCKED_BY_HUMAN_DECISIONS` |
| **Acceptance gate** | sign-up / sign-in / **retry-safe refresh rotation** (`refresh_request_id`; a lost response after a successful rotation recovers the same result within the bounded window) / sign-out / per-session revoke work; an ambiguous rotation failure does not look like theft or force account loss; `AUTH_REQUIRED` is non-destructive; no Google/Firebase path exists |
| **Rollback** | feature-flag the auth surfaces off; local app remains usable |
| **Must NOT bundle** | note sync; attachments; multi-account; collaboration |

---

## Phase A4 — Single-user note sync (push + pull core)

| | |
| --- | --- |
| **Scope** | Room SSOT + outbox + client UUIDs (additive) + server revisions + the server change cursor / client checkpoint + sync tombstones + retry-safe refresh, for one account, text/checklist notes and labels. |
| **Prerequisites** | A1, A3 |
| **Acceptance gate** | create/edit/archive/pin/colour/label/checklist changes sync both directions; duplicate `mutation_id` is ignored AND the dedupe claim is atomic with the apply (crash-injection proves no double-apply); a stale `base_revision` yields 409; a failed delta does not advance the checkpoint; a deleted note does not resurrect; a 404 does not delete a live local row; no entity in a remote-sync state has a NULL `account_id` |
| **Implementation decision** | the exact WorkManager `ExistingWorkPolicy` for the one unique `note_sync` pipeline is an **`A4_IMPLEMENTATION_DECISION`**, selected by deterministic tests (e.g. `KEEP` + drain-until-stable/recheck, serialized append/rerun, or equivalent) against the actual WorkManager version — not frozen speculatively |
| **Rollback** | disable the sync worker; local data intact; outbox retained |
| **Must NOT bundle** | attachments; conflict UI (A6); multi-device hardening (A8); multi-account |

---

## Phase A5 — Offline outbox / retry hardening

| | |
| --- | --- |
| **Scope** | offline-first guarantees under real conditions: bounded retries, `SYNC_FAILED` surfacing, manual retry, coalescing, process-death durability, reconnect triggers. |
| **Prerequisites** | A4 |
| **Acceptance gate** | a long offline edit session survives process death; on reconnect the outbox drains without duplicate application; **a trigger arriving while the worker is running is not lost** (lost-wakeup test); exhausted attempts surface a retry; `AUTH_REQUIRED` leaves the outbox intact |
| **Rollback** | remain on A4 behaviour (worker still runs, just less resilient) |
| **Must NOT bundle** | conflict resolution UI; attachments; performance benchmarking |

---

## Phase A6 — Conflict handling

| | |
| --- | --- |
| **Scope** | the per-field conflict policy (spec §20): user-resolved title/body conflict (keep local / keep server / keep both), item-level checklist merge, operation-based label add/remove, LWW metadata resolved by the **server-assigned clock**, delete-vs-edit conflict. |
| **Prerequisites** | A5 |
| **Acceptance gate** | each conflict class produces the specified observable outcome; no silent text overwrite; **no resolution uses an unsynchronized client wall clock**; concurrent checklist additions both survive; a concurrent label remove is not resurrected (ordering by server-accepted revision); delete-vs-edit is explicit; **`KEEP_BOTH` creates a NEW logical note with a NEW client-generated UUID enqueued as `CREATE` in the same account scope — never reusing the original entity id** |
| **Rollback** | disable the conflict UI; conflicted rows stay `CONFLICT` and are not lost |
| **Must NOT bundle** | CRDT; automatic three-way text merge; attachments |

---

## Phase A7 — Attachments

| | |
| --- | --- |
| **Scope** | attachment metadata + deferred binary upload/download; content-addressing; per-account authorization; orphan handling. |
| **Prerequisites** | A4, A6 |
| **Acceptance gate** | a note with a pending upload stays fully usable; uploads resume; downloads are per-account authorized; abandoned uploads do not corrupt note state |
| **Rollback** | hide the attachment affordance; existing notes unaffected |
| **Must NOT bundle** | image/drawing/voice capture UX (separate product phases); collaboration |

---

## Phase A8 — Multi-device hardening

| | |
| --- | --- |
| **Scope** | two or more devices on one account: propagation, conflict under real concurrency, session list, per-session revoke, remote session invalidation, account-disable flows. |
| **Prerequisites** | A6, A7 |
| **Acceptance gate** | two devices converge; a device-lost session can be revoked remotely without deleting local notes; the propagation/conflict paths hold under concurrent edits |
| **Rollback** | single-device posture; nothing is destroyed |
| **Must NOT bundle** | multi-account; collaboration; sharing |

> Note: Google Keep's exact cross-device propagation timing is `UNKNOWN_PRIVATE` / a J3 reference
> question. A8 targets **KeepLab's own correctness**, not Keep cadence parity.

---

## Phase A9 — Optional multi-account / collaboration (`FUTURE_EXTENSION`)

| | |
| --- | --- |
| **Scope** | multiple KeepLab accounts in one app instance and (only if separately authorized) note sharing/collaboration. |
| **Prerequisites** | A8; human product decisions (AUTH-DEC-009; collaboration scope) |
| **Acceptance gate** | per-account isolation holds (RISK-DATA-001); no cross-account leakage |
| **Rollback** | restrict to single account |
| **Must NOT bundle** | anything into earlier phases — this is strictly additive |

---

## Phase summary

```
A0 governance unlock  ──▶ blocks everything
A1 local data prep    ──▶ A2 backend foundation ──▶ A3 auth/session ──▶ A4 note sync
                                                                        │
                          A7 attachments ◀── A6 conflict ◀── A5 offline hardening
                                 │
                                 └──▶ A8 multi-device ──▶ A9 optional multi-account
```

| Phase | Scope | Prerequisite | Acceptance gate | Rollback | Not bundled |
| --- | --- | --- | --- | --- | --- |
| A0 | governance unlock | — | Mission amended; gate resolved | revert amendment | all code |
| A1 | local data model prep | A0 | existing notes preserved; UUIDs backfilled | additive only | network/auth/sync |
| A2 | backend foundation | A0 + vendor decisions | TLS health + DB + storage | tear down env | client code |
| A3 | auth/session | A2 + auth decisions | auth lifecycle works; non-destructive | feature-flag off | note sync |
| A4 | single-user sync | A1, A3 | bidirectional sync + invariants | disable worker | attachments/conflict UI |
| A5 | offline hardening | A4 | durable offline + retry | A4 behaviour | conflict UI |
| A6 | conflict handling | A5 | per-field policy holds | disable conflict UI | CRDT/attachments |
| A7 | attachments | A4, A6 | deferred upload safe | hide affordance | capture UX |
| A8 | multi-device | A6, A7 | convergence + revocation | single-device | multi-account |
| A9 | multi-account (optional) | A8 | isolation holds | single account | — |

**Smallest coherent roadmap:** A0 → A1 → A2 → A3 → A4 → A5 is the minimum to a working,
invariant-respecting offline-first synced notes product; A6–A8 are correctness/robustness;
A9 is optional.

---

## Test architecture per phase

| Layer | Where it belongs | Phase |
| --- | --- | --- |
| unit | JVM tests | A1+ |
| Room integration (DAO + migration) | instrumented | A1, A4 |
| repository / outbox | JVM + Room | A4, A5 |
| sync-engine | JVM with a fake server | A4, A5 |
| fake-server contract | JVM/CI | A4 |
| backend API | server integration | A2, A3 |
| auth/session | JVM + server integration | A3 |
| WorkManager | instrumented | A5 |
| process death | instrumented | A5 |
| offline/reconnect | instrumented | A5 |
| multi-device simulation | server + 2 clients | A8 |
| conflict simulation | JVM + instrumented | A6 |
| migration | instrumented `MigrationTest` | A1, A4 |

Prefer deterministic tests before true-device journeys. Truly requiring hardware/server: instrumented
Room+Worker on a device; server integration against a real backend; real network fault injection.
**No test in this document was written or run.**

---

## Performance boundary

Performance parity is **out of scope** for the account/sync architecture work and remains a
separate concern (spec §35). Do **not** start `P0B-GK-DEVICE-REBASE` or `P0B-GK-MATCHED-SCALE-A2`
from this roadmap. The final performance device is not decided here.

---

## Execution status

```
PHASES EXECUTED:            0
PHASE A0 STARTED:           YES (2026-10-06 — A0 decision layer done; canonical write BLOCKED_BY_CONTRACT_GUARD)
A0 STATUS:                  INCOMPLETE · BLOCKED_BY_CONTRACT_GUARD
NEXT:                       OPEN_GOVERNANCE_WRITE_CONTRACT
IMPLEMENTATION AUTHORIZATION: NOT_GRANTED
ANDROID DEVICE OPERATED:    NO
PRODUCT CODE MODIFIED:      NO
```

