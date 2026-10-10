# KEEPLAB-AUTH-SYNC-RISK-REGISTER

**Architecture risks for the future KeepLab account / offline / sync architecture**

- Task: `KEEPLAB-AUTH-SYNC-ARCHITECTURE-SPEC`
- Date: 2026-10-05 (CST) · Status: **CANONICAL_ARCHITECTURE_DRAFT · NON_IMPLEMENTATION_AUTHORIZING**
- Each risk lists: trigger · impact · preventive invariant · verification strategy · phase when it
  must be resolved. Phase names reference `KEEPLAB-AUTH-SYNC-IMPLEMENTATION-ROADMAP.md`.
- All are **architecture-level**; no code exists to mitigate them yet.

---

## RISK-AUTH-001 — Wrong identity-provider coupling

| | |
| --- | --- |
| **Trigger** | a developer/agent adds Google sign-in, Firebase Auth, or an Android-account dependency "because Keep uses it" |
| **Impact** | violates frozen governance; couples KeepLab to a third party; security/privacy regression |
| **Preventive invariant** | `IDENTITY AUTHORITY = KeepLab backend` (AUTH-DEC-001/003); Credential Manager is UX-layer only (AUTH-DEC-002); Google/Firebase `FORBIDDEN_UNLESS_HUMAN_APPROVED` |
| **Verification** | dependency audit (no `play-services-auth`, no `firebase-auth`, no `androidx.credentials` as an identity provider); code review gate; credential-manager config review |
| **Resolve by** | **A0/A3** (must be enforced before any auth code lands) |

---

## RISK-SYNC-001 — Silent lost local mutation

| | |
| --- | --- |
| **Trigger** | a local edit is dropped without being pushed (e.g. outbox row removed early, or payload built from the live row after a later edit) |
| **Impact** | user loses work with no error — the worst failure mode |
| **Preventive invariant** | OUT-1 (atomic entity+outbox), OUT-3 (row removed only on confirmed success), OUT-4 (captured payload) |
| **Verification** | outbox unit tests; crash-injection between writes; assert one outbox row per mutation class; fake-server test that a mid-flight edit cannot rewrite a pushed payload |
| **Resolve by** | **A4/A5** |

---

## RISK-SYNC-002 — Duplicate mutation application

| | |
| --- | --- |
| **Trigger** | a retried push is applied twice (server lacks idempotency, or the client regenerates `mutation_id`) |
| **Impact** | duplicated notes/items; corrupted note counts |
| **Preventive invariant** | OUT-2 (`mutation_id` idempotency key); server idempotency ledger (`mutations_applied`); the dedupe record/claim shares ONE server-side consistency boundary with the apply, the revision increment and the change-log append (spec §26, DATA-MODEL §4.1) |
| **Verification** | server duplicate-submission test; crash-injection between the apply and the dedupe write; client test that `mutation_id` is stable across retries |
| **Resolve by** | **A4** |

---

## RISK-SYNC-003 — Stale client resurrection

| | |
| --- | --- |
| **Trigger** | a stale client's delta pull (or push) recreates a tombstoned entity |
| **Impact** | deleted notes reappear; user distrust |
| **Preventive invariant** | DEL-1 (a server deletion must not resurrect); DEL-2 (a stale supported client must not resurrect a permanently deleted entity); tombstone-first sync; revision check on stale push → explicit conflict; Trash ≠ tombstone (TRASH-1/TRASH-2) |
| **Verification** | delta-pull test with a pre-deletion cursor; stale-supported-client replay test; concurrent delete/edit simulation; Trash → restore is not treated as a resurrection |
| **Resolve by** | **A4/A6** |

---

## RISK-SYNC-004 — Cursor advancement over a failed delta

| | |
| --- | --- |
| **Trigger** | the client checkpoint advances past a delta it failed to apply |
| **Impact** | a server change is permanently missed on that device |
| **Preventive invariant** | CUR-1 (checkpoint advances only on a clean apply) |
| **Verification** | sync-engine test: inject an apply failure, assert the checkpoint is unchanged and the batch is retried |
| **Resolve by** | **A4/A5** |

---

## RISK-SYNC-005 — Worker race / duplicate workers

