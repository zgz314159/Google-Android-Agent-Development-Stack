# KEEPLAB-AUTH-SYNC-STATE-MODEL

**Formal auth-UX, session, and sync state machines for future KeepLab account / sync architecture**

- Task: `KEEPLAB-AUTH-SYNC-ARCHITECTURE-SPEC`
- Date: 2026-10-05 (CST) · Status: **CANONICAL_ARCHITECTURE_DRAFT · NON_IMPLEMENTATION_AUTHORIZING**
- Basis: `KEEP-AUTH-REFERENCE-BLUEPRINT.md` §2; `KEEP-OFFLINE-SYNC-BLUEPRINT.md` §4;
  `KEEPLAB-AUTH-SYNC-ARCHITECTURE-SPEC.md` §11/§12.
- No code. No implementation. States are conceptual contracts, not a Room enum yet.

---

## 1. Authentication UX state machine

State set (`FROZEN_ARCHITECTURE_DECISION`). Columns: entry · exit · persistent/transient · UI
behaviour · local-note accessibility · sync behaviour · network behaviour · security restriction.

| State | Entry condition | Exit condition | Persist/Transient | UI behaviour | Local notes | Sync | Network | Security restriction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `SIGNED_OUT` | fresh install / after sign-out | user starts auth | persistent | primary sign-in entry point | readable if any exist (local-only) | off | none | none |
| `AUTHENTICATING` | user tapped sign-in / passkey sheet showing | success → `SIGNED_IN`; failure → a failure state | transient | non-blocking progress; sheet owns interaction | readable | off | required | no credential logging |
| `SIGNED_IN` | valid session | sign-out / expiry / server reject | persistent | normal app shell | readable; edits local-first | active | opportunistic | none |
| `AUTH_EXPIRED` | server rejected the session/refresh | silent **retry-safe** refresh rotation (see INVARIANT SESS-2) → `SIGNED_IN`; else `REAUTH_REQUIRED` | transient | quiet; silent re-auth first | readable | **paused** | required | do not show raw server error; an ambiguous response loss AFTER a successful server rotation MUST NOT be treated as theft |
| `REAUTH_REQUIRED` | refresh failed authoritatively / sensitive action needs fresh auth | re-auth → `SIGNED_IN` | persistent until resolved | non-destructive re-auth gate | **readable; outbox intact** | paused | required | no data deletion |
| `NETWORK_ERROR` | credential exchange could not reach the server | retry | transient | retry affordance | **readable** | paused | absent | must not destroy notes |
| `INVALID_CREDENTIAL` | wrong secret on attempt | retry → `AUTHENTICATING` | transient | field-level error; generic wording | readable | off | required | anti-enumeration wording |
| `ACCOUNT_DISABLED` | account suspended/disabled (authoritative) | (human/ops action) | persistent | distinct actionable message | readable | paused | required | no data deletion |
| `SERVER_ERROR` | backend fault (5xx) | retry | transient | transient-error + retry | readable | paused | required | do not leak internals |
| `OFFLINE_WITH_VALID_LOCAL_SESSION` | no network, local session still valid | reconnect | persistent while offline | app fully usable | **fully readable/writable** | paused | absent | none |
| `OFFLINE_WITHOUT_VALID_SESSION` | no network, no usable session | connect + sign in | persistent while offline | local-only mode / non-blocking prompt | readable (local-only) | off | absent | none |

```
CRITICAL AUTH-1:  AUTH FAILURE MUST NOT DELETE LOCAL NOTES.
```
Status `FROZEN_ARCHITECTURE_DECISION` · Source `OFFICIAL_FACT` (S-06 patterns) +
`KEEPLAB_DESIGN_INFERENCE`.

```
INVARIANT SESS-2 (REFRESH_ROTATION: single-use + RETRY_SAFE):
  a rotating single-use refresh credential is NOT generic HTTP-style idempotency.
  (a) the client sends a `refresh_request_id` (or equivalent one-operation nonce/idempotency key);
  (b) if the SAME authenticated rotation request is retried after response loss, the server may
      return/recover the SAME logical rotation result within a bounded retry window;
  (c) if the already-used refresh credential appears with a DIFFERENT rotation identity, or outside
      the allowed retry semantics, it is a possible reuse/theft signal handled by session-family
      policy;
  (d) an ambiguous network failure after a successful server rotation MUST NOT force accidental
      account loss or automatically look like credential theft.
```
Status `FROZEN_ARCHITECTURE_DECISION` (contract requirement) · Source `OFFICIAL_FACT` (S-29/S-30) +
`KEEPLAB_DESIGN_INFERENCE` + corrective task §5.

### 1.1 Auth transitions

