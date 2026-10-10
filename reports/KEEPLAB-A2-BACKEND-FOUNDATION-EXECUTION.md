# KEEPLAB-A2-BACKEND-FOUNDATION-EXECUTE

**Contract:** `KEEPLAB-A2-BACKEND-FOUNDATION-001` (`READ_ONLY_INPUT`, unchanged)
**Phase:** `A2_BACKEND_FOUNDATION` · **Mode:** PLAN ONCE → EXECUTE → VERIFY ONCE → PASS = STOP
**Date:** 2026-10-06 · **Authorization:** D-07 `KOTLIN_KTOR` · D-08 `TENCENT_CLOUD + PORTABLE_DOCKER` ·
D-09 `POSTGRESQL` · D-15 `YES_BOUNDED_ACCOUNT_NETWORK_UNLOCK`
**Data stage:** `EXPERIMENTAL` — `CLEAN_FOUNDATION > BACKWARD_COMPATIBILITY`
**Status:** `PASS` · **Next:** none — A3 stays `BLOCKED_BY_HUMAN_DECISIONS`

## 1. Final report

```
KEEPLAB-A2-BACKEND-FOUNDATION-EXECUTE
=====================================
BACKEND PATH: /mnt/AndroidDev/Projects/KeepLab-Relay/backend/
BACKEND PATH STATE BEFORE: ABSENT
BACKEND PROJECT: INDEPENDENT_GRADLE_PROJECT
ROOT ANDROID GRADLE MODIFIED: NO
GATE: ./gradlew -p backend test build → PASS
BACKEND TESTS: 7 passed / 0 failed
/health: PASS
/ready (reachable / unreachable): PASS
POSTGRESQL (HikariCP + JDBC): CONFIGURED
FLYWAY + INITIAL MIGRATION: PRESENT
DOCKERFILE / DOCKER-COMPOSE: PRESENT
DOCKER_RUNTIME_SMOKE: SKIPPED_TOOL_UNAVAILABLE
SECRET SCAN: CLEAN
ANDROID APP TOUCHED: NO
AUTH IMPLEMENTED: NO
SYNC IMPLEMENTED: NO
CLOUD PROVISIONED: NO
DEVICE: NOT_USED
STATUS: PASS
NEXT: none — A3 stays BLOCKED_BY_HUMAN_DECISIONS
=====================================
```

## 2. Pre-flight (PLAN ONCE)

| Check | Result |
|---|---|
| Contract package manifest, 5 entries re-hashed | `MANIFEST_OK` |
| `contract_guard.py` sha256 | `e418fc28…4b3746` — matches the contract's expected hash |
| Hook config + allowlist sha256 | matches the contract's recorded hashes; not modified |
| `frozen_inputs` (11 files) re-hashed BEFORE any write | 11/11 byte-identical — no `STALE_BACKEND_FOUNDATION_INPUT` |
| `KeepLab-Relay/backend/` | `ABSENT` — nothing to overwrite, no `A2_BACKEND_PATH_CONFLICT` |
| `HERMES_CONTRACT_PACKAGE` | already pointed at the A2 package in the runtime environment |

Read before starting: this prompt, `acceptance.md`, `KeepLab-Relay/settings.gradle.kts`,
`gradle/wrapper/gradle-wrapper.properties`, `KEEPLAB-AUTH-SYNC-ARCHITECTURE-SPEC.md` §23/§23.1 and
the A2 row of `KEEPLAB-AUTH-SYNC-IMPLEMENTATION-ROADMAP.md`. Nothing was re-planned afterwards.

**Plan (unchanged for the whole run):** TASK-01 project + Ktor foundation → TASK-02 PostgreSQL +
Flyway → TASK-03 Docker → TASK-04 tests → TASK-05 one gate run + evidence.

## 3. TASK-01 — independent backend project and Ktor server

Created `KeepLab-Relay/backend/` as its own Gradle build:

