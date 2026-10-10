# KEEPLAB-M3-OFFLINE-CONFLICT-EXECUTE — M3 execution report

**Contract:** `KEEPLAB-M3-OFFLINE-CONFLICT-001` (READ_ONLY_INPUT)
**Milestone:** `M3 = A5_OFFLINE_HARDENING + A6_CONFLICT_HANDLING`
**Loop:** `PLAN ONCE → A5 EXECUTE → A5 LIGHT CHECKPOINT → A6 EXECUTE → VERIFY M3 ONCE → PASS = STOP`
**Date (D-06):** 2026-10-06 (CST, UTC+08:00) · **Device:** `NOT_USED` · **Cloud:** `NOT_PROVISIONED`
**Data stage:** `EXPERIMENTAL` — `DISPOSABLE_TEST_DATA` · `DEV_DATABASE_RESET_REQUIRED = YES`
**Result:** **M3 PASS · STOP**

---

## 1. Activation (verified before the first write)

| # | Check | Result |
|---|---|---|
| 1 | `HERMES_CONTRACT_PACKAGE` → this package | set (inherited by the hook subprocess) |
| 2 | `sha256(contract_guard.py) == e418fc28…4b3746` | **MATCH** |
| 3 | `pre_tool_call` hook unchanged (`write_file\|patch\|terminal`, `fail_closed: true`) | **UNCHANGED** |
| 4 | `load_contract(this package)` → `MANIFEST_OK`, `contract_id = KEEPLAB-M3-OFFLINE-CONFLICT-001` | **OK** |
| 5 | Re-hash of every `frozen_inputs` file **before the first write** | **58/58 OK** |
| 6 | `KeepLab-Relay/backend/` present and buildable via `./gradlew -p backend` | **OK** |
| 7 | `reports/contracts/` never written | **NO WRITE** |

No guard patch, no hook edit, no config edit, no package write.

## 2. D-06 honoured exactly

`D-06 = TRASH_RETENTION_7_DAYS` (`HUMAN_PROJECT_OWNER_APPROVAL`, 2026-10-06), recorded in
`reports/KEEPLAB-M3-HUMAN-DECISIONS.md` (authored by the contract phase, **not edited**).
`SYNC_TOMBSTONE_RETENTION_OR_COMPACTION` stays `SEPARATE / NOT_7_DAYS / NOT_CHOSEN`;
`TOMBSTONE_GC = DISABLED`; no permanent tombstone retention duration was chosen anywhere.

## 3. A5 — offline hardening

| Decision | Final value | Where |
|---|---|---|
| `AUTO_RETRY_MAX_ATTEMPTS` | **5** (durable, per outbox mutation) | `data/sync/RetryPolicy.kt`; `outbox.attemptCount` |
| `BACKOFF_POLICY` | **EXPONENTIAL** | `RetryPolicy.BACKOFF_POLICY`; `NoteSyncWork.BACKOFF` |
| `BACKOFF_INITIAL_DELAY` | **30 s** | `RetryPolicy.BACKOFF_INITIAL_DELAY_SECONDS`; WorkManager `setBackoffCriteria` |
| `BACKOFF_MAX_DELAY` | **5 h** | `RetryPolicy.BACKOFF_MAX_DELAY_SECONDS` |
| Error/retry classification | `AUTH_REQUIRED · CONFLICT · TEMPORARY_RETRYABLE · PERMANENT_VALIDATION_FAILURE · NOT_FOUND_NON_DESTRUCTIVE · SUCCESS` | `data/sync/SyncErrorClass.kt` |
| Lost-wakeup mechanism | persisted-outbox **drain-until-stable** + worker **post-run follow-up** (`Result.retry()`), single `note_sync` pipeline (`ExistingWorkPolicy.KEEP`, androidx.work **2.10.5**, unchanged) | `SyncEngine.syncNow` / `hasEligiblePendingWork`; `SyncWorker.doWork` |

* **Bounded retry.** A temporary condition (transport, `429`, generic `5xx`, a refresh/network
  condition) is `TEMPORARY_RETRYABLE` and never permanent by default; a `4xx` other than `401/404/409`
  is a `PERMANENT_VALIDATION_FAILURE` and is not retried automatically. A mutation is attempted only
  while `attemptCount < 5` and its last recorded failure was temporary — so automatic retries always
  stop. After exhaustion the entity and its outbox row stay durable, the state becomes `SYNC_FAILED`,
  and nothing local is deleted.
* **Manual retry.** One user-visible **Retry sync** action on the existing Settings surface
  (`SettingsViewModel.syncNow()` → `SyncRetryCoordinator.retrySync()`): it re-arms eligible temporary
  failures (clears the durable bound and the recorded error, returns `SYNC_FAILED` entities to
  `SYNC_PENDING`) and requests the **same unique** `note_sync` pipeline; the outbox `mutationId`
  stays the idempotency key.
