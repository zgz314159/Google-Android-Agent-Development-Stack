# KEEPLAB-AUTH-SYNC-DECISION-REGISTER

**Numbered architecture decisions for the future KeepLab account / offline / sync architecture**

- Task: `KEEPLAB-AUTH-SYNC-ARCHITECTURE-SPEC`
- Date: 2026-10-05 (CST) · Status: **CANONICAL_ARCHITECTURE_DRAFT · NON_IMPLEMENTATION_AUTHORIZING**
- A0 update: 2026-10-06 — seven register entries changed from `HUMAN_DECISION_PENDING` to
  `HUMAN_APPROVED` (D-02/D-03/D-07/D-08/D-09/D-15); see §E. The canonical governance *file*
  amendment is `BLOCKED_BY_CONTRACT_GUARD`.
- Style note: the Stack's existing `DEC-*` namespace is **change-scoped** (embedded in a frozen
  per-package `implementation-contract.json`). This register therefore uses a distinct
  architecture-decision namespace (`AUTH-DEC` / `SYNC-DEC` / `GOV-DEC` / `BACKEND-DEC`) and invents
  **no** parallel governance framework.
- Every decision lists: status · rationale · alternatives · consequence · source basis ·
  human-approval-needed (Y/N).

Status tags: `FROZEN_ARCHITECTURE_DECISION` · `RECOMMENDED_DEFAULT` · `HUMAN_DECISION_PENDING` ·
`FUTURE_EXTENSION` · `NON_GOAL` · `PUBLIC_REFERENCE_ONLY`.

---

## A. Governance decisions

### GOV-DEC-001 — Current Mission forbids account/network; implementation not authorized
- **Status:** `FROZEN_ARCHITECTURE_DECISION` → **`HUMAN_APPROVED`** (D-15, 2026-10-06) at the
  *decision* level; the canonical `MISSION.md` / `FACTORY_RULES.md` amendment is
  `BLOCKED_BY_CONTRACT_GUARD`, so the invariant text is **not yet** amended
- **Approved value (D-15):** `YES_BOUNDED_ACCOUNT_NETWORK_UNLOCK` — bounded, phase-gated, local-first,
  own-backend, no Google/Firebase by default · source `HUMAN_PROJECT_OWNER_APPROVAL` 2026-10-06
- **Rationale:** `MISSION.md` hard invariants (local-first, no network, no account) still bind.
- **Alternatives:** none considered — lifting the invariant is a human act, not an agent act.
- **Consequence:** all auth/sync/backend architecture here is future-facing and non-authorizing.
- **Source:** `HUMAN_ARCHITECTURE_DECISION`; `KeepLab-Relay/MISSION.md`.
- **Human approval needed:** N (already fixed).

### GOV-DEC-002 — `RISK-GOV-001` remains the canonical governance gate
- **Status:** `FROZEN_ARCHITECTURE_DECISION`
- **Rationale:** `RISK-GOV-001` (`ROADMAP.md`, `BASELINE-READY.json`) already requires a human
  amendment before sync/sharing/account areas; it is still unresolved.
- **Alternatives:** create a new parallel gate — rejected (forbidden; invents scope).
- **Consequence:** the account/network gate is the `RISK-GOV-001` family (see GOV-DEC-005).
- **Source:** `HUMAN_ARCHITECTURE_DECISION`; `KeepLab-Relay/specs/google-keep-parity/ROADMAP.md`.
- **Human approval needed:** N (recorded); Y to actually resolve the gate.
- **A0 update (2026-10-06):** the human decision layer is resolved
  (`RISK-GOV-001: RESOLVED_BY_BOUNDED_HUMAN_UNLOCK`). The **canonical** resolution edit to
  `ROADMAP.md` is `BLOCKED_BY_CONTRACT_GUARD` and was not applied. The gate therefore stays
  canonical-unresolved until `OPEN_GOVERNANCE_WRITE_CONTRACT`.

### GOV-DEC-003 — Formal spec package deferred by governance
- **Status:** `FROZEN_ARCHITECTURE_DECISION`
- **Rationale:** canonical spec homes (`Stack specification/**`; `KeepLab-Relay/specs/**`) are
  protected/fail-closed; the compiler's READY gate forbids unresolved questions.