```
backend/settings.gradle.kts      rootProject.name = "keeplab-backend"; own pluginManagement
                                 (gradlePluginPortal + mavenCentral) and
                                 dependencyResolutionManagement (mavenCentral, FAIL_ON_PROJECT_REPOS)
backend/build.gradle.kts         Kotlin/JVM 2.4.20 + kotlinx.serialization plugin + `application`,
                                 mainClass com.keeplab.backend.ApplicationKt, jvmToolchain(21)
src/main/kotlin/com/keeplab/backend/
  Application.kt                 main(): embeddedServer(Netty, the configured port); keeplabModule()
  config/AppConfig.kt            structured configuration from the KEEPLAB_* variables
  routes/Routes.kt               GET /health, GET /ready
  routes/ApiModels.kt            @Serializable HealthResponse / ReadyResponse / ErrorResponse
src/main/resources/application.conf   HOCON with ${?KEEPLAB_*} substitution
src/main/resources/logback.xml        slf4j/logback console configuration
```

- **No** reference to the Android build, the Android version catalog or AGP. No root Gradle change
  (`A2_ROOT_GRADLE_CHANGE_REQUIRED` did not arise) and no second wrapper
  (`A2_BACKEND_WRAPPER_REQUIRED` did not arise): the backend is reached only through
  `./gradlew -p backend`.
- Endpoints: `GET /health` (server-alive, no auth, **no database touch**), `GET /ready` (readiness
  through the injectable probe). No stub product endpoint.
- Centralized error handling via `StatusPages`: `exception<Throwable>` logs the cause server-side and
  answers a generic `INTERNAL_ERROR` body — raw exceptions never leak; a `404` handler answers a
  consistent `NOT_FOUND` body.
- `backend/gradle.properties` was **not** created: no JVM/daemon property was needed.

### Versions (resolved from public repositories, not from the Android catalog — MB-A2-003)

| Component | Version |
|---|---|
| Kotlin / kotlinx.serialization plugin | 2.4.20 |
| Ktor (core, netty, content-negotiation, kotlinx-json, status-pages, call-logging, test-host) | 3.6.0 |
| kotlinx-serialization-json | 1.11.0 |
| HikariCP | 7.1.0 |
| PostgreSQL JDBC | 42.7.13 |
| Flyway (core + database-postgresql) | 13.9.0 |
| Logback | 1.6.5 |
| JUnit Jupiter / junit-platform-launcher | 6.1.3 |

Each artifact's existence was verified against Maven Central before the build, and the Ktor 3.6.0
`StatusPagesConfig`, `CallLoggingConfig`, `EmbeddedServerKt`, `RoutingContext`, `ApplicationCall`,
`Application.log` and `TestApplicationKt` signatures were read from the published jars with `javap`
so the single gate run did not have to discover them.

## 4. TASK-02 — PostgreSQL and Flyway foundation

```
src/main/kotlin/com/keeplab/backend/db/DatabaseReadiness.kt   fun interface DatabaseReadiness
src/main/kotlin/com/keeplab/backend/db/PostgresDatabase.kt    HikariCP pool + SELECT 1 probe + close
src/main/kotlin/com/keeplab/backend/db/FlywayMigrations.kt    Flyway entry point
src/main/resources/db/migration/V1__create_keeplab_foundation_schema.sql
```

- HikariCP pool built from `DatabaseConfig` (`maximumPoolSize = 5`, `connectionTimeout = 3000 ms`).
  `initializationFailTimeout = -1` is deliberate: an unreachable database **never** prevents
  start-up, so a pool failure degrades `/ready` only and `/health` stays independent.
- `SELECT 1` probe returns `true` only on a `1` result; `SQLException` is caught, logged at debug and
  reported as not-ready — never rethrown.
- `close()` closes the pool; `main()` subscribes to `ApplicationStopped` and calls it.
- **No ORM**, no domain repository, no think-about-it-later abstraction layer.
- Flyway is configured against `classpath:db/migration`, i.e.
  `src/main/resources/db/migration/`. Migration is **migrate-on-start through an explicit entry
  point**: `FlywayMigrations.migrate(dataSource)` called once from `main()`, best-effort — a failure
  is logged and degrades `/ready` only.
