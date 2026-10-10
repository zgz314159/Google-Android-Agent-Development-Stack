# KEEPLAB-A1-EXPERIMENTAL-DATA-MODEL-EXECUTE

**Execution prompt — future task. NOT executed by the contract-creation phase.**

| | |
|---|---|
| Contract | `KEEPLAB-A1-EXPERIMENTAL-DATA-MODEL-001` |
| Contract package | `/mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack/reports/contracts/KEEPLAB-A1-EXPERIMENTAL-DATA-MODEL-001` |
| Package declaration | `CONTRACT_PACKAGE: READ_ONLY_INPUT` |
| Phase | `A1_EXPERIMENTAL_DATA_MODEL` |
| Human authorization | D-15 `YES_BOUNDED_ACCOUNT_NETWORK_UNLOCK` (already recorded), 2026-10-06 |
| Project data stage | `EXPERIMENTAL` · test data disposable · old test DB compatibility not required |
| `PRIMARY_KEY_STRATEGY` | `KEEP_LONG_LOCAL_PK_ADD_UNIQUE_CLIENT_UUID` — the existing `Long` rowid key is clean and already referenced by two child foreign keys and the whole id surface; the stable client UUID is added beside it. Replacing the local key is a separate later decision (MIG-1/MIG-2), forbidden here. |
| `DEV_DATABASE_RESET_REQUIRED` | `YES` — version 2 -> 3 with no migration authored; an installed development database may need app-data clearing or a reinstall. Accepted for this data stage. |
| Gradle | `BLOCK` |
| Device | `NOT_USED` (no adb, no instrumentation) |
| Loop | `PLAN ONCE -> EXECUTE -> VERIFY ONCE -> PASS = STOP -> FAIL = fix the failed path only` |
| Stops after | A1. **A2 and A3 must not start. A0 and OBS-1 must not be re-opened.** |

---

## 0. Prohibitions that bind every step

- Do **not** modify the contract package. It is `READ_ONLY_INPUT`.
- Do **not** modify `contract_guard.py`, the hook configuration, Hermes core, the active frozen
  P0B-CLOSE contract, or either A0 contract package.
- Do **not** disable, patch, bypass or skip the guard; do not rename files to evade
  classification; do not write outside the project and copy back.
- Do **not** broaden this contract's allowed paths. Needing a path it does not grant is a STOP
  and a new human-approved contract.
- Do **not** touch Gradle files, `Migrations.kt`, `AppModule.kt`, `LabelEntity.kt`, `model/`,
  `ui/`, `androidTest/`, `benchmark/`, `app/schemas/`, the product governance files, the frozen
  P0B packages, `Testapp/`, `PowerAi/`, `KeepLab-Relay-evidence/`, or the Android device.
- Do **not** implement sync, network, auth, backend, a worker, an outbox, a cursor, a table
  beyond the five columns, or any user-visible behaviour change.
- Do **not** author a Migration, add `fallbackToDestructiveMigration()`, add schema export, or
  write an old-database upgrade path. Test data is disposable; a developer reset is expected.
- Do **not** start A2 or A3, and do **not** resolve D-14 or re-open A0/OBS-1.
- After PASS: **stop**. No post-PASS review, no second audit, no full-repository scan, no
  re-running a task that already passed.
- **Guard scope, stated plainly:** the frozen guard classifies *write targets*, not tool
  choice. It does not block `adb`, `./gradlew`, launching an APK, or Hermes config/core paths
  outside the project root. The device prohibition, the Gradle change prohibition and the
  Hermes-core prohibition therefore bind through these stop conditions. Running adb or an
  instrumentation test, or editing a build script, is a `CONTRACT_DEVIATION` even though the
  guard would allow the command.

---

## 1. Activate the contract (same guard, different package)

```bash
export HERMES_CONTRACT_PACKAGE=/mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack/reports/contracts/KEEPLAB-A1-EXPERIMENTAL-DATA-MODEL-001
```

**Step 1 — verify contract id and MANIFEST_OK.** Load
`orchestration/hermes/evaluation_adapter/contract_guard.py`, call
`load_contract(package_dir)`, assert `contract_id == "KEEPLAB-A1-EXPERIMENTAL-DATA-MODEL-001"`
and `integrity == "MANIFEST_OK"`. Anything else is `INVALID_CONTRACT` → STOP. Do not repair the
package.