- **Alternatives:** write into `KeepLab-Relay/specs/` — rejected (guard fails closed).
- **Consequence:** the architecture spec lives under `reports/**`, labelled
  `CANONICAL_ARCHITECTURE_DRAFT · NON_IMPLEMENTATION_AUTHORIZING`.
- **Source:** observed Contract Guard behaviour + `implementation-contract.json` allowed paths.
- **Human approval needed:** Y (to open a canonical spec path later).
- **A0 update (2026-10-06):** **unchanged**. D-14 was not answered, so
  `FORMAL_SPEC_PACKAGE_LOCATION: HUMAN_DECISION_PENDING` stands; no new package was created.

### GOV-DEC-004 — J1–J4 reclassified `REFERENCE_VALIDATION_WHEN_NEEDED`, program-non-blocking
- **Status:** `FROZEN_ARCHITECTURE_DECISION`
- **Rationale:** those journeys answer *Google Keep reference* questions, not KeepLab design needs.
- **Alternatives:** keep them as program prerequisites — rejected (blocks design for no reason).
- **Consequence:** run a journey only if a future KeepLab UI/behaviour decision needs exact Keep
  behaviour; otherwise do not block architecture/backend/implementation planning.
- **Source:** `KEEPLAB_DESIGN_INFERENCE`; `KEEP-DEVICE-VERIFICATION-BACKLOG.md` (not rewritten).
- **Human approval needed:** N (additive clarification).

### GOV-DEC-005 — Account/network gate is `RISK-GOV-002`, part of the `RISK-GOV-001` family
- **Status:** `FROZEN_ARCHITECTURE_DECISION` → **`HUMAN_APPROVED`** (D-15, 2026-10-06) at the
  decision level; canonical file amendment `BLOCKED_BY_CONTRACT_GUARD`
- **Rationale:** the current Mission forbids account/network implementation specifically; recorded
  additively without editing `RISK-GOV-001`.
- **Consequence:** see RISK-REGISTER `RISK-GOV-002`.
- **Source:** `HUMAN_ARCHITECTURE_DECISION` + `KEEPLAB_DESIGN_INFERENCE`.
- **Human approval needed:** N (recorded); Y to unlock.
- **A0 update (2026-10-06):** unlock approved bounded (`YES_BOUNDED_ACCOUNT_NETWORK_UNLOCK`);
  `IMPLEMENTATION_AUTHORIZATION_MODEL: PHASE_GATED`; no phase starts automatically.

---

## B. Authentication / identity decisions

### AUTH-DEC-001 — Identity authority = KeepLab backend
- **Status:** `FROZEN_ARCHITECTURE_DECISION`
- **Rationale:** human correction: `KEEPLAB_AUTHORITY: OWN_BACKEND`; Google/Firebase forbidden.
- **Alternatives:** Google account identity, Firebase Auth — both `FORBIDDEN_UNLESS_HUMAN_APPROVED`.
- **Consequence:** KeepLab accounts, sessions, credentials and recovery are all KeepLab-owned.
- **Source:** `HUMAN_ARCHITECTURE_DECISION` (`KEEPLAB-AUTH-BOUNDARY-CORRECTION.md`).
- **Human approval needed:** N (given).

### AUTH-DEC-002 — Credential Manager = Android credential UX layer only
- **Status:** `FROZEN_ARCHITECTURE_DECISION`
- **Rationale:** Credential Manager is a client-side credential-exchange API; passkeys are
  relying-party (app-server) owned; it does not require Google to be the identity authority.
- **Alternatives:** no Credential Manager; legacy Google Sign-In — rejected/forbidden.
- **Consequence:** KeepLab uses the sheet for passwords/passkeys; the Google federated provider
  stays disabled.
- **Source:** `OFFICIAL_FACT` (S-01, S-04, S-05, S-33) + `HUMAN_ARCHITECTURE_DECISION`.
- **Human approval needed:** N.

### AUTH-DEC-003 — Google OAuth / Sign in with Google / Firebase Auth forbidden by default
- **Status:** `FROZEN_ARCHITECTURE_DECISION`
- **Rationale:** frozen governance keys.
- **Consequence:** no such dependency may be added without a human-approved contract.
- **Source:** `HUMAN_ARCHITECTURE_DECISION`.
- **Human approval needed:** N (given).

