# Acceptance — KEEPLAB-A1-EXPERIMENTAL-DATA-MODEL-001

**Contract:** `KEEPLAB-A1-EXPERIMENTAL-DATA-MODEL-001`
**Phase:** `A1_EXPERIMENTAL_DATA_MODEL` (temporary execution contract)
**Date:** 2026-10-06
**Human authorization:** D-15 `YES_BOUNDED_ACCOUNT_NETWORK_UNLOCK` (phase-gated; local-first mandatory; account/network optional for local use; Room remains the local SSOT; Google/Firebase identity forbidden)
**Project data stage:** `EXPERIMENTAL` — `TEST_DATA_DISPOSABLE = YES`, `OLD_TEST_DB_COMPATIBILITY = NOT_REQUIRED`
**Status:** READY (contract package validated; A1 itself is NOT executed)

## 0. What this package is

A temporary execution contract that authorizes **one later, separate** A1 session to prepare
the existing local persisted note model for a future sync architecture, through the **same
unmodified Contract Guard**, inside a bounded persistence path surface. It implements no sync,
no network, no auth and no backend, and it changes no user-visible behaviour.

## 1. Machine-readable semantics

Recorded in `implementation-contract.json` (`project_data_stage`, `current_model`,
`target_model`, `primary_key_strategy`, `required_changes`, `required_behaviour`,
`gradle_policy`, `network_auth_backend_policy`, `device_policy`, `verification_intent`,
`stop_conditions`) and mirrored here.

| Field | Value |
|---|---|
| `phase` | `A1_EXPERIMENTAL_DATA_MODEL` |
| `human_decision` | D-15 `YES_BOUNDED_ACCOUNT_NETWORK_UNLOCK` |
| `project_data_stage` | `EXPERIMENTAL` |
| `TEST_DATA_DISPOSABLE` | `YES` |
| `OLD_TEST_DB_COMPATIBILITY` | `NOT_REQUIRED` |
| `DEV_DATABASE_RESET_REQUIRED` | `YES` (accepted consequence of the version bump) |
| `CURRENT_DB_VERSION` / target | `2` / `3` |
| `PRIMARY_KEY_STRATEGY` | `KEEP_LONG_LOCAL_PK_ADD_UNIQUE_CLIENT_UUID` |
| `implementation_authorization` | granted to the A1 execution task only, `PHASE_GATED` |
| `network_change` / `auth_change` / `backend_change` | `FORBIDDEN` |
| `gradle_change` | `FORBIDDEN` |
| `ui_change` / `product_behaviour_change` | `FORBIDDEN` |
| `device_operation` | `FORBIDDEN` |

## 2. The exact target model (exhaustive)

Table `notes` gains exactly these five columns; every existing column is unchanged.

| Column | Type | Nullability | Index | Fresh-row value |
|---|---|---|---|---|
| `clientUuid` | `String` | `NOT NULL` | `UNIQUE` | generated stable UUID string |
| `accountId` | `String?` | nullable | — | `null` |
| `syncState` | `SyncState` | `NOT NULL` | — | `SyncState.LOCAL_ONLY` |
| `serverRevision` | `Long?` | nullable | — | `null` |
| `deletedAt` | `Long?` | nullable | — | `null` |

`SyncState` is a local, type-safe enum with exactly:
`LOCAL_ONLY`, `SYNC_PENDING`, `SYNCING`, `SYNCED`, `SYNC_FAILED`, `CONFLICT`, `DELETE_PENDING`.
A1 stores the state and implements **no transition**: `LOCAL_ONLY` is the only state A1 code
produces.

**TRASH != TOMBSTONE.** `trashed: Boolean` stays the user-visible, reversible product state.
`deletedAt` is the protocol-level **final-deletion** tombstone for future convergence, stays
`null` for every fresh row, and **MUST NOT** be written by trashing, restoring or any A1 path.

**Not in the target model:** checklist-item / label UUID identity, an `accounts` table, an
attachments or outbox table, sync checkpoints or cursors, conflict tables, server-only models,
CRDTs, a `trashedAt` column, migration chains, schema export.

## 3. Allowed write surface (exhaustive)

Persistence source (5 files):

1. `KeepLab-Relay/app/src/main/java/com/keeplab/app/data/local/NoteEntity.kt`
2. `KeepLab-Relay/app/src/main/java/com/keeplab/app/data/local/KeepLabDatabase.kt`
3. `KeepLab-Relay/app/src/main/java/com/keeplab/app/data/local/NoteDao.kt`
4. `KeepLab-Relay/app/src/main/java/com/keeplab/app/data/local/SyncState.kt` (the only new file)
5. `KeepLab-Relay/app/src/main/java/com/keeplab/app/data/NoteRepository.kt`

Tests:

6. `KeepLab-Relay/app/src/test/java/com/keeplab/app/data/`
7. `KeepLab-Relay/app/src/test/java/com/keeplab/app/Fakes.kt`

Build output (regenerated, never authored):

8. `KeepLab-Relay/app/build/`
9. `KeepLab-Relay/build/`

Evidence output:

10. `Google-Android-Agent-Development-Stack/reports/`
11. `Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/keeplab-a1-experimental-data-model/`

Everything else inside the project root is BLOCKED (fail-closed), including every Gradle
input, `Migrations.kt`, `AppModule.kt`, `LabelEntity.kt`, `model/`, `ui/`, `androidTest/`,
`benchmark/`, `app/schemas/`, the product governance files, the frozen P0B packages,
`reports/contracts/` (this package included), `Testapp/`, `PowerAi/` and `KeepLab-Relay-evidence/`.