| | |
| --- | --- |
| **Trigger** | multiple sync workers run concurrently (manual + reconnect + periodic) |
| **Impact** | duplicate pushes, interleaved writes, hard-to-reproduce corruption |
| **Preventive invariant** | SYNC-DEC-010 (single unique pipeline `note_sync`); `enqueueUniqueWork`; anti-patterns forbidden; **frozen invariants**: ONE ACTIVE SYNC EXECUTOR MAX; a trigger arriving while the worker runs MUST NOT be lost; the worker MUST drain to a stable point or guarantee a follow-up run; OUTBOX DURABILITY (not the scheduling event) is the source of work |
| **Verification** | WorkManager instrumentation test asserting a single unique work; trigger-storm test; **lost-wakeup test** — enqueue a mutation mid-pass and assert it is still drained (no dropped trigger); the exact `ExistingWorkPolicy` is chosen by these deterministic tests (`A4_IMPLEMENTATION_DECISION`) |
| **Resolve by** | **A4/A5** |

---

## RISK-SYNC-006 — A 404 silently deleting local work

| | |
| --- | --- |
| **Trigger** | a `NOT_FOUND` (404) response is treated as proof of deletion and the client resolves/deletes the local row |
| **Impact** | user work silently destroyed locally on a stale id, an authorization mismatch, server compaction or a protocol mismatch |
| **Preventive invariant** | ERR-3 (`NOT_FOUND` → `RECONCILE_REQUIRED`; 404 is NOT automatically deletion); only a server-authoritative tombstone/deletion or a documented reconciliation response may cause automatic local deletion |
| **Verification** | fake-server test returning 404 for a still-live local row and asserting the row is preserved and reconciled; compaction/stale-id tests |
| **Resolve by** | **A4/A5** |

---

## RISK-CONFLICT-001 — Silent body overwrite

| | |
| --- | --- |
| **Trigger** | a stale revision write is applied as LWW on `title`/`body` |
| **Impact** | user text lost silently |
| **Preventive invariant** | REV-1 (no silent overwrite); per-field policy (SYNC-DEC-011); server-assigned ordering (`server_revision` / server sequence / server `server_updated_at`); client wall clocks MUST NOT resolve a multi-device conflict; 409 + current representation |
| **Verification** | conflict-simulation tests for both-sides-changed, one-side-changed, delete-vs-edit; skewed-client-clock test proving the client clock does not decide an outcome |
| **Resolve by** | **A6** |

---

## RISK-SESSION-001 — Offline refresh interpreted as logout

| | |
| --- | --- |
| **Trigger** | a failed refresh while offline is treated as a sign-out |
| **Impact** | destructive: user appears signed out; risk of local-data purge |
| **Preventive invariant** | OFF-1/OFF-2, SESS-1 (`AUTH_REQUIRED` non-destructive), SESS-2 (refresh rotation is single-use + **RETRY_SAFE**; an ambiguous response loss after a successful rotation is not theft and not account loss), AUTH-DEC-008 |
| **Verification** | auth/session tests: offline refresh failure leaves session material, notes and outbox intact; retried rotation with the same `refresh_request_id` recovers the same result; a different rotation identity on a used credential is flagged as reuse |
| **Resolve by** | **A3/A5** |

---

## RISK-DATA-001 — Cross-account local data leakage

| | |
| --- | --- |
| **Trigger** | a query/write is not scoped to `account_id` (or multi-account is added without isolation) |
| **Impact** | one account sees another's notes — a severe privacy defect |
| **Preventive invariant** | ISO-1/ISO-1b/ISO-3/ISO-4; ID-3; `account_id` present from the first networked implementation; CLIENT_ACCOUNT_ID_IS_NOT_AUTHORITY (the server derives scope from the authenticated session) |
| **Verification** | per-account isolation tests; a static check that every synced query is account-scoped |
| **Resolve by** | **A1** (schema) and **A9** (multi-account) |

---

## RISK-ATTACH-001 — Orphaned attachment

| | |
| --- | --- |
| **Trigger** | a binary is uploaded/created but its metadata row never records success (crash, delete race) |
| **Impact** | storage leak; possibly an unreferenced object a user cannot delete |
| **Preventive invariant** | `ATTACHMENT_ADD` op + `remote_object_id` set only on confirmed success; note row independent (ATT-1) |
| **Verification** | attachment upload-crash test; assert no metadata-free objects accumulate; GC design |
| **Resolve by** | **A7** |