### AUTH-DEC-004 — Final auth method
- **Status:** `HUMAN_DECISION_PENDING`
- **Rationale:** research recommends a shortlist (A email+password; B passkey-first; C phone+code)
  but freezing one is a human product decision.
- **Alternatives:** A/B/C; explicit rejects recorded (Google/Firebase; username-only; ROPC flow).
- **Consequence:** the credential payloads of register/login/recovery are not frozen.
- **Source:** `KEEPLAB_DESIGN_INFERENCE`; `KEEP-AUTH-REFERENCE-BLUEPRINT.md` §4.
- **Human approval needed:** **Y**.

### AUTH-DEC-005 — Token format
- **Status:** `HUMAN_DECISION_PENDING` (implementation decision)
- **Rationale:** research gives principles (short access + rotating refresh + revocation) but no
  compelling reason to fix JWT vs opaque vs PASETO now.
- **Alternatives:** signed JWT · opaque token · PASETO.
- **Consequence:** the client treats tokens as opaque; no token code exists.
- **Source:** `KEEPLAB_DESIGN_INFERENCE`; S-29/S-30 (principles only).
- **Human approval needed:** **Y**.

### AUTH-DEC-006 — Session model (short-lived access + rotating refresh + revocation)
- **Status:** `RECOMMENDED_DEFAULT` (principle); exact lifetimes → `HUMAN_DECISION_PENDING`
- **Rationale:** RFC 9700 / OAuth 2.1 for public clients; rotation detects theft.
- **Alternatives:** long-lived non-rotating tokens — rejected (weaker).
- **Consequence:** server-side session/device list; per-session and all-session revoke. Rotation is
  **single-use + RETRY_SAFE**: a retried rotation request carrying the same `refresh_request_id`
  recovers the same logical rotation result within a bounded retry window; a different rotation
  identity on an already-used credential is the reuse/theft signal (API-CONTRACT §3.1, STATE-MODEL
  INVARIANT SESS-2). Storage implementation is `IMPLEMENTATION_DECISION_PENDING`.
- **Source:** `OFFICIAL_FACT` (S-29, S-30) + `KEEPLAB_DESIGN_INFERENCE`.
- **Human approval needed:** N (principle) / Y (lifetimes).

### AUTH-DEC-007 — Refresh material stored app-private; Keystore where appropriate
- **Status:** `RECOMMENDED_DEFAULT`
- **Rationale:** device-loss bounds; never outside the sandbox; never logged.
- **Source:** `OFFICIAL_FACT` (S-13) + `KEEPLAB_DESIGN_INFERENCE`.
- **Human approval needed:** N.

### AUTH-DEC-008 — Offline refresh failure / AUTH_REQUIRED is non-destructive
- **Status:** `FROZEN_ARCHITECTURE_DECISION`
- **Rationale:** offline-first requires local data to survive auth failure (S-07; §10 of the spec).
- **Consequence:** `AUTH_REQUIRED` pauses sync; keeps outbox; never deletes notes.
- **Source:** `KEEPLAB_DESIGN_INFERENCE`.
- **Human approval needed:** N.

### AUTH-DEC-009 — Multi-KeepLab-account scope
- **Status:** **`HUMAN_APPROVED`** (2026-10-06) — Phase-1 = `SINGLE_ACTIVE_ACCOUNT_PHASE1`;
  multi-account = `FUTURE_EXTENSION` (no multi-account UI now)
- **Approved value (D-03):** one active KeepLab account at a time; synced entities keep a non-null
  `account_id` so future account-scoped structures remain valid · source
  `HUMAN_PROJECT_OWNER_APPROVAL` 2026-10-06
- **Rationale:** Google Keep's multi-account is `PUBLIC_KEEP_BEHAVIOR`, not a KeepLab requirement.
- **Source:** `KEEPLAB_DESIGN_INFERENCE` (+ S-22 `PUBLIC_REFERENCE_ONLY`).
- **Human approval needed:** N (given as D-03).

