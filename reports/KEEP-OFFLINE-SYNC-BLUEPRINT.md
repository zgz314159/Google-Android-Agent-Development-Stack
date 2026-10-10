# KEEP-OFFLINE-SYNC-BLUEPRINT

**Google Keep public behavior model + Android offline-first guidance + KeepLab sync design inference**

- Task: `KEEP-GLOBAL-RESEARCH-AUTH-SYNC-OFFLINE`
- Date: **2026-10-05 (CST)**
- Status: **RESEARCH + DESIGN INFERENCE ONLY.** No product source modified. No dependency added.
- Governance: `reports/KEEPLAB-AUTH-BOUNDARY-CORRECTION.md` (own backend; no Google private API).

> **Label discipline.** `PUBLIC_KEEP_BEHAVIOR` = what Google publicly documents. `OFFICIAL_FACT` =
> Android/standard documentation. `KEEPLAB_DESIGN_INFERENCE` = **our** proposal, not Keep's
> internals. Google Keep's internal sync algorithm is **not** claimed anywhere below.

---

## 1. GOOGLE_KEEP_PUBLIC_BEHAVIOR_MATRIX

Columns: capability · officially documented · source · observable semantics · unknown internals ·
KeepLab implication · device verification needed.

| Capability | Officially documented? | Source | Observable semantics (as documented) | Unknown internals | KeepLab implication | Device verify? |
|------------|------------------------|--------|--------------------------------------|-------------------|---------------------|----------------|
| Cross-device sync | Yes | S-27, Play listing | "Everything syncs across all your devices" | protocol, transport, cadence | KeepLab needs its own sync; Keep's is not reusable | No |
| Per-account sync toggle | Yes | S-16 | Settings → Accounts → Google → account → Sync → **Keep** toggle | what the toggle actually gates (client fetch vs server push) | KeepLab must let users see/manage sync per account, in-app (no Android account system) | No |
| Multi-account | Yes | S-22, S-60, S-61 | multiple accounts supported; widget asks which account; side-by-side on large screens; **separate note libraries per account** | whether data is cached per account or globally | KeepLab: one account per app instance by default; multi-account is a future, explicitly out-of-scope capability | Optional (D4) |
| Offline editing | Yes (implied, and by S-17/S-18 wording) | S-17, S-18, S-56 | editing while offline is possible; conflicts arise specifically when one device is offline | what is actually persisted locally; size limits | KeepLab: local-first is the *default*, not a mode | Partly (D2) |
| Offline indicator | **No** | — (community only: S-52..S-57) | community reports disagree (some say no indicator, some report a "syncing" animation) | whether any offline banner exists | KeepLab should design an honest, non-blocking sync indicator rather than copy a maybe-nonexistent one | **Yes (D2)** |
| "Conflicting edits found" | **Yes** | S-17 | triggers when the same note is edited on two devices with one offline (or low-bandwidth Wi-Fi); user chooses **Keep selected** or **Keep both** | algorithm, granularity (whole note vs field), what "Keep both" produces | KeepLab: adopt a user-facing conflict path for body text; algorithm is ours | Optional (D1) |
| Version history | Yes (existence) | S-23 | previous versions downloadable from the web client | retention window, granularity, storage | KeepLab: optional server-side note versioning later; do not build now | No |
| Delete propagation | **Yes** | S-19, S-21 | deleting a note you own deletes it for everyone shared with; deleted notes go to Trash for **7 days**, then are unrecoverable | delete vs tombstone internals | KeepLab: tombstones + bounded trash retention (7 days is a defensible product default) | No |
| Archive | Yes | S-21 | archive/unarchive; archiving a note with a task does not affect the task | sync representation of archive | KeepLab: archive is a note-flag mutation flowing through the outbox | No |
| Reload / re-download | **Yes** | S-18 | optional reload prompt; on reload notes are saved then **downloaded to the device again**; needs a strong connection; may not finish; an alert offers "try again" | trigger conditions; whether unsynced local edits survive | KeepLab: re-download must never destroy pending local mutations | **Yes (D3)** |
| Collaboration | Yes | S-19, S-25 | collaborator model; collaborators may label/colour/archive/remind "without changing the note for others"; family-group sharing | per-collaborator metadata model | KeepLab Phase-1: single-user sync only; collaboration is future | No |
| Shared-note access by account | Yes | S-20 | "Request access" when opening from a different account than shared with | — | KeepLab: authorization on every read/write; account-scoped data | No |
| Reminders / cross-app | Yes | S-24 | reminders may live in Google Tasks → visible in Keep/Calendar/Tasks; notification priority Tasks > Calendar | sync of reminders vs notes | Out of KeepLab Phase-1 scope (reminders are a separate capability) | No |
| Widgets | Yes | S-22, S-27 | Single note / Note collection / Quick capture; account selection when multiple accounts; collaborator icon | widget data refresh mechanism | KeepLab: widget is a separate future parity item | No |
| Note state after reinstall | **No** | community only (S-57) | users report sync breaking after reinstall / low storage | — | KeepLab: first-run must be a clean, well-defined state; test reinstall explicitly | Partly (see §24 outcome) |