```
SIGNED_OUT ──sign in──▶ AUTHENTICATING ──ok──────────▶ SIGNED_IN
     ▲                        │  │
     │                        │  ├─ bad secret ──▶ INVALID_CREDENTIAL ──▶ AUTHENTICATING
     │                        │  ├─ 5xx ─────────▶ SERVER_ERROR ──▶ retry
     │                        │  ├─ no network ──▶ NETWORK_ERROR ──▶ retry
     │                        │  └─ disabled ────▶ ACCOUNT_DISABLED
     └────── sign out ────────┴────────────────────────── SIGNED_IN

SIGNED_IN ──token rejected──▶ AUTH_EXPIRED ──silent refresh──▶ SIGNED_IN
                                    └─ refresh fails ──▶ REAUTH_REQUIRED ──▶ AUTHENTICATING

Connectivity loss:
   valid local session ──▶ OFFLINE_WITH_VALID_LOCAL_SESSION   (app fully usable)
   no local session    ──▶ OFFLINE_WITHOUT_VALID_SESSION      (local-only / non-blocking prompt)
```

---

## 2. Sync state machine (per entity)

State set (`FROZEN_ARCHITECTURE_DECISION`): `LOCAL_ONLY` (optional) · `SYNC_PENDING` · `SYNCING` ·
`SYNCED` · `SYNC_FAILED` · `CONFLICT` · `DELETE_PENDING`, plus session-level `AUTH_REQUIRED`.

```
INVARIANT ISO-1b:  an entity in `LOCAL_ONLY` MAY have `account_id = NULL`. An entity in
                   `SYNC_PENDING` / `SYNCING` / `SYNCED` / `SYNC_FAILED` / `CONFLICT` /
                   `DELETE_PENDING` MUST NOT have a NULL `account_id`.
INVARIANT ACCT-1:  no synthetic/placeholder account row exists before sign-in; the linked/unlinked
                   distinction is carried by the entity's `sync_state` + `account_id`, not by an
                   `accounts` row.
```

| State | Entry | Exit | Persistent fields | UI meaning | Network required | Retry policy | Allowed operations |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `LOCAL_ONLY` (optional) | note created before any account exists (`account_id = NULL`) | an **explicit account-link transaction** succeeds → `SYNC_PENDING` (sets `account_id`, assigns the stable client UUID if absent, enqueues the outbox intent) | note row; `account_id = NULL`; no server id | subtle "local" marker (optional) | no | n/a | all local edits |
| `SYNC_PENDING` | local mutation committed (create/update/archive/pin/colour/label/checklist/delete intent) | drain succeeds → `SYNCED`; attempts exhausted → `SYNC_FAILED` | `sync_state`, `attempt_count`, `last_error`, `base_revision` | quiet "waiting to sync" (non-blocking) | yes (deferred) | WorkManager EXPONENTIAL, bounded | further local edits (coalesce) |
| `SYNCING` | worker picks the row | success/failure | transient in-memory (optionally persisted) | optional lightweight indicator | yes | — | none on this row |
| `SYNCED` | server acknowledged | a new local mutation → `SYNC_PENDING` | `server_revision`, `server_updated_at`, checkpoint | none (default clean state) | no | — | all local edits |
| `SYNC_FAILED` | attempts exhausted (e.g. 5) or a permanent server error | user retries → `SYNC_PENDING` | `attempt_count`, `last_error`, `failed_at` | "Couldn't sync — tap to retry" | yes | manual retry resets attempts | read; edit; retry |
| `CONFLICT` | revision check fails and edits are not auto-mergeable | user resolves (keep local / keep server / keep both) → `SYNC_PENDING` | both versions (local + incoming), `base_revision` | badge on the note; a resolution screen | yes | no auto-retry until resolved | resolve; read |
| `DELETE_PENDING` | user deletes a synced note | server acknowledges → row tombstoned / hard-deleted per retention | `deleted_at` (tombstone), `server_revision` | note hidden from the list (as if deleted) | yes | as `SYNC_PENDING` | undo (before ack) |
| `AUTH_REQUIRED` (session-level) | server returns session-invalid | re-auth → resume drain | none (session-level, not per-row) | sign-in gate, non-destructive | yes | resume automatically after sign-in | read; local edits |

### 2.1 Folded states (with reason)

| Considered | Verdict | Reason |
| --- | --- | --- |
| `DIRTY` | folded into `SYNC_PENDING` | duplicate of a pending local mutation |
| `RETRY_WAIT` | folded into `SYNC_PENDING` + attempt metadata | WorkManager owns timing; not a distinct persisted state |
| `TOMBSTONE` | kept as a **field** (`deleted_at`), not a state | a record shape, not a UI state |
| `LOCAL_ONLY` | kept, but **optional** | only meaningful if KeepLab permits notes before sign-in |

### 2.2 Sync transitions

```
(create offline) ──▶ LOCAL_ONLY ──explicit account-link transaction──▶ SYNC_PENDING
(SYNCED) ──local edit──▶ SYNC_PENDING ──worker──▶ SYNCING ──ok──▶ SYNCED
                                              └──fail x N──▶ SYNC_FAILED ──retry──▶ SYNC_PENDING
SYNCING ──revision conflict──▶ CONFLICT ──resolve──▶ SYNC_PENDING
SYNCED ──trash intent──▶ (product Trash: trashed/trashed_at; recoverable; NOT a tombstone)
final DELETE intent ──▶ DELETE_PENDING ──server ack──▶ sync tombstone (deleted_at)
                                                    → (tombstone retention/compaction) → hard delete
any sync state ──server session invalid──▶ session AUTH_REQUIRED   (outbox untouched)
```