### AUTH-DEC-010 — Notes may exist before first sign-in?
- **Status:** **`HUMAN_APPROVED`** (2026-10-06)
- **Approved value (D-02):** `YES_LOCAL_ONLY_BEFORE_SIGNIN` — pre-sign-in notes are `LOCAL_ONLY`
  with `account_id = NULL`; no synthetic server account is created; later linking/migration is an
  explicit safe operation; existing local notes must never be silently assigned, uploaded, deleted
  or merged into an account · source `HUMAN_PROJECT_OWNER_APPROVAL` 2026-10-06
- **Rationale:** determines whether `LOCAL_ONLY` state and the "no-account first-run" UX exist;
  resolved in favour of local-first.
- **Alternatives:** yes (local-first notes, later linked) · no (account required up front).
- **Consequence:** `LOCAL_ONLY` is kept in the state model.
- **Source:** `KEEPLAB_DESIGN_INFERENCE`; `KEEP-OFFLINE-SYNC-BLUEPRINT.md` §4.1 (`LOCAL_ONLY` optional).
- **Human approval needed:** N (given as D-02).

### AUTH-DEC-011 — Sign-out local-data policy
- **Status:** `HUMAN_DECISION_PENDING`; recommended safe default = keep the **app-private local cache**
  (non-destructive)
- **Rationale:** never silently destructive; MISSION.md forbids dropping existing notes. Android
  app-private/device storage protection does **not** imply that this spec has chosen an encrypted
  database: `APPLICATION_LEVEL_DATABASE_ENCRYPTION` is a **`SECURITY_IMPLEMENTATION_DECISION`
  (HUMAN_DECISION_PENDING if the project requires it)**. No encryption dependency is added.
- **Source:** `KEEPLAB_DESIGN_INFERENCE`.
- **Human approval needed:** **Y**.

### AUTH-DEC-012 — Account deletion is distinct from sign-out
- **Status:** `FROZEN_ARCHITECTURE_DECISION` (conceptual distinction);
  retention/grace = **`HUMAN_APPROVED`** (D-05, 2026-10-07)
- **Approved value (D-05):** `ACCOUNT_DELETE_GRACE_30_DAYS` — an authenticated deletion request
  immediately enters `DELETION_PENDING`; normal account access becomes disabled and all server
  sessions are revoked immediately (their access/refresh capability becomes invalid); no new normal
  sync write is accepted while deletion is pending; `purge_after = deletion_requested_at + 30 days`
  under **server clock authority**; within the grace period the owner may cancel through
  re-authentication using the **EXISTING** verified credential system (no new token family invented
  for recovery), restoring `ACTIVE` without resurrecting deleted data because purge has not
  occurred; after expiry an explicit deterministic **purge boundary** permanently deletes the server
  account data. Android local Room data is **never** silently deleted or reassigned because the
  remote account was disabled/deletion-pending/purged. D-06 Trash retention and sync-tombstone
  retention are unrelated; `TOMBSTONE_GC` stays DISABLED · source `HUMAN_PROJECT_OWNER_APPROVAL`
  2026-10-07
- **Rationale:** conflating them causes accidental data loss.
- **Source:** `KEEPLAB_DESIGN_INFERENCE` (+ `HUMAN_PROJECT_OWNER_APPROVAL` 2026-10-07 for retention/grace).
- **Human approval needed:** N (distinction) / N (retention — given as D-05).

---

## C. Sync / data decisions

### SYNC-DEC-001 — Room is the local single source of truth
- **Status:** `FROZEN_ARCHITECTURE_DECISION`
- **Rationale:** Android's offline-first guidance makes the local source canonical (S-07).
- **Alternatives:** network-first reads — rejected (blocks offline, breaks SSOT).
- **Consequence:** all UI reads flow from Room; the network only updates Room.
- **Source:** `OFFICIAL_FACT` (S-07, S-08) + `KEEPLAB_DESIGN_INFERENCE`.
- **Human approval needed:** N.

### SYNC-DEC-002 — UI must not read network; network updates local first
- **Status:** `FROZEN_ARCHITECTURE_DECISION`
- **Rationale:** invariant NET-1; prevents divergent canonical state.
- **Consequence:** the network layer never returns note state directly to the UI.
- **Source:** `OFFICIAL_FACT` (S-07).
- **Human approval needed:** N.