---

## RISK-GOV-001 — Current Mission forbids account/network implementation — `RESOLVED_BY_BOUNDED_HUMAN_UNLOCK` (decision level)

| | |
| --- | --- |
| **Trigger** | an agent implements account/sync/network while `MISSION.md` still forbids it |
| **Impact** | a governance violation; the factory's own hard invariants breached |
| **Preventive invariant** | spec §1.2 (`IMPLEMENTATION_AUTHORIZATION: NOT_GRANTED`) + §1.3 (`RISK-GOV-001` still canonical) |
| **Verification** | Contract Guard stays ACTIVE; `MISSION.md` unchanged; no product/network code added |
| **Resolve by** | **A0** (human governance amendment) |
| **A0 status (2026-10-06)** | **`RESOLVED_BY_BOUNDED_HUMAN_UNLOCK`** at the governance-*record* level — approved decision **D-15 = `YES_BOUNDED_ACCOUNT_NETWORK_UNLOCK`**; scope **account/network architecture phases only**; limits **phase-gated · local-first · own-backend · no Google/Firebase by default**. The **canonical** edits (`KeepLab-Relay/specs/google-keep-parity/ROADMAP.md`, plus the `MISSION.md` / `FACTORY_RULES.md` amendments) are **`BLOCKED_BY_CONTRACT_GUARD`** and were not applied, so `MISSION.md` still literally forbids account/network. Unrelated residual risks (`P3-large-screen`, `P4-rich-text`, `P5-attachments/link`, `P7-ecosystem`) are **not** closed by this. |

---

## RISK-GOV-002 — Account/network gate not formally opened

| | |
| --- | --- |
| **Trigger** | the account/network phase is started without an explicit human amendment of the current Mission invariant |
| **Impact** | an unauthorized implementation phase; possible wasted work if the human declines |
| **Preventive invariant** | this spec records the gate as `REQUIRED_BEFORE_IMPLEMENTATION`; `RISK-GOV-002` is part of the `RISK-GOV-001` family (not a parallel framework) |
| **Verification** | governance record updated before A1 starts; a human-signed authorization |
| **Resolve by** | **A0** |
| **A0 status (2026-10-06)** | same status as `RISK-GOV-001`: a bounded human authorization is recorded (D-15) under the canonical `reports/**` governance record; the **canonical file amendment is `BLOCKED_BY_CONTRACT_GUARD`**, so the gate is **not** formally opened for execution and A1 stays blocked. |

---

## Risk summary

| Risk | Area | Must resolve by | Severity |
| --- | --- | --- | --- |
| RISK-AUTH-001 | identity coupling | A0/A3 | HIGH |
| RISK-SYNC-001 | lost mutation | A4/A5 | HIGH |
| RISK-SYNC-002 | duplicate apply | A4 | MED-HIGH |
| RISK-SYNC-003 | stale resurrection | A4/A6 | HIGH |
| RISK-SYNC-004 | cursor over failed delta | A4/A5 | HIGH |
| RISK-SYNC-005 | worker race | A4/A5 | MED-HIGH |
| RISK-SYNC-006 | 404 silently deletes local work | A4/A5 | HIGH |
| RISK-CONFLICT-001 | silent body overwrite | A6 | HIGH |
| RISK-SESSION-001 | offline refresh → logout | A3/A5 | HIGH |
| RISK-DATA-001 | cross-account leakage | A1/A9 | HIGH |
| RISK-ATTACH-001 | orphaned attachment | A7 | MED |
| RISK-GOV-001 | Mission forbids account/network | A0 | HIGH (blocking) — `RESOLVED_BY_BOUNDED_HUMAN_UNLOCK` at decision level; canonical edit `BLOCKED_BY_CONTRACT_GUARD` |
| RISK-GOV-002 | account/network gate not opened | A0 | HIGH (blocking) — bounded authorization recorded; canonical gate **not** formally opened (`BLOCKED_BY_CONTRACT_GUARD`) |

All preventive invariants are stated normatively in `KEEPLAB-AUTH-SYNC-ARCHITECTURE-SPEC.md` and the
companion state/data/API docs. No risk is mitigated by code in this task.
