# KEEPLAB-M3-OFFLINE-CONFLICT-EXECUTE

**The execution prompt for `KEEPLAB-M3-OFFLINE-CONFLICT-001`.**

Activate this contract and implement **M3 in ONE session**: A5, then an A5 **light checkpoint**,
then A6, then **one** verification pass. `PASS = STOP`.

- **Milestone:** `M3 = A5_OFFLINE_HARDENING + A6_CONFLICT_HANDLING`
- **Loop:** `PLAN ONCE → A5 EXECUTE → A5 LIGHT CHECKPOINT → A6 EXECUTE → VERIFY M3 ONCE → PASS = STOP`
- **Date (`D-06`):** 2026-10-06 (CST, UTC+08:00) · **Device:** `NOT_USED` · **Cloud:** `NOT_PROVISIONED`
- **Data stage:** `EXPERIMENTAL` — `DISPOSABLE_TEST_DATA`; `DEV_DATABASE_RESET_REQUIRED = YES`
- **Package:** `reports/contracts/KEEPLAB-M3-OFFLINE-CONFLICT-001/` — `READ_ONLY_INPUT`

---

## 0. What M3 is, and what it is not

**M3 IS:** A5 (bounded retry, manual retry, outbox durability, lost-wakeup protection, reconnect,
safe coalescing, process-death simulation) **plus** A6 (a persisted conflict record, the
authoritative conflict response, title/body Keep-Local/Keep-Server/Keep-Both, checklist and label
conflict semantics, server-authority metadata, explicit delete-vs-edit, 7-day product Trash distinct
from the sync tombstone, tombstone anti-resurrection with tombstone GC disabled).

**M3 IS NOT:** an A5 contract; an A6 contract; an A5/A6 review; a post-PASS audit; a separate D-06
governance task; A7 attachments; A8 multi-device hardening; A9 multi-account; collaboration; a push
provider; CRDT; automatic three-way text merge; account deletion; cloud deployment; release
hardening; production email; Google Keep work; Testapp or PowerAi.

```
PHASES ARE CHECKPOINTS, NOT BUREAUCRATIC STOPS.
A5 IS A LIGHT CHECKPOINT. DO NOT STOP AFTER A5.
DO NOT RUN THE MILESTONE GATE AT THE A5 CHECKPOINT.
```

## 1. Activation (do this before any write, then stop re-reading)

| # | Check | On failure |
|---|---|---|
| 1 | `HERMES_CONTRACT_PACKAGE` points at this package | set it (see `EXECUTOR-PROMPT.md`) |
| 2 | `sha256(contract_guard.py)` == `e418fc28b08ac7afe4fdd42ec44d572ddaa2f23f6200de300ecac211404b3746` | STOP — validated against a different guard |
| 3 | `pre_tool_call` hook wiring unchanged (`matcher write_file\|patch\|terminal`, `fail_closed: true`) | STOP |
| 4 | `load_contract(this package)` → `MANIFEST_OK`, `contract_id = KEEPLAB-M3-OFFLINE-CONFLICT-001` | STOP |
| 5 | Re-hash **every** `frozen_inputs` file **before the first write** | STOP — emit `STALE_M3_INPUT` |
| 6 | `KeepLab-Relay/backend/` present and buildable via `./gradlew -p backend` | STOP |
| 7 | The package must never be written: `reports/contracts/` is a forbidden path | STOP if a write is attempted |

Write the plan once, then execute it in order. Do not re-read the same architecture files
repeatedly.

## 2. Frozen human decision — `D-06` (honour it; never reinterpret it)

Record: `reports/KEEPLAB-M3-HUMAN-DECISIONS.md`.

```
D-06 = TRASH_RETENTION_7_DAYS
SOURCE = HUMAN_PROJECT_OWNER_APPROVAL
DATE = 2026-10-06
```

- The **product Trash** stays reversible for **7 days**; after that a note may become eligible for
  `FINAL_DELETE`, which produces the normal sync deletion / **tombstone** path.
- A note entering Trash must carry a **Trash timestamp**. `NoteEntity` currently has **none** — M3
  must add one (a schema bump is authorized).
- **Restoring** a trashed note clears/invalidates its Trash expiry state.
- **`LOCAL_ONLY`** notes: local time may drive local Trash retention.
- **Account-scoped synced notes:** do **not** permanently delete based solely on an unacknowledged
  offline client timestamp. Prefer the **authoritative server-accepted Trash time**.