### SYNC-DEC-003 — Outbox hybrid (explicit outbox table + per-entity sync_state)
- **Status:** `FROZEN_ARCHITECTURE_DECISION`
- **Rationale:** dirty flags cannot express field intent, coalesce, or preserve mid-flight intent.
- **Alternatives:** dirty flags only (rejected) · full event sourcing (deferred).
- **Consequence:** one extra table; entity mutation + outbox insert are one transaction.
- **Source:** `KEEPLAB_DESIGN_INFERENCE` (R1) + S-46/S-50/S-51.
- **Human approval needed:** N.

### SYNC-DEC-004 — `mutation_id` is the idempotency key
- **Status:** `FROZEN_ARCHITECTURE_DECISION`
- **Rationale:** retries must be safe; duplicate → success, no double-apply.
- **Consequence:** the server-side `mutation_id` **dedupe record/claim** participates in the SAME
  consistency boundary as the mutation apply, the revision increment and the change-log append
  (DATA-MODEL §4.1, spec §26). A retry after a crash cannot double-apply.
- **Source:** S-46/S-51.
- **Human approval needed:** N.

### SYNC-DEC-005 — Client-generated UUIDs everywhere
- **Status:** `FROZEN_ARCHITECTURE_DECISION`
- **Rationale:** offline entities immediately referenceable; idempotent create.
- **Consequence:** the stable client UUID is the **sync identity** of a future synced entity and is
  introduced **additively**: the existing local primary key may remain as an implementation-local
  identity during migration, and replacing it is a **separate migration decision** that MUST NOT be
  required for first network enablement (DATA-MODEL §6.1, INVARIANT MIG-1/MIG-2).
- **Source:** `KEEPLAB_DESIGN_INFERENCE` (R2) + S-47/S-51.
- **Human approval needed:** N.

### SYNC-DEC-006 — Server revision + `base_revision` optimistic concurrency; 409 on conflict
- **Status:** `FROZEN_ARCHITECTURE_DECISION`
- **Rationale:** detects stale writes; prevents silent text overwrite.
- **Source:** S-51 + S-17 (`PUBLIC_KEEP_BEHAVIOR` precedent for a user-visible chooser only).
- **Human approval needed:** N.

### SYNC-DEC-007 — Monotonic delta cursor for pull
- **Status:** `FROZEN_ARCHITECTURE_DECISION`
- **Rationale:** correct watermark; checkpoint advances only on a clean apply.
- **Consequence:** the **server change cursor** (opaque, account-scoped server position in the ordered
  change stream) and the **client checkpoint** (the last server cursor THIS client has cleanly and
  completely applied) are distinct concepts and MUST NOT be conflated (DATA-MODEL §2.8/§4.2,
  INVARIANT CUR-2/CUR-3). Clients MUST NOT compare cursors across accounts.
- **Source:** S-51.
- **Human approval needed:** N.

### SYNC-DEC-008 — Tombstone deletion (`deleted_at`), never a hard local delete of a synced row
- **Status:** `FROZEN_ARCHITECTURE_DECISION`
- **Rationale:** a physical delete resurrects on delta pull.
- **Consequence:** **Trash ≠ sync tombstone.** Trash (`trashed` / `trashed_at`) is a user-visible,
  recoverable product state; `deleted_at` is a protocol-level record of FINAL deletion for
  convergence / anti-resurrection. Trash MUST NOT set `deleted_at` (DATA-MODEL TRASH-1/TRASH-2,
  STATE-MODEL §4).
- **Source:** `KEEPLAB_DESIGN_INFERENCE` (R4) + S-21 (`PUBLIC_KEEP_BEHAVIOR`) + S-50.
- **Human approval needed:** N.

### SYNC-DEC-009 — Sync topology = HYBRID (push local, pull remote)
- **Status:** `FROZEN_ARCHITECTURE_DECISION`
- **Rationale:** Android documents pull/push/hybrid; hybrid fits a local-first notes app.
- **Alternatives:** pull-only · push-only — rejected (worse freshness / worse batching).
- **Source:** `OFFICIAL_FACT` (S-08) + `KEEPLAB_DESIGN_INFERENCE`.
- **Human approval needed:** N.

