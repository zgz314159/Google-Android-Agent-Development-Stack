# KEEPLAB-M2-HUMAN-DECISIONS

**Human decisions frozen for Milestone M2 (`A3` auth/session + `A4` single-user sync)**

- Task: `KEEPLAB-M2-AUTH-SINGLE-USER-SYNC-CONTRACT`
- Date: 2026-10-06 (CST, UTC+08:00)
- Source: `HUMAN_PROJECT_OWNER_APPROVAL`, 2026-10-06
- Status: **FROZEN · not reinterpreted · not re-asked · do not reopen**

```
D-01 = EMAIL_PASSWORD_VERIFIED
D-04 = PRESERVE_LOCAL_CACHE
D-10 = JWT_ACCESS_OPAQUE_ROTATING_REFRESH
```

---

## D-01 — `EMAIL_PASSWORD_VERIFIED`

| | |
| --- | --- |
| Meaning | email + password registration; email verification required; password login; forgot/reset password supported |
| Allowed later | a passkey MAY be added in a later phase |
| Deferred | phone login |
| Forbidden | Google login; Firebase Auth |
| Does not decide | D-05 account-deletion retention (still pending, not blocking M2) |

Consequences used by M2:

- A3 uses a **server-side password credential** with a modern password KDF (Argon2id preferred; no
  custom/invented hashing).
- Registration requires **email verification** with a deterministic code flow.
- A password **reset** flow exists and revokes existing sessions.
- **No** Google identity, **no** Google private API, **no** Firebase Auth, **no** phone auth and
  **no** OAuth social login may be added. Credential Manager is permitted only as Android
  credential **UX** for password credentials; it never becomes the identity authority.
- KeepLab backend remains the `IDENTITY_AUTHORITY`.

## D-04 — `PRESERVE_LOCAL_CACHE`

| | |
| --- | --- |
| Meaning | on sign-out: revoke/clear the current session credentials, remove the active-account state, stop account sync, **preserve** Room data, **preserve** account-scoped cached notes, **preserve** the outbox, **preserve** `LOCAL_ONLY` notes |

Signed-out UI must continue showing `LOCAL_ONLY` data.

Account-scoped rows belonging to a signed-out account:

- remain stored;
- are **not** treated as another account's data;
- must **not** sync.

Re-login to the same account may resume them.

```
DO NOT CLAIM FULL ROOM DATABASE ENCRYPTION.
No database-encryption feature is authorized here.
```

## D-10 — `JWT_ACCESS_OPAQUE_ROTATING_REFRESH`

| | |
| --- | --- |
| Access token | **JWT**, short-lived, default target ≈ 15 minutes, configurable |
| Refresh token | **opaque**, high-entropy, default target ≈ 30 days, configurable |
| Refresh secrets at rest | must **not** be stored plaintext; the server stores a secure verifier/hash form |
| Rotation | required |
| Retry safety | refresh uses `refresh_request_id`; if a refresh rotation succeeded but the response was lost, retrying the **same** old refresh token with the **same** `refresh_request_id` within a bounded replay window must recover the **same** rotated result |

Forbidden outcomes of the retry path:

- minting multiple child sessions;
- treating the request immediately as theft;
- destroying account access.

```
Use the smallest safe implementation.
If replay state must retain a secret result, it must be encrypted at rest or safely re-derived.
Never write token plaintext to reports/evidence/logs.
```

---

## Recorded, not applied elsewhere (deliberate)

- No separate governance task was created for these three decisions.
- `KeepLab-Relay/MISSION.md`, `KeepLab-Relay/FACTORY_RULES.md` and any parity `ROADMAP` were
  **not** modified to record them. MISSION.md invariant 1 already carries the bounded
  account/network policy (v2, 2026-10-06) and the phase-gated rule.
- Stale wording elsewhere in `reports/**` that still shows D-01/D-04/D-10 as
  `HUMAN_DECISION_PENDING` (for example `reports/KEEPLAB-AUTH-SYNC-HUMAN-DECISIONS.md` §0/§1 and
  `reports/KEEPLAB-AUTH-SYNC-ARCHITECTURE-SPEC.md` §23.1) is left as-is and recorded as
  `MINOR_BACKLOG` — **not a blocker**.

## Decisions that remain pending and do **not** block M2

| # | Decision | M2 treatment |
| --- | --- | --- |
| D-05 | account deletion retention | account deletion is **not implemented** → not blocking |
| D-06 | Trash automatic retention duration | no automatic Trash expiration/purge is implemented; Trash stays reversible; an explicit final deletion may create a tombstone but M2 does not auto-purge it → not blocking |
| D-11 | push provider | no push provider in M2 |
| D-12 | collaboration | out of scope |
| D-13 | attachment limits | attachments out of scope |
| D-14 | formal spec package location | still pending; does not block M2 |

```
HUMAN_DECISIONS_FROZEN_FOR_M2: D-01, D-04, D-10
HUMAN_DECISIONS_PENDING_NOT_BLOCKING_M2: D-05, D-06, D-11, D-12, D-13, D-14
PHASE_STATE: A0 READY · A1 PASS · A2 PASS · M2 AUTHORIZED_BY_HUMAN (A3 + A4) · A5+ NOT_STARTED
```
