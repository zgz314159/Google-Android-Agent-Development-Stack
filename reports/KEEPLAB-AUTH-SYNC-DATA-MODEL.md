# KEEPLAB-AUTH-SYNC-DATA-MODEL

**Conceptual local + server data model for future KeepLab account / sync architecture**

- Task: `KEEPLAB-AUTH-SYNC-ARCHITECTURE-SPEC`
- Date: 2026-10-05 (CST) · Status: **CANONICAL_ARCHITECTURE_DRAFT · NON_IMPLEMENTATION_AUTHORIZING**
- Basis: `KEEPLAB-AUTH-SYNC-ARCHITECTURE-SPEC.md` §13/§14/§27; `KEEP-OFFLINE-SYNC-BLUEPRINT.md` §5;
  `KeepLab-Relay/HANDOFF.md` (current Room schema v2).
- **No Room migration is generated. No production schema (v2) is modified.** This is conceptual only.

> Current KeepLab (Phase B) local schema v2: `notes`, `checklist_items`, `labels`, `note_labels`.
> This document describes the **future networked** conceptual model, additively compatible with it.

---

## 1. Design rules

1. Every synced entity has a **stable client-generated UUID** as its sync identity
   (`FROZEN_ARCHITECTURE_DECISION`). The UUID column is introduced **additively**; the existing
   local primary key MAY remain as an implementation-local identity during migration (§6.1), and
   replacing it is a separate migration decision — never a prerequisite of first network
   enablement.
2. Every entity that has entered a remote-synchronisation state carries **`account_id`** for
   scoping (`RECOMMENDED_DEFAULT`, spec §28). `account_id` MAY be NULL **only** while the entity is
   `LOCAL_ONLY`; it MUST NOT be NULL in `SYNC_PENDING` / `SYNCING` / `SYNCED` / `SYNC_FAILED` /
   `CONFLICT` / `DELETE_PENDING` (INVARIANT ISO-1b).
3. Every synced entity carries sync metadata: `sync_state`, `server_revision`,
   `local_updated_at`, `server_updated_at`, `deleted_at`.
4. Deletion is a **sync tombstone** (`deleted_at`), never a hard local delete of a synced row.
   Trash is a *separate product state* and is never a tombstone (§2.2, §6.2).
5. An entity mutation and its outbox row are written in **one transaction**.

---

## 2. Local conceptual tables

### 2.1 `accounts`

| Field | Type (conceptual) | Notes |
| --- | --- | --- |
| `account_id` | UUID/opaque string | PK; server-issued `AccountId` |
| `display_name` | string | profile; local cache |
| `email_or_identifier` | string? | only if the chosen auth method has one |
| `state` | enum | `ACTIVE` · `DISABLED` (a former `PENDING_LOCAL` value is removed — see ACCT-1) |
| `is_active_on_device` | bool | Phase-1 single active account |
| `created_at` | long | local |

Primary key `account_id`. Ownership: the account itself. Lifecycle: created on first successful
sign-in (server-issued); retained per sign-out policy (§29 of spec).

```
INVARIANT ACCT-1:  an `accounts` row exists ONLY for a server-issued KeepLab account. NO synthetic
                   or placeholder account row is created before sign-in. An unlinked pre-auth note is
                   represented by `notes.sync_state = LOCAL_ONLY` + `notes.account_id = NULL`, NOT by
                   an account row. (`state = PENDING_LOCAL` is therefore removed: a server-issued
                   account row cannot simultaneously be an unlinked local placeholder.)
INVARIANT ACCT-2:  `accounts.account_id` is the SERVER-ISSUED `AccountId`; a locally invented id is
                   never written there, and no fake server account may be created to satisfy an FK.
                   If a future phase needs a distinct local identity concept, it MUST be modelled
                   explicitly as such.
```

### 2.2 `notes`