### SYNC-DEC-010 — Background engine = WorkManager, single unique pipeline `note_sync`
- **Status:** `FROZEN_ARCHITECTURE_DECISION`
- **Rationale:** WorkManager is Android's recommendation; duplicate work is the common bug.
- **Alternatives:** sync adapters (not the default recommendation) · custom scheduler (rejected).
- **Consequence:** one unique logical pipeline `note_sync`; `NetworkType.CONNECTED`; exponential
  bounded backoff. Frozen **invariants** (see spec §18): ONE ACTIVE SYNC EXECUTOR MAX; a trigger
  arriving while running MUST NOT be lost; the worker MUST drain to a stable point or guarantee a
  follow-up run; OUTBOX DURABILITY is the source of work, not the scheduling event. The exact
  `ExistingWorkPolicy` (e.g. `KEEP` + drain-until-stable/recheck, serialized append/rerun, or an
  equivalent) is **`A4_IMPLEMENTATION_DECISION`** — to be selected by deterministic tests against the
  actual WorkManager version, never frozen blindly here.
- **Source:** `OFFICIAL_FACT` (S-09..S-12, S-14) + S-46/S-47/S-49.
- **Human approval needed:** N.

### SYNC-DEC-011 — Per-field conflict policy
- **Status:** `FROZEN_ARCHITECTURE_DECISION`
- **Rationale:** text, checklist items, labels, metadata and attachments need different treatment.
- **Consequence:** resolution uses **server-assigned ordering** (`server_revision` / server change
  sequence / server `server_updated_at`). Client `local_updated_at` is ordering/UI only and is never
  used to resolve a multi-device conflict.
- **Alternatives:** one global LWW — rejected (silent text loss).
- **Source:** `KEEPLAB_DESIGN_INFERENCE` + S-08 + S-17.
- **Human approval needed:** N.

### SYNC-DEC-012 — Labels use operation-based add/remove (refinement over "set union")
- **Status:** `FROZEN_ARCHITECTURE_DECISION`
- **Rationale:** a pure union would resurrect a label a user concurrently **removed**.
- **Consequence:** concurrent membership changes are made **deterministic** by ordering them by the
  **server-accepted revision / change sequence**. A later accepted `LABEL_REMOVE` MUST NOT be
  resurrected by a client-side set union; a later intentional `LABEL_ADD` MAY re-add the label. No
  CRDT is introduced in Phase 1 (DATA-MODEL INVARIANT LBL-1).
- **Alternatives:** set union (research draft) — **refined/rejected** for loss of removal intent.
- **Source:** `KEEPLAB_DESIGN_INFERENCE` (rationale).
- **Human approval needed:** N.

### SYNC-DEC-013 — CRDT for note bodies is NOT adopted in Phase 1
- **Status:** `NON_GOAL` (Phase 1); `FUTURE_EXTENSION` (option kept open)
- **Rationale:** no evidence of need at single-user, low-concurrency scale; real cost.
- **Alternatives:** CRDT now — rejected; revisit if conflict frequency justifies it.
- **Source:** `KEEPLAB_DESIGN_INFERENCE`; S-08/S-46/S-50.
- **Human approval needed:** N.

### SYNC-DEC-014 — Connectivity ≠ backend reachability ≠ auth validity
- **Status:** `FROZEN_ARCHITECTURE_DECISION`
- **Rationale:** a `NetworkCallback` proves neither reachability nor auth.
- **Source:** `OFFICIAL_FACT` (S-12) + `KEEPLAB_DESIGN_INFERENCE`.
- **Human approval needed:** N.

### SYNC-DEC-015 — Trash retention duration
- **Status:** `HUMAN_DECISION_PENDING`; 7 days = `REFERENCE_DEFAULT_CANDIDATE` (`PUBLIC_REFERENCE_ONLY`)
- **Rationale:** Google Keep's 7-day Trash is public, but KeepLab retention is a product decision.
- **Separate concern:** `SYNC_TOMBSTONE_RETENTION_OR_COMPACTION` is a **protocol-correctness** concern,
  NOT the same product setting as Trash duration, and it is NOT automatically 7 days. It is governed
  by the anti-resurrection invariant: tombstone GC may occur only when the protocol proves old clients
  cannot legally replay pre-deletion state (retention horizon / generation-snapshot reset /
  cursor-compaction protocol / equivalent) — spec §21, STATE-MODEL INVARIANT DEL-2. No final duration
  is selected here; the mechanism choice is `IMPLEMENTATION_DECISION_PENDING` (A4/A6).