**Step 2 — verify guard identity.** Assert
`sha256(contract_guard.py) == e418fc28b08ac7afe4fdd42ec44d572ddaa2f23f6200de300ecac211404b3746`
and that the hook config still wires the same fail-closed `pre_tool_call` hook. A different
guard means the contract was validated against a different guard → STOP.

**Step 3 — verify the input is not stale.** Re-hash and compare against
`expected_before_hashes.files` in `implementation-contract.json`:

| File | Expected sha256 |
|---|---|
| `.../data/local/NoteEntity.kt` | `d417b89a4ba1156fd5722d5435743b6f55f5fcb8c82096cba87af6011caa3c98` |
| `.../data/local/KeepLabDatabase.kt` | `abe7b2e3ef73e1f7206f4dc864d9ca3f9367209d8d3c794d517023558b34fd86` |
| `.../data/local/NoteDao.kt` | `3744797a7c0c169eae3fd954da9265c2245b4dd1b6ddc2e6948e6905735c059f` |
| `.../data/NoteRepository.kt` | `9e284b91994368f8e178a32204eae10d6a3b0f811a55776eedadf24579c7e34f` |
| `.../test/.../Fakes.kt` | `56e3e96b94cc61c0ef74f1c83fa3adaeb1f8abcfecd47e85503834bdad47ecf7` |
| `.../test/.../data/DefaultNoteRepositoryTest.kt` | `3d5b31d3a7a4b568ddcdd7b64b8a85e5a1bacdffe471f912c8ae4732fa34a2b3` |

Any drift → STOP with **`STALE_DATA_MODEL_INPUT`**. Never re-baseline.

---

## 2. PLAN ONCE

Write the plan once, in this order, and do not re-plan afterwards:

1. `SyncState.kt` (new): the seven-state enum.
2. `NoteEntity.kt`: the five columns with fresh-row defaults + UNIQUE index on `clientUuid`.
3. `KeepLabDatabase.kt`: `version = 3` (entity list, class name, `exportSchema = false` unchanged).
4. `NoteDao.kt`: remove the full-row `@Update updateNote(NoteEntity)` write path; add the targeted
   content-column update.
5. `NoteRepository.kt`: creation boundary establishes the defaults once; `saveNote` uses the
   content-only update; `setTrashed` writes `trashed` only.
6. `Fakes.kt` + `app/src/test/java/com/keeplab/app/data/`: follow the DAO change and add the tests.
7. Verify once, write the evidence, stop.

## 3. EXECUTE — the exact target model

`notes` gains exactly five columns; every existing column keeps its name, type and meaning:

| Column | Kotlin | Nullability | Index | Fresh row |
|---|---|---|---|---|
| `clientUuid` | `String` | `NOT NULL` | **UNIQUE** | generated stable UUID string |
| `accountId` | `String?` | nullable | — | `null` |
| `syncState` | `SyncState` | `NOT NULL` | — | `SyncState.LOCAL_ONLY` |
| `serverRevision` | `Long?` | nullable | — | `null` |
| `deletedAt` | `Long?` | nullable | — | `null` |

`SyncState` (local, type-safe; `SyncState.kt` is the only new file A1 may create):
`LOCAL_ONLY`, `SYNC_PENDING`, `SYNCING`, `SYNCED`, `SYNC_FAILED`, `CONFLICT`, `DELETE_PENDING`.
Room 2.8.4 persists enums as text by default; a `TypeConverter` is permitted **only inside
`SyncState.kt`**. A1 implements **no transition** — `LOCAL_ONLY` is the only state A1 produces.
`accountId` is null for every note (INVARIANT ISO-1b: null is legal while `LOCAL_ONLY`).

**TRASH != TOMBSTONE.** `trashed` stays the reversible product state. `deletedAt` is the
final-deletion tombstone, `null` for every fresh row, never written by trashing or restoring,
and never written by any A1 code path.

**Fresh-row defaults come from one place:** entity defaults + the single repository creation
boundary. Do not scatter sync-metadata initialization across call sites.

**The edit path must not rewrite sync metadata.** `saveNote` currently reconstructs a whole
`NoteEntity` from a domain model that carries no sync fields; a full-row overwrite would
regenerate the sync identity on every edit. Persist content only (`title`, `body`, `color`,
`pinned`, `archived`, `trashed`, `updatedAt`) through a targeted update.

**Explicitly out of the target model:** checklist-item / label UUID identity, an `accounts`
table, attachments, outbox, sync checkpoints, cursors, conflicts, server-only models, CRDTs, a
`trashedAt` column, any migration, schema export, any UI or domain-model change.

## 4. VERIFY ONCE