| Field | Type | Notes |
| --- | --- | --- |
| `note_id` | UUID | **stable sync identity**, client-generated. Additively introduced; the existing v2 primary key MAY remain as an implementation-local identity during migration (§6.1) |
| `account_id` | string? | FK → `accounts`; scope. NULL **only** while `sync_state = LOCAL_ONLY`; MUST NOT be NULL in any remote-sync state (ISO-1b) |
| `title` | text | revision-checked field |
| `body` | text | revision-checked field |
| `color` | int/enum | LWW field |
| `pinned` | bool | LWW field |
| `archived` | bool | LWW field |
| `trashed` | bool | **product Trash** state; carried forward from v2 `trashed`; user-visible and recoverable |
| `trashed_at` | long? | when the row entered Trash (`RECOMMENDED_DEFAULT`) |
| `kind` | enum | `TEXT` · `CHECKLIST` |
| `server_revision` | long | 0 until first server ack |
| `sync_state` | enum | see STATE-MODEL §2 |
| `local_updated_at` | long | local ordering only (never a conflict source) |
| `server_updated_at` | long? | server LWW clock for metadata fields |
| `deleted_at` | long? | **SYNC TOMBSTONE only** — final deletion for convergence / anti-resurrection; NEVER set by Trash |
| `last_error` | string? | honest FAILED surface |

```
INVARIANT TRASH-1:  Trash (`trashed` / `trashed_at`) is a user-visible, recoverable PRODUCT state.
                    A sync tombstone (`deleted_at`) is a PROTOCOL-level record representing final
                    deletion for convergence / anti-resurrection. Moving a note to Trash MUST NOT set
                    `deleted_at`, and an item that is merely in Trash MUST NOT be turned into a
                    permanently-deleted sync tombstone.
INVARIANT ISO-1b:   `account_id` MAY be NULL while `sync_state = LOCAL_ONLY`; it MUST NOT be NULL
                    for `SYNC_PENDING` / `SYNCING` / `SYNCED` / `SYNC_FAILED` / `CONFLICT` /
                    `DELETE_PENDING`.
```

### 2.3 `labels`

| Field | Type | Notes |
| --- | --- | --- |
| `label_id` | UUID | stable sync identity, client-generated; introduced additively (§6.1) |
| `account_id` | string? | scope; NULL only while `LOCAL_ONLY` |
| `name` | text | |
| `server_revision` | long | |
| `sync_state` | enum | |
| `deleted_at` | long? | sync tombstone (final deletion), never product Trash |

### 2.4 `note_labels` (junction)

| Field | Type | Notes |
| --- | --- | --- |
| `note_id` | UUID | part of composite PK |
| `label_id` | UUID | part of composite PK |
| `account_id` | string? | scope (denormalised for isolation); NULL only while `LOCAL_ONLY` |
| `sync_state` | enum | labels are operation-based (spec §20) |
| `server_revision` | long? | server-accepted revision / change sequence that ordered this membership change |
| `local_updated_at` | long | ordering/UI only — never a conflict source |
| `deleted_at` | long? | unlink sync tombstone |

No CASCADE-by-association across accounts: the junction is deleted by **unlink tombstone**, then a
`LABEL_REMOVE` mutation, not by a destructive cascade, once synced. (Current v2 uses CASCADE; the
future model must not let a cascade silently drop sync intent.)

```
INVARIANT LBL-1:  label membership changes (`LABEL_ADD` / `LABEL_REMOVE`) are ordered by the
                  SERVER-accepted revision / change sequence. A later accepted REMOVE MUST NOT be
                  resurrected merely because a client performs a set union; a later intentional ADD
                  MAY re-add the label. No CRDT is introduced in Phase 1. Client wall clocks are
                  never the ordering source.
```

### 2.5 `checklist_items`

| Field | Type | Notes |
| --- | --- | --- |
| `item_id` | UUID | stable sync identity, client-generated; **stable across edits** (enables item-level merge); introduced additively (§6.1) |
| `note_id` | UUID | FK → `notes` |
| `account_id` | string? | scope; NULL only while `LOCAL_ONLY` |
| `text` | text | per-item resolution uses the **server-assigned ordering** (`server_revision` / server change sequence / server `server_updated_at`); client `local_updated_at` is ordering/UI only |
| `checked` | bool | per-item resolution uses the **server-assigned ordering** (same rule as `text`) |
| `position` | int | ordering |
| `server_revision` | long | |
| `server_updated_at` | long? | server-assigned per-item clock (`RECOMMENDED_DEFAULT`) |
| `sync_state` | enum | |
| `deleted_at` | long? | item delete tombstone |

### 2.6 `attachments`

