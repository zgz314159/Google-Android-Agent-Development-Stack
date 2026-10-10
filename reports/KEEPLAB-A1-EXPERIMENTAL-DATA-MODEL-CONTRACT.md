# KEEPLAB-A1-EXPERIMENTAL-DATA-MODEL-CONTRACT

**Targeted discovery + contract creation for the A1 experimental local data model.**

- Task: `KEEPLAB-A1-EXPERIMENTAL-DATA-MODEL-CONTRACT` (contract creation only)
- Date: 2026-10-06 (CST) · Status: **READY** · Execution: **NOT_EXECUTED**
- Contract: `KEEPLAB-A1-EXPERIMENTAL-DATA-MODEL-001`
- Package: `Google-Android-Agent-Development-Stack/reports/contracts/KEEPLAB-A1-EXPERIMENTAL-DATA-MODEL-001/`
- Not in scope and not started: A1 implementation, A2, A3, backend, auth, network, cloud, device validation, Google Keep.

---

## 1. Discovery (targeted, persistence only)

Read: `KeepLab-Relay/MISSION.md`; `KEEPLAB-AUTH-SYNC-ARCHITECTURE-SPEC.md` (indexed);
`KEEPLAB-AUTH-SYNC-DATA-MODEL.md`; `KEEPLAB-AUTH-SYNC-STATE-MODEL.md`;
`KEEPLAB-AUTH-SYNC-ARCHITECTURE-REVIEW.md` (indexed); then only the persistence code:
`KeepLabDatabase.kt`, `NoteEntity.kt`, `LabelEntity.kt`, `NoteDao.kt`, `Migrations.kt`,
`AppModule.kt`, `NoteRepository.kt`, `Fakes.kt`, `DefaultNoteRepositoryTest.kt`,
`NoteDaoRoomTest.kt`, `MigrationTest.kt`, `app/build.gradle.kts`, `gradle/libs.versions.toml`.

| Question | Answer |
|---|---|
| `CURRENT_DB_VERSION` | `2` |
| `CURRENT_ENTITIES` | `notes`, `checklist_items`, `labels`, `note_labels` |
| `CURRENT_NOTE_PRIMARY_KEY` | `Long @PrimaryKey(autoGenerate = true)` (rowid alias; FK target of `checklist_items.noteId` and `note_labels.noteId`) |
| `CURRENT_TRASH_MODEL` | `trashed: Boolean` only — product Trash, reversible; no tombstone column anywhere |
| `CURRENT_CHECKLIST_MODEL` | `checklist_items(id Long PK, noteId FK CASCADE, text, checked, position)` |
| `CURRENT_LABEL_MODEL` | `labels(id Long PK, name, createdAt)` + `note_labels(noteId,labelId)` composite PK, CASCADE both sides |
| `CURRENT_DB_CREATION_STRATEGY` | `Room.databaseBuilder("keeplab.db").addMigrations(MIGRATION_1_2)`; `exportSchema = false`; no destructive fallback; ksp `room.schemaLocation` set but unused |
| `CURRENT_SCHEMA_EXPORT` | none (no `app/schemas/`) |
| `CURRENT_RELEVANT_TESTS` | 16 JVM repository tests over `FakeNoteDao`; device-only `NoteDaoRoomTest`, `MigrationTest` |
| Creation boundary | `DefaultNoteRepository.createNote()` (explicit literals) and `saveNote()` (full-row `@Update` from a domain model with no sync fields) |

Not inspected: UI screens, navigation, theming, benchmarks, Testapp, PowerAi, Google Keep material.

## 2. Decisions frozen in the package

