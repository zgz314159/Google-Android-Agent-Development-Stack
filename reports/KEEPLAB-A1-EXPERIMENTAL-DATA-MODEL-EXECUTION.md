# KEEPLAB-A1-EXPERIMENTAL-DATA-MODEL-EXECUTION

**Contract:** `KEEPLAB-A1-EXPERIMENTAL-DATA-MODEL-001`
**Phase:** `A1_EXPERIMENTAL_DATA_MODEL`
**Date:** 2026-10-06 (CST, UTC+08:00)
**Human authorization:** D-15 `YES_BOUNDED_ACCOUNT_NETWORK_UNLOCK` (recorded; not reinterpreted, not re-asked)
**Package declaration:** `CONTRACT_PACKAGE: READ_ONLY_INPUT`
**Loop:** `PLAN ONCE -> EXECUTE -> VERIFY ONCE -> PASS = STOP`

```
KEEPLAB-A1-EXPERIMENTAL-DATA-MODEL-EXECUTE
PROJECT DATA STAGE: EXPERIMENTAL
DEV_DATABASE_RESET_REQUIRED: YES
PRIMARY_KEY_STRATEGY: KEEP_LONG_LOCAL_PK_ADD_UNIQUE_CLIENT_UUID
CURRENT DB VERSION: 2 -> 3
clientUuid / accountId / syncState / serverRevision / deletedAt: PASS
TRASH != TOMBSTONE: PASS
ROOM SCHEMA (KSP generated, version 3): PASS
GRADLE GATE (testDebugUnitTest + assembleDebug, run once): PASS
PROTECTED FILES BYTE-IDENTICAL: PASS
NETWORK / AUTH / BACKEND / GRADLE / UI / DEVICE UNTOUCHED: PASS
A1: PASS
NEXT: A2 (READY_FOR_SEPARATE_CONTRACT) — not started here
```

## 1. Contract activation (passed before any mutation)

| Check | Expected | Observed | Result |
|---|---|---|---|
| `load_contract(package_dir).contract_id` | `KEEPLAB-A1-EXPERIMENTAL-DATA-MODEL-001` | `KEEPLAB-A1-EXPERIMENTAL-DATA-MODEL-001` | PASS |
| `load_contract(package_dir).integrity` | `MANIFEST_OK` | `MANIFEST_OK` (5/5 manifest entries) | PASS |
| `sha256(contract_guard.py)` | `e418fc28…4b3746` | `e418fc28…4b3746` | PASS |
| `pre_tool_call` hook wiring | `contract_guard.py`, matcher `write_file\|patch\|terminal`, `fail_closed: true` | identical, unchanged | PASS |
| `sha256(config.yaml)` / `sha256(shell-hooks-allowlist.json)` | `7ac5c4cb…` / `343cf576…` | identical | PASS |
| `HERMES_CONTRACT_PACKAGE` | this package | this package | PASS |
| All 6 `expected_before_hashes` | frozen | all match, 0 drift | PASS |
| `SyncState.kt` | absent | absent | PASS |

No `INVALID_CONTRACT`, no `STALE_DATA_MODEL_INPUT`, no `CONTRACT_PACKAGE_TAMPERED`.

The same unmodified guard was active on every write in this session. Its own verdict log
(`orchestration/hermes/evidence/p0b-close/contract-guard-decisions.jsonl`) records **0 blocks** and
10 allowed writes, every one of them inside `allowed_paths` — an independent record of the change
set produced by the guard, not by this session.

## 2. Plan (written once, executed in this order, never re-planned)

1. `SyncState.kt` (new) — the seven-state enum.
2. `NoteEntity.kt` — the five columns with fresh-row defaults + UNIQUE index on `clientUuid`.
3. `KeepLabDatabase.kt` — `version = 3`.
4. `NoteDao.kt` — remove the full-row `@Update updateNote(NoteEntity)`; add the targeted content-column update.
5. `NoteRepository.kt` — creation boundary establishes the defaults once; `saveNote` uses the content-only update; `setTrashed` writes `trashed` only.
6. `Fakes.kt` + `app/src/test/java/com/keeplab/app/data/` — follow the DAO change and add the proofs.
7. Verify once, write the evidence, stop.