```
CRITICAL SYNC-1:  AUTH_REQUIRED MUST NOT delete pending outbox rows.
```
Status `FROZEN_ARCHITECTURE_DECISION` · Source `KEEPLAB_DESIGN_INFERENCE`.

---

## 3. Offline / session model (consolidated)

The governing distinction and the per-situation behaviour are in
`KEEPLAB-AUTH-SYNC-ARCHITECTURE-SPEC.md` §10. Restated as invariants:

```
OFF-1  NO_NETWORK ≠ AUTH_INVALID; NO_NETWORK ≠ SIGN_OUT.
OFF-2  Only authoritative server invalidation OR explicit human sign-out transitions toward
       destructive account-exit semantics.
OFF-3  Local data (notes, outbox, pending mutations, attachment metadata) is never silently
       deleted, in any transition.
OFF-4  A failed refresh must not erase notes, outbox, or pending mutations (SESS-1).
```

---

## 4. Delete / trash / tombstone state

```
DELETE_PENDING ──server ack──▶ sync tombstone (deleted_at set) ──compaction──▶ hard delete
```

TRASH and SYNC TOMBSTONE are **distinct**:

| Concept | Meaning | Recoverable? |
| --- | --- | --- |
| **TRASH** (`trashed` / `trashed_at`) | user-visible, recoverable **product** state | yes — the user can restore |
| **SYNC TOMBSTONE** (`deleted_at`) | protocol-level record of **final** deletion for convergence / anti-resurrection | no |

- A trashed note is hidden from the normal UI (or shown in a Trash view) while Trash state propagates
  as an ordinary product-state change. **Trash MUST NOT set `deleted_at`**, and an item in Trash MUST
  NOT be silently turned into a permanently-deleted sync tombstone.
- `TRASH_RETENTION: HUMAN_DECISION_PENDING` (7 days is a `REFERENCE_DEFAULT_CANDIDATE` only).
- `SYNC_TOMBSTONE_RETENTION_OR_COMPACTION` is a **separate** protocol-correctness concern — NOT the
  same product setting as Trash duration, and NOT automatically 7 days.
- `INVARIANT DEL-1`: a server deletion must not resurrect from a stale client.
- `INVARIANT DEL-2`: a stale supported client MUST NOT be able to resurrect a permanently deleted
  entity. Tombstone GC may occur only when the protocol can prove old clients cannot legally replay
  pre-deletion state — e.g. a retention horizon, a generation/snapshot reset, a cursor-compaction
  protocol, or an equivalent safe mechanism. No final duration is selected here.

---

## 5. State ↔ error mapping (bridge to the API taxonomy)

| Incoming condition | Auth state effect | Sync state effect | UI |
| --- | --- | --- | --- |
| no network | `OFFLINE_WITH_VALID_LOCAL_SESSION` | rows stay `SYNC_PENDING` | quiet |
| 401 `AUTH_REQUIRED`/`AUTH_EXPIRED` | `AUTH_EXPIRED`→`REAUTH_REQUIRED` | session `AUTH_REQUIRED` | non-destructive gate |
| 403 `FORBIDDEN` | unchanged | row `SYNC_FAILED` (permanent) | "couldn't sync" |
| 409 `REVISION_CONFLICT` | unchanged | entity `CONFLICT` | conflict screen |
| 429 `RATE_LIMITED` | unchanged | row `SYNC_PENDING` (backoff) | quiet |
| 404 `NOT_FOUND` (context does NOT prove deletion) | unchanged | `RECONCILE_REQUIRED` — the local row is NOT deleted | quiet / reconcile |
| 5xx (unclassified / unknown) | unchanged | row `SYNC_PENDING` (retryable with bounded attempts) | quiet |
| 5xx with a stable semantic/application error classification | unchanged | row `SYNC_FAILED` (permanent) | visible |
| `SYNC_CURSOR_INVALID` | unchanged | checkpoint reset flow | quiet |
| `ATTACHMENT_FAILED` | unchanged | attachment `UPLOAD_FAILED` | per-attachment |

Full mapping in `KEEPLAB-AUTH-SYNC-API-CONTRACT.md` §4.

---

## 6. Traceability

Auth states from `KEEP-AUTH-REFERENCE-BLUEPRINT.md` §2 (`OFFICIAL_FACT` patterns + KeepLab mapping);
sync states from `KEEP-OFFLINE-SYNC-BLUEPRINT.md` §4 (`KEEPLAB_DESIGN_INFERENCE`, endorsed by
Android S-07/S-08 `OFFICIAL_FACT`). No state claims Google Keep internals.
