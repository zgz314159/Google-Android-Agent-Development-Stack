# KEEPLAB-MINOR-BACKLOG

Non-blocking minor findings. No entry here stops a phase or creates a contract.

## From A1 targeted discovery (2026-10-06, `KEEPLAB-A1-EXPERIMENTAL-DATA-MODEL-CONTRACT`)

- **MB-A1-001 — dead legacy migration chain after the A1 version bump.**
  `KeepLab-Relay/app/src/main/java/com/keeplab/app/data/local/Migrations.kt` (`MIGRATION_1_2`)
  and `app/src/androidTest/.../MigrationTest.kt` become unreachable once `KeepLabDatabase`
  moves to version 3: no installable path exists from that chain to the current schema, while
  the file's own comment still reads as if an upgrade is preserved. Not fixed in A1
  (`Migrations.kt` is intentionally outside A1's allowed surface). Suggested future handling,
  when the data stops being disposable: either delete the chain and its test, or author a real
  2 -> 3 path. Non-blocking.

- **MB-A1-002 — verification baseline is hash-only.**
  `KeepLab-Relay` is a git repository with **no commits**, so `git diff` cannot prove a change
  set and the A0-style "one line changed" proof is unavailable. A1 therefore verifies with
  sha256 before/after plus a scope scan. Committing a baseline would make future phases
  cheaper to verify. Non-blocking.

- **MB-A1-003 — execution-environment write-verb extraction is easy to trip.**
  Observed live during this task: the frozen guard reads a quoted JSON string containing `>`
  as a write target (a payload embedded in a shell command was reported as
  `AMBIGUOUS_WRITE_TARGET` / a `.kt` path), and the surrounding terminal security scanner
  refuses grouped bodies, pipes into an interpreter, and any command text containing an
  absolute-path delete. Practical guidance for future device-free phases: drive the guard by
  script files, not by inline heredocs, pipes or payload-bearing shell commands. The guard
  source must not be changed, so this is recorded rather than fixed. Non-blocking.

- **MB-A1-004 — carried forward: OBS-1.**
  The residual `MISSION.md` descriptive sentence recorded as OBS-1 by the A0 flow remains
  NON_BLOCKING. Noted here for continuity only; A0 is not reopened and this task does not
  touch it.

## From A1 execution (2026-10-06, `KEEPLAB-A1-EXPERIMENTAL-DATA-MODEL-EXECUTE`)

- **MB-A1-005 — the generated schema artifact is Kotlin, not Java.**
  `KEEPLAB-A1-EXPERIMENTAL-DATA-MODEL-EXECUTE.md` §4.1 directs the executor to read
  `KeepLab-Relay/app/build/generated/ksp/debug/java/.../KeepLabDatabase_Impl.java`. With the
  pinned toolchain (Room 2.8.4 + KSP 2.3.9 / KSP2) the same generated implementation is emitted
  as **`KeepLabDatabase_Impl.kt`** under `app/build/generated/ksp/debug/kotlin/...` (the Hilt
  factories still go to `.../generated/ksp/debug/java/`). It is the identical generated artifact
  with a different extension; A1 read the `.kt` file as the schema evidence
  (`schema-evidence.json`). Suggested future handling: name the artifact by its role
  ("the KSP-generated `KeepLabDatabase_Impl` under `app/build/generated/ksp/debug/`") rather
  than by extension. No contract change is needed. Non-blocking.

- **MB-A1-006 — stale test count in the contract's `current_model`.**
  `implementation-contract.json -> current_model.CURRENT_RELEVANT_TESTS` describes
  `app/src/test/java/com/keeplab/app/data/DefaultNoteRepositoryTest.kt` as "(16 JVM unit
  tests)". The file declares 17 `@Test` methods and the gate reports 17 (`tests="17"
  failures="0"`), unchanged by A1. Documentation-only count drift in a READ_ONLY_INPUT
  package; not corrected here. Non-blocking.

## From A2 targeted discovery (2026-10-06, `KEEPLAB-A2-BACKEND-FOUNDATION-CONTRACT`)

- **MB-A2-001 — no container runtime on the host.** `docker` and `docker compose` are not
  installed and `psql` is absent, so A2's Docker runtime smoke and any live-PostgreSQL check will
  report `SKIPPED_TOOL_UNAVAILABLE`. A2 is never blocked by that (the backend Gradle build/test is
  the gate), but `backend/docker-compose.yml` and `Dockerfile` will be validated statically rather
  than executed, and any later phase that needs real container verification must have the runtime
  installed first. Non-blocking.

- **MB-A2-002 — the backend is a large new untracked tree on a repo with no commits.** Carried
  forward from MB-A1-002: `KeepLab-Relay` still has **no commits**, so `git diff` cannot prove
  A2's change set and the scope proof is a sha256 before/after scan plus the assertion that every
  created file lies under `KeepLab-Relay/backend/**`. A2 adds an entire new directory rather than
  editing five files, so committing a baseline would help future phases more than it would have
  helped A1. Non-blocking.

- **MB-A2-003 — backend version resolution is per-phase, not catalog-driven.** The root
  `gradle/libs.versions.toml` is Android-scoped (Kotlin 2.3.21, AGP 9.2.1, Room 2.8.4) and is
  deliberately not a source for the backend build, so the Kotlin/JVM and Ktor versions will be
  chosen during A2 execution and recorded in the A2 report instead of being pinned in the contract
  or the catalog. Not a defect — recorded so a later reader does not read the absence of a backend
  entry in the catalog as an oversight. Non-blocking.

- **MB-A2-004 — the root gradle.properties does not reach a `-p backend` build.** Running with
  `-p backend` makes Gradle read `backend/gradle.properties` (and `GRADLE_USER_HOME`), not
  `KeepLab-Relay/gradle.properties`, so the root JVM-args, parallel and caching settings do not
  apply to the backend build. The contract already places `backend/gradle.properties` inside the
  allowed surface; nothing to fix, recorded so the difference is known in advance. Non-blocking.

- **MB-A2-005 — architecture spec section 23.1 defers three items to A2 implementation level.**
  `KEEPLAB-AUTH-SYNC-ARCHITECTURE-SPEC.md` leaves the object-storage product, the load-balancer
  product and managed-vs-container PostgreSQL as decisions it assigns to A2. The A2 foundation
  contract deliberately decides none of them: it creates no object storage, no load balancer and
  no managed database, and provisions no cloud resource. They are genuine later-phase decisions
  (object storage belongs with attachments; the others with deployment). Non-blocking; noted so
  the deferral is explicit rather than looking like an omission.

## From A2 execution (2026-10-06, `KEEPLAB-A2-BACKEND-FOUNDATION-EXECUTE`)

- **MB-A2-006 — the Docker build cannot reuse the repository wrapper.** `backend/docker-compose.yml`
  uses `build.context: .` (the backend directory) so that `backend/.dockerignore` actually applies;
  that context cannot carry `KeepLab-Relay/gradlew`, and stop-condition 5 forbids adding a second
  wrapper to the repository. `backend/Dockerfile` therefore takes its toolchain from the official
  `gradle:9.5.1-jdk21` image — the same Gradle line the repository pins, so no version drift — and
  runs `installDist` there. Recorded so nobody reads the absent wrapper in the Dockerfile as an
  oversight. Non-blocking.

- **MB-A2-007 — `application.conf` is a descriptor; `AppConfig.fromEnvironment()` is the resolver.**
  TASK-01 asks for a HOCON `application.conf` with environment substitution **and** for structured
  configuration read from the `KEEPLAB_*` variables. A2 satisfies both, but the HOCON file is not
  read by `embeddedServer`: both use the identical `keeplab.*` key names and the env-variable
  resolver is authoritative. Keeping them in sync is manual. If a later phase wants one source of
  truth, the cheap options are an `EngineMain` entry point that loads the HOCON, or generating the
  file from the config object. Non-blocking.

- **MB-A2-008 — carried forward: MB-A1-003, with a concrete reproduction.** The frozen guard's
  narrow write-intent extractor reads a literal `>` anywhere in a terminal command as a shell
  redirect: `grep -o '<version>[^<]*</version>'` produced
  `BLOCK … target=Google-Android-Agent-Development-Stack/[^` (UNCLASSIFIED_FAIL_CLOSED), and
  `tr '>' '\n'` produced the same class of false positive. Worked around by fetching to files with
  `curl -o` and reading them with `read_file`/`search_files`. Same guidance as MB-A1-003: drive the
  guard by files and read-only commands, never by shell text containing `>`. The guard source must
  not be changed. Non-blocking.

- **MB-A2-009 — a read-only `git` command moves `.git`'s directory mtime.** Running `git log` /
  `git status` as a read-only baseline moved the mtime of `KeepLab-Relay/.git` (the directory only;
  no file inside it changed). In an mtime-based scope scan — the only kind available while the repo
  has no commits — that alone looks like an out-of-scope change. Future scope scans should assert
  *files* rather than directory mtimes, or exclude `.git` explicitly. Non-blocking.

## M2 (KEEPLAB-M2-AUTH-SINGLE-USER-SYNC-001)

- **MB-M2-001 — `SyncDao.nextOutboxEntry` is no longer used by the engine.** The push loop had to
  stop re-selecting a row it deliberately keeps on a 404/5xx, so it now reads
  `pendingMutations(accountId)` and skips ids it already attempted in the same run. The single-row
  query is retained (it is a natural query and the doubles implement it) but nothing calls it in
  production code. Non-blocking; deleting it is a one-line change whenever A5 reshapes the push loop.

- **MB-M2-002 — a few unit-test imports are now unused.** `DefaultNoteRepository` is still imported by
  the ViewModel tests after they were switched to the `fakeNoteRepository(...)` builder, and
  `HomeViewModelTest` no longer references it directly. Compiler warnings only. Non-blocking.

- **MB-M2-003 — the legacy `MIGRATION_1_2` sits beside the direct experimental bump.** M2 moved Room
  from version 3 to 4 with `fallbackToDestructiveMigration(dropAllTables = true)` and authored no
  migration chain, so `MIGRATION_1_2` is dead code for any path that now runs. It is harmless, but it
  can be deleted once the development database reset is universal (it is not deleted now because that
  is a behaviour change beyond M2's brief). Non-blocking.

- **MB-M2-004 — `dl.google.com` is unreachable from this host.** `androidx.work` is not in the Gradle
  cache, so M2 added a user-level init script
  (`~/.gradle/init.d/00-keeplab-google-mirror.gradle`, outside the project root) pointing resolution
  at reachable mirrors. No project file depends on it; if the environment is fixed the file can simply
  be deleted. Non-blocking, and recorded in the M2 execution report as an environment accommodation.

- **MB-M2-005 — Ktor's OkHttp engine needs `compileSdk 37`.** `io.ktor:ktor-client-okhttp:3.6.0`
  pulls `com.squareup.okhttp3:okhttp-android:5.5.0`, whose AAR metadata demands `compileSdk 37`. M2
  chose the pure-Kotlin **CIO** engine instead of bumping the compile SDK. If okhttp-specific
  behaviour is ever needed, that decision has to be revisited together with the SDK level.
  Non-blocking.

- **MB-M2-006 — the guard's `>` false positive recurred twice in M2.** A literal `>` anywhere in a
  terminal command is read as a redirect: `printf "%-62s "` followed by `->` produced
  `BLOCK … target=KeepLab-Relay/"`, and a `grep -E "^ +> "` pattern produced a similar false positive.
  Same class as MB-A1-003 / MB-A2-008, same workaround (drive the guard with files and read-only
  commands). Non-blocking; the guard source must not be changed.

## M3 (KEEPLAB-M3-OFFLINE-CONFLICT-001)

- **MB-M3-001 — stale `D-06` wording in the historical architecture records.** `D-06` is now frozen
  as `TRASH_RETENTION_7_DAYS` (`HUMAN_PROJECT_OWNER_APPROVAL`, 2026-10-06) and recorded in the new
  `reports/KEEPLAB-M3-HUMAN-DECISIONS.md`. `reports/KEEPLAB-AUTH-SYNC-DECISION-REGISTER.md`
  (`SYNC-DEC-015`) and `reports/KEEPLAB-AUTH-SYNC-HUMAN-DECISIONS.md` (§0 remaining-pending list and
  the §1 `D-06` row) still show `D-06` as `HUMAN_DECISION_PENDING`. They are historical records and
  were deliberately **not** edited (the contract-creation task was told not to reopen old governance
  phases and not to create a separate D-06 governance task). The M3 record is authoritative for M3.
  Non-blocking.

- **MB-M3-002 — `NoteEntity` has no Trash timestamp.** `trashed: Boolean` exists but there is no
  Trash-timestamp column, and `trashed`/`trashed_at` are distinct in the frozen state model
  (`KEEPLAB-AUTH-SYNC-STATE-MODEL` §4). M3/A6 must add one (a direct experimental schema bump is
  already authorized). Recorded so the absent column is not mistaken for a design decision.
  Non-blocking.

- **MB-M3-003 — the backend `409 REVISION_CONFLICT` body carries no revision or state.**
  `SyncService.applyMutation` returns `Outcome.Failure(409, "REVISION_CONFLICT")` and
  `MutationApplyOutcome.Conflict(currentRevision)` already knows the current revision, but
  `routes/RouteSupport.respondOutcome` collapses a failure to `{error, message}` and therefore drops
  it. M3/A6 must surface the authoritative current revision and current server payload on the 409
  (contract requirement AC-M3-012). The information already exists server-side; only the response
  shape needs extending. Non-blocking.

- **MB-M3-004 — `ApiResult.isRetryable()` exists but is unused by the engine.** `data/remote/ApiResult.kt`
  already encodes `status >= 500 || status == 429 || transport`, while `SyncEngine` hand-maps statuses.
  A5 should either adopt the existing helper or replace it with the explicit classification enum the
  contract requires — do not leave two divergent retry notions in the codebase. Non-blocking.

- **MB-M3-005 — the A5 checkpoint must not stop the session.** Recorded here so it is not lost:
  the M3 execution prompt requires `A5_CHECKPOINT: READY_FOR_A6` to be recorded and the session to
  continue **directly** into A6 with no Milestone gate at that point. Non-blocking.

## From M3 execution (2026-10-06, `KEEPLAB-M3-OFFLINE-CONFLICT-EXECUTE`)

- **MB-M3-006 — the guard's `>` false positive recurred a third time.** `grep -E "FAILED|BUILD|error:"`
  and `grep -E "^ +> "` produce `BLOCK … target=KeepLab-Relay/BUILD`
  (UNCLASSIFIED_FAIL_CLOSED): any literal `>` in a terminal command is read as a redirect. Same class
  as MB-A1-003 / MB-A2-008 / MB-M2-006; same workaround (drive the guard with files and avoid `>`
  in shell text). The guard source must not be changed. Non-blocking.

- **MB-M3-007 — `SyncDao.nextOutboxEntry` is still unused (carried from MB-M2-001).** A5 reshaped the
  push loop around `pendingMutations` + the durable `attemptCount` bound; the single-row query is
  retained only because the doubles implement it. Deleting it is a one-line change. Non-blocking.

- **MB-M3-008 — `NoteDao.updateNoteContent` still writes `trashed` without `trashedAt`.** The editor
  save path (`saveNote`) passes the domain `trashed` flag, which never changes in the editor, so the
  Trash timestamp is untouched in practice; a direct `saveNote(trashed = true)` would move the row
  into Trash without stamping `trashedAt`. Routing Trash exclusively through `setTrashed` (which the
  UI does) is correct today. Non-blocking.

- **MB-M3-009 — `MIGRATION_1_2` remains dead code beside the direct experimental bump.** Room is now
  at version 5 (`fallbackToDestructiveMigration(dropAllTables = true)`, `exportSchema = false`), so
  the 1→2 chain is reachable by no path. Same posture as MB-A1-001 / MB-M2-003. Non-blocking.

- **MB-M3-010 — the worker's catch-all `Result.retry()` is unbounded at the WorkManager level.** The
  engine's durable per-mutation bound (`RetryPolicy.AUTO_RETRY_MAX_ATTEMPTS`) bounds *mutation*
  attempts; a `Throwable` raised before the outbox is touched would be retried under WorkManager's own
  exponential backoff with no durable ceiling. No observed trigger; recorded so the distinction is
  explicit. Non-blocking.

- **MB-M3-011 — test fixtures containing the string `password = "..."` trip a naive secret scan.**
  The scan reports the pre-existing backend test passwords (`correct-horse-battery`, `owner-password`)
  and the `KEEPLAB_DB_PASSWORD` env-var *name*; none is a real credential. A future scan should
  exclude `*/src/test/**` fixtures or match only high-entropy values. Non-blocking.

## M4 (KEEPLAB-M4-ATTACHMENTS-001)

- **MB-M4-001 — stale `D-13` wording in the historical architecture records.** `D-13` is now frozen as
  `ATTACHMENT_LIMITS_V1` (`HUMAN_PROJECT_OWNER_APPROVAL`, 2026-10-06) and recorded in
  `reports/KEEPLAB-M4-HUMAN-DECISIONS.md`. `reports/KEEPLAB-AUTH-SYNC-DECISION-REGISTER.md` and
  `reports/KEEPLAB-AUTH-SYNC-HUMAN-DECISIONS.md` (§1 `D-13` row and the remaining-pending list) still
  show `D-13` as `HUMAN_DECISION_PENDING`, and `reports/KEEPLAB-M3-HUMAN-DECISIONS.md` lists it as
  pending-not-blocking for M3. Those are historical records and were deliberately **not** edited (the
  contract-creation task was told not to reopen old governance phases and not to create a separate
  D-13 governance task). The M4 record is authoritative for M4. Same class as MB-M3-001.
  Non-blocking.

- **MB-M4-002 — the Room schema is on a destructive-fallback bump, so M4 must NOT author a migration.**
  `KeepLabDatabase` is at version 5 with only the legacy `MIGRATION_1_2` registered and
  `fallbackToDestructiveMigration(dropAllTables = true)`, so a development database is recreated
  rather than upgraded. The M4 attachment tables therefore need a **direct version bump** (expected
  5 → 6) and no migration chain — recorded so the absent chain is not read as an omission and nobody
  authors a production migration for disposable test data. Carries MB-M3-009 forward. Non-blocking.

- **MB-M4-003 — `res/` had to be enumerated instead of blanket-forbidden.** M3 blocked
  `app/src/main/res/` as one directory. M4 needed a narrow `res/xml/` carve-out (a possible
  FileProvider configuration), but the guard tests `forbidden_paths` first, so an allowed path nested
  inside a forbidden parent is unreachable. M4 therefore lists the existing resource subdirectories
  (`drawable`, `mipmap-anydpi`, `mipmap-anydpi-v26`, `values`, `values-night`) individually as
  forbidden and allows `res/xml/`. A consequence to remember: any **new** resource directory is
  neither allowed nor forbidden and is therefore blocked as `UNCLASSIFIED_FAIL_CLOSED`. Recorded so a
  later phase does not read the enumeration as an accidental narrowing. Non-blocking.

- **MB-M4-004 — the backend test suite has no binary-body request helper yet.** The existing backend
  tests exercise JSON routes through Ktor's in-process test host; the attachment upload path needs a
  binary (byte-stream / chunk) request body. Ktor's test client can send one
  (`setBody(ByteArray)` with an octet-stream content type), so no new dependency is expected — but a
  small shared helper will have to be added in `backend/src/test/**`. Recorded so the absent helper is
  not mistaken for a blocker and so the "no dependency change" expectation is not broken for it.
  Non-blocking.

- **MB-M4-005 — `application.conf` remains a descriptor that M4 must keep in sync.** Carried from
  MB-A2-007: `application.conf` mirrors the `KEEPLAB_*` keys as HOCON substitution but is not read by
  `embeddedServer` — `AppConfig.fromEnvironment()` is the resolver. M4 adds new
  `KEEPLAB_ATTACHMENT_*` / `KEEPLAB_OBJECT_STORAGE_*` keys, so the HOCON file needs the same keys added
  by hand if the mirror is to stay honest. Non-blocking.

### Findings from the M4 execution session (`KEEPLAB-M4-ATTACHMENTS-EXECUTE`, 2026-10-06)

- **MB-M4-006 — the HOCON mirror was updated by hand (MB-M4-005 closed for M4).** Resolved during the
  execution: `application.conf` and `backend/.env.example` both carry the six attachment keys, the two
  object-storage keys and the D-13 defaults, so the mirror is honest again. The mirror is still a
  hand-maintained list, so the same care is needed at every future key addition. Non-blocking.

- **MB-M4-007 — the guard's own audit log is outside `allowed_paths` but is written on every write.**
  `orchestration/hermes/evidence/p0b-close/contract-guard-decisions.jsonl` is appended by the frozen
  `pre_tool_call` hook on each write-class tool call, so a post-run scope scan will always see it as
  "touched / unclassified". It is guard-owned, not an M4 write, and the guard must not be modified to
  change that. Recorded so a later scope scan does not misread it as a contract deviation.
  Non-blocking.

- **MB-M4-008 — the `ObjectStorage` port reads whole ranges into a `ByteArray`.** Correct and adequate
  for 25 MiB attachments and for the filesystem/in-memory drivers, but a production driver (and a
  streaming download) would prefer a stream-based range read so a large range is never buffered twice
  in memory. Revisit at deployment/infrastructure time, together with the Tencent COS adapter.
  Non-blocking.

- **MB-M4-009 — the Android limits cache refreshes on demand only.** `AttachmentLimitsProvider`
  refreshes when asked (attach path / explicit refresh) and otherwise keeps the cached or D-13 values;
  the server re-enforces every limit regardless, so a stale cache can never over-permit. A later
  milestone may refresh it on sign-in for a better first-attach UX. Non-blocking.

- **MB-M4-010 — removing an account-scoped attachment that was never uploaded is local-first.** The
  local row and file are removed and the server-side reservation is released by the attachment
  service's expiry boundary rather than by an explicit abort call. Correct and conservative; a later
  phase could add an explicit abort round-trip so the reservation is released immediately.
  Non-blocking.

- **MB-M4-011 — the Android attachment import is single-directory.** Imported bytes live in one
  app-private directory keyed by the attachment UUID; there is no per-state or per-note subdirectory
  and no cleanup of `*.part` leftovers at startup (the importer deletes its own partial file on every
  rejection path, and the directory is recreated only by a re-import). A later phase may add a
  startup sweep for stray `.part` files. Non-blocking.