No step was inserted, reordered or re-planned after the plan was written.

## 3. Change set (5 persistence files, 2 test files — all inside `allowed_paths`)

| File | Kind | What changed |
|---|---|---|
| `data/local/SyncState.kt` | NEW | `enum class SyncState` with exactly `LOCAL_ONLY, SYNC_PENDING, SYNCING, SYNCED, SYNC_FAILED, CONFLICT, DELETE_PENDING`. No converter, no transition. The only new source file. |
| `data/local/NoteEntity.kt` | MODIFIED | Five columns appended with fresh-row defaults; `indices = [Index(value = ["clientUuid"], unique = true)]`; `internal fun generateClientUuid()`. Every pre-existing column keeps its name, type, order and meaning. |
| `data/local/KeepLabDatabase.kt` | MODIFIED | `version = 2` → `version = 3`. Entity list, class name and `exportSchema = false` unchanged. |
| `data/local/NoteDao.kt` | MODIFIED | `@Update suspend fun updateNote(NoteEntity)` **removed** (and its `androidx.room.Update` import). Added `updateNoteContent(id, title, body, color, pinned, archived, trashed, updatedAt)` as a targeted `@Query UPDATE`. |
| `data/NoteRepository.kt` | MODIFIED | `createNote` is the single creation boundary and establishes the five defaults; `saveNote` now calls `updateNoteContent` instead of reconstructing and overwriting a whole row. |
| `test/…/Fakes.kt` | MODIFIED | `FakeNoteDao` drops the removed override and implements the targeted update (content columns only); a `storedNote(id)` accessor exposes the raw row so tests can assert persistence-layer metadata the domain model hides. |
| `test/…/data/NoteSyncMetadataTest.kt` | NEW | 5 proofs: fresh-row defaults, two distinct non-empty `clientUuid`s, an identity-preserving edit, trash≠tombstone, the exact seven-state set. |

`DefaultNoteRepositoryTest.kt` was **not** touched (byte-identical to its pre-A1 hash) and its 17
tests still pass.

### The target model as built

| Column | Kotlin | Nullability | Index | Fresh row |
|---|---|---|---|---|
| `clientUuid` | `String` | `NOT NULL` | **UNIQUE** | `generateClientUuid()` — a random UUID string |
| `accountId` | `String?` | nullable | — | `null` |
| `syncState` | `SyncState` | `NOT NULL` (TEXT) | — | `SyncState.LOCAL_ONLY` |
| `serverRevision` | `Long?` | nullable | — | `null` |
| `deletedAt` | `Long?` | nullable | — | `null` |

Fresh-row defaults come from exactly one place: the entity's own defaults plus the single
repository creation boundary (`createNote`). No other construction site initialises sync metadata.

**TRASH != TOMBSTONE** is structural, not conventional: no write statement in `NoteDao.kt` names
`deletedAt`; `setTrashed`/`setTrashedFor` write `trashed` and `updatedAt` only; `updateNoteContent`
cannot reach it; and the only `deletedAt` value A1 production code can write is the literal `null`
in `createNote`. A1 implements no transition — `LOCAL_ONLY` is the only state produced.

## 4. Verification (one pass)

**Gate: `./gradlew :app:testDebugUnitTest :app:assembleDebug` — run ONCE, `BUILD SUCCESSFUL`, exit 0, 2m 47s.**
57 tests, 0 failures, 0 errors, 0 skipped. No task was re-run; no failed path existed to fix.

**Schema (AC-A1DM-001/002) — PASS.** Read from the KSP-generated implementation
(`app/build/generated/ksp/debug/kotlin/com/keeplab/app/data/local/KeepLabDatabase_Impl.kt`,
sha256 `242d44e1…`, read-only). The generated DDL is:

```
CREATE TABLE IF NOT EXISTS `notes` (… , `clientUuid` TEXT NOT NULL, `accountId` TEXT,
  `syncState` TEXT NOT NULL, `serverRevision` INTEGER, `deletedAt` INTEGER)
CREATE UNIQUE INDEX IF NOT EXISTS `index_notes_clientUuid` ON `notes` (`clientUuid`)
```

`RoomOpenDelegate(3, "e6235c09…", "a939b1d7…")` — version 3. `createAutoMigrations()` returns an
empty list, `getRequiredAutoMigrationSpecs()` an empty set, and no `fallbackToDestructiveMigration`
appears anywhere. The only migration registration in the project is the pre-existing
`.addMigrations(MIGRATION_1_2)` in the byte-identical `AppModule.kt`. `exportSchema` stays `false`;
no `app/schemas/` directory exists. The 10 pre-existing `notes` columns and all three child tables
are unchanged.

**Model (AC-A1DM-003/004/005/006) — PASS.** The five new tests pass. The edit proof seeds a row
carrying *non-default* metadata (`SYNCED`, `serverRevision = 42`, a real `accountId`, a fixed
`clientUuid`) and then asserts whole-row equality against `before.copy(title, body, updatedAt)` —
i.e. every column other than the content columns is byte-identical after an edit. The generated
`NoteDao_Impl.kt` contains an insert adapter for `NoteEntity` and **no update adapter**, confirming
the full-row write path is gone.

**Scope (AC-A1DM-007) — PASS.** All 8 `protected_snapshot` files re-hash byte-identically; both
hook/core files re-hash identically; all 15 manifest entries across this package and both A0
packages verify. An independent `find -newermt` scan shows the A1-authored set is exactly the 7
files above, an unchanged `DefaultNoteRepositoryTest.kt`, build outputs under `app/build/`, and the
evidence artifacts. The pre-A1 state of `KeepLab-Relay` has been re-checked against the frozen
`expected_before_hashes` immediately before mutation, and *every* pre-existing field of every
touched file other than the intended change is preserved.

**No device (AC-A1DM-007) — PASS.** No `adb`, no device lock, no instrumentation, no Maestro or
UiAutomator, no APK install or launch. The device serial was never referenced. The gate is
device-free and `androidTest/` was neither edited nor executed.

Two files outside the A1 surface changed during the session window and are reported rather than
hidden: the frozen guard's own audit log (written by `contract_guard._log()` on every tool call,
pre-existing contract-independent behaviour that A1 must not modify) and
`_evaluation/.auto_finalize_index.json` (refreshed by the Hermes / CommandCode evaluation layer).
Neither was reached by an A1 tool call — the guard's verdict log records no write to either path —
and neither is a KeepLab product source file. No `CONTRACT_DEVIATION` arises: no *required* A1
write fell outside `allowed_paths`.

## 5. Data-stage consequence (accepted, by contract)

`DEV_DATABASE_RESET_REQUIRED = YES`. Version 2 → 3 with no migration authored and no destructive
fallback registered. An installed version-2 development database is **not** upgraded; clearing app
data or reinstalling is the expected developer action. Test data is disposable; no multi-version
migration chain, no old-database upgrade path and no compatibility field was authored.

## 6. Minor findings (appended to `KEEPLAB-MINOR-BACKLOG.md`, non-blocking, not stops)

- **MB-A1-005** — the execution prompt names the generated schema artifact
  `KeepLabDatabase_Impl.java`; Room 2.8.4 + KSP2 emits `KeepLabDatabase_Impl.kt`.
- **MB-A1-006** — `implementation-contract.json → current_model` describes
  `DefaultNoteRepositoryTest.kt` as "16 JVM unit tests"; the file holds 17 and the gate reports 17.

## 7. Stop

`A1: PASS.` A2 and A3 were not started; D-14, A0 and OBS-1 were not reopened; no post-PASS review,
no second audit and no full-repository scan was performed. No further A1 work is authorized by this
contract.

Evidence: `orchestration/hermes/evidence/keeplab-a1-experimental-data-model/` —
`pre-change-hashes.json`, `contract-activation.json`, `schema-evidence.json`,
`model-verification.json`, `unchanged-scope-scan.json`, `verification.json`.