* **Outbox durability.** The persisted Room outbox is the only pending-mutation authority; the
  in-pass `attempted` set is bookkeeping, never authority. Proven deterministically across
  repository/engine/worker reconstruction.
* **Lost wakeup.** `KEEP` alone drops a trigger that arrives during a run, so a run drains until a
  pass makes no progress against the persisted outbox, and the worker guarantees one follow-up run
  when eligible work arrived after the last drain check. `KEEP` is neither blindly preserved nor
  blindly replaced; no parallel pipeline exists.
* **Reconnect.** `NetworkType.CONNECTED` on the one unique request; no FCM, no push provider, no
  background socket.
* **Coalescing.** An obsolete pending `UPDATE` is dropped only when the entity's entire pending set
  is `UPDATE`; a pending `CREATE`/`DELETE` makes the combination unclear and it is **not** coalesced.
* **Process death.** Deterministic simulation only (persist Room state, destroy/recreate the
  repository and sync objects, resume from the persisted outbox/checkpoint). No adb, no Maestro, no
  UiAutomator, no APK install.

**A5 light checkpoint** (`orchestration/hermes/evidence/keeplab-m3-offline-conflict/A5-CHECKPOINT.md`):
`BOUNDED_RETRY: READY · MANUAL_RETRY: READY · OUTBOX_DURABLE: READY · LOST_WAKEUP: PROTECTED ·
AUTH_REQUIRED_PRESERVES_OUTBOX: YES · A5_CHECKPOINT: READY_FOR_A6` — then continued directly into A6.

## 4. A6 — conflict handling

* **Persisted conflict record.** A first-class Room table `conflicts` (`data/local/ConflictEntity.kt`)
  with `accountId · entityType · entityClientUuid · conflictType · local payload · remote/server
  payload · local/base revision · server revision · createdAt · resolution state`. No secret, no
  generic event system. Room moves 4 → 5 by the authorized direct experimental bump; a note entering
  Trash now carries `trashedAt` (`TRASH != TOMBSTONE`).
* **Authoritative server response.** A stale `baseRevision` stays `HTTP 409 REVISION_CONFLICT`, and
  the body is extended with the current authoritative revision, the current server payload and the
  deleted flag (`ConflictState` → `ConflictResponse`). The server stays the only revision/order
  authority; no client wall clock participates.
* **Title/body.** an explicit `PENDING` conflict is recorded and the local text is never silently
  overwritten. `KEEP_LOCAL` preserves the local text, rebases against the current server revision and
  re-enqueues in the current account scope; `KEEP_SERVER` accepts the authoritative version and clears
  the conflict; `KEEP_BOTH` leaves the server version on the original and creates a **second** note
  with a **NEW client UUID**, the **same `accountId`**, `SYNC_PENDING` and a `CREATE` mutation —
  never reusing the original client UUID or revision identity.
* **Checklist.** Concurrent additions (distinct stable UUIDs) both survive; different items merge
  independently; a same-item divergence is resolved by the server-accepted revision/order; item
  deletion-vs-edit is explicit. No CRDT.
* **Labels.** Membership is an *operation* (`add`/`remove`) ordered by the revision stored per
  relation; an op whose revision is not greater than the one already applied is ignored, so a later
  accepted `remove` is never resurrected by replaying an older `add`.
* **Metadata** (archive, pin, colour, Trash state) resolves by the server revision / server change
  order; an unsynchronized client `updatedAt` is never the authority.
* **Delete vs edit.** explicit `ACCEPT_DELETE` / `RESTORE_LOCAL`. A remote delete racing a local edit
  records a `DELETE_VS_EDIT` conflict instead of destroying the edit. `RESTORE_LOCAL` rebases against
  the current server state and, when the remote is already final-deleted, carries the content into a
  logically new note with a **NEW client UUID** and a `CREATE` mutation.
* **Trash retention = 7 days.** Trashing stamps `trashedAt`; restoring clears it; a `LOCAL_ONLY` note
  may use local time; an account-scoped note is eligible for `FINAL_DELETE` only once the server has
  **accepted** the Trash state (`SYNCED` with a server revision) and its `trashedAt` holds the
  authoritative server-accepted time. An offline, unacknowledged Trash is never final-deleted. After
  the authoritative 7-day expiry the note is tombstoned and a normal `DELETE` mutation is enqueued.
* **Tombstone.** `TRASH != TOMBSTONE`; `TOMBSTONE_GC = DISABLED`; no tombstone retention duration is
  chosen and no code path purges a tombstone by age. Anti-resurrection holds: a final delete leaves a
  tombstone and an old mutation or stale delta/replay cannot bring the note back.
* **404** stays `NOT_FOUND_NON_DESTRUCTIVE`: it never deletes a live local note. **`AUTH_REQUIRED`**
  preserves Room rows, the outbox, conflict records and the checkpoint.