| ID | Decision |
|---|---|
| `PRIMARY_KEY_STRATEGY` | `KEEP_LONG_LOCAL_PK_ADD_UNIQUE_CLIENT_UUID` — the `Long` rowid key is clean and already referenced by two child FKs and the whole id surface; the stable UUID is added beside it. Consistent with `KEEPLAB-AUTH-SYNC-DATA-MODEL` MIG-1/MIG-2 (replacing the local key is a separate later decision). Not a data-preservation argument. |
| `A1-DM-002` | Version `2 -> 3`, **no** Migration authored, **no** destructive fallback, `DEV_DATABASE_RESET_REQUIRED = YES`. The data stage is `EXPERIMENTAL` and test data is disposable. |
| `A1-DM-003` | Only `notes` gains sync metadata; `checklist_items` / `labels` / `note_labels` keep their current shape (child-entity UUID identity deferred). |
| `A1-DM-004` | The domain model and UI are not extended; sync metadata is persistence-local in A1. |
| `A1-DM-005` | The full-row `@Update updateNote(NoteEntity)` write path is removed and replaced by a targeted content-column update, so an edit can never regenerate the sync identity. |
| `A1-DM-006` | Fresh-row defaults come from entity defaults + one creation boundary. |
| `A1-DM-007` | Allowed surface: 5 persistence files, 2 test locations, 2 build-output dirs, 2 evidence locations — not `KeepLab-Relay/app/**`. |
| `A1-DM-008` | Gradle blocked; a genuine dependency need stops with `A1_GRADLE_DEPENDENCY_REQUIRED`. |
| `A1-DM-009` | No device work, no instrumented test. |
| `A1-DM-010` | Single gate: `./gradlew :app:testDebugUnitTest :app:assembleDebug`, run once. |

Target model on `notes`: `clientUuid` (String, NOT NULL, UNIQUE), `accountId` (String?, null),
`syncState` (`SyncState`, NOT NULL, `LOCAL_ONLY`), `serverRevision` (Long?, null),
`deletedAt` (Long?, null) — with `TRASH != TOMBSTONE` preserved and no sync transition
implemented (`SyncState` declares exactly the seven states of the state model).

## 3. What was created

```
reports/contracts/KEEPLAB-A1-EXPERIMENTAL-DATA-MODEL-001/
  implementation-contract.json                        (guard source of truth: boundaries, model, decisions, stop conditions)
  project-context.json                                (source_root + path_classes)
  manifest.json                                       (sha256 of the authored artifacts)
  READY.json
  acceptance.md                                       (AC-A1DM-001..008 + required guard classifications)
  EXECUTOR-PROMPT.md                                  (activation + recorded PK strategy / DEV_DATABASE_RESET_REQUIRED)
  KEEPLAB-A1-EXPERIMENTAL-DATA-MODEL-EXECUTE.md       (the future A1 execution prompt)

orchestration/hermes/evidence/keeplab-a1-experimental-data-model-contract/
  before-hash.json                                    (frozen before-hashes + protected snapshot)
  guard-simulation.json                               (module-level guard simulation)
  hook-contract-activation.log                        (hook-level activation, exit codes)
```

Activation (unchanged mechanism): `export HERMES_CONTRACT_PACKAGE=<package>` — same
`contract_guard.py`, same fail-closed `pre_tool_call` hook, no guard/hook/config edit.

## 4. Validation (one pass)

| Gate | Result | Evidence |
|---|---|---|
| acceptance | PASS | `AC-A1DM-001..008` defined and each mapped to a task and a requirement |
| boundaries | PASS | paths project-relative; no forbidden path is a parent of an allowed path; no path conflicts; task paths inside the contract surface |
| hashes | PASS | `MANIFEST_OK` from `load_contract`; frozen project hashes re-verified live |
| schema | PASS | JSON parses; required blocks present; A0-compatible package shape |
| traceability | PASS | requirement -> acceptance -> task mapping complete, no orphan acceptance id, no unresolved question |
| guard_simulation | PASS | module-level: 12/12 checks PASS, 14 ALLOW decisions, 31 BLOCK decisions, 7 terminal cases; hook-level: 9/9 (exit 0 allow / exit 2 block) |
| guard identity | PASS | `contract_guard.py` sha256 `e418fc28…b3746`, version `p0b-close-1`, hook config unchanged |

Stated limits (not hidden): the guard classifies **write targets only**, so `adb`,
`./gradlew` and out-of-root Hermes config/core are not blocked by any path list — those
prohibitions bind through the contract's stop conditions. The package's `manifest.json`
carries an additive `metadata` block in the same way the validated A0 package does.

## 5. Phase state after this task

```
A0:  READY                  (not reopened; OBS-1 stays NON_BLOCKING MINOR_BACKLOG)
A1:  READY_TO_EXECUTE       (contract KEEPLAB-A1-EXPERIMENTAL-DATA-MODEL-001, NOT_EXECUTED)
A2:  READY_FOR_SEPARATE_CONTRACT
A3:  BLOCKED_BY_HUMAN_DECISIONS
D-15: YES_BOUNDED_ACCOUNT_NETWORK_UNLOCK
D-14: HUMAN_DECISION_PENDING
```

No implementation, no Gradle change, no network/auth/backend, no device access, no A2 work
was performed by this task.