### 1.1 What the Keep public model establishes (HIGH confidence)

- Google Keep is **account-bound**, **multi-account capable**, and its sync is exposed as an
  **Android account sync item** (S-16, S-22).
- Offline editing exists, and the **only publicly documented conflict surface** is the
  "Conflicting edits found" chooser (Keep selected / Keep both) (S-17).
- Deletion propagates and is bounded by a 7-day Trash (S-21).
- A **reload / full re-download** path exists and can be incomplete (S-18).

### 1.2 What is *not* public (must stay unknown)

Sync protocol; conflict algorithm and granularity; the local store's schema; retry/backoff; the
notification/transport (push vs poll); token model; the meaning of the account sync toggle
internally; whether "Keep both" duplicates the note or merges it; version-history retention.

---

## 2. Android official offline-first guidance — `OFFICIAL_FACT` (S-07, S-08, S-09..S-12, S-14)

| Guidance | Statement |
|----------|-----------|
| Local source of truth | An offline-first repository must always have a local data source; **the local data source is the canonical source of truth** (S-07) |
| Reads | UI reads local and observes it as state; screens reflect local data automatically (S-07) |
| Writes | Persist user input for later retrieval; writes go through the repository (S-07) |
| Data sources | ≥2 per repository that uses network: local + network (S-07) |
| Sync taxonomy | **pull-based** (fetch on navigation/demand), **push-based** (replicate + server notifications), **hybrid** (S-08) |
| Conflict resolution | Official guidance documents **last-write-wins** by timestamp (S-08) |
| Background execution | **WorkManager** is the recommended solution for most background work; sync adapters exist but the page itself recommends WorkManager (S-14) |
| WorkManager semantics | constraints (NetworkType / BatteryNotLow / RequiresCharging / DeviceIdle / StorageNotLow); `Result.retry()` + LINEAR/EXPONENTIAL backoff, min 10 s, default EXPONENTIAL 30 s; work is persisted across reboot; unmet constraints stop and re-schedule (S-09, S-10) |
| Work chaining | `Result.retry()` retries only the failed request; `Result.failure()` fails dependents; `KEEP` vs `APPEND_OR_REPLACE` policies (S-11) |
| Connectivity | register a `NetworkCallback` to react to `onAvailable`/`onLost`/capability changes (S-12) |

### 2.1 Mapping to a note-taking product (`KEEPLAB_DESIGN_INFERENCE`)

| Android concept | Note-taking mapping |
|-----------------|---------------------|
| Local data source | Room DB holding notes, labels, checklist items, attachments metadata |
| Single source of truth | the notes list/detail screens observe Room Flows; **never** the network |
| Offline reads | app opens to the full local note set with no spinner |
| Offline writes | note create/edit/archive/pin/delete commit to Room immediately and enqueue a mutation |
| Queued / lazy writes | mutations drain in the background under a network constraint |
| Online-only writes | attachment **content** upload may be deferred, but the note row must still commit locally |
| Network monitoring | `NetworkCallback` triggers an immediate drain attempt on reconnect (in addition to constraints) |
| Pull sync | cursor/watermark-based delta pull of server changes since the last checkpoint |
| Push sync | outbox drain of local mutations to the server |
| Periodic sync | low-frequency `PeriodicWorkRequest` (≥15 min, system-batched) as a safety net |
| WorkManager | single unique sync pipeline (see §4) |
| Constraints / retry / backoff | network constraint; EXPONENTIAL backoff; bounded attempts then a visible FAILED state |
| Battery/data-aware | de-prioritise large attachment uploads to unmetered networks |
| Conflict resolution | see §5 — LWW for metadata, revision-checked + user-visible for body, item-level merge for checklists |