| Field | Type | Notes |
| --- | --- | --- |
| `attachment_id` | UUID | PK, client-generated |
| `note_id` | UUID | FK → `notes` |
| `account_id` | string? | scope; NULL only while its note is `LOCAL_ONLY` |
| `local_uri` | string? | local file path while unsynced/pending |
| `content_hash` | string | content address |
| `size_bytes` | long | |
| `mime_type` | string | |
| `upload_state` | enum | `LOCAL_ONLY` · `UPLOAD_PENDING` · `UPLOADING` · `UPLOADED` · `UPLOAD_FAILED` |
| `remote_object_id` | string? | set on upload success |
| `attempt_count` / `last_error` | int / string? | retry state |

### 2.7 `outbox_mutations`

See §3.

### 2.8 `sync_checkpoints` (client checkpoint)

| Field | Type | Notes |
| --- | --- | --- |
| `account_id` | string | PK (account-scoped) |
| `cursor` | string | **CLIENT CHECKPOINT** — the last **server change cursor** that THIS client has successfully and completely applied |
| `updated_at` | long | |

```
INVARIANT CUR-2:  the server change cursor and the client checkpoint are NOT the same thing. The
                  server issues an opaque, account-scoped CURSOR into the ordered change stream; the
                  server does NOT automatically know a client's applied checkpoint unless the protocol
                  explicitly uploads it. The checkpoint advances ONLY after a clean apply (CUR-1).
INVARIANT CUR-3:  the cursor is ACCOUNT-SCOPED (or otherwise opaque and authorization-safe); clients
                  MUST NOT compare cursors across accounts.
```

### 2.9 `conflicts`

| Field | Type | Notes |
| --- | --- | --- |
| `conflict_id` | UUID | PK |
| `account_id` | string | scope |
| `entity_type` / `entity_id` | enum / UUID | which entity |
| `field` | string | `title`/`body`/`delete_vs_edit`/… |
| `local_value` | text/blob | captured local version |
| `server_value` | text/blob | captured incoming server version |
| `server_revision` | long | incoming revision |
| `created_at` | long | |
| `resolution` | enum? | `KEEP_LOCAL` · `KEEP_SERVER` · `KEEP_BOTH` · null (unresolved) |

### 2.10 `sessions_metadata` (optional)

Local, non-secret mirror of server session metadata for a device/session list UI (labels, last
seen, `session_id`). **Never** stores the refresh secret in a queryable column; the secret lives in
app-private/Keystore-protected storage keyed separately (spec §9). Status
`RECOMMENDED_DEFAULT`, `FUTURE_EXTENSION`.

---

## 3. Outbox model (conceptual)

```
OUTBOX_MODEL: OUTBOX_TABLE + PER_ENTITY_SYNC_STATE (hybrid)   FROZEN
```

| Field | Purpose |
| --- | --- |
| `mutation_id` | **idempotency key** (client UUID); server tolerates duplicates |
| `entity_id` | target entity (client UUID) |
| `entity_type` | `note` · `label` · `note_label` · `checklist_item` · `attachment` |
| `account_id` | scope (NOT NULL — a synced intent always belongs to an account; ISO-1b) |
| `op_type` | `CREATE`/`UPDATE`/`DELETE`/`ARCHIVE`/`UNARCHIVE`/`PIN`/`UNPIN`/`SET_COLOR`/`LABEL_ADD`/`LABEL_REMOVE`/`CHECKLIST_PUT`/`ATTACHMENT_ADD` |
| `payload` | the delta / full desired state **captured at enqueue time** |
| `base_revision` | the `server_revision` the client edited against |
| `attempt_count` | retry bookkeeping |
| `last_error` | last failure (honest surface) |
| `created_at` | client ordering only — **never** a conflict source |
| `coalesce_key` | `(entity_id, op-class)` so repeated edits collapse to one push |
| `state` | `PENDING` · `IN_FLIGHT` · `FAILED` |

### 3.1 Operation types — is more granularity needed?

`FROZEN_ARCHITECTURE_DECISION`: the 12 op types above are sufficient for Phase 1. They are
**field-class** granular, not per-keystroke — a burst of body edits coalesces to one `UPDATE`.

### 3.2 Deliberately deferred granularity (`FUTURE_EXTENSION`)