## 4. Acceptance criteria

### AC-A1DM-001 — the five sync-metadata columns exist exactly as specified

- Verification: the Room KSP generated database implementation is read after the build and
  asserted to declare `clientUuid TEXT NOT NULL`, a UNIQUE index on `clientUuid`,
  `accountId`/`serverRevision`/`deletedAt` nullable, and `syncState TEXT NOT NULL` on `notes`.

### AC-A1DM-002 — experimental data-stage policy honoured

- Verification: `KeepLabDatabase` declares `version = 3`; no new `Migration` class exists;
  no `fallbackToDestructiveMigration*` call exists; `exportSchema` stays `false`; the report
  records `DEV_DATABASE_RESET_REQUIRED = YES` and states that old development databases are
  not upgraded.

### AC-A1DM-003 — fresh-row defaults

- Verification: JVM unit test through the production creation boundary — `clientUuid` is
  non-empty, `accountId == null`, `syncState == LOCAL_ONLY`, `serverRevision == null`,
  `deletedAt == null`; and two freshly created notes carry different `clientUuid` values.

### AC-A1DM-004 — identity and metadata survive an edit

- Verification: JVM unit test — after a title/body edit, `clientUuid` is unchanged,
  `syncState` is unchanged, `serverRevision` is unchanged and `deletedAt` is unchanged;
  the DAO exposes no full-row overwrite write path.

### AC-A1DM-005 — TRASH is not a TOMBSTONE

- Verification: JVM unit test — trashing a note sets `trashed = true` and leaves
  `deletedAt == null`; restoring it clears `trashed` and still leaves `deletedAt == null`;
  no A1 code path writes `deletedAt`.

### AC-A1DM-006 — sync state is type-safe and complete

- Verification: the declared state set equals the seven states named in KEEPLAB-AUTH-SYNC-STATE-MODEL §2,
  `LOCAL_ONLY` is the fresh-row default, and no sync transition or worker exists.

### AC-A1DM-007 — bounded change set

- Verification: sha256 before/after — every protected file byte-identical (Gradle files,
  `Migrations.kt`, `AppModule.kt`, `LabelEntity.kt`, `model/`, `ui/`, `androidTest/`,
  `benchmark/`, governance files, frozen P0B packages, both A0 packages, the guard source,
  the hook configuration); every modified file inside the allowed surface; no device, adb or
  instrumentation command was run.

### AC-A1DM-008 — one verification pass

- Verification: `./gradlew :app:testDebugUnitTest :app:assembleDebug` run once, PASS; after
  any deterministic failure, only the failed task re-run; no review of the review, no
  post-PASS audit, no full-repository scan.

## 5. Required guard classifications (validated in this phase, simulated)

| Write target | Required |
|---|---|
| `KeepLab-Relay/app/src/main/java/com/keeplab/app/data/local/NoteEntity.kt` | ALLOW |
| `.../data/local/KeepLabDatabase.kt` | ALLOW |
| `.../data/local/NoteDao.kt` | ALLOW |
| `.../data/local/SyncState.kt` (new) | ALLOW |
| `.../data/NoteRepository.kt` | ALLOW |
| `KeepLab-Relay/app/src/test/java/com/keeplab/app/data/...` | ALLOW |
| `KeepLab-Relay/app/src/test/java/com/keeplab/app/Fakes.kt` | ALLOW |
| `KeepLab-Relay/app/build/...` | ALLOW |
| `Google-Android-Agent-Development-Stack/reports/...` | ALLOW |
| `.../orchestration/hermes/evidence/keeplab-a1-experimental-data-model/...` | ALLOW |
| `KeepLab-Relay/app/build.gradle.kts`, `gradle/libs.versions.toml`, `settings.gradle.kts` | BLOCK |
| `KeepLab-Relay/app/src/main/java/com/keeplab/app/di/AppModule.kt` | BLOCK |
| `.../data/local/Migrations.kt` | BLOCK |
| `.../data/local/LabelEntity.kt` | BLOCK |
| `KeepLab-Relay/app/src/main/java/com/keeplab/app/ui/...` | BLOCK |
| `KeepLab-Relay/app/src/main/java/com/keeplab/app/model/...` | BLOCK |
| `KeepLab-Relay/app/src/androidTest/...` | BLOCK |
| `KeepLab-Relay/app/schemas/...` | BLOCK |
| `Testapp/...`, `PowerAi/...`, `KeepLab-Relay-evidence/...` | BLOCK |
| `.../evaluation_adapter/contract_guard.py` | BLOCK |
| this contract package itself | BLOCK |
| either A0 contract package | BLOCK |

**Guard scope, stated plainly.** The frozen guard classifies write *targets*, not tool choice.
`adb`, an instrumentation run, `./gradlew` and Hermes config/core paths (outside the project
root) are not blocked by any path list, so the device, Gradle-execution and Hermes-core
prohibitions are enforced by this contract's stop conditions. They are not weaker for that:
violating them is a `CONTRACT_DEVIATION`.

## 7. Readiness gates

| Gate | Result |
|---|---|
| acceptance | PASS |
| boundaries | PASS |
| hashes | PASS |
| schema | PASS |
| traceability | PASS |
| guard_simulation | PASS |
