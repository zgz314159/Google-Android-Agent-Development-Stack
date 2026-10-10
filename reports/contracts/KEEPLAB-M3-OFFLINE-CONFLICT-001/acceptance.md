# Acceptance — KEEPLAB-M3-OFFLINE-CONFLICT-001

**Contract:** `KEEPLAB-M3-OFFLINE-CONFLICT-001`
**Milestone:** `M3` = `A5_OFFLINE_HARDENING` + `A6_CONFLICT_HANDLING` — **one** contract, **one** session, **one** verification pass
**Execution model:** `PLAN ONCE → A5 EXECUTE → A5 LIGHT CHECKPOINT → A6 EXECUTE → VERIFY M3 ONCE → PASS = STOP`
**Date:** 2026-10-06 (CST, UTC+08:00) · **Device:** `NOT_USED` · **Cloud:** `NOT_PROVISIONED`
**Data stage:** `EXPERIMENTAL` — `DISPOSABLE_TEST_DATA`; `DEV_DATABASE_RESET_REQUIRED = YES`
**Frozen human decision:** `D-06 = TRASH_RETENTION_7_DAYS` (`HUMAN_PROJECT_OWNER_APPROVAL`, 2026-10-06)

---

## 0. What this package is

This package is a **TEMPORARY EXECUTION CONTRACT**. It exists so that a later **fresh** Hermes
session can implement A5 and then A6 through the **same unmodified Contract Guard**, under an
explicit and bounded write surface, with A5 kept as a **light checkpoint inside one session** and
**one** final verification pass.

- `package_role`: `TEMPORARY_EXECUTION_CONTRACT`
- `package_access`: `READ_ONLY_INPUT` (enforced by `reports/contracts/` being a forbidden path)
- `implementation_authorization`: `GRANTED_TO_M3_EXECUTION_TASK_ONLY`
- This contract-creation task performed targeted discovery and authored the package. It did **not**
  implement M3, and it did **not** create an A5 contract, an A6 contract, an A5/A6 review, a
  post-PASS audit or a separate D-06 governance task.

## 1. Machine-readable semantics

| Key | Value |
|---|---|
| `contract_id` | `KEEPLAB-M3-OFFLINE-CONFLICT-001` |
| `milestone` | `M3 = A5 (offline hardening) + A6 (conflict handling)` |
| `execution_model` | `PLAN ONCE → A5 EXECUTE → A5 LIGHT CHECKPOINT → A6 EXECUTE → VERIFY M3 ONCE → PASS = STOP` |
| `contracts_in_milestone` | `1` |
| `execution_sessions` | `1` |
| `verification_passes` | `1` |
| `root_gradle_change_required` | `NO` |
| `android_surface_policy` | `ENUMERATED_NOT_WHOLE_APP` |
| `device` | `NOT_USED` |
| `cloud` | `NOT_PROVISIONED` |
| `LIVE_POSTGRES_INTEGRATION` | `SKIPPED_TOOL_UNAVAILABLE` (no docker, no podman, no psql on this host) |
| `TOMBSTONE_GC` | `DISABLED` |
| `SYNC_TOMBSTONE_RETENTION` | `NOT_7_DAYS · NOT_CHOSEN · SEPARATE_CONCERN` |

## 2. Frozen human decision — `D-06` (do not reopen, do not reinterpret)

```
D-06 = TRASH_RETENTION_7_DAYS
SOURCE = HUMAN_PROJECT_OWNER_APPROVAL
DATE = 2026-10-06
RECORD = reports/KEEPLAB-M3-HUMAN-DECISIONS.md
```

- The **product Trash** remains reversible for **7 days**. After that period a note may become
  eligible for `FINAL_DELETE`, which produces the normal sync deletion / **tombstone** path.
- A note entering Trash carries a **Trash timestamp**; restoring it clears/invalidates the expiry.
- For an **account-scoped synced note**, the **authoritative server-accepted Trash time** governs.
  An unacknowledged offline client timestamp alone must **never** cause a permanent deletion.
- For a **`LOCAL_ONLY`** note, local time may drive local Trash retention.

Explicitly **not** decided here, and never to be read out of `D-06`:

```
SYNC_TOMBSTONE_RETENTION_OR_COMPACTION : SEPARATE / IMPLEMENTATION_DECISION_PENDING
TOMBSTONE_RETENTION_EQUALS_TRASH_RETENTION : NO
SYNC_TOMBSTONE_RETENTION = 7 DAYS : NO
PERMANENT_TOMBSTONE_RETENTION_DURATION : NOT CHOSEN (do not choose one)
TOMBSTONE_GC_FOR_M3 : DISABLED
```