- Exactly one migration. Its complete content is `CREATE SCHEMA IF NOT EXISTS keeplab;` plus a
  comment. No business table, and no placeholder table created merely to prove migrations run.

## 5. TASK-03 — portable Docker development setup

| File | Content |
|---|---|
| `backend/Dockerfile` | multi-stage: `gradle:9.5.1-jdk21` (the same Gradle line the project pins) builds `installDist`; `eclipse-temurin:21-jre` runs `/app/bin/keeplab-backend`. `EXPOSE 8080`. No embedded credential. |
| `backend/docker-compose.yml` | `postgres` service (`postgres:17-alpine`, development-only placeholder credentials, **named volume** `keeplab-postgres-data:/var/lib/postgresql/data`, healthcheck) + `backend` service built from the Dockerfile, wired by `KEEPLAB_HTTP_PORT` / `KEEPLAB_DB_URL` / `KEEPLAB_DB_USER` / `KEEPLAB_DB_PASSWORD`, `depends_on` the healthy database, port 8080 mapped. |
| `backend/.dockerignore` | excludes `build/`, `.gradle/`, `.kotlin/`, `.env`, `.env.*` (keeping `.env.example`), the container description files and editor/VCS noise. |
| `backend/.env.example` | placeholders only. `backend/.env` was never created. |

Portability: public upstream images only — no Tencent-proprietary image, no cloud volume driver, no
managed-service binding, no cloud credential. **Nothing was deployed or provisioned.**

Build-context note: the compose `build.context` is `backend/` itself, so `backend/.dockerignore`
genuinely applies. Because that context cannot carry the repository wrapper, the build stage uses the
official Gradle image at the pinned 9.5.1 line rather than adding a **second** `gradlew` to the
repository (which stop-condition 5 forbids).

## 6. TASK-04 — deterministic test suite (7 tests)

| Class | Tests |
|---|---|
| `ConfigurationTest` | `KEEPLAB_*` values resolve; absent variables fall back to non-secret defaults with an empty password |
| `HealthRouteTest` | `/health` returns 200 + an UP body and the recording probe proves the database is **never** queried |
| `ReadyRouteTest` | probe reachable ⇒ 200 READY; probe unreachable ⇒ 503 NOT_READY with `/health` still 200 |
| `ApplicationStartupTest` | the module starts under `testApplication` and serves both endpoints; an unknown route is answered by the centralized error handling |

No live PostgreSQL is required and none was started. No test framework beyond the one Ktor ships was
built.

## 7. TASK-05 — the single verification pass

```
cd /mnt/AndroidDev/Projects/KeepLab-Relay
./gradlew -p backend test build --console=plain
→ BUILD SUCCESSFUL in 3m 36s      (8 actionable tasks: 8 executed)
→ tests="7" failures="0" errors="0" skipped="0"
```

Run **once**. No retry, no `--continue-on-fail`, no second review, no post-PASS cleanup, no
full-repository scan and no Android build.

Docker runtime smoke: `docker`, `docker-compose` and `podman` are all absent on the host, so
`docker compose config` was not run and
`DOCKER_RUNTIME_SMOKE = SKIPPED_TOOL_UNAVAILABLE` is recorded (anticipated by MB-A2-001; never a
blocker for A2).

### Post-run checks

