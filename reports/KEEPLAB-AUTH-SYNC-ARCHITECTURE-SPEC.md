# KEEPLAB-AUTH-SYNC-ARCHITECTURE-SPEC

**KeepLab-owned Authentication / Account / Offline-first / Sync Architecture Specification**

- Task: `KEEPLAB-AUTH-SYNC-ARCHITECTURE-SPEC`
- Date: **2026-10-05 (CST)**
- Phase type: **ARCHITECTURE SPECIFICATION PHASE.** No implementation, no backend coding, no
  Android feature work, no Google Keep device validation, no P0B, no P1.
- Status label: **CANONICAL_ARCHITECTURE_DRAFT · NON_IMPLEMENTATION_AUTHORIZING**
- Authority basis (preserved, not re-decided):
  `reports/KEEPLAB-AUTH-BOUNDARY-CORRECTION.md` (canonical governance record).

> This is a transformation of completed research into architecture **decisions, contracts,
> invariants, state machines, data models and gates**. It is **not** a copy of the research
> reports. It re-opens no frozen contract. It authorizes **no** implementation.

---

## 0. Document control

### 0.1 Authoritative inputs read (targeted)

| Input | Path | Used for |
| --- | --- | --- |
| Auth boundary correction | `reports/KEEPLAB-AUTH-BOUNDARY-CORRECTION.md` | frozen governance keys, spec mechanism |
| Global research | `reports/KEEP-GLOBAL-RESEARCH-AUTH-SYNC-OFFLINE.md` | research findings → decisions |
| Auth reference blueprint | `reports/KEEP-AUTH-REFERENCE-BLUEPRINT.md` | auth UX state model, session principles |
| Offline-sync blueprint | `reports/KEEP-OFFLINE-SYNC-BLUEPRINT.md` | sync state model, outbox, conflict, server |
| Research source matrix | `reports/KEEP-RESEARCH-SOURCE-MATRIX.md` | S-xx provenance + tiers |
| Device verification backlog | `reports/KEEP-DEVICE-VERIFICATION-BACKLOG.md` | J1–J4 classification |
| Device validation binding | `reports/KEEP-DEVICE-VALIDATION-DEVICE-BINDING.md` | execution serial / binding state |
| KeepLab mission | `KeepLab-Relay/MISSION.md` | current-phase hard invariants |
| KeepLab factory rules | `KeepLab-Relay/FACTORY_RULES.md` | protected paths, irreversible list |
| KeepLab factory ops | `KeepLab-Relay/FACTORY.md` | factory operation model |
| KeepLab handoff | `KeepLab-Relay/HANDOFF.md` | actual current local data model (v2) |
| KeepLab roadmap | `KeepLab-Relay/specs/google-keep-parity/ROADMAP.md` | **RISK-GOV-001** gate |

No broad scan of unrelated repositories. **Testapp and PowerAi were not touched.**

### 0.2 Companion artifacts (this package)

```
reports/KEEPLAB-AUTH-SYNC-ARCHITECTURE-SPEC.md    ← this file (master)
reports/KEEPLAB-AUTH-SYNC-DATA-MODEL.md           conceptual local + server model
reports/KEEPLAB-AUTH-SYNC-STATE-MODEL.md          auth + sync + session state machines
reports/KEEPLAB-AUTH-SYNC-API-CONTRACT.md         conceptual API + error taxonomy
reports/KEEPLAB-AUTH-SYNC-DECISION-REGISTER.md    numbered decisions (AUTH-DEC / SYNC-DEC / …)
reports/KEEPLAB-AUTH-SYNC-IMPLEMENTATION-ROADMAP.md  future phases A0…A9 (not executed)
reports/KEEPLAB-AUTH-SYNC-RISK-REGISTER.md        RISK-AUTH/SYNC/… with invariants
reports/KEEPLAB-AUTH-SYNC-HUMAN-DECISIONS.md      the explicit open-decision table
reports/KEEPLAB-AUTH-SYNC-ARCHITECTURE-REVIEW.md  corrective-review record (ISSUE-01..ISSUE-12)
reports/KEEP-REFERENCE-DEVICE-BACKLOG-STATUS.md   additive J1–J4 reclassification
orchestration/hermes/evidence/keeplab-auth-sync-architecture-spec/   compact evidence
orchestration/hermes/evidence/keeplab-auth-sync-architecture-review-fix/  corrective evidence
```

### 0.3 Statement labels used in this document

**Status tag** (every architecture statement carries exactly one):

| Tag | Meaning |
| --- | --- |
| `FROZEN_ARCHITECTURE_DECISION` | Decided here (or by prior human governance); do not reopen without a human |
| `RECOMMENDED_DEFAULT` | Strongly recommended, research-backed; changeable by a recorded human decision |
| `HUMAN_DECISION_PENDING` | Not decided; implementation must not proceed as if decided |
| `FUTURE_EXTENSION` | Deliberately out of the first networked phase; keep the seam open |
| `NON_GOAL` | Explicitly will not be built in the addressed phase |
| `PUBLIC_REFERENCE_ONLY` | True of Google Keep (public evidence); never evidence for KeepLab internals |

**Source-basis label** (§47 traceability):

`OFFICIAL_FACT` · `PUBLIC_KEEP_BEHAVIOR` · `KEEPLAB_DESIGN_INFERENCE` ·
`HUMAN_ARCHITECTURE_DECISION`.

Cite style: `S-xx` refers to `KEEP-RESEARCH-SOURCE-MATRIX.md`.

---

## 1. Governance boundary (preserved — do not reopen)

### 1.1 Frozen human architecture decision

```
GOOGLE_KEEP_ROLE:                    REFERENCE_PRODUCT_ONLY
GOOGLE_KEEP_ACCOUNT_SCOPE:           REFERENCE_APP_ONLY
BENCHMARK_GOOGLE_ACCOUNT:            REFERENCE_SIDE_ONLY
KEEPLAB_AUTHORITY:                   OWN_BACKEND
KEEPLAB_GOOGLE_ACCOUNT_REQUIRED:     NO
GOOGLE_AUTH_IN_KEEPLAB:              FORBIDDEN_UNLESS_HUMAN_APPROVED
FIREBASE_AUTH_IN_KEEPLAB:            FORBIDDEN_UNLESS_HUMAN_APPROVED
GOOGLE_PRIVATE_API:                  FORBIDDEN
GOOGLE_PRIVATE_BACKEND_PROTOCOL:     FORBIDDEN
```
Status `FROZEN_ARCHITECTURE_DECISION` · Source `HUMAN_ARCHITECTURE_DECISION`.

KeepLab is **not** a Google Keep backend clone, not a Google OAuth client by default, not a
Firebase-auth product, and not a Google-account identity product. KeepLab is an independent
product with its own backend authority.

### 1.2 Current mission constraint (unchanged, not lifted)

`KeepLab-Relay/MISSION.md` currently declares (hard invariants, §1 and §Out-of-scope):

- local-first, **no network**;
- **no account** / no sign-in / no cloud sync;
- "shared", "synced", "multi-device" are properties the product **does not have**.

This specification defines **future** auth / sync / backend architecture. It **does not** claim
those features are authorized today:

```
CURRENT_IMPLEMENTATION_AUTHORIZATION: NOT_GRANTED
IMPLEMENTATION_AUTHORIZATION_MODEL:   PHASE_GATED
AUTH_NETWORK_GOVERNANCE_GATE:         REQUIRED_BEFORE_IMPLEMENTATION → HUMAN_APPROVED_BOUNDED · CANONICAL_AMENDMENT_BLOCKED_BY_CONTRACT_GUARD
```

Status `FROZEN_ARCHITECTURE_DECISION` · Source `HUMAN_ARCHITECTURE_DECISION`.

**`MISSION.md` was read only and was not modified by this task.**

### 1.3 The exact existing governance gate — **RISK-GOV-001**

The canonical governance gate is **`RISK-GOV-001`**, recorded in
`KeepLab-Relay/specs/google-keep-parity/ROADMAP.md` (and surfaced in `BASELINE-READY.json`):

> `MISSION.md` declares labels, trash, attachments, rich text, widgets, sync, sharing and any
> second form factor out of scope — yet labels and trash already ship. **A human decision is
> required** to amend `MISSION.md` / `FACTORY_RULES.md` before implementing those areas.

- `RISK-GOV-001` currently scopes `P3-large-screen`, `P4-rich-text`, `P5-attachments/link`,
  `P7-ecosystem`. **P7-ecosystem explicitly includes sync / sharing / account.**
