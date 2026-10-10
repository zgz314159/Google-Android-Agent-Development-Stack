# KEEPLAB-M4-HUMAN-DECISIONS

**Human decision frozen for Milestone M4 (`A7` attachments)**

- Task: `KEEPLAB-M4-ATTACHMENTS-CONTRACT`
- Date: 2026-10-06 (CST, UTC+08:00)
- Source: `HUMAN_PROJECT_OWNER_APPROVAL`, 2026-10-06
- Status: **FROZEN · not reinterpreted · not re-asked · do not reopen**

```
D-13 = ATTACHMENT_LIMITS_V1
SOURCE = HUMAN_PROJECT_OWNER_APPROVAL
DATE = 2026-10-06
```

---

## D-13 — `ATTACHMENT_LIMITS_V1`

| Key | Value |
|---|---|
| `MAX_SINGLE_ATTACHMENT_BYTES` | `26214400` (25 MiB) |
| `MAX_ATTACHMENTS_PER_NOTE` | `20` |
| `ACCOUNT_ATTACHMENT_QUOTA_BYTES` | `1073741824` (1 GiB) |
| `ALLOWED_MIME_TYPES` | `image/jpeg`, `image/png`, `image/webp`, `application/pdf` |
| `LIMIT_AUTHORITY` | `SERVER_CONFIGURABLE` — the backend is authoritative |

### Out of scope for D-13 (must NOT be added)

```
audio/*
video/*
application/octet-stream
arbitrary binary files
executables
archives (unless separately approved later)
```

### Authority rules

- The limits are **server-configurable**. The backend is the authoritative enforcer.
- Android may pre-validate for UX using **cached server limits** or these **D-13 defaults**.
  Server-side enforcement remains authoritative even when a cached client value is stale.

---

## Quota semantics for D-13 (frozen)

```
ACCOUNT_ATTACHMENT_QUOTA_BYTES = LOGICAL_ATTACHMENT_BYTES_OWNED_BY_THE_ACCOUNT
DUPLICATE_FILES_DO_NOT_BYPASS_QUOTA = YES
```

- Storage **may** deduplicate the binary for the same content hash.
- Both logical attachments still count toward the 1 GiB account quota.
- **Pending upload reservations also count while active**, so concurrent uploads cannot race
  past the quota.
- On abort, expiry, or a failed initiation before commitment, the reservation is released
  safely.

---

## Project data stage (frozen for M4)

```
PROJECT_DATA_STAGE = EXPERIMENTAL
TEST_DATA_DISPOSABLE = YES
OLD_TEST_DATABASE_COMPATIBILITY = NOT_REQUIRED
```

Therefore: Room may bump directly to a clean new schema version, and backend Flyway may add new
migrations. **No production migration complexity is built for disposable development data.**

---

## M4 object-storage implementation decision (frozen for M4)

```
OBJECT_STORAGE = PORTABLE_ABSTRACTION
REFERENCE_DRIVER = FILESYSTEM_DEV_TEST
TENCENT_CLOUD_PROVISIONED = NO
CLOUD_RESOURCES_PROVISIONED = NO
```

`D-08` (`TENCENT_CLOUD` + `PORTABLE_DOCKER`) remains the production deployment target, but **M4
does not provision Tencent Cloud**. M4 implements a portable `ObjectStorage` abstraction plus a
`FilesystemObjectStorage` development/test reference driver, configured by environment variables
(`KEEPLAB_OBJECT_STORAGE_DRIVER`, `KEEPLAB_OBJECT_STORAGE_ROOT`). A Tencent COS adapter may be
added later at deployment/infrastructure time without changing attachment domain logic.

This is a **DEVELOPMENT_REFERENCE_DRIVER**: it is **not** a claim that production Tencent COS has
already been implemented.

---

## Decisions that remain pending and do **not** block M4

| # | Decision | M4 treatment |
|---|---|---|
| D-05 | account-deletion retention | account deletion is **not implemented** → not blocking |
| D-11 | push provider | no push provider, no FCM, no background push architecture in M4 |
| D-12 | collaboration | out of scope |
| D-14 | formal spec package location | still pending; does not block M4 |

`SYNC_TOMBSTONE_RETENTION_OR_COMPACTION` stays a separate `IMPLEMENTATION_DECISION_PENDING`
protocol-correctness concern; `TOMBSTONE_GC` stays `DISABLED`. M4 does not choose a tombstone
retention duration and does not garbage-collect tombstones by age.

---

## What M4 explicitly is not

```
M4 is not: A8 multi-device, A9 multi-account, collaboration, cloud deployment,
release hardening, camera/drawing/voice/video capture, archive or executable support,
Google Keep work, Testapp or PowerAi.
```

M4 must not split attachment metadata/upload/download into separate Contracts, must not create an
Attachment Review, a Storage Review, an Upload Review or a post-PASS audit, and must not start A8.

---

## Where this is recorded (deliberately minimal)

- This file is the **smallest appropriate decision record** for D-13, mirroring the accepted
  `reports/KEEPLAB-M3-HUMAN-DECISIONS.md` and `reports/KEEPLAB-M2-HUMAN-DECISIONS.md` precedent.
  It is the record the M4 contract and the M4 execution session read.
- **No separate D-13 governance task was created.** No old governance phase was reopened.
- `KeepLab-Relay/MISSION.md`, `KeepLab-Relay/FACTORY_RULES.md`,
  `specs/google-keep-parity/ROADMAP.md` and `.factory/decisions.md` were **not** modified to record
  D-13.
- `reports/KEEPLAB-AUTH-SYNC-DECISION-REGISTER.md` and
  `reports/KEEPLAB-AUTH-SYNC-HUMAN-DECISIONS.md` still show D-13 as `HUMAN_DECISION_PENDING`. That
  stale wording is **left as-is** and recorded as `MINOR_BACKLOG` in
  `reports/KEEPLAB-MINOR-BACKLOG.md` — **not a blocker**; editing those historical records is not
  required for M4.
- The canonical A0 governance amendment remains unrelated and untouched
  (`BLOCKED_BY_CONTRACT_GUARD`); M4 does not reopen it.

---

```
HUMAN_DECISIONS_FROZEN_FOR_M4: D-13 = ATTACHMENT_LIMITS_V1
HUMAN_DECISIONS_PENDING_NOT_BLOCKING_M4: D-05, D-11, D-12, D-14
SYNC_TOMBSTONE_RETENTION_OR_COMPACTION: SEPARATE / NOT_7_DAYS / IMPLEMENTATION_DECISION_PENDING
TOMBSTONE_GC_FOR_M4: DISABLED
PHASE_STATE: A0 READY · A1 PASS · A2 PASS · M2 PASS · M3 PASS · M4 AUTHORIZED_BY_HUMAN (A7) · A8+ NOT_STARTED
```