* **UI** is the minimal surface only: a sync-failed indicator, `Retry sync`, a conflict indicator, and
  a conflict-resolution screen (`ui/conflict/`) with Keep Local / Keep Server / Keep Both and
  Accept Delete / Restore Local. Home, the theme, the navigation architecture and the note editor are
  not redesigned.

## 5. Verification — ONE pass, each gate ONCE

| Gate | Command | Runs | Result |
|---|---|---|---|
| BACKEND | `cd /mnt/AndroidDev/Projects/KeepLab-Relay && ./gradlew -p backend test build` | 1 | **PASS** (62 tests, 0 failures, 0 errors) |
| ANDROID | `cd /mnt/AndroidDev/Projects/KeepLab-Relay && ./gradlew :app:testDebugUnitTest :app:assembleDebug` | 1 | **PASS** (159 tests, 0 failures; `app-debug.apk` built, 22,250,735 bytes) |

No failed task existed, so nothing was re-run. `LIVE_POSTGRES_INTEGRATION = SKIPPED_TOOL_UNAVAILABLE`
(no docker, no podman, no psql on this host); no infrastructure was installed and the transactional
semantics were not weakened.

**Post-run proof** (`orchestration/hermes/evidence/keeplab-m3-offline-conflict/`):

* `frozen-input-verification.json` — 58 frozen inputs; **20 changed, all inside `allowed_paths`**;
  38 re-hash byte-identical; **0** changed outside `allowed_paths`; **0** changed inside a forbidden
  path; protected snapshot (root Gradle, wrapper, `MISSION.md`, `FACTORY_RULES.md`, `res/`, `theme/`,
  `common/`, androidTest, benchmark, schemas, contract_guard, A0/A1/A2/M2 packages, this package)
  **untouched**.
* `scope-and-secret-scan.json` — 47 writes this session; **0 forbidden-path writes**; the single
  out-of-scope mtime entry is the Contract Guard hook's own decision log; **0 real secret hits**
  across 253 scanned files; `backend/.env` **absent**; no device operation; no cloud provisioning.
* `gate-and-milestone-verification.json` — the per-class gate results and the APK artifact.
* `A5-CHECKPOINT.md` — the A5 light checkpoint.

## 6. M3 acceptance checklist

```
[x] A5 bounded retries
[x] retry exhaustion -> SYNC_FAILED
[x] manual retry
[x] outbox durability
[x] AUTH_REQUIRED preserves outbox
[x] reconnect behaviour
[x] lost-wakeup protection
[x] one serialized sync pipeline
[x] safe coalescing
[x] A6 persisted conflict handling
[x] title/body explicit conflict
[x] KEEP_LOCAL
[x] KEEP_SERVER
[x] KEEP_BOTH
[x] KEEP_BOTH new UUID
[x] checklist concurrent additions survive
[x] label remove does not resurrect
[x] metadata uses server authority
[x] delete-vs-edit explicit
[x] Trash retention = 7 days
[x] Trash restore works
[x] offline Trash not prematurely final-deleted
[x] Trash != tombstone
[x] tombstone anti-resurrection holds
[x] no tombstone 7-day coupling
[x] backend build PASS
[x] Android build PASS
[x] relevant tests PASS
[x] no device
[x] no cloud provisioning
[x] no A7+ work
```

## 7. Test coverage added by M3

**Android (JVM, `${app}/src/test/…`, +43 tests → 159 total).**
`M3RetryClassificationTest`, `M3BoundedRetryTest`, `M3OutboxDurabilityTest` (incl.
`TRIGGER_DURING_ACTIVE_SYNC`), `M3CoalescingTest`, `M3ConflictResolutionTest`,
`M3ChecklistLabelMetadataTest`, `M3TrashRetentionTest`.

**Backend (JUnit 5, `backend/src/test/…`, +9 tests → 62 total).**
`M3SyncConflictTest` (409 body carries the authoritative revision and payload; no resurrection; the
change log is the ordering authority), `M3TrashTombstoneTest` (server-accepted Trash time; restore
clears it; final delete is a tombstone; no tombstone is purged by age).

## 8. Errors, deviations and stop conditions

* **Contract deviations:** none.
* **Stop conditions triggered:** none.
* **Root-cause analyses:** none required (no gate failure).
* **Minor findings** appended compactly to `reports/KEEPLAB-MINOR-BACKLOG.md`
  (`MB-M3-006 … MB-M3-011`). No backlog item was fixed and none blocks M3.
* **Not resolved by M3** (unchanged): `D-05`, `D-11`, `D-12`, `D-13`, `D-14`,
  `SYNC_TOMBSTONE_RETENTION_OR_COMPACTION`; `A7`, `A8`, `A9` **NOT_STARTED**.

---

```
M3 RESULT: PASS (A5 + A6 verified once)
PASS = STOP.
No post-PASS review. No second audit. No separate A5/A6 contract. No A7.
No re-run of a passed gate side. No re-opening of A0/A1/A2/M2.
```