- `RISK-GOV-001` is **still canonical** and is **still unresolved**.
- This specification therefore extends it additively: the account/network gate is the
  **`RISK-GOV-001` family** (`RISK-GOV-001` + this spec's `RISK-GOV-002`, see §37), not a new
  parallel framework.
- The Specification Compiler's per-package `DEC-*` mechanism is change-scoped and cannot host a
  global rule (see `KEEPLAB-AUTH-BOUNDARY-CORRECTION.md` §4). No parallel governance framework
  was invented.

Status `FROZEN_ARCHITECTURE_DECISION` · Source `HUMAN_ARCHITECTURE_DECISION`.

### 1.4 Scope boundaries

| Boundary | Rule |
| --- | --- |
| KeepLab production code | may be modified **only** in an official implementation phase (never here) |
| Google Keep device | exclusive mutable resource, capacity 1; **not used by this task** |
| J1–J4 backlog | **not executed**; reclassified additively (§50 of the task → device-backlog status doc) |
| Testapp / PowerAi | **never** in scope |
| P0B / P1 | **not started** |

---

## 2. Official non-goals of this task

Status `NON_GOAL` (all): implement anything; modify `KeepLab-Relay/app/src/main/**`; modify Gradle
dependencies; modify the Room production schema; generate a Room migration; add a Credential
Manager dependency; add Retrofit/Ktor code; create a backend server; choose a hosting provider;
create a database; add OAuth; add Firebase; write token code; write password code; execute
J1–J4; touch a Google account; operate an Android device; benchmark; start P0B; start P1.

---

## 3. Target architecture — candidate evaluated (not merely accepted)

### 3.1 Candidate presented by the task

```
Compose UI → ViewModel → Repository
                          ├──► Room SSOT
                          └──► Sync Engine → WorkManager → HTTPS API
                                                            └► KeepLab Backend
                                                                 ├► Primary DB
                                                                 └► Object Storage
```

### 3.2 Verdict: **ACCEPTED with four refinements** (research-backed, not assumed)

The candidate was checked against the completed research (`KEEP-OFFLINE-SYNC-BLUEPRINT.md` §3,
Android S-07/S-08, and independent implementation evidence S-46/S-50/S-51). It is correct. Four
refinements are mandatory — the same four the research already established:

| # | Refinement | Why | Basis |
| --- | --- | --- | --- |
| R1 | explicit **Outbox table** (not per-entity dirty flags alone) | dirty flags cannot express field intent, cannot coalesce, lose mid-flight intent | S-46, S-50, S-51 |
| R2 | **client-generated UUIDs** everywhere | idempotent create; offline entity is immediately referenceable | S-47, S-51 |
| R3 | **server revision** + **monotonic delta cursor** | optimistic-concurrency detection + a correct watermark | S-51 |
| R4 | **tombstones** (`deleted_at`) | prevents resurrection on delta pull | S-21, S-50 |

Status `FROZEN_ARCHITECTURE_DECISION` · Source `KEEPLAB_DESIGN_INFERENCE` + `OFFICIAL_FACT`.

### 3.3 Frozen architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Presentation — Jetpack Compose                                           │
│   observes Room Flows only; optimistic; NEVER blocks on a network call   │
└───────────────▲───────────────────────────────────┬──────────────────────┘
                │ Flow<UI state>                    │ user actions
┌───────────────┴───────────────────────────────────▼──────────────────────┐
│ ViewModel (application layer)                                            │
└───────────────┬───────────────────────────────────▲──────────────────────┘
                │ suspend calls                     │ state
┌───────────────▼───────────────────────────────────┴──────────────────────┐
│ Repository — the ONLY writer of local note state                         │
│   write: @Transaction { upsert entity(sync_state=SYNC_PENDING)           │
│                         + insert/coalesce outbox row }                   │
│   read : Room Flows                                                      │
└───────┬───────────────────────────────▲──────────────────────────────────┘
        │                               │
┌───────▼───────────────┐   ┌───────────┴──────────────────────────────────┐
│ Room (SSOT)           │   │ Sync coordinator / engine                    │
│  accounts             │   │  SyncWorker (CoroutineWorker)                │
│  notes                │   │   - drain outbox (push, idempotent)          │
│  labels / note_labels │   │   - delta pull since checkpoint              │
│  checklist_items      │   │   - apply server state into Room             │
│  attachments (meta)   │   │   - advance checkpoint ONLY on a clean pass  │
│  outbox_mutations     │   │   - ConflictDetector → CONFLICT              │
│  sync_checkpoints     │   └───────────┬──────────────────────────────────┘
│  conflicts            │               │
└───────────────────────┘   ┌───────────┴───────────────┐
                            │ WorkManager               │
                            │  unique work "note_sync"  │
                            │  NetworkType.CONNECTED    │
                            │  EXPONENTIAL backoff      │
                            └───────────┬───────────────┘
                                        │ HTTPS (JSON, revisioned)
                            ┌───────────▼───────────────┐
                            │ Network API client        │
                            │  (sole network caller)    │
                            └───────────┬───────────────┘
                                        │
                            ┌───────────▼───────────────┐
                            │ KeepLab Backend API       │
                            │  Auth / User / Session /  │
                            │  Notes / Sync / Attachments│
                            └───────────┬───────────────┘
                                        │
                     ┌──────────────────┴──────────────────┐
                     ▼                                      ▼
              Primary DB                            Object Storage
        (users, sessions, notes, revisions,        (attachment binaries,
         labels, checklist items, change log)       content-addressed)
```

Status `FROZEN_ARCHITECTURE_DECISION` · Source `KEEPLAB_DESIGN_INFERENCE` +
`OFFICIAL_FACT` (S-07 local SSOT, S-08 sync taxonomy, S-14 WorkManager).

---

## 4. Architectural layers — ownership and dependency direction

Rules: **layers may depend only downward** in the list below; an upward or sideways dependency is
forbidden. "Owns" = is the single authority for that class of operation.

| Layer | Owns | Allowed dependencies | Forbidden dependencies |
| --- | --- | --- | --- |
| Presentation (Compose) | rendering, input capture, optimistic affordance | ViewModel | Repository internals, Room directly, network client, backend |
| ViewModel / application | screen state orchestration, calling repository | Repository (public surface), domain models | Room DAOs, network client, WorkManager |
| Domain (where appropriate) | pure business rules, conflict *policy* decisions | domain models only | Android, Room, network |
| Repository | reads/writes of local note state; single writer | Room, Outbox, domain | network client (it *signals* the sync engine instead) |
| Room / local persistence | durable local state (SSOT) | SQLite only | network, WorkManager, UI |
| Sync coordinator | sync transitions, checkpoint advancement, conflict detection | Repository, Outbox DAO, network client, session layer | UI |
| Outbox | durable pending-mutation record | Room (its own table) | network, UI |
| Network API client | the **only** code that performs HTTPS | HTTP library, auth/session layer | Room, UI |
| Authentication / session layer | session validity, token lifecycle, re-auth gate | network client, secure storage | Room note tables |
| Credential integration | Credential Manager interaction (UX layer only) | Credential Manager API, auth client | Google identity, Firebase |
| Background worker (WorkManager) | scheduling + executing sync runs | sync coordinator | UI, direct HTTPS |
| Backend API (edge) | request validation, authn/authz, routing | backend services | primary DB driver directly |
| Backend services | domain logic, invariants, transaction boundaries | primary DB, object storage | client internals |
| Primary database | server-side durable state | — | — |
| Object storage | attachment binaries | — | — |

### 4.1 Critical invariant — UI never reads network

```
INVARIANT NET-1:  The UI MUST NOT depend on a network response as the canonical note state.
                  A network response MUST update local state (Room) first; the UI observes Room.
```
Status `FROZEN_ARCHITECTURE_DECISION` · Source `OFFICIAL_FACT` (S-07) + `KEEPLAB_DESIGN_INFERENCE`.

### 4.2 Who owns what (summary)

| Question | Owner |
| --- | --- |
| who owns **writes** to note state | Repository (single writer); entity write + outbox insert are one transaction |
| who owns **reads** for the UI | Room Flows (via Repository) |
| who owns **network calls** | Network API client only |
| who owns **sync transitions** | Sync coordinator (states persisted in Room) |
| who owns **session validity** | Authentication / session layer + server |
| who owns **the cursor** | server is authoritative; client persists the last cleanly-applied cursor |

---

## 5. Local source of truth

```
ROOM_AS_SSOT: FROZEN (accepted)
```
Status `FROZEN_ARCHITECTURE_DECISION` · Source `OFFICIAL_FACT` (S-07, S-08) +
`KEEPLAB_DESIGN_INFERENCE` (§3.3 of the sync blueprint).

Invariants (all `FROZEN_ARCHITECTURE_DECISION`):

1. **All normal note-UI reads flow from Room** (Flow/`StateFlow` derived from Room), never from a
   network response.
2. **A network response MUST update local state first**; the UI then observes the updated local
   state. The network layer never returns note state directly to the UI.
3. **Offline: existing notes remain readable.** Opening a note never requires the network.
4. **Local user mutations commit locally before network acknowledgement**, except explicitly
   online-only operations (§5.1). "Commit locally" = entity write + outbox insert in one
   transaction.
5. A local mutation's success does **not** depend on the server accepting it; the server
   acknowledgement only changes the entity's `sync_state`.

### 5.1 Explicitly online-only operations (exceptions)

| Operation | Why online-only | Local effect while offline |
| --- | --- | --- |
| **first sign-in / registration** | requires the backend to mint an account | no account until online |
| **account recovery / password reset / passkey re-enrolment** | server-verified | unavailable |
| **attachment binary upload** | object storage write | metadata commits locally; upload deferred |
| **attachment binary download** | object storage read | not present locally until fetched |
| **remote session revocation / account-disable acknowledgement** | server-authoritative | local session stays usable, sync paused |

Everything else (note create/edit/delete/archive/pin/colour/label/checklist item change) is
**local-first** and offline-capable. Status `FROZEN_ARCHITECTURE_DECISION`.

---

## 6. Account ownership model

KeepLab account identity is **independent of** the Google account, the Android owner user, the
benchmark Google account, and any Google Keep identity.

### 6.1 Core concepts (conceptual, no schema)

| Concept | Meaning | Owner | Status |
| --- | --- | --- | --- |
| `KeepLabUser` | a person's KeepLab account (the identity principal) | KeepLab backend | `FROZEN_ARCHITECTURE_DECISION` |
| `AccountId` | opaque, stable, server-issued identifier for a `KeepLabUser`; never a Google id | KeepLab backend | `FROZEN_ARCHITECTURE_DECISION` |
| `DeviceSession` | one signed-in app instance's session record (device-labelled, individually revocable) | KeepLab backend, mirrored locally | `FROZEN_ARCHITECTURE_DECISION` |
| `Credential` | a passkey (public key) or a password verifier bound to the account | KeepLab backend stores verifier/public key; device credential provider stores the private key/secret | `FROZEN_ARCHITECTURE_DECISION` |
| `ServerSession` | the server-side authority for session validity + revocation | KeepLab backend | `FROZEN_ARCHITECTURE_DECISION` |
| `SyncAccountScope` | the `account_id` partition under which all synced entities are scoped; the server derives the effective scope from the authenticated session | KeepLab backend + local tables | `FROZEN_ARCHITECTURE_DECISION` |

### 6.2 Independence invariants

```
INVARIANT ID-1:  KeepLab account identity MUST NOT depend on Google, Firebase, the Android owner
                 user, or the benchmark Google account.
INVARIANT ID-2:  One KeepLabUser MAY have multiple DeviceSessions.
INVARIANT ID-3:  All synced data is owned per-account and MUST be partitioned by account_id.
INVARIANT ID-4:  A DeviceSession MAY be revoked individually; all sessions MAY be revoked at once.
INVARIANT ID-5:  A local entity MAY carry a NULL account_id ONLY while it is `LOCAL_ONLY`; an entity in
                 any remote-sync state (`SYNC_PENDING` / `SYNCING` / `SYNCED` / `SYNC_FAILED` /
                 `CONFLICT` / `DELETE_PENDING`) MUST carry a non-NULL account_id. No synthetic or
                 placeholder account row is created before sign-in to satisfy a foreign key.
INVARIANT ID-6:  CLIENT_ACCOUNT_ID_IS_NOT_AUTHORITY. The server derives the effective account scope
                 from the authenticated session/access credential; sending `account_id` = <other
                 account> MUST NOT grant another account's data. A future multi-account/org mode may
                 transmit a selected scope, but the server MUST validate membership/authorization
                 against the authenticated session.
```
Status `FROZEN_ARCHITECTURE_DECISION` · Source `HUMAN_ARCHITECTURE_DECISION` +
`KEEPLAB_DESIGN_INFERENCE`.

### 6.3 Multi-KeepLab-account in one app instance

```
MULTI_ACCOUNT_IN_ONE_APP_INSTANCE:
  PHASE_1            = SINGLE_ACTIVE_ACCOUNT_PHASE1    (HUMAN_APPROVED 2026-10-06, D-03)
  MULTI_ACCOUNT      = FUTURE_EXTENSION
  FINAL_PRODUCT_SCOPE= SINGLE_ACTIVE_ACCOUNT_PHASE1    (no multi-account UI now)
```
Status `HUMAN_APPROVED` (2026-10-06, D-03) · Source `HUMAN_PROJECT_OWNER_APPROVAL` +
`KEEPLAB_DESIGN_INFERENCE`.

Google Keep is multi-account capable (S-22, S-60, S-61) — this is `PUBLIC_KEEP_BEHAVIOR` and is
**not** evidence that KeepLab must be. KeepLab must not infer Google-style multi-account from the
reference app. Whether KeepLab *ever* supports multiple accounts in one app instance is a human
product decision.

---

## 7. Authentication method status

```
AUTH_METHOD: HUMAN_DECISION_PENDING
```
Status `HUMAN_DECISION_PENDING` · Source `KEEPLAB_DESIGN_INFERENCE` (recommended shortlist, not a
decision).

### 7.1 Recommended shortlist (ordering = research recommendation, not a decision)

| # | Option | Trade-offs (summary) |
| --- | --- | --- |
| A | **email + password**, optional passkey upgrade | lowest first cost; natural recovery channel; weakest link is the password |
| B | **passkey-first**, email / recovery-code bootstrap | best security end-state; higher build cost; recovery is the hard part |
| C | **phone + verification code** | viable fallback; SMS cost/abuse are the real constraints |

### 7.2 Explicitly rejected as a default

| Rejected | Reason |
| --- | --- |
| **Google OAuth / Sign in with Google** | `FORBIDDEN_UNLESS_HUMAN_APPROVED` |
| **Firebase Authentication** | `FORBIDDEN_UNLESS_HUMAN_APPROVED` |
| **username + password only, no recovery channel** | no recovery path |
| **raw resource-owner-password OAuth flow** | being removed by RFC 9700 / OAuth 2.1 (S-30) |

No auth dependency was added. No auth code exists. Status `NON_GOAL` for this task.

---

## 8. Credential Manager boundary

```
CREDENTIAL_MANAGER_ROLE: ANDROID_CREDENTIAL_UX_LAYER
KEEPLAB_IDENTITY_AUTHORITY: KEEPLAB_BACKEND
```
Status `FROZEN_ARCHITECTURE_DECISION` · Source `OFFICIAL_FACT` (S-01, S-04, S-05, S-33) +
`HUMAN_ARCHITECTURE_DECISION`.

### 8.1 Architecture

```
Android Credential Manager UI   (bottom sheet: passkey / password)
        │  credential request / response  — UX layer only
        ▼
KeepLab credential  (passkey private key on device / username+password)
        │
        ▼
KeepLab Auth Client  (client-side credential exchange)
        │  HTTPS
        ▼
KeepLab Backend  (relying-party server: challenge, public-key store, verification, sessions)
        │
        ▼
KeepLab account  (KeepLab-owned identity)
```

### 8.2 What Credential Manager may and may not be used for

| MAY | MUST NOT imply |
| --- | --- |
| password credential UX (store/retrieve for KeepLab's own account) | Google account identity |
| passkey credential UX (RP = KeepLab backend) | Sign in with Google |
| inline bottom-sheet credential chooser | Google OAuth |
| optional Restore Credentials convenience | Firebase / Google Identity Services |

### 8.3 Responsibility split

| Party | Responsibility |
| --- | --- |
| **Platform (Credential Manager)** | credential chooser UI, credential storage in the platform credential provider, passkey creation/assertion transport, restore-on-new-device plumbing |
| **KeepLab application** | decide which credential types KeepLab accepts; drive the credential exchange; own session persistence; own the re-auth gate; never enable the Google federated provider |
| **KeepLab backend** | be the relying-party server: issue challenges, store public keys, verify assertions, validate passwords, mint/rotate/revoke sessions, own all recovery semantics |

The two paths below share a UI *container* but are different trust relationships:

```
KeepLab credential  → KeepLab Auth Client → KeepLab Backend → KeepLab account   [APPROVED DIRECTION]
Sign in with Google → Google identity federation                              [FORBIDDEN_UNLESS_HUMAN_APPROVED]
```
Status `FROZEN_ARCHITECTURE_DECISION` · Source `OFFICIAL_FACT` (S-01, S-04, S-05).

---

## 9. Session architecture

Formal principles (principles are frozen; exact values are not):

| # | Principle | Status |
| --- | --- | --- |
| 1 | short-lived **access** credential + longer-lived **refresh/session** credential | `RECOMMENDED_DEFAULT` |
| 2 | **rotate** the refresh credential on every use; invalidate the previous one; rotation is **single-use + RETRY_SAFE** (`refresh_request_id`; a lost response after a successful rotation recovers the same logical result in a bounded window) | `RECOMMENDED_DEFAULT` |
| 3 | reuse of a rotated credential is a theft signal → revoke the family | `RECOMMENDED_DEFAULT` |
| 4 | server-side **revocation**: sign-out, per-session revoke, all-session revoke, admin disable | `FROZEN_ARCHITECTURE_DECISION` |
| 5 | **device/session list** with per-session revoke | `RECOMMENDED_DEFAULT` |
| 6 | secure **app-private** storage for refresh material; Android **Keystore** where appropriate | `FROZEN_ARCHITECTURE_DECISION` |
| 7 | never log session material | `FROZEN_ARCHITECTURE_DECISION` |
| 8 | offline sessions are a **first-class case** (see §10) | `FROZEN_ARCHITECTURE_DECISION` |

Source: RFC 9700 / OAuth 2.1 (S-29, S-30) + `KEEP-AUTH-REFERENCE-BLUEPRINT.md` §5.

```
TOKEN_FORMAT: HUMAN_IMPLEMENTATION_DECISION_PENDING
```
No exact token format (JWT / opaque / PASETO) is frozen. No token code exists.

### 9.1 Critical session invariant

```
INVARIANT SESS-1:  An offline failure to refresh MUST NOT erase notes, the outbox, or pending
                   mutations. Only an authoritative server "session invalid" response (or an
                   explicit human sign-out) may move the app toward account-exit semantics —
                   and even then local-data disposition is explicit (§6/§12 of the task →
                   HUMAN_DECISIONS doc).
```
Status `FROZEN_ARCHITECTURE_DECISION` · Source `KEEPLAB_DESIGN_INFERENCE`.

---

## 10. Offline session model

The governing distinction:

```
NO_NETWORK  ≠  AUTH_INVALID
```
Status `FROZEN_ARCHITECTURE_DECISION` · Source `KEEPLAB_DESIGN_INFERENCE`.

| Situation | Classification | Expected behaviour |
| --- | --- | --- |
| network disappears while signed in | `NO_NETWORK` | app fully usable on local data; sync paused; no destructive action |
| access credential expires while offline | `NO_NETWORK` (refresh not yet attempted) | stay usable; attempt refresh on reconnect |
| refresh impossible due to network | `NO_NETWORK` | keep session material; retry later; **never** treat as sign-out |
| server explicitly rejects the session | `AUTH_INVALID` | transition to `AUTH_EXPIRED` → `REAUTH_REQUIRED`; pause sync; keep all local data + outbox |
| user signs out intentionally | explicit human action | enter sign-out semantics (§31) — local-data disposition is `HUMAN_DECISION_PENDING` |
| account disabled remotely | `AUTH_INVALID` (authoritative) | sync paused; non-destructive gate; local data disposition explicit |

Invariants:

```
INVARIANT OFF-1:  NO_NETWORK MUST NOT be interpreted as sign-out.
INVARIANT OFF-2:  Only authoritative server invalidation OR explicit human sign-out should
                  transition into destructive account-exit semantics.
INVARIANT OFF-3:  Local data is never silently deleted, in any transition.
```
Status `FROZEN_ARCHITECTURE_DECISION` · Source `KEEPLAB_DESIGN_INFERENCE` + (§11).

---

## 11. Auth UX state machine (formalized)

The full state table (entry, exit, persistent/transient, UI, local-note accessibility, sync,
network, security) is in `KEEPLAB-AUTH-SYNC-STATE-MODEL.md` §1. The canonical state set:

```
SIGNED_OUT · AUTHENTICATING · SIGNED_IN · AUTH_EXPIRED · REAUTH_REQUIRED · NETWORK_ERROR ·
INVALID_CREDENTIAL · ACCOUNT_DISABLED · SERVER_ERROR ·
OFFLINE_WITH_VALID_LOCAL_SESSION · OFFLINE_WITHOUT_VALID_SESSION
```
Status `FROZEN_ARCHITECTURE_DECISION` (state set) · Source `OFFICIAL_FACT` (S-06) +
`KEEPLAB_DESIGN_INFERENCE`.

```
CRITICAL REQUIREMENT AUTH-1:  AUTH FAILURE MUST NOT DELETE LOCAL NOTES.
```
Status `FROZEN_ARCHITECTURE_DECISION` · Source `KEEPLAB_DESIGN_INFERENCE`.

---

## 12. Sync state model (formalized)

Per-entity states (full table in `KEEPLAB-AUTH-SYNC-STATE-MODEL.md` §2):

```
LOCAL_ONLY (optional) · SYNC_PENDING · SYNCING · SYNCED · SYNC_FAILED · CONFLICT · DELETE_PENDING
session-level: AUTH_REQUIRED
```
Status `FROZEN_ARCHITECTURE_DECISION` (minimal model accepted).

Folded away (with reason):

| Considered | Verdict | Reason |
| --- | --- | --- |
| `DIRTY` | → `SYNC_PENDING` | duplicate of a pending local mutation |
| `RETRY_WAIT` | → `SYNC_PENDING` + attempt metadata | WorkManager owns timing; not a distinct persisted state |
| `TOMBSTONE` | → a **field** (`deleted_at`) | a record shape, not a UI/sync state |
| `LOCAL_ONLY` | kept, **required** | D-02 `HUMAN_APPROVED` 2026-10-06 (`YES_LOCAL_ONLY_BEFORE_SIGNIN`): KeepLab permits notes before sign-in — `account_id = NULL`, no synthetic account row |

```
CRITICAL REQUIREMENT SYNC-1:  AUTH_REQUIRED MUST NOT delete pending outbox rows.
```
Status `FROZEN_ARCHITECTURE_DECISION` · Source `KEEPLAB_DESIGN_INFERENCE`.

---

## 13. Outbox model

```
OUTBOX_MODEL: OUTBOX_TABLE + PER_ENTITY_SYNC_STATE (hybrid)   FROZEN
```
Status `FROZEN_ARCHITECTURE_DECISION` · Source `KEEPLAB_DESIGN_INFERENCE` (R1) + S-46/S-50/S-51.

Outbox row fields (conceptual): `mutation_id` · `entity_id` · `account_id` · `op_type` ·
`payload` · `base_revision` · `attempt_count` · `last_error` · `created_at` · `coalesce_key`.
Full field table: `KEEPLAB-AUTH-SYNC-DATA-MODEL.md` §3.

Operation types: `CREATE` · `UPDATE` · `DELETE` · `ARCHIVE` · `UNARCHIVE` · `PIN` · `UNPIN` ·
`SET_COLOR` · `LABEL_ADD` · `LABEL_REMOVE` · `CHECKLIST_PUT` · `ATTACHMENT_ADD`.
Status `FROZEN_ARCHITECTURE_DECISION`; granularity is deliberately **field-class**, not
per-keystroke. `CHECKLIST_PUT` carries a captured item set; a later `CHECKLIST_ITEM_*` refinement
is `FUTURE_EXTENSION` (see DATA-MODEL §3.2).

Invariants (all `FROZEN_ARCHITECTURE_DECISION`):

```
INVARIANT OUT-1:  An entity mutation and its outbox insertion MUST be ONE LOCAL TRANSACTION.
INVARIANT OUT-2:  mutation_id MUST be the idempotency key (server tolerates duplicates).
INVARIANT OUT-3:  An outbox row MUST NOT be removed until confirmed success OR explicit
                  permanent-failure handling.
INVARIANT OUT-4:  The pushed payload is the CAPTURED payload, not the live DB row.
INVARIANT OUT-5:  Coalesce per (entity_id, op-class); a burst of edits yields one push.
```
Source `KEEPLAB_DESIGN_INFERENCE` + S-46/S-50/S-51.

---

## 14. Client IDs and server IDs

```
CLIENT_GENERATED_UUID: FROZEN
```
Status `FROZEN_ARCHITECTURE_DECISION` · Source `KEEPLAB_DESIGN_INFERENCE` (R2) + S-47/S-51.

| Entity | Identifier | Generation | Lifecycle |
| --- | --- | --- | --- |
| note | `note_id` | client UUID at creation | stable forever; server adopts the same id |
| checklist item | `item_id` | client UUID at item creation | stable; enables item-level merge |
| label | `label_id` | client UUID at creation | stable |
| attachment | `attachment_id` | client UUID at creation | stable; content hash separate |
| mutation | `mutation_id` | client UUID at enqueue | idempotency key; never reused |

Invariants:

```
INVARIANT IDL-1:  Offline-created entities MUST be immediately referenceable without the server.
INVARIANT IDL-2:  Local creation MUST NOT require a server-generated primary key.
INVARIANT IDL-3:  The server MUST accept a client-generated id and MUST NOT rename it.
INVARIANT IDL-4:  The client UUID is introduced ADDITIVELY. The existing local primary key MAY remain an
                  implementation-local identity during migration; replacing it is a SEPARATE migration
                  decision and MUST NOT be required for first network enablement (A1 is additive).
```
Status `FROZEN_ARCHITECTURE_DECISION`.

---

## 15. Revision / optimistic concurrency

```
SERVER_REVISION + BASE_REVISION: FROZEN
```
Status `FROZEN_ARCHITECTURE_DECISION` · Source `KEEPLAB_DESIGN_INFERENCE` (R3) + S-51 + S-17
(`PUBLIC_KEEP_BEHAVIOR`, precedent for a user-visible conflict surface only).

- The server maintains a **monotonic `server_revision`** per entity.
- For a revision-sensitive mutation the client sends the `base_revision` it edited against.
- On a **stale** conflicting mutation the server returns **`409` + the current server
  representation and revision**.

| Condition | Definition | Action |
| --- | --- | --- |
| fast-forward | only one side changed since `base_revision` | apply the change; advance revision |
| conflict | both sides changed a conflict-sensitive field | `409`; client enters `CONFLICT`; user resolves |
| retry | transient server/network failure | retry via WorkManager backoff (no state change) |

```
INVARIANT REV-1:  The server MUST NOT silently overwrite important text on a stale mutation.
```
Status `FROZEN_ARCHITECTURE_DECISION`.

---

## 16. Delta sync

```
DELTA_CURSOR: FROZEN (monotonic server-side SYNC_CURSOR)
```
Status `FROZEN_ARCHITECTURE_DECISION` · Source `KEEPLAB_DESIGN_INFERENCE` (R3) + S-51.

Conceptual pull: `GET /sync/changes?since=<cursor>`.

| Property | Definition |
| --- | --- |
| SERVER CHANGE CURSOR | opaque, server-issued, **monotonic**, **account-scoped** position in the account's ordered change stream; every accepted server write advances it |
| CLIENT CHECKPOINT | the last server cursor that **this client** has successfully and completely applied (a client-side fact) |
| ordering | changes are ordered by (cursor) ascending; the cursor totally orders server changes within the account |
| checkpoint advancement | only after a **clean** apply of every returned delta |
| failure behaviour | a failed/conflicted delta does **not** advance the checkpoint; the batch is retried |
| partial apply | allowed only if the protocol explicitly guarantees replay safety; otherwise all-or-nothing per batch |
| server head | a server MAY expose `latest_available_cursor`; it does not thereby know a client's applied checkpoint |
| `GET /sync/checkpoint` | **optional / bootstrap** only (server-head semantics) — it is not part of the conceptual required set, and it never reports the client's checkpoint |

```
INVARIANT CUR-1:  The client checkpoint MUST NOT advance past an unhandled failed/conflicted
                  delta unless the protocol explicitly guarantees safety.
INVARIANT CUR-2:  The SERVER CHANGE CURSOR and the CLIENT CHECKPOINT MUST NOT be conflated; the cursor
                  is ACCOUNT-SCOPED (or otherwise opaque and authorization-safe) and clients MUST NOT
                  compare cursors across accounts.
```
Status `FROZEN_ARCHITECTURE_DECISION` · Source `KEEPLAB_DESIGN_INFERENCE` + S-51.

---

## 17. Sync topology

```
SYNC_TOPOLOGY: HYBRID (push local mutations; pull remote changes)
```
Status `FROZEN_ARCHITECTURE_DECISION` · Source `OFFICIAL_FACT` (S-08 taxonomy) +
`KEEPLAB_DESIGN_INFERENCE`.

| Direction | Mechanism |
| --- | --- |
| **push** | outbox drain of local mutations (idempotent by `mutation_id`) |
| **pull** | cursor-based delta pull `GET /sync/changes?since=<cursor>` |

Triggers:

| Trigger | What it starts |
| --- | --- |
| app foreground / open | a push pass then a delta pull |
| local write | enqueue a push pass (constrained) |
| network reconnect (`NetworkCallback`) | a full sync pass |
| successful auth refresh | a sync pass |
| manual retry (user) | a push pass, resetting attempts for FAILED rows |
| periodic safety-net worker | a full sync pass (fallback only) |

```
WorkManager periodic work is a FALLBACK, never a real-time guarantee.
Exact Google Keep sync cadence is NOT claimed (it is not public — UNKNOWN_PRIVATE).
```
Status `FROZEN_ARCHITECTURE_DECISION` / `NON_GOAL` (cadence parity).

---

## 18. WorkManager policy

```
BACKGROUND_ENGINE: WORKMANAGER
SYNC_WORKER_MODEL: SINGLE_UNIQUE_PIPELINE
```
Status `FROZEN_ARCHITECTURE_DECISION` · Source `OFFICIAL_FACT` (S-09..S-12, S-14) +
`KEEPLAB_DESIGN_INFERENCE` + S-46/S-47/S-49.

| Property | Decision |
| --- | --- |
| worker type | `CoroutineWorker` |
| unique work name | `note_sync` (one pipeline for manual + background + reconnect) |
| enqueue policy | **NOT frozen at API-choice level.** The exact `ExistingWorkPolicy` for the one unique `note_sync` pipeline is an **`A4_IMPLEMENTATION_DECISION`**, selected by deterministic tests against the actual WorkManager version. Candidates include `KEEP` + drain-until-stable/recheck, or a serialized append/rerun, or an equivalent that satisfies the frozen invariants below. Do **not** freeze `KEEP` vs `APPEND_OR_REPLACE` speculatively. |
| constraint | `NetworkType.CONNECTED` |
| backoff | `EXPONENTIAL` (WorkManager's 10 s minimum / 30 s default governs) |
| retries | **bounded**; on exhaustion → `SYNC_FAILED`, surfaced with a manual retry |
| periodic safety net | a low-frequency `PeriodicWorkRequest` (≥15 min, system-batched) |

Explicitly prevented (anti-patterns from research):

```
FORBIDDEN: multiple simultaneous sync workers
FORBIDDEN: one unique worker per individual keystroke
FORBIDDEN: unbounded unique-work names
FORBIDDEN: treating getWorkInfosByTagFlow() as an event stream (S-48)
```
Status `FROZEN_ARCHITECTURE_DECISION` · Source S-48, S-49.

Frozen scheduling invariants (independent of the API choice):

```
INVARIANT WM-1:  ONE ACTIVE SYNC EXECUTOR MAX.
INVARIANT WM-2:  A TRIGGER ARRIVING WHILE THE WORKER IS RUNNING MUST NOT BE LOST.
INVARIANT WM-3:  THE WORKER MUST DRAIN TO A STABLE POINT OR GUARANTEE A FOLLOW-UP RUN.
INVARIANT WM-4:  OUTBOX DURABILITY IS THE SOURCE OF WORK — not the scheduling event itself.
```
Status `FROZEN_ARCHITECTURE_DECISION` · Source S-46/S-47/S-49 + corrective task §9.
The unique logical pipeline name stays `note_sync`.

Ownership: the sync coordinator owns the worker's logic; the worker owns only scheduling +
`Result` reporting. Enqueue is centralised in one place so no feature can fork the pipeline.

---

## 19. Connectivity

Three distinct conditions — never conflated:

```
NETWORK_AVAILABLE  ≠  BACKEND_REACHABLE  ≠  AUTH_VALID
```
Status `FROZEN_ARCHITECTURE_DECISION` · Source `OFFICIAL_FACT` (S-12) + `KEEPLAB_DESIGN_INFERENCE`.

| Condition | Signal | Meaning | Transition on failure |
| --- | --- | --- | --- |
| `NETWORK_AVAILABLE` | `ConnectivityManager` / `NetworkCallback` | a network may exist | lose it → sync passes are deferred, not failed |
| `BACKEND_REACHABLE` | a successful API round-trip | KeepLab backend answered | reachability loss → transient error / retry, **not** auth error |
| `AUTH_VALID` | server accepted the session | credentials valid | server rejects → `AUTH_EXPIRED` (authoritative) |

`NetworkCallback` availability MAY trigger a sync opportunity, but **does not prove** backend
reachability or auth validity.

---

## 20. Conflict policy (per field)

```
CONFLICT_POLICY: PER_FIELD     FROZEN
```
Status `FROZEN_ARCHITECTURE_DECISION` · Source `KEEPLAB_DESIGN_INFERENCE` + S-08 (LWW is the only
officially documented strategy) + S-17 (`PUBLIC_KEEP_BEHAVIOR`, a user-visible chooser exists).

| Field / capability | Policy |
| --- | --- |
| `title`, `body` | server revision check; both sides changed → `CONFLICT`, user resolves (**keep local** / **keep server** / **keep both**); one side changed → fast-forward. **`KEEP_BOTH` creates a NEW logical note with a NEW client-generated UUID, enqueued as `CREATE` against the same account scope — the original entity id is never reused.** (This is KeepLab's independent rule; no Google Keep private behaviour is claimed.) |
| checklist items | **item-level merge by stable item id**: union of adds; deletes by id; per-item resolution uses the **SERVER-ASSIGNED ordering** (`server_revision` / server change sequence / server `server_updated_at`) — never an unsynchronized client wall clock |
| labels | **operation-based add/remove** (NOT pure set union) — concurrent `LABEL_ADD` both survive; membership changes are ordered by the **server-accepted revision / change sequence**, so a later accepted `LABEL_REMOVE` is not resurrected by a union and a later intentional `LABEL_ADD` may re-add |
| archive / pin / colour | **LWW on server revision** (latest accepted revision) |
| attachments | **append-only / content-addressed**; concurrent adds both survive; no merge |
| delete vs concurrent edit | **explicit conflict** surfaced to the user |

**Refinement over the raw research (recorded):** the offline-sync blueprint recommended "set
union" for labels. That is insufficient when a concurrent **remove** must be preserved: a union
would re-add a label the user removed. This spec therefore refines labels to **operation-based
add/remove semantics** carried by `LABEL_ADD` / `LABEL_REMOVE` outbox ops. Status
`FROZEN_ARCHITECTURE_DECISION` · Source `KEEPLAB_DESIGN_INFERENCE` (rationale in DECISION-REGISTER
SYNC-DEC-012/017).

Explicitly **not** adopted for Phase 1 (`NON_GOAL`):

```
FORBIDDEN PHASE-1:  CRDT for note bodies
FORBIDDEN PHASE-1:  automatic three-way text merge
FORBIDDEN PHASE-1:  client-wins-everywhere
```
Basis: no Phase-1 evidence of need at single-user, low-concurrency scale (S-08, S-46, S-50).

---

## 21. Delete / trash / tombstone

```
TOMBSTONE_DELETE: FROZEN (deleted_at field; never a hard local delete of a synced row)
```
Status `FROZEN_ARCHITECTURE_DECISION` · Source `KEEPLAB_DESIGN_INFERENCE` (R4) + S-21
(`PUBLIC_KEEP_BEHAVIOR`) + S-50.

**TRASH ≠ SYNC TOMBSTONE** (two distinct concepts — do not conflate):

```
TRASH STATE            : user-visible, RECOVERABLE product state (`trashed` / `trashed_at`)
SYNC TOMBSTONE         : PROTOCOL-level record of FINAL deletion for convergence /
                         anti-resurrection (`deleted_at`)
```

Lifecycle:

```
product Trash (recoverable; trashed/trashed_at; NOT a tombstone)
        │  user empties Trash / final delete intent
        ▼
final delete intent  →  DELETE_PENDING (hidden from UI)
                     →  server sync tombstone (deleted_at set; server_revision advances)
                     →  tombstone retention / compaction
                     →  hard delete
```

```
TRASH_RETENTION: HUMAN_DECISION_PENDING
REFERENCE_DEFAULT_CANDIDATE: 7 days   (PUBLIC_REFERENCE_ONLY — Google Keep's public Trash window)
```
Google Keep publicly exposes a 7-day Trash (S-21), but KeepLab retention is a **product
decision**, not automatically Google-derived. 7 days is listed only as a `REFERENCE_DEFAULT_CANDIDATE`.

```
SYNC_TOMBSTONE_RETENTION_OR_COMPACTION: separate PROTOCOL-CORRECTNESS concern
                                        (NOT the product Trash duration; NOT automatically 7 days)
```
Its governing rule is DEL-2 below; the mechanism (retention horizon / generation-snapshot reset /
cursor-compaction protocol / equivalent) is `IMPLEMENTATION_DECISION_PENDING`. No final duration is
selected here.

```
INVARIANT TRASH-1: Moving a note to Trash MUST NOT set `deleted_at`; an item merely in Trash MUST NOT
                   be turned into a permanently-deleted sync tombstone.
INVARIANT DEL-1:  A server deletion MUST NOT resurrect from a stale client.
                  (A stale client's pull must not recreate a tombstoned entity; a stale push
                   against a tombstoned entity is an explicit conflict.)
INVARIANT DEL-2:  A stale SUPPORTED client MUST NOT be able to resurrect a permanently deleted entity.
                  Tombstone GC may occur only when the protocol can prove old clients cannot legally
                  replay pre-deletion state (retention horizon / generation-snapshot reset /
                  cursor-compaction protocol / equivalent safe mechanism).
```
Status `FROZEN_ARCHITECTURE_DECISION` · Source S-50 + corrective task §3/§4.

---

## 22. Attachments

Status `RECOMMENDED_DEFAULT` (design) / `FUTURE_EXTENSION` (implementation phase).

Two separated commits — **note metadata** and **attachment binary**:

```
INVARIANT ATT-1:  A local note MUST NOT block merely because a binary upload is pending.
```
Status `FROZEN_ARCHITECTURE_DECISION` · Source `KEEPLAB_DESIGN_INFERENCE` + S-18 (reload
re-download must never destroy pending local mutations).

Attachment metadata (conceptual): `attachment_id` (client UUID) · `note_id` · `account_id` ·
local URI/path · **content hash** · size · MIME type · upload state · remote object id ·
retry state. See DATA-MODEL §5.

| Property | Decision |
| --- | --- |
| semantics | content-addressed, **append-only**; no merge |
| upload | deferred; unmetered-network preference; resumable; separate outbox op (`ATTACHMENT_ADD`) |
| download | authorized per account; non-guessable object ids |
| object storage | future backend infrastructure; **no provider chosen now** |
| failing/abandoned uploads | retried; abandoned binary → orphan candidate (see RISK-ATTACH-001) |

---

## 23. Backend service model (technology-agnostic)

Status `RECOMMENDED_DEFAULT` (service boundary) · Source `KEEPLAB_DESIGN_INFERENCE` +
`OFFICIAL_FACT` (S-29..S-31, standards).

```
Client ──HTTPS──▶ API gateway (authn/authz, rate limiting, routing)
                    │
      ┌─────────────┼───────────────┬───────────────┬──────────────────┐
      ▼             ▼               ▼               ▼                  ▼
   Auth API     User service    Session service  Notes service     Sync service
   register      profile         issue/rotate     CRUD + revisions  mutation push
   login         settings        revoke           labels/checklist  delta pull
   verify        account ops                      attachments meta  checkpoint
   reset         disable
      │             │               │               │                  │
      └─────────────┴───────────────┴───────┬───────┴──────────────────┘
                                           ▼
                                   Primary database
                    (users, sessions, notes, revisions, change log,
                     labels, checklist items, mutation-id dedupe)
                                           │
                                   Object storage (attachment binaries)
                                           │
                              (optional, later) Notification/push layer   FUTURE_EXTENSION
```

### 23.1 Backend stack — chosen by human decision (2026-10-06)

```
CLOUD_PROVIDER:     TENCENT_CLOUD           (HUMAN_APPROVED 2026-10-06, D-08 · PORTABLE_DOCKER)
BACKEND_LANGUAGE:   KOTLIN + KTOR           (HUMAN_APPROVED 2026-10-06, D-07)
DATABASE_VENDOR:    POSTGRESQL              (HUMAN_APPROVED 2026-10-06, D-09)
```
Status `HUMAN_APPROVED` (2026-10-06) · Source `HUMAN_PROJECT_OWNER_APPROVAL` (D-07/D-08/D-09).

Interpretation limits (unchanged by A0): Tencent Cloud is the **initial deployment target**, but
application/service packaging must avoid unnecessary proprietary coupling and the backend runtime
must stay container-portable where practical. **Not** assumed: Firebase, GCP, AWS-specific
architecture, vendor-exclusive application APIs. Object-storage product, load-balancer product and
managed-vs-container PostgreSQL deployment remain **A2 implementation-level decisions**.

Still `HUMAN_DECISION_PENDING`: auth method (D-01) · sign-out local-data policy (D-04) ·
account-deletion retention (D-05) · trash retention (D-06) · token format (D-10) · push provider
(D-11) · collaboration scope (D-12) · attachment limits (D-13) · formal spec package location
(D-14). **No stack component was created, provisioned or coded.**

---

## 24. Conceptual API contract

Full semantics in `KEEPLAB-AUTH-SYNC-API-CONTRACT.md`. These are **architecture contract
examples**, not final route names.

| Purpose | Conceptual endpoint |
| --- | --- |
| Register | `POST /auth/register` |
| Login (password) | `POST /auth/login` |
| Passkey challenge/verify | `POST /auth/passkey/challenge`, `POST /auth/passkey/verify` |
| Refresh (rotating) | `POST /auth/refresh` |
| Logout / revoke | `POST /auth/logout`, `POST /auth/sessions/{id}/revoke` |
| Notes CRUD | `GET /notes/{id}`, `POST /notes`, `PATCH /notes/{id}`, `DELETE /notes/{id}` |
| Mutation push (idempotent) | `POST /sync/mutations` |
| Delta pull | `GET /sync/changes?since=<cursor>` |
| Checkpoint (optional / bootstrap) | `GET /sync/checkpoint` — server-head semantics only; it never reports the client's applied checkpoint |
| Attachment upload/download | `POST /attachments`, `GET /attachments/{id}` |

Each endpoint's required identity context, idempotency behaviour and revision behaviour are
specified in the API-CONTRACT doc. Status `RECOMMENDED_DEFAULT` (contract shape);
`HUMAN_DECISION_PENDING` for final route names.

---

## 25. API error taxonomy (stable, conceptual)

Full server→repository→sync-state→UI mapping in `KEEPLAB-AUTH-SYNC-API-CONTRACT.md` §4.

```
AUTH_REQUIRED · AUTH_EXPIRED · INVALID_CREDENTIAL · ACCOUNT_DISABLED · FORBIDDEN · NOT_FOUND ·
REVISION_CONFLICT · RATE_LIMITED · VALIDATION_ERROR · PAYLOAD_TOO_LARGE ·
NETWORK_UNAVAILABLE · SERVER_TEMPORARY · SERVER_UNCLASSIFIED · SERVER_PERMANENT ·
SYNC_CURSOR_INVALID · ATTACHMENT_FAILED
```
Status `FROZEN_ARCHITECTURE_DECISION` (taxonomy) · Source `KEEPLAB_DESIGN_INFERENCE`.

```
INVARIANT ERR-1:  Raw server exceptions MUST NOT be exposed directly to the UI.
INVARIANT ERR-2:  Unknown/unclassified 5xx is RETRYABLE with bounded attempts — a generic 5xx is NOT a
                  permanent classification by default; permanent failures carry a stable
                  semantic/application error classification. Nothing retries forever.
INVARIANT ERR-3:  `NOT_FOUND` (404) MUST NOT automatically delete a local row. Only a
                  server-authoritative tombstone/deletion or a documented reconciliation response may
                  cause automatic local deletion; otherwise → `RECONCILE_REQUIRED`.
```
Status `FROZEN_ARCHITECTURE_DECISION` · Source `KEEPLAB_DESIGN_INFERENCE` + corrective task §12.

---

## 26. Server invariants

| # | Invariant | Status |
| --- | --- | --- |
| 1 | mutations idempotent by `mutation_id` (duplicate → success, no double-apply) | `FROZEN_ARCHITECTURE_DECISION` |
| 2 | monotonic entity `server_revision` | `FROZEN_ARCHITECTURE_DECISION` |
| 3 | monotonic delta cursor | `FROZEN_ARCHITECTURE_DECISION` |
| 4 | every read/write authorized per account | `FROZEN_ARCHITECTURE_DECISION` |
| 5 | deletes tombstoned server-side with a retention window | `FROZEN_ARCHITECTURE_DECISION` |
| 6 | attachment authorization per account on every fetch | `FROZEN_ARCHITECTURE_DECISION` |
| 7 | refresh/session revocation | `FROZEN_ARCHITECTURE_DECISION` |
| 8 | explicit transaction boundaries | `FROZEN_ARCHITECTURE_DECISION` |

Atomicity requirement (one consistency boundary server-side):

```
mutation_id dedupe record/claim  +  mutation apply  +  revision increment  +  change-log append
                                                                      ==  ONE TRANSACTION
```
Otherwise a crash between them would either double-apply a mutation, record an apply without its
dedupe key (so a retry re-applies it), or lose a delta from the pull stream. Source
`KEEPLAB_DESIGN_INFERENCE` + S-51 + corrective task §8.

---

## 27. Local database conceptual model

Full table/field detail in `KEEPLAB-AUTH-SYNC-DATA-MODEL.md`. Conceptual tables to evaluate:

```
accounts · notes · labels · note_labels · checklist_items · attachments ·
outbox_mutations · sync_checkpoints · conflicts · (optional) sessions_metadata
```
Status `FROZEN_ARCHITECTURE_DECISION` (table set). No Room migration is generated and no
production schema is modified by this task (`NON_GOAL`).

---

## 28. Multi-account data isolation

```
RECOMMENDATION: account_id SHOULD exist in local tables from the FIRST networked implementation.
```
Status `RECOMMENDED_DEFAULT` · Source `KEEPLAB_DESIGN_INFERENCE`.

Rationale: even if Phase 1 supports only one active account, introducing `account_id` later would
force a schema migration and a data-backfill on every user's device. Adding it at the first
networked implementation is cheap and future-proofs multi-account. The column is **nullable** — NULL
is legal only while an entity is `LOCAL_ONLY`. Not implemented here.

```
INVARIANT ISO-1:  Every entity in a remote-sync state carries an account_id; a read/write MUST be
                  scoped to the active account. Cross-account local leakage is a defect (RISK-DATA-001).
INVARIANT ISO-1b: account_id MAY be NULL only while the entity is LOCAL_ONLY; it MUST NOT be NULL in
                  any remote-sync state (ID-5).
INVARIANT ISO-4:  CLIENT_ACCOUNT_ID_IS_NOT_AUTHORITY (ID-6) — the client-supplied account_id is a
                  scope hint, never authorization; the server derives scope from the authenticated
                  session.
```
Status `FROZEN_ARCHITECTURE_DECISION`.

---

## 29. Sign-out semantics

Sign-out is an explicit human action and is **distinct** from auth failure and from account
deletion.

```
SIGN_OUT_LOCAL_DATA_POLICY: HUMAN_DECISION_PENDING
```
Options (none chosen; destructive behaviour is never silent):

| Option | Description |
| --- | --- |
| A | **keep the app-private local cache** (recommended safe default, non-destructive) — notes stay readable; sync resumes on re-sign-in |
| B | remove account-local data **after explicit confirmation** |
| C | local-only export / migration path before removal |

```
RECOMMENDED_SAFE_DEFAULT: A (keep the app-private local cache), with an explicit, separate
                          "remove this account's data from this device" action.

APPLICATION_LEVEL_DATABASE_ENCRYPTION: SECURITY_IMPLEMENTATION_DECISION
                                       (HUMAN_DECISION_PENDING if the project requires it)
```
Status `RECOMMENDED_DEFAULT` (default) / `HUMAN_DECISION_PENDING` (final policy).
Source `KEEPLAB_DESIGN_INFERENCE` + (§31 of task) + corrective task §13.

Android app-private / device-storage protection does **not** mean this spec has chosen an encrypted
database (e.g. SQLCipher). No encryption dependency is added or implied.

`AUTH_REQUIRED` (auth failure) does **not** enter sign-out semantics and does **not** clear data.

---

## 30. Account deletion semantics

Four distinct operations, never conflated:

| Operation | Meaning | Server effect | Local effect |
| --- | --- | --- | --- |
| **sign-out** | end this device's session | session revoked | per §29 |
| **remove local account** | forget the account on this device only | none | local account-scoped data removed per §29 |
| **delete server account** | destroy the account server-side | account + data deletion state machine, optional grace period | local cleanup after server confirms |
| **disable account** | operator suspends the account | account disabled; sessions invalidated | non-destructive gate |

```
ACCOUNT_DELETION_IS_NOT_LOGOUT: FROZEN (conceptual distinction)
SERVER_ACCOUNT_DELETION_RETENTION/GRACE: HUMAN_DECISION_PENDING
```
Future requirements (conceptual only): explicit confirmation; server deletion state; optional
grace period; local cleanup; **sync cancellation**; attachment deletion. Nothing implemented.

---

## 31. Security invariants (architecture-level, not implemented)

| Area | Invariant |
| --- | --- |
| transport | TLS only; no cleartext auth |
| passwords | server-side **adaptive** hashing (Argon2id preferred; per-user salt; tuned work factor) |
| rate limiting | per-account **and** per-IP on login / code issue / code verify / reset |
| enumeration | anti-account-enumeration (uniform responses/timings) |
| codes | verification-code abuse limits (expiry, single-use, attempt caps, resend cooldowns) |
| sessions | refresh/session rotation + revocation |
| storage | secure secret storage (app-private; Keystore where appropriate) |
| logging | **never** log password / OTP / 2FA / refresh token / access token / credential assertion |
| PII | PII minimisation |
| attachments | per-account authorization on every fetch |

Anchors: RFC 9700 / OAuth 2.1 (S-29, S-30), OWASP password storage (S-31),
`KEEP-AUTH-REFERENCE-BLUEPRINT.md` §6. Status `FROZEN_ARCHITECTURE_DECISION` (invariants);
nothing implemented.

---

## 32. Privacy / telemetry boundary

Future sync diagnostics MAY contain: operation type · latency · retry count · error class ·
anonymous device/session id.

Future sync diagnostics MUST NOT contain: note body · note title · password · token ·
verification code · private attachment contents.

```
No telemetry SDK is selected now.  FUTURE_EXTENSION
```
Status `FROZEN_ARCHITECTURE_DECISION` (boundary) · Source `KEEPLAB_DESIGN_INFERENCE`.

---

## 33. Offline-first user experience

Principles (independent of Google Keep):

| Principle | Status |
| --- | --- |
| the UI stays usable offline | `FROZEN_ARCHITECTURE_DECISION` |
| local edits appear immediately (optimistic) | `FROZEN_ARCHITECTURE_DECISION` |
| normal successful sync is quiet | `RECOMMENDED_DEFAULT` |
| persistent failure becomes visible | `RECOMMENDED_DEFAULT` |
| conflict is visible | `RECOMMENDED_DEFAULT` |
| `AUTH_REQUIRED` is non-destructive | `FROZEN_ARCHITECTURE_DECISION` |

Avoid (`NON_GOAL`): blocking spinner on every edit; network-required note opening; silent data
loss; silent dropped mutation.

```
Exact Google Keep snackbar wording: NOT_REQUIRED_FOR_ARCHITECTURE.
```
Status `PUBLIC_REFERENCE_ONLY` / `NON_GOAL` (wording parity not required).

---

## 34. Google Keep reference boundary

Clean three-column table so future agents cannot conflate the layers:

| PUBLIC_KEEP_REFERENCE (publicly documented Keep behaviour) | KEEPLAB_ARCHITECTURE (ours) | UNKNOWN_GOOGLE_PRIVATE (must not be guessed) |
| --- | --- | --- |
| account-bound note visibility; multi-account; per-account library (S-20, S-22) | KeepLab-owned account; single active account in Phase 1; per-account scoping | how Keep caches accounts locally |
| sync as an Android account sync item (S-16) | in-app sync management; WorkManager pipeline | what the Keep toggle gates internally |
| offline editing; "Conflicting edits found" chooser (S-17) | per-field conflict policy; user-resolved body conflict | Keep's conflict algorithm/granularity; what "Keep both" produces |
| reload / re-download path that can be incomplete (S-18) | pending mutations never destroyed by a re-download | whether unsynced edits survive Keep's reload |
| delete propagation; 7-day Trash (S-19, S-21) | tombstone + tombstone-first sync | Keep's delete internals; retention mechanics |
| version history exists (web) (S-23) | optional future note versioning (`FUTURE_EXTENSION`) | retention/algorithm |
| Android offline-first guidance; LWW; WorkManager (S-07..S-12) | Room SSOT + hybrid sync + WorkManager | — (platform guidance, not Keep) |

Rule: Google Keep is referenced **only** for observable UX quality, publicly documented behaviour,
interaction inspiration, and (later) performance targets. It is **never** evidence for KeepLab's
private protocol, DB schema, token model, server technology, or sync algorithm.

---

## 35. Performance boundary

```
This task does NOT benchmark. Performance parity remains a SEPARATE concern.
```
Status `NON_GOAL` (benchmarking here). Future same-device performance work may cover: cold start,
warm start, restart, jank, memory, rotation/state restoration, 10/100/500/1000-note scale.

```
Do NOT start P0B-GK-DEVICE-REBASE.  Do NOT start P0B-GK-MATCHED-SCALE-A2.
The final performance device is NOT decided here.
```

---

## 36. Migration / backward compatibility

KeepLab already has local notes (Room schema v2 — `notes`, `checklist_items`, `labels`,
`note_labels`, per `HANDOFF.md`). Future account/sync introduction must **not** assume empty data.

```
CRITICAL: existing local data MUST NEVER be silently deleted when future auth is introduced.
```
Status `FROZEN_ARCHITECTURE_DECISION` · Source `HUMAN_ARCHITECTURE_DECISION`
(`MISSION.md` irreversible list: "any change to what is stored on the device in a way that would
drop existing notes") + `KEEPLAB_DESIGN_INFERENCE`.

Migration concepts to design later (not implemented): treat existing local notes as
`LOCAL_ONLY` (`account_id = NULL`); add the stable client UUID **additively** while the existing local
primary key may remain as an implementation-local identity (primary-key replacement is a separate
decision, never required for first network enablement); keep `trashed` as **product Trash** — it does
NOT map to `deleted_at`; on first sign-in offer to link/migrate the notes through an **explicit
account-link transaction** (sets `account_id`, assigns the UUID if absent, enqueues the outbox intent);
allow keeping them local-only; duplicate detection; rollback if sync onboarding fails. Detailed in
`KEEPLAB-AUTH-SYNC-IMPLEMENTATION-ROADMAP.md` phase A1 and `KEEPLAB-AUTH-SYNC-DATA-MODEL.md` §6.

---

## 37. Test architecture

Layers to define later (not executed): unit · Room integration · repository · outbox ·
sync-engine · fake-server contract · backend API · auth/session · WorkManager · process death ·
offline/reconnect · multi-device simulation · conflict simulation · migration.

Prefer deterministic tests before true-device journeys. Reserved for real hardware / server:
instrumented Room + Worker on a device; server-integration tests against a real backend; real
network fault injection. Status `RECOMMENDED_DEFAULT`. Detailed in the roadmap.

---

## 38. Observability

Future non-sensitive sync diagnostics (event names, no note content):

```
SYNC_STARTED · OUTBOX_DRAIN_STARTED · MUTATION_ACKED · MUTATION_RETRY · DELTA_PULL_STARTED ·
DELTA_APPLIED · CONFLICT_CREATED · AUTH_REFRESH_FAILED · AUTH_REQUIRED · SYNC_COMPLETED
```

Correlation ids: `session_id` · `sync_run_id` · `mutation_id` — **never** exposing credentials.
Status `RECOMMENDED_DEFAULT` · Source `KEEPLAB_DESIGN_INFERENCE` + §32.

---

## 39. Decision register

See `KEEPLAB-AUTH-SYNC-DECISION-REGISTER.md` for every numbered decision
(`AUTH-DEC-*`, `SYNC-DEC-*`, `GOV-DEC-*`, `BACKEND-DEC-*`) with status, rationale, alternatives,
consequence, source basis and human-approval flag. Style note: the Stack's existing `DEC-*`
namespace is **change-scoped** (per spec package); this spec therefore uses a distinct
architecture-decision namespace and invents no parallel governance framework.

---

## 40. Formal spec / governance location

Investigation result: the Stack's canonical spec mechanism is the Specification Compiler
(`specification/**`, per-change-package `implementation-contract.json`) and KeepLab's spec
packages live under `KeepLab-Relay/specs/**`. Both are protected:

- `Google-Android-Agent-Development-Stack/specification/` is `MUST NOT TOUCH / protected`.
- The active frozen contract (`p0b-close-benchmarkability`) allows only
  `KeepLab-Relay/specs/p0b-close-benchmarkability/`, `.../PERFORMANCE-PARITY.md`,
  `.../PARITY-MATRIX.md` under `specs/`; any new path there is `UNCLASSIFIED_FAIL_CLOSED`.
- The Specification Compiler's READY gate requires `unresolved_questions` to be **empty** —
  incompatible with the `HUMAN_DECISION_PENDING` items this architecture legitimately carries.

Therefore no direct implementation template was permitted—so the spec was written under `reports/**`
with the label `CANONICAL_ARCHITECTURE_DRAFT · NON_IMPLEMENTATION_AUTHORIZING`.

```
FORMAL_SPEC_PACKAGE:        DEFERRED_BY_GOVERNANCE
IMPLEMENTATION_AUTHORIZATION: NOT_GRANTED
```
No canonical path was blocked-and-bypassed; the guard was neither modified nor bypassed.

---

## 41. Internal consistency check

| Cross-check | Result |
| --- | --- |
| Room SSOT does **not** coexist with UI-direct-network reads | **CONSISTENT** — NET-1 + §5 |
| Outbox idempotency aligns with server mutation semantics | **CONSISTENT** — OUT-2 + server §26.1 |
| Revision conflict aligns with 409 behaviour | **CONSISTENT** — §15 + §24 `REVISION_CONFLICT` |
| Tombstone semantics align with delta pull | **CONSISTENT** — §21 DEL-1 + §16 CUR-1 |
| `AUTH_REQUIRED` does not delete pending outbox rows | **CONSISTENT** — SYNC-1 + OFF-1/2 |
| Sign-out semantics do not contradict offline-local guarantees | **CONSISTENT** — §29 keeps data by default |
| Account scoping consistent across Room and backend API | **CONSISTENT** — ISO-1 + ID-3 |
| LOCAL_ONLY may exist without a server account; no synthetic account row | **CONSISTENT** — ID-5 + DATA-MODEL ACCT-1/ACCT-2 |
| A synced entity cannot have a NULL `account_id` | **CONSISTENT** — ID-5 + ISO-1b |
| Trash is recoverable and is not a sync tombstone | **CONSISTENT** — TRASH-1 + §21 |
| Trash retention ≠ tombstone retention/compaction | **CONSISTENT** — §21 (separate concern, DEL-2) |
| Client-supplied `account_id` is not authorization | **CONSISTENT** — ID-6 + ISO-4 |
| Server change cursor ≠ client checkpoint | **CONSISTENT** — CUR-2 + §16 |
| Mutation atomicity includes the dedupe record/claim | **CONSISTENT** — §26 + DATA-MODEL §4.1 |
| WorkManager trigger cannot be lost | **CONSISTENT** — WM-1..WM-4 |
| Client wall clock never resolves a conflict | **CONSISTENT** — §20 (server-assigned ordering) |
| 404 cannot silently delete local work | **CONSISTENT** — ERR-2/ERR-3 |
| Refresh rotation is retry-safe, not naively idempotent | **CONSISTENT** — §9 principle 2 + SESS-2 + API §3.1 |
| `KEEP_BOTH` uses a new client UUID | **CONSISTENT** — §20 |
| No encrypted database is claimed | **CONSISTENT** — §29 |

No contradiction found. Full machine-checkable restatement: evidence `verification.json`.

---

## 42. Completion gate

| Gate | Result |
| --- | --- |
| architecture internally coherent | **PASS** (§41) |
| auth authority is KeepLab backend | **PASS** (§1, §8) |
| Credential Manager boundary explicit | **PASS** (§8) |
| Room SSOT decided | **PASS** (§5) |
| outbox semantics decided | **PASS** (§13) |
| client UUID model decided | **PASS** (§14) |
| revision model decided | **PASS** (§15) |
| delta cursor model decided | **PASS** (§16) |
| tombstone model decided | **PASS** (§21) |
| WorkManager sync model decided | **PASS** (§18) |
| conflict policy decided or explicitly gated | **PASS** (§20; trash retention gated) |
| session/offline semantics explicit | **PASS** (§9, §10) |
| backend conceptual contract exists | **PASS** (§23, §24, API-CONTRACT doc) |
| human decisions isolated | **PASS** (HUMAN-DECISIONS doc) |
| governance gate intact | **PASS** (§1.3) |
| no product code changed | **PASS** (see §43 verification) |

---

## 43. Verification

| # | Check | Result |
| --- | --- | --- |
| 1 | No Android device was operated | **PASS** — no `adb`/Maestro/UiAutomator device run |
| 2 | No KeepLab product source changed | **PASS** — `app/src/main/**` untouched |
| 3 | No Gradle dependency changed | **PASS** — no Gradle file touched |
| 4 | No Room production schema changed | **PASS** — schema v2 untouched; no migration |
| 5 | No auth implementation started | **PASS** — no auth code, no dependency |
| 6 | No backend implementation started | **PASS** — no server, no DB, no host |
| 7 | No Google OAuth/Firebase added | **PASS** — none |
| 8 | No Google private implementation guessed | **PASS** — UNKNOWN_PRIVATE preserved |
| 9 | `MISSION.md` unchanged | **PASS** — read only |
| 10 | Historical research reports unchanged | **PASS** — read only |
| 11 | J1–J4 not executed | **PASS** — 0 journeys |
| 12 | Architecture spec internally consistent | **PASS** (§41) |
| 13 | Every major decision has traceability | **PASS** (DECISION-REGISTER + §47) |
| 14 | Human-decision-pending items explicit | **PASS** (HUMAN-DECISIONS doc) |
| 15 | Implementation remains governance-blocked | **PASS** (§1.2, §1.3, §40) |

---

## 44. Traceability

Every frozen/recommended architecture decision traces to at least one of: an official
source/research finding (`S-xx`), an existing human governance decision, or explicit architecture
rationale. No claim is made that "Google Keep does this internally". Label legend:
`OFFICIAL_FACT` · `PUBLIC_KEEP_BEHAVIOR` · `KEEPLAB_DESIGN_INFERENCE` · `HUMAN_ARCHITECTURE_DECISION`.

---

## 45. Final output

```
KEEPLAB-AUTH-SYNC-ARCHITECTURE-SPEC
===================================

GOOGLE KEEP ROLE:
REFERENCE_PRODUCT_ONLY

KEEPLAB IDENTITY AUTHORITY:
OWN_BACKEND

GOOGLE AUTH IN KEEPLAB:
FORBIDDEN_UNLESS_HUMAN_APPROVED

CREDENTIAL MANAGER ROLE:
ANDROID_CREDENTIAL_UX_LAYER

FINAL AUTH METHOD:
HUMAN_DECISION_PENDING

ROOM AS LOCAL SSOT:
YES

OUTBOX:
YES

CLIENT-GENERATED UUID:
YES

SERVER REVISION:
YES

DELTA CURSOR:
YES

TOMBSTONE DELETE:
YES

SYNC TOPOLOGY:
HYBRID

BACKGROUND ENGINE:
WORKMANAGER

SYNC WORKER MODEL:
SINGLE_UNIQUE_PIPELINE

CONFLICT POLICY:
PER_FIELD

CRDT PHASE 1:
NO

OFFLINE REFRESH FAILURE DELETES LOCAL DATA:
NO

AUTH REQUIRED DELETES OUTBOX:
NO

CLOUD PROVIDER:
TENCENT_CLOUD  (D-08, HUMAN_APPROVED 2026-10-06 · PORTABLE_DOCKER)

BACKEND LANGUAGE:
KOTLIN_KTOR  (D-07, HUMAN_APPROVED 2026-10-06)

DATABASE VENDOR:
POSTGRESQL  (D-09, HUMAN_APPROVED 2026-10-06)

TOKEN FORMAT:
HUMAN_DECISION_PENDING

SIGN-OUT LOCAL DATA POLICY:
HUMAN_DECISION_PENDING

TRASH RETENTION:
HUMAN_DECISION_PENDING

REFERENCE J1-J4 PROGRAM BLOCKING:
NO

FORMAL SPEC PACKAGE:
DEFERRED_BY_GOVERNANCE

CURRENT MISSION NETWORK/ACCOUNT GATE:
HUMAN_APPROVED_BOUNDED · CANONICAL_FILE_AMENDMENT_BLOCKED_BY_CONTRACT_GUARD

IMPLEMENTATION AUTHORIZATION:
NOT_GRANTED

ANDROID DEVICE USED:
NO

KEEPLAB PRODUCT SOURCE MODIFIED:
NO

GRADLE MODIFIED:
NO

ROOM PRODUCTION SCHEMA MODIFIED:
NO

BACKEND IMPLEMENTED:
NO

GOOGLE/FIREBASE AUTH ADDED:
NO

CONTRACT GUARD:
ACTIVE

STATUS:
READY

NEXT:
OPEN_GOVERNANCE_WRITE_CONTRACT

PRIMARY SPEC:
/mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack/reports/KEEPLAB-AUTH-SYNC-ARCHITECTURE-SPEC.md

===================================
```

Stopped here. No implementation. J1–J4 not executed. No Android device operated. P0B not started.

---

## 46. A0 update — human architecture decisions (2026-10-06)

Appended by `KEEPLAB-HUMAN-ARCHITECTURE-DECISIONS-A0`. This section does not change any frozen
architecture decision; it records which decisions left `HUMAN_DECISION_PENDING`.

```
D-02: DECIDED  YES_LOCAL_ONLY_BEFORE_SIGNIN
D-03: DECIDED  SINGLE_ACTIVE_ACCOUNT_PHASE1
D-07: DECIDED  KOTLIN_KTOR
D-08: DECIDED  TENCENT_CLOUD + PORTABLE_DOCKER
D-09: DECIDED  POSTGRESQL
D-15: DECIDED  YES_BOUNDED_ACCOUNT_NETWORK_UNLOCK
```

```
PHASE_1_ACCOUNT_MODE:            SINGLE_ACTIVE_ACCOUNT
LOCAL_NOTES_BEFORE_SIGNIN:       YES  (LOCAL_ONLY, account_id = NULL, no synthetic account row)
CLOUD_PROVIDER:                  TENCENT_CLOUD
DEPLOYMENT_PORTABILITY:          PORTABLE_DOCKER
BACKEND_LANGUAGE:                KOTLIN
BACKEND_FRAMEWORK:               KTOR
PRIMARY_DATABASE:                POSTGRESQL
IMPLEMENTATION_AUTHORIZATION_MODEL: PHASE_GATED
CURRENT_IMPLEMENTATION_AUTHORIZATION: NOT_GRANTED
AUTH_NETWORK_GOVERNANCE_GATE:    HUMAN_APPROVED_BOUNDED
CANONICAL GOVERNANCE AMENDMENT:  BLOCKED_BY_CONTRACT_GUARD  (MISSION.md / FACTORY_RULES.md / ROADMAP.md)
FORMAL_SPEC_PACKAGE_LOCATION:    HUMAN_DECISION_PENDING  (D-14 unanswered)
HUMAN_DECISIONS_PENDING:         9  (D-01, D-04, D-05, D-06, D-10, D-11, D-12, D-13, D-14)
```

Status surfaces updated in this document: §1.2 gate line, §6.3 phase-1 account scope, §5 `LOCAL_ONLY`
posture, §23.1 backend stack, §45 final block. Unresolved decisions (D-01/D-04/D-10 and the rest)
remain `HUMAN_DECISION_PENDING`; Google/Firebase identity remains
`FORBIDDEN_UNLESS_HUMAN_APPROVED`; the spec remains
`NON_IMPLEMENTATION_AUTHORIZING`, with future phases `PHASE_GATED_ELIGIBLE` only once the canonical
A0 governance write lands. **No implementation detail belonging to A1/A2/A3 was added.**

Record: `reports/KEEPLAB-A0-HUMAN-ARCHITECTURE-DECISIONS.md`;
bounded policy + amendment proposal: `reports/KEEPLAB-A0-BOUNDED-ACCOUNT-NETWORK-GOVERNANCE.md`.

---

Stopped here for A0. No implementation. A1 not started. A2 not started. Auth not implemented.
Backend not implemented. J1–J4 not executed. No Android device operated. P0B not started.
P1 not started.
