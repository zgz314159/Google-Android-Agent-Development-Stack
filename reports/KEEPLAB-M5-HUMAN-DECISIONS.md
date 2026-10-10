# KEEPLAB-M5-HUMAN-DECISIONS

**Human-approved A8 decisions frozen by the M5 contract package**

- Task: `KEEPLAB-M5-A8-MULTI-DEVICE` (contract `KEEPLAB-M5-A8-MULTI-DEVICE-001`)
- Date: **2026-10-07** (CST, UTC+08:00)
- Source of approval: `HUMAN_PROJECT_OWNER_APPROVAL`, 2026-10-07. No other approval source is claimed.
- These are **human decisions, not model choices**. They were recorded, not re-asked and not
  reinterpreted. The values below are the frozen values; nothing here changes their meaning.
- Canonical governance record: `reports/KEEPLAB-AUTH-SYNC-HUMAN-DECISIONS.md` (rows D-05 and D-11)
  and `reports/KEEPLAB-AUTH-SYNC-DECISION-REGISTER.md` (entries `AUTH-DEC-012` and `BACKEND-DEC-005`).

---

## D-05 — `ACCOUNT_DELETE_GRACE_30_DAYS`

- **Status:** `DECIDED` · `HUMAN_APPROVED` · 2026-10-07
- **Canonical decision:** `AUTH-DEC-012`
- **Blocks:** A8 (M5)

Semantics, exactly as approved:

- account deletion request immediately enters `DELETION_PENDING`
- normal account access becomes disabled
- all server sessions are revoked immediately
- access/refresh capability for those sessions becomes invalid
- no new normal sync write is accepted while deletion is pending
- `purge_after = deletion_requested_at + 30 days`
- within the 30-day grace period the owner may cancel deletion through re-authentication using the
  **EXISTING** verified credential system
- do **not** invent a new token family merely for recovery
- cancellation restores `ACTIVE`; it does not resurrect deleted server data because purge has not yet
  occurred
- after expiry, an explicit deterministic purge boundary permanently deletes the server account data
- M5 needs deterministic clock/service tests for the purge boundary; it does **not** need a
  production cloud scheduler
- Android local Room data **MUST NEVER** be silently deleted because the remote account was
  disabled / deletion-pending / purged
- local notes **MUST NOT** be silently reassigned to another account
- D-06 `TRASH_RETENTION_7_DAYS` is unrelated
- SYNC tombstone retention is unrelated
- `TOMBSTONE_GC` stays **DISABLED** unless separately authorized

---

## D-11 — `NO_PUSH_PROVIDER_IN_A8_CORRECTNESS_PATH`

- **Status:** `DECIDED` · `HUMAN_APPROVED` · 2026-10-07
- **Canonical decision:** `BACKEND-DEC-005`
- **Blocks:** A8 (M5)

Semantics, exactly as approved:

- choose **NO** FCM / Firebase / vendor push provider for M5 correctness
- no Google / Firebase dependency
- no Xiaomi / Huawei / etc. vendor push dependency
- normal correctness remains pull/delta based
- WorkManager / foreground / manual sync may detect remote state
- authenticated API requests and refresh paths must detect revoked/disabled state
- push may be a **FUTURE** latency optimization only
- any future push implementation must sit behind a provider abstraction
- A8 PASS must be possible with `PUSH_PROVIDER = NONE`

---

## Not decided here (unchanged)

```
D-12  collaboration scope        FUTURE / A9   (NOT decided by this session)
D-14  formal spec package location  NON_BLOCKING (NOT decided by this session)
```

## Frozen earlier (not reopened)

```
D-01 / D-04 / D-06 / D-07 / D-08 / D-09 / D-10 / D-13 / D-15
A5 retry/outbox policy
A6 conflict policy
A7 attachment binary architecture · attachment limits · attachment UI · object storage
Google Keep reference research
M4 = A7 ATTACHMENTS  PASS / CLOSED
```

## Status

```
FROZEN_BY_THIS_RECORD:            2  (D-05, D-11)
DECISIONS_REINTERPRETED:          0
DECISIONS_RE_ASKED:               0
D-12 RESOLVED:                    NO (remains FUTURE / A9)
D-14 RESOLVED:                    NO (remains NON_BLOCKING)
M5 IMPLEMENTATION AUTHORIZED:     YES (by contract KEEPLAB-M5-A8-MULTI-DEVICE-001)
M5 IMPLEMENTED BY THIS SESSION:   NO
```