- **Source:** S-21 (`PUBLIC_KEEP_BEHAVIOR`).
- **Human approval needed:** **Y** (product Trash duration only).

### SYNC-DEC-016 — Attachments: content-addressed, append-only, deferred upload
- **Status:** `RECOMMENDED_DEFAULT` (design) / `FUTURE_EXTENSION` (implementation)
- **Rationale:** bytes have no meaningful merge; a note must not block on a binary upload.
- **Source:** `KEEPLAB_DESIGN_INFERENCE` + S-18.
- **Human approval needed:** N (design) / Y (limits/quotas).

### SYNC-DEC-017 — `account_id` in local tables from the first networked implementation
- **Status:** `RECOMMENDED_DEFAULT`; the product-scope question is now **`HUMAN_APPROVED`** (D-03)
- **Rationale:** avoids a later migration + backfill on every device.
- **Consequence:** the column is **nullable** — NULL is legal only while the entity is `LOCAL_ONLY`,
  and MUST NOT be NULL once the entity has entered any remote-sync state (DATA-MODEL INVARIANT
  ISO-1b). A pre-auth note keeps `account_id = NULL` until an explicit account-link transaction sets
  it. No synthetic account row is created to satisfy the FK (INVARIANT ACCT-1/ACCT-2).
- **Authority note:** a client-supplied `account_id` is NOT authorization; the server derives the
  effective account scope from the authenticated session (INVARIANT ISO-4 = CLIENT_ACCOUNT_ID_IS_NOT_AUTHORITY).
- **Source:** `KEEPLAB_DESIGN_INFERENCE`.
- **Human approval needed:** N — resolved by D-03 (product scope: Phase-1
  `SINGLE_ACTIVE_ACCOUNT_PHASE1`; `LOCAL_ONLY` entities may keep `account_id = NULL`).

---

## D. Backend decisions

### BACKEND-DEC-001 — Service boundary model (technology-agnostic)
- **Status:** `RECOMMENDED_DEFAULT`
- **Rationale:** Auth/User/Session/Notes/Sync/Attachments + primary DB + object storage is the
  minimal coherent split matching the client contract.
- **Alternatives:** monolithic single service (acceptable for a first implementation) — not rejected,
  the boundary is logical.
- **Source:** `KEEPLAB_DESIGN_INFERENCE`; S-29..S-31.
- **Human approval needed:** N (design) / Y (implementation shape).

### BACKEND-DEC-002 — Cloud provider
- **Status:** **`HUMAN_APPROVED`** (2026-10-06)
- **Approved value (D-08):** `INITIAL_CLOUD_PROVIDER: TENCENT_CLOUD` +
  `DEPLOYMENT_PORTABILITY: PORTABLE_DOCKER` · source `HUMAN_PROJECT_OWNER_APPROVAL` 2026-10-06
- **Rationale:** no existing KeepLab decision froze one; no vendor chosen before A0.
- **Consequence:** avoid unnecessary proprietary coupling; backend application runtime
  container-portable where practical. **Not** assumed: Firebase, GCP, AWS-specific architecture,
  vendor-exclusive application APIs. Object-storage product, load-balancer product and
  managed-vs-container DB deployment remain A2 implementation-level decisions.
- **Human approval needed:** N (given as D-08).

### BACKEND-DEC-003 — Backend language
- **Status:** **`HUMAN_APPROVED`** (2026-10-06) · **Human approval needed:** N (given as D-07).
- **Approved value (D-07):** `BACKEND_LANGUAGE: KOTLIN` · `BACKEND_FRAMEWORK: KTOR`.
  Android dependencies unchanged; no backend code created.

### BACKEND-DEC-004 — Database vendor
- **Status:** **`HUMAN_APPROVED`** (2026-10-06) · **Human approval needed:** N (given as D-09).
- **Approved value (D-09):** `PRIMARY_DATABASE: POSTGRESQL` (database technology only; self-hosted
  vs TencentDB for PostgreSQL vs containerized, major version, HA topology and backup policy remain
  A2 implementation design; no database created).