---

## 3. KeepLab independent sync blueprint — `KEEPLAB_DESIGN_INFERENCE`

> This is **our** architecture. It is **not** Google Keep's internal architecture and must never be
> presented as such.

### 3.1 Candidate evaluated

```
Compose UI → ViewModel → Repository → Room (SSOT) + Sync metadata + PendingMutation/Outbox
          → WorkManager → HTTPS API → KeepLab Backend → KeepLab Database
```

### 3.2 Verdict: **candidate accepted with four refinements**

The candidate is broadly correct and matches both Android's official guidance (S-07, S-08) and
independent implementation experience (S-40, S-46, S-47, S-50, S-51). Refinements:

| # | Refinement | Why | Basis |
|---|-----------|-----|-------|
| R1 | **Persist an explicit outbox table** rather than relying only on per-entity dirty flags | dirty flags cannot express *which fields* changed, cannot coalesce safely, and lose intent when a later local edit changes the payload mid-flight | S-46, S-50, S-51 |
| R2 | **Client-generated UUIDs** for every entity and mutation | makes create idempotent on retry; a row created offline is immediately referenceable | S-47, S-51 |
| R3 | **Server revision/version + updated_at**, with a monotonic server-issued cursor for delta pull | enables optimistic-concurrency detection and a correct watermark | S-51 |
| R4 | **Tombstones (`deleted_at`)**, never hard local delete of synced rows before server acknowledgement | prevents resurrection on delta pull | S-21 (Keep's 7-day trash), S-50 |

### 3.3 Recommended architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│ UI (Compose)                                                         │
│   observes Room Flows only; optimistic; never blocks on network      │
└───────────────▲──────────────────────────────────┬───────────────────┘
                │ Flow<List<Note>>                 │ user actions
┌───────────────┴──────────────────────────────────▼───────────────────┐
│ ViewModel                                                            │
└───────────────┬──────────────────────────────────▲───────────────────┘
                │ suspend calls                     │ state
┌───────────────▼──────────────────────────────────┴───────────────────┐
│ Repository  (the only writer)                                        │
│   write path:  @Transaction { upsert entity(sync_state=SYNC_PENDING)  │
│                               + insert/coalesce outbox row }          │
│   read  path:  Room Flows                                             │
└───────┬───────────────────────────────▲──────────────────────────────┘
        │                               │
┌───────▼───────────────┐   ┌───────────┴──────────────────────────────┐
│ Room (SSOT)           │   │ Sync engine                              │
│  notes                │   │  SyncWorker (CoroutineWorker)            │
│  labels               │   │   - drain outbox (push, idempotent)      │
│  checklist_items      │   │   - delta pull since checkpoint          │
│  attachments (meta)   │   │   - apply server state into Room         │
│  outbox_mutations     │   │   - advance checkpoint ONLY on clean pass│
│  sync_state (meta)    │   │   - ConflictDetector → CONFLICT          │
│  tombstones(deleted_at)│  └───────────┬──────────────────────────────┘
└───────────────────────┘               │
                        ┌───────────────┴───────────────┐
                        │ WorkManager                   │
                        │  unique work "note_sync"      │
                        │  NetworkType.CONNECTED        │
                        │  EXPONENTIAL backoff          │
                        └───────────────┬───────────────┘
                                        │ HTTPS (JSON, revisioned)
                        ┌───────────────▼───────────────┐
                        │ KeepLab Backend API           │
                        │  Auth / Notes / Sync /        │
                        │  Attachments                  │
                        └───────────────┬───────────────┘
                                        │
                        ┌───────────────▼───────────────┐
                        │ KeepLab Database (+ object    │
                        │ storage for attachments)      │
                        └───────────────────────────────┘
```

### 3.4 Sync topology recommendation

- **Hybrid**, weighted to **push** for local changes and **pull** for remote changes:
  - *push*: outbox drain immediately after a local mutation (constrained), plus on app open and on
    reconnect (`NetworkCallback`, S-12).
  - *pull*: cursor-based delta pull (`GET /sync/changes?since=<cursor>`) at app open, after a push
    pass, and periodically as a safety net.
  - *periodic*: `PeriodicWorkRequest` (≥15 min, system-batched — S-49) as a fallback, **not** the
    primary mechanism.
- One **unique** sync pipeline (`enqueueUniqueWork`) so manual + background + reconnect triggers
  cannot race or fork into redundant workers (S-49). `APPEND_OR_REPLACE` is a defensible default so
  a mutation arriving mid-pass is not dropped (S-46).

---

## 4. Data / sync state model — `KEEPLAB_DESIGN_INFERENCE`

### 4.1 Recommended **minimal robust** set

| State | Entry condition | Exit condition | Persisted fields | UI indication | Network required | Retry policy |
|-------|-----------------|----------------|------------------|---------------|------------------|--------------|
| `LOCAL_ONLY` | note created before any account exists | account link succeeds → `SYNC_PENDING` | note row, no server id | subtle "local" marker (optional) | no | n/a |
| `SYNC_PENDING` | local mutation committed (create/update/archive/pin/colour/label/checklist/delete intent) | outbox drain succeeds → `SYNCED`; exhausted → `SYNC_FAILED` | `sync_state`, `attempt_count`, `last_error`, `base_revision` | quiet "waiting to sync" (non-blocking) | yes (deferred) | WorkManager EXPONENTIAL, bounded attempts |
| `SYNCING` | worker picks the row | success/failure | transient in-memory (optionally `sync_state`) | optional lightweight indicator | yes | — |
| `SYNCED` | server acknowledged | a new local mutation → `SYNC_PENDING` | `server_revision`, `updated_at`, checkpoint | none (default clean state) | no | — |
| `SYNC_FAILED` | attempts exhausted (e.g. 5) or a permanent server error | user retries → `SYNC_PENDING` | `attempt_count`, `last_error`, `failed_at` | "Couldn't sync — tap to retry" | yes | manual retry resets attempts |
| `CONFLICT` | revision check fails and edits are not auto-mergeable | user resolves (keep local / keep server / keep both) → `SYNC_PENDING` | both versions (local + incoming), `base_revision` | badge on the note; a resolution screen | yes | no auto-retry until resolved |
| `DELETE_PENDING` | user deletes a synced note | server acknowledges → row tombstoned/hard-deleted per retention | `deleted_at` (tombstone), `server_revision` | note hidden from the list (as if deleted) | yes | as `SYNC_PENDING` |
| `AUTH_REQUIRED` | server returns session-invalid | re-auth → resume drain | none (session-level, not per-row) | sign-in gate, non-destructive | yes | resume automatically after sign-in |

**Dropped / folded (with reason):**

| Considered state | Verdict | Reason |
|------------------|---------|--------|
| `DIRTY` | folded into `SYNC_PENDING` | duplicate of a pending local mutation; a second name adds no semantics |
| `RETRY_WAIT` | folded into `SYNC_PENDING` + attempt metadata | "waiting for the next attempt" is not a distinct persisted state; WorkManager owns the timing (S-10) |
| `TOMBSTONE` | kept as a **field** (`deleted_at`), not a state | it is a record shape, not a UI state; `DELETE_PENDING` covers the pending case |
| `LOCAL_ONLY` | kept, but optional | only meaningful if KeepLab permits notes before sign-in; if it does not, drop it |

→ **Core set: 7 note states** (`LOCAL_ONLY` optional) + **1 session-level gate** (`AUTH_REQUIRED`).

### 4.2 Persisted sync metadata (per note)

`id (client UUID)` · `server_revision` · `updated_at (server)` · `local_updated_at` · `sync_state` ·
`deleted_at` · `attempt_count` · `last_error`. Plus a per-account **sync checkpoint** (server cursor)
and the **outbox**.

---

## 5. Mutation outbox — `KEEPLAB_DESIGN_INFERENCE`

### 5.1 Operation log vs dirty flags vs hybrid

| Approach | Strength | Weakness | Verdict |
|----------|----------|----------|---------|
| Entity dirty flags only | trivial | cannot express field-level intent; cannot coalesce; loses mid-flight intent | rejected alone |
| Full operation log (event-sourced) | replayable, auditable | heavier; compaction needed; overkill for Phase-1 | deferred |
| **Outbox table + per-entity `sync_state`** (hybrid) | resilient, coalescible, simple to reason about | one extra table | **recommended** (R1) |

### 5.2 Outbox row (`KEEPLAB_DESIGN_INFERENCE`)

| Field | Purpose |
|-------|---------|
| `mutation_id` (client UUID) | **idempotency key** — the server must tolerate a duplicate (S-51) |
| `entity_id` (client UUID) | target note (client-generated, R2) |
| `op_type` | `CREATE` · `UPDATE` · `DELETE` · `ARCHIVE` · `UNARCHIVE` · `PIN` · `UNPIN` · `SET_COLOR` · `LABEL_ADD` · `LABEL_REMOVE` · `CHECKLIST_PUT` · `ATTACHMENT_ADD` |
| `payload` | the delta or the full desired state for this op, captured at enqueue time |
| `base_revision` | the `server_revision` the client believed it was editing (optimistic concurrency) |
| `attempt_count` / `last_error` | retry bookkeeping + honest FAILED surface |
| `created_at` (client) | ordering only — **never** the source of truth for conflict (S-51) |
| `coalesce_key` | `(entity_id, op_type_class)` so repeated edits collapse to one push |

### 5.3 Rules

1. **Entity write + outbox insert are one transaction.** A crash between them must be impossible
   (S-46, S-50).
2. **Coalesce** per `(entity, op-class)`; a rapid burst of edits yields one push, not N.
3. **Push the captured payload**, not "the current DB row" — otherwise a concurrent local edit
   silently rewrites the intent of an in-flight mutation (S-46).
4. **Delete an outbox row only after a confirmed success** (or a permanent-failure decision).
5. **Cap attempts**; on exhaustion set `SYNC_FAILED` and surface a retry — never drop silently.
6. Attachments: note row commits locally; **attachment content upload is a separate deferred op**
   (unmetered-network preference, resumable).

---

## 6. Conflict resolution — `KEEPLAB_DESIGN_INFERENCE`

### 6.1 Research basis

- Android officially documents **last-write-wins** only (S-08).
- Google Keep **publicly** documents a user-facing "Conflicting edits found" chooser when the same
  note is edited on two devices with one offline (S-17) — this is `PUBLIC_KEEP_BEHAVIOR`; it is **not**
  proof of Keep's internal algorithm.
- Independent implementation practice converges on: LWW for simple data; **revision checks**;
  user resolution when the cost of loss is high; optional three-way merge (S-40, S-46, S-50, S-51).

### 6.2 Recommended policy — **per field** (not one global rule)

| Field / capability | Policy | Rationale |
|--------------------|--------|-----------|
| `title`, `body` | **Server revision check**; if both sides changed → `CONFLICT`, user resolves (keep local / keep server / **keep both** as a duplicate); if only one side changed → fast-forward | text is where silent loss hurts most; a Keep-style chooser is a defensible, publicly-precedented UX (S-17) |
| checklist items | **Item-level merge by stable item id**: union of added items; deletions applied by id; per-item text uses LWW on `updated_at` | checklist operations are naturally per-item; whole-note LWW would lose ticks/additions |
| labels | **Set union** (add/remove as independent ops) | additive semantics; concurrent adds both survive |
| archive / pin / colour | **LWW on server revision** | cheap metadata; loss is trivially recoverable |
| attachments | **Content-addressed, append-only**; no merge; concurrent adds both survive | byte content has no meaningful merge |
| delete vs concurrent edit | **explicit conflict** ("deleted on another device, but you have unsaved changes") | the one case where auto-merge cannot help (S-46, S-50) |

### 6.3 Explicitly **not** recommended for Phase-1

- **CRDT** for note bodies: no evidence of need at single-user, low-concurrency scale; a real cost
  in schema, storage and migration complexity. Keep the option open; do not build it now.
- **Auto three-way merge** of text: no Phase-1 evidence; revisit if conflict frequency justifies it.
- **Client-wins LWW everywhere**: silently destroys edits (the failure users complain about — S-54,
  S-55).

### 6.4 Server behaviour on a stale mutation

Return a **conflict signal** (HTTP 409 + the current server version) rather than silently applying or
silently rejecting. The client then: pulls the current version, decides fast-forward vs `CONFLICT`
per §6.2, and never advances the checkpoint on a conflicted pass (S-51).

---

## 7. Server-side blueprint (technology-agnostic) — `KEEPLAB_DESIGN_INFERENCE`

**No cloud provider is chosen.** This is a conceptual service model.

```
Client ──HTTPS──▶ API gateway
                    │
      ┌─────────────┼──────────────┬───────────────┬──────────────────┐
      ▼             ▼              ▼               ▼                  ▼
  Auth API      User service   Session/token    Notes API         Sync API
   register      profile        issue            CRUD              delta pull
   login         settings       refresh          revisions        mutation push
   verify        account ops    revoke           labels           checkpoint
   reset                        device list      checklist
      │             │              │               │                  │
      └─────────────┴──────────────┴───────┬───────┴──────────────────┘
                                           ▼
                                   Primary database
                              (users, sessions, notes, revisions,
                               labels, checklist items, outbox-acks)
                                           │
                                   Object storage (attachments)
                                           │
                              (optional, later) Notification/push layer
```

### 7.1 Conceptual endpoints (design examples, **not** commitments)

| Purpose | Conceptual endpoint |
|---------|---------------------|
| Register | `POST /auth/register` |
| Login (password / passkey challenge) | `POST /auth/login`, `POST /auth/passkey/challenge`, `POST /auth/passkey/verify` |
| Refresh | `POST /auth/refresh` (rotating) |
| Logout / revoke | `POST /auth/logout`, `POST /auth/sessions/{id}/revoke` |
| Notes CRUD | `GET/POST/PATCH/DELETE /notes/{id}` |
| Mutation push (idempotent) | `POST /sync/mutations` with `mutation_id` |
| Delta pull | `GET /sync/changes?since=<cursor>` |
| Checkpoint | `GET /sync/checkpoint` |
| Attachment upload | `POST /attachments` (or pre-signed target) |
| Attachment download | `GET /attachments/{id}` (authorized per account) |

### 7.2 Server-side invariants

1. Every mutation is **idempotent** by `mutation_id` (duplicate → success, no double-apply).
2. Every note row carries a monotonically increasing **revision**; a stale `base_revision` on a
   conflicting field returns 409.
3. The **delta cursor is monotonic** and is advanced server-side only when the client confirms a
   clean apply.
4. Deletes are **tombstoned** server-side with a retention window (7 days is a defensible default —
   S-21) before hard deletion.
5. Attachments are authorized **per account** on every fetch.

---

## 8. Public vs private boundary (sync/auth)

```
KNOWN_PUBLICLY
  - Keep is Google-account-bound, multi-account capable, with an Android account sync toggle (S-16, S-22)
  - offline editing and a "Conflicting edits found" chooser (Keep selected / Keep both) (S-17)
  - reload / full re-download path that can be incomplete (S-18)
  - delete propagation + 7-day Trash + archive semantics (S-19, S-21)
  - note version history exists (S-23)
  - Android official offline-first guidance + LWW + WorkManager (S-07..S-12)

DESIGN_INFERENCE  (ours — never present as Keep fact)
  - the entire KeepLab architecture (§3), state model (§4), outbox (§5), conflict policy (§6),
    server blueprint (§7)

UNKNOWN_PRIVATE  (must not be guessed)
  - Keep's sync protocol, conflict algorithm/granularity, local schema, retry/backoff, transport,
    token model, "Keep both" outcome, version retention

DEVICE_CHECK_REQUIRED
  - the 6 journeys in KEEP-DEVICE-VERIFICATION-BACKLOG.md (4 MUST + 2 OPTIONAL)
```

## 9. Confidence

| Conclusion | Confidence | Basis |
|------------|------------|-------|
| Local Room DB should be the single source of truth | **HIGH** | T1 (S-07) |
| WorkManager is the right background engine (not sync adapters) | **HIGH** | T1 (S-09..S-12, S-14) |
| A durable outbox + client UUIDs + revisions + tombstones | **HIGH** | T1 (S-07) + ≥2 independent T3 (S-46, S-47, S-50, S-51) |
| Hybrid push/pull with a monotonic cursor | **MEDIUM-HIGH** | T1 (S-08) + T3 corroboration |
| Per-field conflict policy (LWW metadata; user-resolved body; item-merge checklists) | **MEDIUM** | T1 documents LWW only; Keep's chooser is public (S-17); policy is our inference |
| CRDT is unnecessary for Phase-1 | **MEDIUM** | absence of evidence of need; reversible decision |
| Keep's internal algorithm | **UNKNOWN (by design)** | not public; must not be guessed |