Run the frozen gate **once**:

```
./gradlew :app:testDebugUnitTest :app:assembleDebug
```

Then, in one pass:

1. **Schema (AC-A1DM-001/002).** Read the generated
   `KeepLab-Relay/app/build/generated/ksp/debug/java/.../KeepLabDatabase_Impl.java` and assert:
   `clientUuid TEXT NOT NULL`, a UNIQUE index on `clientUuid`, `accountId`/`serverRevision`/
   `deletedAt` nullable, `syncState TEXT NOT NULL`, version `3`, and **no** migration/fallback
   registration. A generated file is read, never written.
2. **Model (AC-A1DM-003/004/005/006).** The new JVM unit tests prove: fresh-row defaults; two
   notes with different non-empty `clientUuid`; an edit preserving `clientUuid`/`syncState`/
   `serverRevision`/`deletedAt`; trashing leaving `deletedAt == null`; the exact seven-state set.
3. **Scope (AC-A1DM-007).** Re-hash every `protected_snapshot` file and assert byte-identity
   (Gradle files, `Migrations.kt`, `AppModule.kt`, `LabelEntity.kt`, `model/`, `ui/`, `androidTest/`,
   `benchmark/`, `MISSION.md`, the frozen P0B contract, the guard source, the hook config);
   assert every modified file lies inside the allowed surface. No `git diff` is available (the
   product repository has no commits) — use sha256 before/after and the scope scan.
4. **No device (AC-A1DM-007).** No adb, no device lock, no instrumentation, no Maestro, no
   launch of the APK.
5. **Write the evidence** under
   `orchestration/hermes/evidence/keeplab-a1-experimental-data-model/`:
   `pre-change-hashes.json`, `contract-activation.json`, `schema-evidence.json`,
   `model-verification.json`, `unchanged-scope-scan.json`, `verification.json`; and the report
   `reports/KEEPLAB-A1-EXPERIMENTAL-DATA-MODEL-EXECUTION.md`.

**If a task fails:** stop at the first deterministic failure, read the failure once, fix only the
failed path inside the allowed surface, and re-run **only the failed task**. Do not re-run a task
that already passed. If the fix would need a path, a dependency or a decision the contract does
not grant → STOP with the matching code.

**PASS = STOP.** No post-PASS review, no second audit, no full-repository scan, no A2, no device.

## 5. Stop codes

| Code | When |
|---|---|
| `CONTRACT_DEVIATION` | a required write falls outside `allowed_paths` or targets a forbidden path |
| `STALE_DATA_MODEL_INPUT` | an `expected_before_hashes` file has drifted |
| `A1_GRADLE_DEPENDENCY_REQUIRED` | a genuinely missing dependency or build-script change is required (report it exactly; do not work around it) |
| `INVALID_CONTRACT` | contract id mismatch or `MANIFEST_OK` not achieved |
| `CONTRACT_PACKAGE_TAMPERED` | a package manifest entry does not verify |
| `PROCESS_OVERHEAD_TOO_HIGH` | the task starts expanding into repeated review/audit cycles; simplify and stop |
| `BLOCKED` | the change cannot be made without violating an invariant (Trash/tombstone, PK strategy, no-migration policy) |

Minor findings (naming, wording, warnings, cleanups) are **not** stops: append them compactly to
`reports/KEEPLAB-MINOR-BACKLOG.md` and continue.

## 6. Report afterwards

```
KEEPLAB-A1-EXPERIMENTAL-DATA-MODEL-EXECUTE
PROJECT DATA STAGE: EXPERIMENTAL
DEV_DATABASE_RESET_REQUIRED: YES
PRIMARY_KEY_STRATEGY: KEEP_LONG_LOCAL_PK_ADD_UNIQUE_CLIENT_UUID
CURRENT DB VERSION: 2 -> 3
clientUuid / accountId / syncState / serverRevision / deletedAt: <PASS|FAIL>
TRASH != TOMBSTONE: <PASS|FAIL>
ROOM SCHEMA (KSP generated, version 3): <PASS|FAIL>
GRADLE GATE (testDebugUnitTest + assembleDebug, run once): <PASS|FAIL>
PROTECTED FILES BYTE-IDENTICAL: <PASS|FAIL>
NETWORK / AUTH / BACKEND / GRADLE / UI / DEVICE UNTOUCHED: <PASS|FAIL>
A1: <PASS|FAIL>
NEXT: A2 (READY_FOR_SEPARATE_CONTRACT) — not started here
```

Then stop.
