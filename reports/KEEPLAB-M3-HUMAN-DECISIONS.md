# KEEPLAB-M3-HUMAN-DECISIONS

**Human decision frozen for Milestone M3 (`A5` offline hardening + `A6` conflict handling)**

- Task: `KEEPLAB-M3-OFFLINE-CONFLICT-CONTRACT`
- Date: 2026-10-06 (CST, UTC+08:00)
- Source: `HUMAN_PROJECT_OWNER_APPROVAL`, 2026-10-06
- Status: **FROZEN · not reinterpreted · not re-asked · do not reopen**

```
D-06 = TRASH_RETENTION_7_DAYS
SOURCE = HUMAN_PROJECT_OWNER_APPROVAL
DATE = 2026-10-06
```

---

## D-06 — `TRASH_RETENTION_7_DAYS`

| | |
| --- | --- |
| Meaning | the **product Trash** stays reversible for **7 days** |
| After the 7 days | a note becomes eligible for `FINAL_DELETE`, which produces the normal sync deletion / **tombstone** path |
| Trash timestamp | a note entering Trash carries a Trash timestamp |
| Restore | restoring a trashed note clears/invalidates its Trash expiry state |
| Authority | for a synced note, the **authoritative server-accepted Trash time** governs; an unacknowledged offline client timestamp alone must never cause a permanent deletion |
| `LOCAL_ONLY` | local time may drive local Trash retention (no server authority exists) |

### What D-06 explicitly does **not** decide

```
SYNC_TOMBSTONE_RETENTION_OR_COMPACTION:
    SEPARATE CONCERN - NOT the same product setting as Trash duration
TOMBSTONE_RETENTION_EQUALS_TRASH_RETENTION:
    NO
SYNC_TOMBSTONE_RETENTION = 7 DAYS:
    NO
PERMANENT_TOMBSTONE_RETENTION_DURATION:
    NOT CHOSEN (do not choose one)
TOMBSTONE_GC:
    DISABLED for M3 (safe implementation posture)
```

`SYNC_TOMBSTONE_RETENTION_OR_COMPACTION` remains a separate **protocol-correctness** concern
(`IMPLEMENTATION_DECISION_PENDING`), governed by the anti-resurrection invariant
(`KEEPLAB-AUTH-SYNC-STATE-MODEL` INVARIANT DEL-2): tombstone GC may happen only in a future
Milestone, only together with an anti-resurrection protocol proving that old clients can never
legally replay pre-delete state. A tombstone must **never** be garbage-collected merely because it
is older than 7 days, and 7 days must **never** be read as a tombstone retention duration.

---

## Decisions that remain pending and do **not** block M3

| # | Decision | M3 treatment |
| --- | --- | --- |
| D-05 | account-deletion retention | account deletion is **not implemented** → not blocking |
| D-11 | push provider | no push provider, no FCM, no background push architecture in M3 |
| D-12 | collaboration | out of scope |
| D-13 | attachment limits | attachments out of scope |
| D-14 | formal spec package location | still pending; does not block M3 |

---

## Where this is recorded (deliberately minimal)

- This file is the **smallest appropriate decision record** for D-06, mirroring the accepted
  `reports/KEEPLAB-M2-HUMAN-DECISIONS.md` precedent. It is the record the M3 contract and the M3
  execution session read.
- **No separate D-06 governance task was created.** No old governance phase was reopened.
- `KeepLab-Relay/MISSION.md`, `KeepLab-Relay/FACTORY_RULES.md`, `specs/google-keep-parity/ROADMAP.md`
  and `.factory/decisions.md` were **not** modified to record D-06.
- `reports/KEEPLAB-AUTH-SYNC-DECISION-REGISTER.md` (§ SYNC-DEC-015) and
  `reports/KEEPLAB-AUTH-SYNC-HUMAN-DECISIONS.md` (§1 D-06 row / §0 remaining-pending list) still
  show D-06 as `HUMAN_DECISION_PENDING`. That stale wording is **left as-is** and recorded as
  `MINOR_BACKLOG` in `reports/KEEPLAB-MINOR-BACKLOG.md` — **not a blocker**, and editing those
  historical records is not required for M3.
- The canonical governance amendment remains unrelated and untouched
  (`KEEPLAB-AUTH-SYNC-DECISION-REGISTER.md` GOV-DEC-001/GOV-DEC-005 note it as
  `BLOCKED_BY_CONTRACT_GUARD`); M3 does not reopen it.

---

```
HUMAN_DECISIONS_FROZEN_FOR_M3: D-06 = TRASH_RETENTION_7_DAYS
HUMAN_DECISIONS_PENDING_NOT_BLOCKING_M3: D-05, D-11, D-12, D-13, D-14
SYNC_TOMBSTONE_RETENTION_OR_COMPACTION: SEPARATE / NOT_7_DAYS / IMPLEMENTATION_DECISION_PENDING
TOMBSTONE_GC_FOR_M3: DISABLED
PHASE_STATE: A0 READY · A1 PASS · A2 PASS · M2 PASS · M3 AUTHORIZED_BY_HUMAN (A5 + A6) · A7+ NOT_STARTED
```