## 3. What M3 must add — A5 (offline hardening)

| Area | Required behaviour |
|---|---|
| Error/retry classification | one small explicit enumeration: `AUTH_REQUIRED` · `CONFLICT` · `TEMPORARY_RETRYABLE` · `PERMANENT_VALIDATION_FAILURE` · `NOT_FOUND_NON_DESTRUCTIVE` · `SUCCESS` |
| Temporary conditions | transport failure, HTTP `429`, generic `5xx`, a temporary refresh/network condition — **never** permanent by default |
| Bounded retry | bounded, with recorded `AUTO_RETRY_MAX_ATTEMPTS` · `BACKOFF_POLICY` · `BACKOFF_INITIAL_DELAY` · `BACKOFF_MAX_DELAY` |
| Retry exhaustion | entity + outbox stay durable; syncing becomes `SYNC_FAILED`; **no local data deleted** |
| Manual retry | one user-visible `Retry sync` on the existing Settings/Account/Sync-status surface; re-arms eligible temporary failures; same unique pipeline; idempotent |
| Outbox durability | persisted Room outbox is authority; survives repository recreation, worker recreation, process reconstruction; **no** in-memory-only authority |
| Lost wakeup | a trigger arriving during an active sync is **not lost**; smallest correct mechanism chosen against the real WorkManager version; test `TRIGGER_DURING_ACTIVE_SYNC` |
| One pipeline | exactly one **serialized** `note_sync` pipeline; no parallel pipeline; a duplicate mutation still applies once |
| Reconnect | network-required work resumes on connectivity via constraints + the existing unique pipeline; no FCM, no push, no permanent socket |
| Coalescing | safe + minimal; preserves CREATE / DELETE / Trash / revision semantics / idempotency; unclear combinations are **not** coalesced |
| Process death | deterministic simulation only (persist Room state, destroy/recreate objects, resume); no adb, no Maestro, no UiAutomator, no device |

## 4. What M3 must add — A6 (conflict handling)

| Area | Required behaviour |
|---|---|
| Persisted conflict record | survives process death; `accountId`, entity type, entity client UUID, conflict type, local state/payload, remote/server state/payload, local/base revision, server/current revision, `createdAt`, resolution state; **no secrets**; **no** generic event system |
| Server conflict response | stale `baseRevision` stays `409 REVISION_CONFLICT` and carries enough authoritative state/revision to resolve; **never** client wall clock |
| Title/body | **never** silently overwritten; exactly `KEEP_LOCAL` / `KEEP_SERVER` / `KEEP_BOTH` |
| `KEEP_LOCAL` | preserve local title/body · rebase on the current server revision · enqueue a new mutation · current account scope |
| `KEEP_SERVER` | accept the authoritative server version · update Room · clear the conflict safely |
| `KEEP_BOTH` | original note keeps the authoritative server version · a **SECOND** logical local note is created from the local conflicting content with a **NEW client UUID**, same `accountId`, `SYNC_PENDING`, `CREATE` mutation · never reuse the original client UUID or server revision identity |
| Checklist | concurrent additions both survive · different items merge independently · same item resolved by server-accepted revision/order · deletion-vs-edit explicit · **no CRDT** |
| Labels | operation semantics ordered by server-accepted revision/order; a later accepted remove is **not** resurrected by an older add |
| Metadata | archive / pin / colour / Trash via last-server-accepted ordering; **never** an unsynchronized client `updatedAt` |
| Delete-vs-edit | explicit: `ACCEPT_DELETE` or `RESTORE_LOCAL`; no silent resurrection; no silent discard; `RESTORE_LOCAL` rebases without reusing invalid deletion state; a logically new note gets a **NEW client UUID** |
| Trash retention | `7 DAYS`; Trash timestamp; restore invalidates expiry; offline Trash is **not** prematurely final-deleted |
| Tombstone | Trash ≠ tombstone; `TOMBSTONE_GC = DISABLED`; no retention duration chosen; no GC by age |
| Anti-resurrection | final delete → tombstone exists; an old mutation / stale delta replay cannot resurrect the note |
| `404` | never silently deletes a live local note; may become a resolvable/non-destructive failure state |
| `AUTH_REQUIRED` | preserves Room rows, outbox, conflict records and checkpoint |

## 5. Allowed write surface (exhaustive)