### BACKEND-DEC-005 — Push notification provider
- **Status:** **`HUMAN_APPROVED`** (2026-10-07) — A8 correctness uses
  `NO_PUSH_PROVIDER_IN_A8_CORRECTNESS_PATH`; a push provider remains `FUTURE_EXTENSION`
  (latency optimization only)
- **Approved value (D-11):** no FCM / Firebase / Google-services / vendor push dependency is chosen
  for M5 correctness; correctness stays pull/delta based; WorkManager, foreground or manual sync and
  the authenticated API and refresh paths detect revoked/disabled remote state; any future push must
  sit behind a provider abstraction; A8 PASS must be possible with `PUSH_PROVIDER = NONE` · source
  `HUMAN_PROJECT_OWNER_APPROVAL` 2026-10-07
- **Rationale:** sync is pull-based; push is an optional later latency improvement.
- **Human approval needed:** N (given as D-11).

---

## E. Decision summary

| Namespace | Count | FROZEN | RECOMMENDED | HUMAN-PENDING | HUMAN-APPROVED (2026-10-06) | NON_GOAL/FUTURE |
| --- | --- | --- | --- | --- | --- | --- |
| GOV-DEC | 5 | 3 | 0 | 0 | 2 | 0 |
| AUTH-DEC | 12 | 5 | 3 | 2 | 2 | 3 (overlapping) |
| SYNC-DEC | 17 | 12 | 3 | 1 | 1 | 2 |
| BACKEND-DEC | 5 | 0 | 1 | 1 | 3 | 1 |
| **Total** | **39** | — | — | **4** | **8** | — |

Human-approval-required decisions are consolidated in `KEEPLAB-AUTH-SYNC-HUMAN-DECISIONS.md`
(6 approved by A0 on 2026-10-06, 9 still pending).

**A0 status changes (2026-10-06)** — no decision ID was duplicated or renumbered:

| Entry | From | To |
| --- | --- | --- |
| `GOV-DEC-001` | `FROZEN_ARCHITECTURE_DECISION` | `HUMAN_APPROVED` — D-15 at the decision level (canonical file amendment `BLOCKED_BY_CONTRACT_GUARD`) |
| `GOV-DEC-005` | `FROZEN_ARCHITECTURE_DECISION` | `HUMAN_APPROVED` — D-15 bounded unlock, `PHASE_GATED` |
| `AUTH-DEC-009` | `HUMAN_DECISION_PENDING` | `HUMAN_APPROVED` — `SINGLE_ACTIVE_ACCOUNT_PHASE1` (D-03) |
| `AUTH-DEC-010` | `HUMAN_DECISION_PENDING` | `HUMAN_APPROVED` — `YES_LOCAL_ONLY_BEFORE_SIGNIN` (D-02) |
| `BACKEND-DEC-002` | `HUMAN_DECISION_PENDING` | `HUMAN_APPROVED` — `TENCENT_CLOUD + PORTABLE_DOCKER` (D-08) |
| `BACKEND-DEC-003` | `HUMAN_DECISION_PENDING` | `HUMAN_APPROVED` — `KOTLIN_KTOR` (D-07) |
| `BACKEND-DEC-004` | `HUMAN_DECISION_PENDING` | `HUMAN_APPROVED` — `POSTGRESQL` (D-09) |
| `SYNC-DEC-017` (product-scope question only) | `HUMAN_DECISION_PENDING` element | resolved by D-03; entry stays `RECOMMENDED_DEFAULT` |

Still `HUMAN_DECISION_PENDING: AUTH-DEC-004 (D-01) · AUTH-DEC-005 (D-10) · AUTH-DEC-011 (D-04) ·
AUTH-DEC-012 (D-05) · SYNC-DEC-015 (D-06) · SYNC-DEC-016 (D-13) · BACKEND-DEC-005 (D-11) ·
GOV-DEC-003 (D-14)`.

Source of approval: `HUMAN_PROJECT_OWNER_APPROVAL`, 2026-10-06 conversation/task input. No other
approval source is claimed.