| Check | Result |
|---|---|
| `frozen_inputs` re-hashed (11 files) | 11/11 byte-identical, `mismatches = []` |
| Scope scan — files created/modified outside `KeepLab-Relay/backend/**` | 0 files (two **directory** mtimes: `KeepLab-Relay` gained `backend/`, and `.git`'s directory mtime moved while the read-only `git log`/`git status` baseline ran — no file inside `.git` changed) |
| Scope scan — files touched under `KeepLab-Relay/app/**` | 0. Anchor `app/build.gradle.kts` byte-identical |
| Root Gradle surface | `settings.gradle.kts`, `build.gradle.kts`, `libs.versions.toml`, `gradle-wrapper.properties`, `gradle.properties`, `gradlew` all byte-identical |
| Secret scan (whole backend tree incl. build output) | CLEAN — 0 matches across private-key/AWS/GCP/GitHub/Slack/JWT/credential-assignment/connection-string patterns |
| `backend/.env` | ABSENT |
| Guard, hook config, allowlist, contract packages | byte-identical; the A2 package was not rewritten, re-hashed or extended |

## 8. Acceptance criteria

| Criterion | Result |
|---|---|
| AC-A2BF-001 independent backend project exists and builds | PASS |
| AC-A2BF-002 the server starts structurally (serialization, config, error handling) | PASS |
| AC-A2BF-003 `/health` without auth and without the database | PASS |
| AC-A2BF-004 `/ready` through the injectable abstraction, both outcomes | PASS |
| AC-A2BF-005 environment configuration, no real secret | PASS |
| AC-A2BF-006 PostgreSQL connectivity foundation | PASS |
| AC-A2BF-007 Flyway foundation, one foundation-only migration | PASS |
| AC-A2BF-008 portable Docker development setup | PASS (`SKIPPED_TOOL_UNAVAILABLE` for the runtime smoke) |
| AC-A2BF-009 nothing later-phase was implemented | PASS |
| AC-A2BF-010 one verification pass, untouched Android product | PASS |

**Verdict: 10/10 PASS.** No stop code was reached.

## 9. Boundaries held

| Boundary | State |
|---|---|
| Android product / Android Gradle | untouched (`app/**` and every root Gradle file byte-identical) |
| Authentication, sessions, tokens, user/credential tables, Google/Firebase | none — not implemented, not required |
| Notes API, sync, outbox, delta cursor, conflict/revision protocol, attachments, collaboration | none |
| Tencent Cloud / any cloud resource or credential | none provisioned, none referenced |
| Business table for migration proof | none — the only migration statement creates a schema |
| Physical device `87296ada`, `adb`, instrumentation | not used |
| Guard source, hook configuration, Hermes core, P0B-CLOSE, A0/A1 packages, this package | unmodified |

## 10. Evidence

`Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/keeplab-a2-backend-foundation/`

| File | Content |
|---|---|
| `after-hash.json` | package manifest + guard/hook hashes, `frozen_inputs` before/after, the 21 created files with sha256, the protected-snapshot result |
| `acceptance-evidence.json` | AC-A2BF-001…010, each with its evidence and result, plus the stop-condition checklist |
| `gate.txt` | the single gate run: command, task graph, results, observed HTTP behaviour, build outputs, the Docker smoke outcome |
| `scope-scan.txt` | the mtime-based scope proof (backend-only writes, `app/**` untouched) |
| `secret-scan.txt` | the pattern scan and the manual placeholder inspection |
| `before-hash.json`, `guard-simulation.json` (pre-existing) | the contract phase's pre-phase hashes and guard simulation — untouched |

## 11. Notes for a later reader (honest limitations)

1. **`application.conf` is a descriptor, not the resolver.** It declares the exact `keeplab.http.*` /
   `keeplab.database.*` keys with `${?KEEPLAB_*}` substitution, but the authoritative runtime
   resolver is `AppConfig.fromEnvironment()`, which reads the same variables directly (as TASK-01
   requires). The two use identical key names and cannot disagree; the HOCON file is not read by
   `embeddedServer` and exists for documentation and for engine-based deployments.
2. **Docker is statically validated only.** No container runtime exists on this host, so no image was
   built and no container was started. The Dockerfile and compose file were not executed.
3. **The scope proof is mtime + sha256, not `git diff`.** `KeepLab-Relay` still has no commits
   (MB-A1-002 / MB-A2-002).
4. **MB-A2-005 stays open by design.** Object storage, the load-balancer product and
   managed-vs-container PostgreSQL remain later-phase decisions; A2 created none of them.

Stop. A3 is not started, A0/A1 are not reopened, and no post-PASS audit was run.