Per-item checklist ops (`CHECKLIST_ITEM_ADD/UPDATE/CHECK/REMOVE`) could replace the coarser
`CHECKLIST_PUT`. Deferred because: Phase-1 concurrency is single-user low-frequency; item-level
merge is already achievable from the `CHECKLIST_PUT` payload plus stable `item_id`s; adding
per-item ops now increases outbox volume and coalescing complexity without proven need.

### 3.3 Rules (FROZEN_ARCHITECTURE_DECISION)

```
OUT-1  entity write + outbox insert == ONE LOCAL TRANSACTION
OUT-2  mutation_id == idempotency key
OUT-3  outbox row removed only on confirmed success OR explicit permanent-failure handling
OUT-4  push the CAPTURED payload, not the live DB row
OUT-5  coalesce per (entity_id, op-class)
OUT-6  attachment content upload is a separate deferred op; note row commits independently
```

---

## 4. Server-side conceptual model

Technology-agnostic. **No vendor, engine or language chosen** (`HUMAN_DECISION_PENDING`).

| Server table | Purpose | Key | Invariants |
| --- | --- | --- | --- |
| `users` | account identity + credential links | `account_id` | `account_id` server-issued, opaque |
| `credentials` | password verifiers / passkey public keys | `credential_id` | adaptive hash; per-user salt; never reversible |
| `sessions` | device sessions (revocable) | `session_id` | rotation; revocation; device label |
| `notes` | note rows | `note_id` (client UUID) | monotonic `revision`; `deleted_at` tombstone |
| `labels` / `note_labels` | label model + links | composite | operation-based add/remove |
| `checklist_items` | checklist rows | `item_id` (client UUID) | stable ids |
| `mutations_applied` | dedupe of applied `mutation_id` | `mutation_id` | idempotency ledger |
| `change_log` | ordered delta stream | `cursor` (monotonic) | append-only; drives `GET /sync/changes` |
| `attachments` | attachment metadata | `attachment_id` | content-hash; per-account authz |

### 4.1 The single consistency boundary

```
mutation_id dedupe record/claim  +  mutation apply  +  revision increment  +  change-log append
                                                                        ==  ONE TRANSACTION
```
The **idempotency record/claim** (the `mutations_applied` keyed by `mutation_id`) participates in the
SAME server-side consistency boundary as the apply, the revision increment and the change-log append.
Otherwise the server could apply a mutation and crash before recording its `mutation_id`, then apply
it again on retry. A crash between any two of these would either double-apply (no ledger) or drop a
delta from the pull stream (no change-log row). Status `FROZEN_ARCHITECTURE_DECISION` · Source
`KEEPLAB_DESIGN_INFERENCE` + S-51 + corrective task §8.

### 4.2 Cursor semantics

- `change_log.cursor` is a **SERVER CHANGE CURSOR**: a monotonic, opaque, **account-scoped** position
  in the account's ordered change stream; it total-orders server changes for that account.
- Every accepted write appends exactly one ordered change row.
- The client persists only the cursor it has **cleanly applied** (`sync_checkpoints.cursor`) — the
  **CLIENT CHECKPOINT**, which is a client-side fact, not a server-side one.
- A server MAY expose `latest_available_cursor` (the server head). It does not thereby know a given
  client's applied checkpoint.

---

## 5. Attachments data flow (conceptual)

```
note row commits locally  ──►  attachment metadata row (upload_state=UPLOAD_PENDING)
                                     │
                                     ▼  ATTACHMENT_ADD outbox op (separate, deferred)
                              binary upload to object storage
                                     │
                                     ▼  success → remote_object_id set, upload_state=UPLOADED
```

```
INVARIANT ATT-1:  a local note MUST NOT block merely because a binary upload is pending.
```
Status `FROZEN_ARCHITECTURE_DECISION`. Orphan handling: an uploaded object whose metadata row is
deleted before the client records success is an orphan candidate → RISK-ATTACH-001 (garbage
collection is a `FUTURE_EXTENSION`).

---

## 6. Migration / backward compatibility (conceptual)

Current local data (Room schema v2) must survive:

| Existing (v2) | Future conceptual treatment |
| --- | --- |
| `notes` rows | become `LOCAL_ONLY` (`account_id = NULL` until an **explicit account-link transaction** sets it) |
| `checklist_items` | keep; add a stable client UUID column (`item_id`) **additively** if absent; preserve existing references |
| `labels`, `note_labels` | keep; add a stable client UUID column (`label_id`) **additively** if absent; preserve existing foreign keys |
| `trashed` | stays **product Trash** (`trashed` / `trashed_at`); it does **NOT** map to `deleted_at` |

```
CRITICAL: existing local data MUST NEVER be silently deleted when future auth is introduced.
```
Status `FROZEN_ARCHITECTURE_DECISION` · Source `HUMAN_ARCHITECTURE_DECISION` (MISSION.md
irreversible list). Migration steps are designed in the roadmap (phase A1); **not implemented here**.

### 6.1 Additive identity migration (A1)

```
INVARIANT MIG-1:  A1 is ADDITIVE. The existing local primary key MAY remain as an
                  implementation-local identity during migration; a stable client UUID column is
                  added FIRST if the current schema does not already use a UUID primary key.
INVARIANT MIG-2:  The server identity of a future synced entity is the stable client UUID.
                  Replacing the local primary key is a SEPARATE migration decision and MUST NOT be
                  required for first network enablement.
INVARIANT MIG-3:  existing notes, existing references and existing foreign keys are preserved.
```

### 6.2 Trash vs sync tombstone

```
INVARIANT TRASH-2:  TRASH STATE is a user-visible, recoverable product state.
                    SYNC TOMBSTONE (`deleted_at`) is a protocol-level record representing FINAL
                    deletion for convergence / anti-resurrection.
                    The two are distinct and MUST NOT be conflated.
```

The future conceptual model uses `trashed` / `trashed_at` for Trash and reserves `deleted_at` for
the final-deletion tombstone. An item currently in Trash MUST NOT be silently turned into a
permanently-deleted sync tombstone by the migration.

### 6.3 Linking pre-auth (LOCAL_ONLY) notes

Pre-auth notes keep `account_id = NULL` and `sync_state = LOCAL_ONLY`. If the human later chooses to
link/migrate them, the linking is an **explicit account-link transaction** that (a) sets
`account_id`, (b) assigns the stable client UUID if absent, and (c) creates the appropriate outbox
intent — after which the entity may enter `SYNC_PENDING`. `account_id` MUST NOT be NULL for any
entity that has entered a remote-sync state (ISO-1b). No fake server account is created to satisfy
the FK (ACCT-1/ACCT-2).

---

## 7. Account scoping summary

```
ISO-1   Every entity that has entered a remote-sync state carries account_id; reads/writes are
        scoped to the active account.
ISO-1b  account_id MAY be NULL only while the entity is LOCAL_ONLY; it MUST NOT be NULL in any
        remote-sync state (SYNC_PENDING / SYNCING / SYNCED / SYNC_FAILED / CONFLICT / DELETE_PENDING).
ISO-2   account_id exists in local tables from the FIRST networked implementation (nullable;
        RECOMMENDED_DEFAULT — avoids a future migration).
ISO-3   account_id is consistent between local tables and every backend API call.
ISO-4   CLIENT_ACCOUNT_ID_IS_NOT_AUTHORITY: the server derives the effective account scope from the
        authenticated session/access credential. Sending account_id = <other account> MUST NOT give a
        client another account's data. Local Room account_id remains mandatory for synced local data
        isolation.
ISO-5   In a future multi-account/org mode an explicit selected account/scope MAY be transmitted, but
        the server MUST validate membership/authorization against the authenticated session.
```
Status `FROZEN_ARCHITECTURE_DECISION` / `RECOMMENDED_DEFAULT` (ISO-2).

---

## 8. Traceability

Local model derives from `KEEP-OFFLINE-SYNC-BLUEPRINT.md` §4.2/§5 (`KEEPLAB_DESIGN_INFERENCE`) +
`OFFICIAL_FACT` S-07 (local SSOT). Server model derives from §7 of the same blueprint
(`KEEPLAB_DESIGN_INFERENCE`) + S-29..S-31 (standards). Tombstone basis S-21 (`PUBLIC_KEEP_BEHAVIOR`)
+ S-50 (`COMMUNITY_OBSERVATION`). No Google Keep private schema is modeled or claimed.