Project-relative to `/mnt/AndroidDev/Projects` (the Contract Guard's `source_root`). A path matching
neither list is BLOCKED (`UNCLASSIFIED_FAIL_CLOSED`); `forbidden_paths` is tested first.

```
KeepLab-Relay/backend/
KeepLab-Relay/app/build.gradle.kts
KeepLab-Relay/gradle/libs.versions.toml
KeepLab-Relay/app/src/main/AndroidManifest.xml                 (only if genuinely needed)
KeepLab-Relay/app/src/main/java/com/keeplab/app/KeepLabApplication.kt
KeepLab-Relay/app/src/main/java/com/keeplab/app/MainActivity.kt
KeepLab-Relay/app/src/main/java/com/keeplab/app/data/
KeepLab-Relay/app/src/main/java/com/keeplab/app/model/
KeepLab-Relay/app/src/main/java/com/keeplab/app/di/
KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/conflict/      (NEW - minimal conflict surface)
KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/settings/
KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/auth/
KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/navigation/
KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/trash/
KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/note/
KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/editor/
KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/home/
KeepLab-Relay/app/src/test/
Google-Android-Agent-Development-Stack/reports/
Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/keeplab-m3-offline-conflict/
```

**Backend write surface: `KeepLab-Relay/backend/` (whole directory).**

Blocked, notably: `app/src/main/res/`, `ui/theme/`, `ui/common/`, `app/src/androidTest/`,
`app/src/benchmark/`, `app/schemas/`, `proguard-rules.pro`, the root Gradle files, the wrapper,
`gradlew`, `specs/`, `verification/`, `harness/`, the governance markdown, `Dockerfile`,
`docker-compose.yml`, `server/`, `infra/`, `cloud/`, `firebase/`, `Testapp/`, `PowerAi/`, the
Stack's `specification/`, `verification/`, `verification-benchmark/`, `references/`,
`orchestration/hermes/evaluation_adapter/`, `evaluation/`, and **`reports/contracts/`** (so this
package is a read-only input to its own execution session).

`KeepLab-Relay/app/**` is **not** authorized as a whole. Themes, shared widgets, resources,
`androidTest`, `benchmark` and schema exports are blocked. A needed change there is a STOP
(`M3_SURFACE_BROADENING_REQUIRED`), not a silent broadening.

## 6. Acceptance criteria

### AC-M3-001 — explicit error/retry classification

`PASS` requires a small explicit classification in code
(`AUTH_REQUIRED` / `CONFLICT` / `TEMPORARY_RETRYABLE` / `PERMANENT_VALIDATION_FAILURE` /
`NOT_FOUND_NON_DESTRUCTIVE` / `SUCCESS`), with transport failure, `429`, generic `5xx` and a
temporary refresh/network condition classified temporary and **never** permanent by default, and
validation/permanent failures not retried forever. A remote `404` stays non-destructive.
Evidence: `data/remote/**`, `data/sync/**` and their deterministic JVM tests.

### AC-M3-002 — bounded retry stops

`PASS` requires bounded retries with recorded `AUTO_RETRY_MAX_ATTEMPTS`, `BACKOFF_POLICY`,
`BACKOFF_INITIAL_DELAY`, `BACKOFF_MAX_DELAY`, and a deterministic test proving the bound is reached
and automatic retries then **stop**.

### AC-M3-003 — retry exhaustion surfaces `SYNC_FAILED`

`PASS` requires that after exhaustion the entity and its outbox row remain durable, the sync state
becomes `SYNC_FAILED`, and **no local data is deleted** on any failure path.

### AC-M3-004 — manual `Retry sync`

`PASS` requires one user-visible `Retry sync` action on the existing Settings/Account/Sync-status
surface that re-arms eligible temporary failures, requests the **same unique** `note_sync` pipeline
and preserves idempotency (the outbox `mutationId` stays the idempotency key). The app is not
redesigned.

### AC-M3-005 — outbox durability

`PASS` requires the persisted Room outbox to be the only pending-mutation authority and to survive
repository recreation, worker recreation and process reconstruction. Evidence: a deterministic
simulation that persists Room state, destroys/recreates the repository and sync objects, and resumes
from the persisted outbox/checkpoint. **No** in-memory-only pending authority.

### AC-M3-006 — `AUTH_REQUIRED` preserves everything

`PASS` requires `AUTH_REQUIRED` to leave Room rows, the outbox, conflict records and the checkpoint
untouched, with a later sign-in resuming work.

### AC-M3-007 — reconnect resumption

`PASS` requires network-required work to resume when connectivity returns, using WorkManager
constraints and the existing unique pipeline only. No FCM, no push provider, no permanent
background socket.

### AC-M3-008 — lost wakeup protected

`PASS` requires: the actual WorkManager version (`androidx.work 2.10.5`) and the current
`ExistingWorkPolicy` are inspected first; the **smallest correct** mechanism is selected and
recorded (persistent request generation + drain-until-stable, serialized append/rerun, or a
deterministic equivalent); `ExistingWorkPolicy.KEEP` is neither blindly preserved nor blindly
replaced. The `TRIGGER_DURING_ACTIVE_SYNC` test proves all work is eventually observed/applied.

### AC-M3-009 — one serialized pipeline, no duplicate apply

`PASS` requires exactly one serialized `note_sync` pipeline, no parallel duplicate pipeline, and a
duplicate mutation still applying exactly once (the server `mutation_id` dedupe remains the
authority).

### AC-M3-010 — safe coalescing

`PASS` requires deterministic, tested coalescing that collapses obsolete superseded `UPDATE`s for
the same entity without breaking `CREATE`, `DELETE`, Trash, revision semantics or mutation
idempotency, and that leaves an unclear combination **un-coalesced**. Correctness > optimization.

### AC-M3-011 — persisted conflict record

`PASS` requires a Room-persisted conflict record that survives process death and carries at minimum
`accountId`, entity type, entity client UUID, conflict type, local state/payload, remote/server
state/payload, local/base revision, server/current revision, `createdAt` and resolution state. No
secrets. No generic giant event system.

### AC-M3-012 — authoritative server conflict response

`PASS` requires a stale `baseRevision` to remain `409 REVISION_CONFLICT` and the response to carry
enough authoritative server state/revision to resolve the conflict without any client wall clock.
The server remains the single revision/order authority.

### AC-M3-013 — title/body conflict is explicit

`PASS` requires a concurrent title/body divergence to be surfaced as an explicit conflict and the
local text to **never** be silently overwritten.

### AC-M3-014 — `KEEP_LOCAL`

`PASS` requires `KEEP_LOCAL` to preserve the local title/body, rebase against the current server
revision, enqueue a new mutation and use the current account scope.

### AC-M3-015 — `KEEP_SERVER`

`PASS` requires `KEEP_SERVER` to accept the authoritative server version, update Room and clear the
conflict safely.

### AC-M3-016 — `KEEP_BOTH` creates a NEW client UUID

`PASS` requires `KEEP_BOTH` to keep the authoritative server version on the original entity and to
create a **SECOND logical local note** from the user's local conflicting content with:
a **NEW client UUID** · a new local identity as appropriate · the **same `accountId`** ·
`SYNC_PENDING` · a **`CREATE`** mutation in the outbox. The original client UUID and the original
server revision identity are **never** reused.

### AC-M3-017 — checklist concurrent additions survive

`PASS` requires concurrent checklist additions to both survive and different items to merge
independently (stable item UUIDs).

### AC-M3-018 — checklist same-item order

`PASS` requires a same-item text conflict to resolve by the **server-accepted revision/order**, the
client wall clock to be **no** authority, and deletion-vs-edit of the same item to be explicit and
non-silent. No CRDT.

### AC-M3-019 — label remove is not resurrected

`PASS` requires label add/remove to be ordered by the server-accepted revision/order and a later
accepted remove to be **not** resurrected by replaying an older add, proven by a deterministic test.

### AC-M3-020 — metadata uses server authority

`PASS` requires archive / pin / colour / Trash state to resolve by last-server-accepted ordering
(server revision / server change order) and an unsynchronized client `updatedAt` to never be the
conflict authority.

### AC-M3-021 — delete-vs-edit is explicit

`PASS` requires an explicit represented conflict with `ACCEPT_DELETE` and `RESTORE_LOCAL`
(equivalent names allowed): no silent resurrection, no silent discard of local edited content;
`RESTORE_LOCAL` creates/rebases a valid mutation against the current server state without reusing
invalid deletion state, and uses a **NEW client UUID** where restoration means a logically new note.
The chosen semantics are recorded clearly.

### AC-M3-022 — Trash retention is 7 days

`PASS` requires `TRASH_RETENTION = 7 DAYS`; a note entering Trash carries a Trash timestamp;
restoring clears/invalidates the Trash expiry; `LOCAL_ONLY` notes may use local time; account-scoped
synced notes use the **authoritative server-accepted Trash time**.

### AC-M3-023 — offline Trash is not prematurely final-deleted

`PASS` requires a note trashed offline to appear locally in Trash immediately while automatic final
deletion waits until the server accepted the Trash state; after the authoritative 7-day expiry
`FINAL_DELETE` is enqueued/performed and produces the normal tombstone path.

### AC-M3-024 — Trash ≠ tombstone, no 7-day coupling

`PASS` requires Trash to stay structurally distinct from the sync tombstone, `TOMBSTONE_GC` to be
`DISABLED`, no permanent tombstone retention duration to be chosen anywhere, and no tombstone to be
garbage-collected merely for being older than 7 days.

### AC-M3-025 — tombstone anti-resurrection holds

`PASS` requires: final delete → a tombstone exists; an old mutation arriving → the note remains
deleted; an old delta/replay → the note remains deleted.

### AC-M3-026 — one verification pass, boundaries held

`PASS` requires both gates to run **once** each, in one pass, with a failure fixing only the failed
path and re-running only the failed task:

| # | Command | Runs |
|---|---|---|
| 1 | `cd /mnt/AndroidDev/Projects/KeepLab-Relay && ./gradlew -p backend test build` | ONCE |
| 2 | `cd /mnt/AndroidDev/Projects/KeepLab-Relay && ./gradlew :app:testDebugUnitTest :app:assembleDebug` | ONCE |

plus: frozen inputs re-hash byte-identical; the scope scan shows changes only inside
`allowed_paths` and nothing under a forbidden path; the secret scan is clean; no token plaintext is
written into reports/evidence/logs; **no device**; **no cloud provisioning**; **no A7+ work**;
`PASS = STOP`.

## 7. Required guard classifications (validated in this phase, simulated)

| Target | Expected |
|---|---|
| `KeepLab-Relay/app/src/main/java/com/keeplab/app/data/sync/SyncEngine.kt` | `ALLOW` |
| `KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/conflict/ConflictResolutionScreen.kt` | `ALLOW` |
| `KeepLab-Relay/app/src/test/java/com/keeplab/app/data/M3ConflictTest.kt` | `ALLOW` |
| `KeepLab-Relay/backend/src/main/kotlin/com/keeplab/backend/sync/SyncModels.kt` | `ALLOW` |
| `KeepLab-Relay/backend/src/main/resources/db/migration/V4__m3_conflict.sql` | `ALLOW` |
| `Google-Android-Agent-Development-Stack/reports/KEEPLAB-M3-OFFLINE-CONFLICT-EXECUTION.md` | `ALLOW` |
| `.../orchestration/hermes/evidence/keeplab-m3-offline-conflict/result.json` | `ALLOW` |
| `KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/theme/Theme.kt` | `BLOCK` |
| `KeepLab-Relay/app/src/main/res/values/strings.xml` | `BLOCK` |
| `KeepLab-Relay/app/src/androidTest/java/com/keeplab/app/verify/X.kt` | `BLOCK` |
| `KeepLab-Relay/app/src/benchmark/...` | `BLOCK` |
| `KeepLab-Relay/settings.gradle.kts` / `build.gradle.kts` / `gradle.properties` / `gradlew` | `BLOCK` |
| `KeepLab-Relay/MISSION.md` / `FACTORY_RULES.md` | `BLOCK` |
| `Google-Android-Agent-Development-Stack/reports/contracts/KEEPLAB-M3-OFFLINE-CONFLICT-001/implementation-contract.json` | `BLOCK` |
| `Google-Android-Agent-Development-Stack/orchestration/hermes/evaluation_adapter/contract_guard.py` | `BLOCK` |
| `Testapp/...` / `PowerAi/...` | `BLOCK` |
| an unlisted project path | `BLOCK` (`UNCLASSIFIED_FAIL_CLOSED`) |
| a path outside `/mnt/AndroidDev/Projects` | `ALLOW` (`OUT_OF_CONTRACT_SCOPE`) |

The recorded simulation lives at
`orchestration/hermes/evidence/keeplab-m3-offline-conflict-contract/guard-simulation.json`.

## 8. Readiness gates

```
EXECUTOR-PROMPT: READY
CONTRACT VALIDATION: PASS
STATUS: READY
NEXT: KEEPLAB-M3-OFFLINE-CONFLICT-EXECUTE
```

If the guard sha256 at execution start differs from
`e418fc28b08ac7afe4fdd42ec44d572ddaa2f23f6200de300ecac211404b3746`, the contract was validated
against a **different** guard: STOP.
