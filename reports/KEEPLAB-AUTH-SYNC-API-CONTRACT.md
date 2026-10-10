# KEEPLAB-AUTH-SYNC-API-CONTRACT

**Conceptual API semantics + error taxonomy for the future KeepLab backend**

- Task: `KEEPLAB-AUTH-SYNC-ARCHITECTURE-SPEC`
- Date: 2026-10-05 (CST) · Status: **CANONICAL_ARCHITECTURE_DRAFT · NON_IMPLEMENTATION_AUTHORIZING**
- Basis: `KEEP-OFFLINE-SYNC-BLUEPRINT.md` §7; `KEEPLAB-AUTH-SYNC-ARCHITECTURE-SPEC.md` §24–§26.
- These are **architecture contract examples**, not final route names. No server exists.

---

## 1. Conventions

| Convention | Rule |
| --- | --- |
| transport | HTTPS only; TLS; no cleartext auth |
| auth context | every non-auth endpoint requires a valid access credential. The **server derives the effective account scope from the authenticated session/access credential**; a client-supplied `account_id` is a scope hint, never authority (INVARIANT AUTHZ-1) |
| account scope | a client MUST NOT gain another account's data merely by sending `account_id = <other account>`; local Room `account_id` remains mandatory for synced local-data isolation |
| ids | client-generated UUIDs for entities; server adopts them (spec §14) |
| revision | revision-sensitive writes carry `base_revision`; stale → `409` |
| idempotency | mutation push is idempotent by `mutation_id`; refresh rotation is `RETRY_SAFE_ROTATION`, **not** generic HTTP-style idempotency (§3.1) |
| time | server timestamps; client timestamps are ordering-only |
| errors | stable conceptual taxonomy (§3); raw exceptions never reach the UI |

---

## 2. Endpoint semantics

Legend: **Identity** = required identity context · **Idem** = idempotent · **Rev** = revision
behaviour.

### 2.1 Auth endpoints

| Endpoint | Purpose | Identity | Idem | Rev |
| --- | --- | --- | --- | --- |
| `POST /auth/register` | create a KeepLab account (method per human decision) | none | no (unique account) | n/a |
| `POST /auth/login` | password credential exchange → session | none | no | n/a |
| `POST /auth/passkey/challenge` | issue a WebAuthn challenge | none (pre-auth) | no | n/a |
| `POST /auth/passkey/verify` | verify a passkey assertion → session | none (pre-auth) | no | n/a |
| `POST /auth/refresh` | rotate the refresh credential → new access credential | valid refresh credential | `RETRY_SAFE_ROTATION` (§3.1) | n/a |
| `POST /auth/logout` | revoke the current session | valid session | yes | n/a |
| `POST /auth/sessions/{id}/revoke` | revoke one session | valid session (own account) | yes | n/a |
| `POST /auth/recovery/*` | recovery / reset (method per human decision) | none / recovery token | no | n/a |

### 2.2 Notes endpoints

| Endpoint | Purpose | Identity | Idem | Rev |
| --- | --- | --- | --- | --- |
| `GET /notes/{id}` | fetch current server representation | session + account | yes | returns `revision` |
| `POST /notes` | create a note (client id supplied) | session + account | yes (by supplied id / mutation id) | initial revision |
| `PATCH /notes/{id}` | update fields | session + account | per `mutation_id` | requires `base_revision`; stale → `409` |
| `DELETE /notes/{id}` | move the note to **Trash** (product state / recoverable); the sync **tombstone** is set only on final deletion — Trash is never a tombstone | session + account | yes | the state change advances the revision |

### 2.3 Sync endpoints

| Endpoint | Purpose | Identity | Idem | Rev |
| --- | --- | --- | --- | --- |
| `POST /sync/mutations` | push a batch of outbox mutations | session + account | **yes, by `mutation_id`** | per-mutation `base_revision` |
| `GET /sync/changes?since=<cursor>` | pull deltas after a **server change cursor** | session + account (server-derived scope) | yes (read) | ordered by monotonic, account-scoped cursor |
| `GET /sync/checkpoint` | **optional / bootstrap**: server-head or server-authoritative cursor for the account. It does NOT report a client's applied **checkpoint** (that is a client-side fact) | session + account | yes (read) | n/a |

### 2.4 Attachment endpoints

| Endpoint | Purpose | Identity | Idem | Rev |
| --- | --- | --- | --- | --- |
| `POST /attachments` | register + upload a binary (or pre-signed target) | session + account | yes (by `attachment_id`) | n/a |
| `GET /attachments/{id}` | download a binary | session + account (**authorized per account**) | yes (read) | n/a |

---

## 3. Revision + idempotency semantics

```
POST /sync/mutations   request body: { mutations: [ { mutation_id, entity_type, entity_id,
                                          op_type, payload, base_revision } ] }
                       response:      { results: [ { mutation_id, status, server_revision?,
                                          conflict? } ] }
```

Per-mutation result statuses: `APPLIED` · `DUPLICATE_IGNORED` (same `mutation_id` seen) ·
`CONFLICT` (409-equivalent, with current representation) · `REJECTED` (permanent).

```
INVARIANT:  duplicate mutation_id → success, no double-apply.
INVARIANT:  stale base_revision on a conflict-sensitive field → conflict result + current revision.
INVARIANT:  the mutation_id dedupe record/claim, the mutation apply, the revision increment and the
            change-log append share ONE server-side consistency boundary (DATA-MODEL §4.1).
```

### 3.1 Refresh rotation: single-use + retry-safe (NOT naive idempotency)

```
REFRESH_ROTATION: single-use + RETRY_SAFE
```

A rotating single-use refresh credential is **not** generic HTTP-style idempotency. The frozen
contract requirement is:

- the client sends a `refresh_request_id` (or an equivalent one-operation nonce / idempotency key);
- if the **same** authenticated rotation request is retried after a lost response, the server MAY
  return/recover the **same logical rotation result** within a bounded retry window;
- if the already-used refresh credential appears with a **different** rotation request identity, or
  outside the allowed retry semantics, it is treated as a possible reuse/theft signal according to
  the session-family policy;
- an ambiguous network failure after a successful server rotation MUST NOT force accidental account
  loss or automatically look like credential theft.

Status `FROZEN_ARCHITECTURE_DECISION` (contract requirement) · Storage implementation is **NOT**
frozen here (`IMPLEMENTATION_DECISION_PENDING`). See STATE-MODEL INVARIANT SESS-2.

---

## 4. Error taxonomy and mapping

Stable conceptual classes (`FROZEN_ARCHITECTURE_DECISION`). Mapped server → repository result →
sync state → UI.

| Error class | Typical HTTP | Meaning | Repository result | Sync state | UI |
| --- | --- | --- | --- | --- | --- |
| `AUTH_REQUIRED` | 401 | no/absent session | `AuthRequired` | session `AUTH_REQUIRED` | non-destructive gate |
| `AUTH_EXPIRED` | 401 | session expired/revoked/reused | `AuthExpired` | → `REAUTH_REQUIRED` | quiet then gate |
| `INVALID_CREDENTIAL` | 401 (login) | wrong secret | `InvalidCredential` | n/a (auth flow) | generic field error |
| `ACCOUNT_DISABLED` | 403 | account suspended | `AccountDisabled` | session `AUTH_REQUIRED` | actionable message |
| `FORBIDDEN` | 403 | not authorized for this resource | `Forbidden` | row `SYNC_FAILED` (permanent) | "couldn't sync" |
| `NOT_FOUND` | 404 | entity absent — may mean true deletion, a stale id, an authorization mismatch, server compaction, or a protocol mismatch | `NotFound` → `ReconcileRequired` unless a server-authoritative tombstone/deletion or a documented reconciliation response proves deletion | row `RECONCILE_REQUIRED` (local row **NOT** deleted) | quiet / reconcile |
| `REVISION_CONFLICT` | 409 | stale `base_revision`, both sides changed | `Conflict(current)` | entity `CONFLICT` | conflict screen |
| `RATE_LIMITED` | 429 | throttled | `Retryable` | row `SYNC_PENDING` (backoff) | quiet |
| `VALIDATION_ERROR` | 422 | malformed payload | `Permanent` | row `SYNC_FAILED` | developer-visible + honest user msg |
| `PAYLOAD_TOO_LARGE` | 413 | body too big | `Permanent` | row `SYNC_FAILED` | honest message |
| `NETWORK_UNAVAILABLE` | (client) | no reachable network | `Retryable` | row stays `SYNC_PENDING` | quiet |
| `SERVER_TEMPORARY` | 5xx | transient backend fault | `Retryable` | row `SYNC_PENDING` | quiet |
| `SERVER_UNCLASSIFIED` | 5xx (unknown / unmapped) | fault with no stable semantic/application classification — **retryable with bounded attempts**, never generically permanent | `Retryable` (bounded) | row `SYNC_PENDING` | quiet |
| `SERVER_PERMANENT` | semantic/app error class (not "any 5xx") | a **stable semantic or application** error classification marking the mutation non-recoverable | `Permanent` | row `SYNC_FAILED` | visible |
| `SYNC_CURSOR_INVALID` | 409/410 | client cursor no longer valid | `CursorReset` | checkpoint reset flow | quiet |
| `ATTACHMENT_FAILED` | 4xx/5xx | attachment upload/download failed | `Retryable`/`Permanent` | attachment `UPLOAD_FAILED` | per-attachment |

```
INVARIANT ERR-1:  Raw server exceptions MUST NOT be exposed directly to the UI.
INVARIANT ERR-2:  A generic `5xx` is NOT a permanent classification by default. Unknown/unclassified
                  5xx is retryable with bounded attempts; permanent failures carry a stable
                  semantic/application error classification. Nothing retries forever.
INVARIANT ERR-3:  `NOT_FOUND` (404) MUST NOT automatically mean "local row resolved/deleted". 404 may
                  mean a true deletion, a stale id, an authorization mismatch, server compaction or a
                  protocol mismatch. Only a server-authoritative tombstone/deletion or a documented
                  reconciliation response may cause automatic local deletion; otherwise the state is
                  `RECONCILE_REQUIRED`.
INVARIANT AUTHZ-1: CLIENT_ACCOUNT_ID_IS_NOT_AUTHORITY. The server derives the effective account
                  scope from the authenticated session/access credential. Sending a different
                  `account_id` MUST NOT grant another account's data. A future multi-account/org mode
                  may transmit a selected scope, but the server MUST validate membership/authorization
                  against the authenticated session.
```
Status `FROZEN_ARCHITECTURE_DECISION` · Source `KEEPLAB_DESIGN_INFERENCE` + corrective task §6/§12.

---

## 5. Auth-method dependency

The concrete bodies of `POST /auth/register`, `POST /auth/login`, and the recovery endpoints
depend on the **not-yet-decided** auth method (`AUTH_METHOD: HUMAN_DECISION_PENDING`). The contract
shape is stable; the credential payload is not frozen.

---

## 6. Traceability

Endpoint set and invariants from `KEEP-OFFLINE-SYNC-BLUEPRINT.md` §7.1/§7.2
(`KEEPLAB_DESIGN_INFERENCE`), anchored in S-28..S-31 (OAuth/OWASP standards) and S-51
(sync-failure catalogue). No route name is claimed final; no Google Keep API is referenced.