- A note trashed **offline** may appear locally in Trash immediately, but automatic final deletion
  must **wait** until the server has accepted the Trash state (or another correctness-equivalent
  authority exists).
- After the authoritative 7-day expiry: enqueue/perform `FINAL_DELETE`, producing the normal
  tombstone path.

```
TRASH_RETENTION = 7 DAYS
SYNC_TOMBSTONE_RETENTION_OR_COMPACTION = SEPARATE / NOT_7_DAYS / NOT_CHOSEN
TOMBSTONE_RETENTION_EQUALS_TRASH_RETENTION = NO
TOMBSTONE_GC = DISABLED
NEVER choose a permanent tombstone retention duration.
NEVER garbage-collect a tombstone merely because it is older than 7 days.
```

## 3. Decisions that stay pending and do NOT block M3

`D-05` account-deletion retention · `D-11` push provider · `D-12` collaboration ·
`D-13` attachment limits · `D-14` formal spec package location.

Do **not** implement account deletion, a push provider, collaboration, attachments or a formal spec
relocation. Do **not** reopen A0/A1/A2/M2 without new explicit failure evidence.

## 4. Write surface

`allowed_paths` (project-relative to `/mnt/AndroidDev/Projects`):

```
KeepLab-Relay/backend/                                            <-- the whole backend directory
KeepLab-Relay/app/build.gradle.kts
KeepLab-Relay/gradle/libs.versions.toml
KeepLab-Relay/app/src/main/AndroidManifest.xml                    (only if genuinely needed)
KeepLab-Relay/app/src/main/java/com/keeplab/app/KeepLabApplication.kt
KeepLab-Relay/app/src/main/java/com/keeplab/app/MainActivity.kt
KeepLab-Relay/app/src/main/java/com/keeplab/app/data/
KeepLab-Relay/app/src/main/java/com/keeplab/app/model/
KeepLab-Relay/app/src/main/java/com/keeplab/app/di/
KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/conflict/      <-- NEW; the minimal conflict surface
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

**Backend write surface: `KeepLab-Relay/backend/` (whole directory).** `ROOT_GRADLE_CHANGE: NO`.

Blocked (do not write, do not "fix"): `app/src/main/res/`, `ui/theme/`, `ui/common/`,
`app/src/androidTest/`, `app/src/benchmark/`, `app/schemas/`, `proguard-rules.pro`, the root Gradle
files, the wrapper, `gradlew`, `specs/`, `verification/`, `harness/`, the governance markdown,
`Dockerfile`, `docker-compose.yml`, `server/`, `infra/`, `cloud/`, `firebase/`, `Testapp/`,
`PowerAi/`, the Stack's `specification/`, `verification/`, `verification-benchmark/`,
`references/`, `orchestration/hermes/evaluation_adapter/`, `evaluation/`, and **`reports/contracts/`**.

`KeepLab-Relay/app/**` is **not** broadly authorized — the surface is enumerated. A needed file
outside it is a STOP (`M3_SURFACE_BROADENING_REQUIRED`), never a silent broadening.

## 5. A5 — bounded retry

Implement a small bounded retry policy. Temporary conditions include: network transport failure,
HTTP `429`, generic `5xx`, a temporary refresh/network condition. Do **not** mark them permanent by
default. Retries must be **bounded**.

Recorded implementation decisions (adjust a constant only if deterministic evidence requires it, and
then record the final value — never remove the bound):

```
AUTO_RETRY_MAX_ATTEMPTS = 5            (per outbox mutation; the durable bound)
BACKOFF_POLICY          = EXPONENTIAL  (WorkManager BackoffPolicy.EXPONENTIAL for the run,
                                        plus the durable per-mutation attemptCount bound)
BACKOFF_INITIAL_DELAY   = 30 seconds
BACKOFF_MAX_DELAY       = 5 hours      (WorkManager's own exponential cap)
```

After retry exhaustion:

- the entity and its outbox row remain durable;
- the sync state becomes `SYNC_FAILED`;
- manual retry becomes available;
- **no local data is deleted**.

Do not ask the human unless a genuine product decision emerges.

## 6. A5 — manual retry

Provide **one** simple user-visible `Retry sync` action. Prefer the **existing**
Settings/Account/Sync-status surface (`ui/settings/` — `SettingsViewModel.syncNow()` already exists
and already requests the unique pipeline). Do **not** redesign the app.

Manual retry must: reset/re-arm eligible temporary failures; request the **same unique** sync
pipeline; preserve idempotency (the outbox `mutationId` stays the idempotency key).

## 7. A5 — outbox durability

The outbox must survive: repository recreation; worker recreation; application process
reconstruction.

```
NO IN-MEMORY-ONLY PENDING MUTATION AUTHORITY.
THE PERSISTED ROOM OUTBOX REMAINS AUTHORITY.
```

Test this deterministically. `AUTH_REQUIRED` must leave the outbox **untouched**.

## 8. A5 — lost wakeup (mandatory)

M2 has one unique `note_sync` pipeline with `ExistingWorkPolicy.KEEP` (`androidx.work 2.10.5`). A5
must prove that **a sync trigger arriving while sync work is already running is NOT silently lost**.

Procedure:

1. Inspect the **actual** WorkManager version (`gradle/libs.versions.toml` → `androidxWork`) and the
   current `ExistingWorkPolicy`.
2. Choose the **smallest correct** mechanism. Allowed examples: persistent request generation +
   drain-until-stable; serialized append/rerun; another deterministic equivalent.
3. Record the chosen mechanism as an implementation decision with its evidence.

```
DO NOT create parallel sync pipelines.
DO NOT blindly preserve ExistingWorkPolicy.KEEP if deterministic evidence shows it loses a trigger.
DO NOT blindly change it either.
```

Required test: `TRIGGER_DURING_ACTIVE_SYNC` → all work is eventually observed/applied; no duplicate
mutation apply; exactly one serialized pipeline.

## 9. A5 — reconnect

Network-required work must resume when connectivity returns. Use WorkManager constraints and the
existing unique pipeline. No FCM. No push provider. No permanent background socket.

## 10. A5 — coalescing

Implement safe, minimal outbox coalescing: avoid sending many obsolete `UPDATE` mutations for the
same entity when a later mutation supersedes them. Do **not** break `CREATE`, `DELETE`, Trash,
revision semantics or mutation idempotency. Rules must be deterministic and tested.

```
IF SAFE COALESCING FOR A MUTATION COMBINATION IS UNCLEAR: DO NOT COALESCE THAT COMBINATION.
CORRECTNESS > OPTIMIZATION.
```

## 11. A5 — process-death test

True physical-device process death is **not** required for M3. Prefer deterministic simulation:
persist Room state; destroy/recreate the repository and sync objects; resume using the persisted
outbox/checkpoint. If an existing WorkManager testing mechanism can cheaply validate worker
reconstruction, use it.

```
DO NOT USE: adb · Maestro · UiAutomator · device installation.
```

## 12. A5 light checkpoint (NOT a review — do not stop the session)

Record only:

```
BOUNDED_RETRY: READY
MANUAL_RETRY: READY
OUTBOX_DURABLE: READY
LOST_WAKEUP: PROTECTED
AUTH_REQUIRED_PRESERVES_OUTBOX: YES
A5_CHECKPOINT: READY_FOR_A6
```

Then **immediately continue into A6**. No full gate here. No separate A6 contract. No review.

## 13. A6 — conflict record

Conflicts must survive process death. Use a persisted conflict representation (a Room entity) if the
current model does not already provide one. Minimum information:

```
accountId · entity type · entity client UUID · conflict type · local state/payload ·
remote/server state/payload · local/base revision · server/current revision · createdAt ·
resolution state
```

Do **not** store secrets. Do **not** create a generic giant event system.

## 14. A6 — server conflict response

A stale `baseRevision` remains `HTTP 409 REVISION_CONFLICT`. A6 must provide enough authoritative
server state/revision to resolve the conflict (extend the 409 body with the current authoritative
revision and the current server payload for the entity). Do **not** rely on the client wall clock.
The server remains revision/order authority.

## 15. Title / body conflict

A concurrent title/body conflict **MUST NOT** silently overwrite text. Expose three explicit
choices: `KEEP_LOCAL`, `KEEP_SERVER`, `KEEP_BOTH`.

- `KEEP_LOCAL`: preserve local title/body; rebase against the current server revision; enqueue a new
  mutation; use the current account scope.
- `KEEP_SERVER`: accept the authoritative server version; update Room; clear the conflict safely.
- `KEEP_BOTH`: the original note becomes/keeps the authoritative server version; create a **SECOND**
  logical local note from the user's local conflicting content. The new note MUST have a **NEW
  client UUID**, a new local identity as appropriate, the **same `accountId`**, `SYNC_PENDING`, and a
  `CREATE` mutation in the outbox. **Never reuse** the original client UUID or the original server
  revision identity.

## 16. Checklist conflict

Checklist items already have stable UUIDs.

- concurrent additions: **both survive**;
- different items: merge independently;
- same item text conflict: the **server-accepted revision/order** is authority; the client wall clock
  is **not** authority;
- deletion vs edit for the same checklist item: must be explicit/non-silent.

Do **not** introduce a CRDT.

## 17. Label conflict

Label relationships use operation semantics (add/remove). Order by the **server-accepted
revision/order**, never the client wall clock. A later accepted `remove` must **not** be resurrected
by replaying an older `add`. Provide a deterministic test.

## 18. Metadata conflict

Metadata such as archive, pin, colour and Trash state may use last-server-accepted ordering using
the **server revision / server change order**. Do **not** use an unsynchronized client `updatedAt` as
conflict authority. Title/body remain explicit user-resolved conflicts.

## 19. Delete vs edit

Delete-vs-edit must be explicit. No silent resurrection. No silent discard of local edited content.
Represent the conflict. Minimum user outcome: `ACCEPT_DELETE` or `RESTORE_LOCAL` (equivalent names
allowed).

`RESTORE_LOCAL` creates/rebases a valid mutation against the current server state **without reusing
invalid deletion state**. If the remote note is already final-deleted and restoration means a
logically new note: use a **NEW client UUID**. Record the chosen semantics clearly.

## 20. Trash retention — 7 days

See §2. Implementation requirements:

- a note entering Trash gets a **Trash timestamp** (new local column; schema bump authorized);
- restoring clears/invalidates the Trash expiry state;
- `LOCAL_ONLY`: local time may drive retention;
- account-scoped synced notes: the **authoritative server-accepted Trash time** governs — never an
  unacknowledged offline client timestamp alone;
- a note trashed offline may appear locally in Trash immediately, but automatic final deletion waits
  until the server accepted the Trash state;
- after the authoritative 7-day expiry: enqueue/perform `FINAL_DELETE` → the normal tombstone path.

## 21. Tombstone rule

```
TRASH != TOMBSTONE.
7 DAYS APPLIES TO PRODUCT TRASH, NOT TO THE SYNC TOMBSTONE.
TOMBSTONE_GC = DISABLED is the accepted M3 posture.
DO NOT create a final tombstone retention duration.
```

Tombstone compaction may happen in a future Milestone **only** with an anti-resurrection protocol
proving that old clients cannot legally replay pre-delete state.

## 22. Anti-resurrection

A final-deleted note must not reappear because an old mutation or stale client state is replayed.
Required tests include: final delete → tombstone exists; old mutation arrives → the note remains
deleted; old delta/replay → the note remains deleted.

## 23. 404 rule remains

A remote/server `404` must **not** silently delete a live local note. A6 may convert it into a
resolvable/non-destructive failure state. No data loss.

## 24. AUTH_REQUIRED rule remains

`AUTH_REQUIRED` must preserve Room rows, the outbox, conflict records and the checkpoint. The user
may sign in again and continue.

## 25. Error / retry classification

Maintain a small explicit classification:

```
AUTH_REQUIRED · CONFLICT · TEMPORARY_RETRYABLE · PERMANENT_VALIDATION_FAILURE ·
NOT_FOUND_NON_DESTRUCTIVE · SUCCESS
```

Do not treat a generic `5xx` as permanent. Do not retry validation/permanent failures forever.

## 26. Test strategy (deterministic; no giant framework)

**A5 tests must cover at minimum:** offline mutation remains in the outbox; repository/worker
reconstruction preserves pending work; a temporary network failure retains data; bounded retries
stop; `SYNC_FAILED` surfaces; manual retry re-arms work; `AUTH_REQUIRED` keeps the outbox; reconnect
schedules/resumes; a trigger during an active worker is not lost; no parallel duplicate pipeline; a
duplicate mutation still applies once; safe coalescing.

**A6 tests must cover at minimum:** title/body conflict is explicit; `KEEP_LOCAL`; `KEEP_SERVER`;
`KEEP_BOTH`; `KEEP_BOTH` new UUID; concurrent checklist additions both survive; same checklist item
ordered by server authority; label remove not resurrected; metadata server-order LWW; delete-vs-edit
explicit; remote delete does not silently destroy a local edit; Trash restore before 7 days; 7-day
final-delete eligibility; offline unacknowledged Trash does not prematurely final-delete;
tombstone != Trash; stale replay cannot resurrect a tombstone.

Place tests in `app/src/test/**` (JVM) and `backend/src/test/**`. Use fakes/in-process doubles and
deterministic time. No device. No live PostgreSQL.

## 27. UI scope

Add only the minimal user-visible surfaces required by M3. Acceptable: sync-failed indicator;
`Retry sync`; conflict indicator; conflict resolution screen/dialog; Keep Local; Keep Server; Keep
Both; delete-vs-edit resolution.

Do **not** redesign Home, the theme, the navigation architecture or the note editor unless a tiny
integration point is needed.

## 28. Backend scope

The backend may extend: sync schema; conflict response payload; change-log semantics; Trash
timestamp; final-delete/tombstone handling — only as required by M3. Do **not** implement
attachments, object storage, collaboration, multi-device features or push.

## 29. No live PostgreSQL blocker

No Docker, no podman, no `psql` on this host. Do **not** install infrastructure inside M3. Use
deterministic service/store tests. Record `LIVE_POSTGRES_INTEGRATION = SKIPPED_TOOL_UNAVAILABLE`.
Do not weaken transactional semantics.

## 30. No device

M3 is device-free by default. Do **not** use adb, Maestro, UiAutomator, APK installation or
physical-device testing. Deterministic tests first.

## 31. Minor backlog

Do not clean the backlog by count. Append minor findings compactly to
`reports/KEEPLAB-MINOR-BACKLOG.md` and continue. Only fix a minor finding if it blocks M3, breaks
the build/tests, or repeatedly impedes implementation.

## 32. Process overhead

Do not spend large effort reviewing M2, rewriting governance, rechecking passed M2 gates, performing
full repo scans, or writing evidence before product work. After contract activation, targeted
discovery and one plan, begin implementation. If process-only work dominates implementation:
`PROCESS_OVERHEAD_TOO_HIGH` — simplify.

## 33. Final verification — ONCE

After A5 + A6, run **one** Milestone verification pass. Each gate runs **once**:

| # | Command | Runs |
|---|---|---|
| 1 | `cd /mnt/AndroidDev/Projects/KeepLab-Relay && ./gradlew -p backend test build` | ONCE |
| 2 | `cd /mnt/AndroidDev/Projects/KeepLab-Relay && ./gradlew :app:testDebugUnitTest :app:assembleDebug` | ONCE |

If one fails: fix the failed path only and rerun **only** the failed task. Do **not** rerun the
already-passed side. If the same failure survives two genuine fixes: **ONE** root cause analysis.

### 33.1 Post-run proof

Record: frozen-input before/after sha256; a scope scan (every created/modified file inside
`allowed_paths`; nothing under a forbidden path); a secret scan (clean); `backend/.env` absent; no
device operation; no cloud provisioning. Write the evidence under
`orchestration/hermes/evidence/keeplab-m3-offline-conflict/` and the report under `reports/`.

## 34. Acceptance checklist (M3 PASS requires all of these)

```
[ ] A5 bounded retries
[ ] retry exhaustion -> SYNC_FAILED
[ ] manual retry
[ ] outbox durability
[ ] AUTH_REQUIRED preserves outbox
[ ] reconnect behaviour
[ ] lost-wakeup protection
[ ] one serialized sync pipeline
[ ] safe coalescing
[ ] A6 persisted conflict handling
[ ] title/body explicit conflict
[ ] KEEP_LOCAL
[ ] KEEP_SERVER
[ ] KEEP_BOTH
[ ] KEEP_BOTH new UUID
[ ] checklist concurrent additions survive
[ ] label remove does not resurrect
[ ] metadata uses server authority
[ ] delete-vs-edit explicit
[ ] Trash retention = 7 days
[ ] Trash restore works
[ ] offline Trash not prematurely final-deleted
[ ] Trash != tombstone
[ ] tombstone anti-resurrection holds
[ ] no tombstone 7-day coupling
[ ] backend build PASS
[ ] Android build PASS
[ ] relevant tests PASS
[ ] no device
[ ] no cloud provisioning
[ ] no A7+ work
```

## 35. Stop

```
PASS = STOP.

No post-PASS review. No second audit. No separate A5/A6 contract. No A7.
No re-run of a passed gate side. No re-opening A0/A1/A2/M2.
```

If M3 PASSes, record the result, stop, and do not start A7 attachments, A8 multi-device, A9
multi-account or collaboration.
