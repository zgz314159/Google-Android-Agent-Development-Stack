# Acceptance — KEEPLAB-A2-BACKEND-FOUNDATION-001

**Contract:** `KEEPLAB-A2-BACKEND-FOUNDATION-001`
**Phase:** `A2_BACKEND_FOUNDATION` (temporary execution contract)
**Date:** 2026-10-06
**Human authorization:** D-07 `KOTLIN_KTOR` · D-08 `TENCENT_CLOUD + PORTABLE_DOCKER` · D-09 `POSTGRESQL` · D-15 `YES_BOUNDED_ACCOUNT_NETWORK_UNLOCK` (phase-gated; local-first mandatory; account/network optional for local use; Room remains the local SSOT; Google/Firebase identity forbidden)
**Project data stage:** `EXPERIMENTAL` — `TEST_DATA_DISPOSABLE = YES`, `OLD_TEST_DB_COMPATIBILITY = NOT_REQUIRED`, `CLEAN_FOUNDATION > BACKWARD_COMPATIBILITY`
**Status:** READY (contract package validated; A2 itself is NOT executed)

## 0. What this package is

A temporary execution contract that authorizes **one later, separate** A2 session to create the
foundation of KeepLab's own backend through the **same unmodified Contract Guard**, inside a bounded
write surface (`KeepLab-Relay/backend/**` plus two reporting/evidence locations). It implements no
authentication, no session handling, no notes API and no sync, and it touches no Android file.

## 1. Machine-readable semantics

Recorded in `implementation-contract.json` (`frozen_technology`, `discovered_state`,
`backend_project`, `required_server_foundation`, `configuration_requirements`,
`postgresql_foundation`, `migration_foundation`, `docker_foundation`, `gradle_scope`,
`android_product_policy`, `auth_sync_boundary`, `device_policy`, `allowed_paths`,
`forbidden_paths`, `verification_intent`, `stop_conditions`) and mirrored here.

| Field | Value |
|---|---|
| `phase` | `A2_BACKEND_FOUNDATION` |
| `human_decisions` | D-07 / D-08 / D-09 / D-15 |
| `project_data_stage` | `EXPERIMENTAL` (backend data included) |
| `BACKEND_PATH` | `/mnt/AndroidDev/Projects/KeepLab-Relay/backend/` |
| `BACKEND_PATH_STATE` | `ABSENT` — never existed, no conflict to overwrite |
| `BACKEND_BUILD_MODEL` | `INDEPENDENT_GRADLE_PROJECT` |
| `WRAPPER` | reuse `KeepLab-Relay/gradlew` (Gradle 9.5.1) |
| `ROOT_ANDROID_GRADLE_CHANGE_REQUIRED` | `NO` |
| `LANGUAGE` / `SERVER` / `DATABASE` / `DEPLOYMENT` | `KOTLIN` / `KTOR` / `POSTGRESQL` / `PORTABLE_DOCKER` |
| `implementation_authorization` | granted to the A2 execution task only, `PHASE_GATED` |
| `auth_change` / `sync_change` / `cloud_provisioning` | `FORBIDDEN` |
| `android_product_change` / `android_gradle_change` | `FORBIDDEN` |
| `device_operation` | `FORBIDDEN` (`NOT_USED`) |

## 2. Required server foundation

| Item | Requirement |
|---|---|
| engine | Ktor on Netty or an equivalent normal Ktor engine (`embeddedServer`) |
| entry point | `Application.kt` with `main()` and/or the application module used by `testApplication` |
| serialization | JSON via Ktor content negotiation (kotlinx.serialization or Jackson) |
| configuration | structured config read from `KEEPLAB_*` environment variables |
| error handling | centralized `StatusPages`-style handling; raw exceptions never leak |
| `GET /health` | no authentication; server-alive result; **must not** touch the database |
| `GET /ready` | readiness incl. **database reachability through a small injectable abstraction**; success when the probe reports reachable, non-success when it reports unreachable; never crashes the process |

**Not in the server:** no user, account, credential, password, session or token logic; no
authentication middleware; no notes API; no sync API; no outbox; no cursor; no conflicts; no
attachments; no collaboration.

## 3. Configuration

| Variable | Role |
|---|---|
| `KEEPLAB_HTTP_PORT` | HTTP port (non-secret default allowed) |
| `KEEPLAB_DB_URL` | JDBC URL of the PostgreSQL database |
| `KEEPLAB_DB_USER` | database user |
| `KEEPLAB_DB_PASSWORD` | database password |

- `backend/.env.example` exists with **placeholders only**.
- `backend/.env` **must not** be created and must not be committed.
- No real password, token, key or certificate may be written, committed or echoed into evidence.

## 4. PostgreSQL foundation

HikariCP connection pool + the official PostgreSQL JDBC driver. **No ORM**, no domain repository.
One explicit DB component that can initialize the pool from configuration, execute a `SELECT 1`
readiness probe and close the pool cleanly on shutdown. The probe sits behind a small abstraction
so `/ready` is testable with a fake and needs no live PostgreSQL.

## 5. Migration foundation

Flyway, `backend/src/main/resources/db/migration/`, exactly one initial migration `V1` whose only
content is a foundation namespace (e.g. `CREATE SCHEMA IF NOT EXISTS keeplab;`).

**Forbidden in the initial migration:** `users`, `credentials`, `sessions`, refresh tokens, `notes`,
sync operations, outbox, change log/cursors, attachments, collaboration tables. No fake business
table may be created merely to prove that migrations run.

## 6. Docker foundation

`backend/Dockerfile` (multi-stage, no embedded credentials), `backend/docker-compose.yml`
(PostgreSQL service with a **named volume** for its data + backend service wired by `KEEPLAB_*`
environment variables), `backend/.dockerignore`, `backend/.env.example`.

Development-only placeholder database credentials are allowed and must be obviously local. The
setup must stay **portable to other normal container hosts**. **Nothing is deployed or provisioned**;
no Tencent Cloud resource, credential or proprietary binding exists.

## 7. Allowed write surface (exhaustive)

1. `KeepLab-Relay/backend/` — the whole new backend project (source, backend-local Gradle files,
   resources, migrations, tests, Dockerfile, docker-compose.yml, .env.example, .dockerignore)
2. `Google-Android-Agent-Development-Stack/reports/`
3. `Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/keeplab-a2-backend-foundation/`

Everything else inside the project root is BLOCKED (fail-closed), including all of
`KeepLab-Relay/app/**`, `benchmark/`, every root Gradle file, `gradle/`, `gradlew`, `specs/`,
`verification/`, the product governance files, the frozen P0B packages,
`reports/contracts/` (this package included), `Testapp/`, `PowerAi/` and `KeepLab-Relay-evidence/`.

## 8. Acceptance criteria

### AC-A2BF-001 — independent backend project exists and builds

- Verification: `backend/settings.gradle.kts` and `backend/build.gradle.kts` exist as an independent
  build; `cd /mnt/AndroidDev/Projects/KeepLab-Relay && ./gradlew -p backend build` succeeds;
  `KeepLab-Relay/settings.gradle.kts` is byte-identical (no `:backend` include was added).

### AC-A2BF-002 — the server starts structurally

- Verification: the Ktor application module starts under `testApplication` (or an equivalent
  deterministic test harness) on a normal engine, with JSON serialization, `KEEPLAB_*`
  configuration parsing and centralized error handling wired.

### AC-A2BF-003 — `/health` works without authentication and without the database

- Verification: a deterministic test asserts a success status and a server-alive body for
  `GET /health` with no credentials supplied, and asserts the database is never queried on that path.

### AC-A2BF-004 — `/ready` reflects the injectable readiness abstraction

- Verification: two deterministic tests through a fake probe — reachable ⇒ success status;
  unreachable ⇒ a non-success (service-unavailable class) status, with the process still alive.

### AC-A2BF-005 — environment configuration, no real secret

- Verification: every environment-specific value resolves from a `KEEPLAB_*` variable or a
  non-secret default; `backend/.env.example` contains placeholders only; no `backend/.env` exists;
  a secret scan over the created backend tree finds no real credential.

### AC-A2BF-006 — PostgreSQL connectivity foundation exists

- Verification: the DB component compiles against HikariCP and the PostgreSQL JDBC driver, builds
  its pool from configuration, exposes a `SELECT 1` probe behind the readiness abstraction and
  closes the pool cleanly on shutdown.

### AC-A2BF-007 — Flyway foundation exists

- Verification: Flyway is configured against `backend/src/main/resources/db/migration/`; exactly one
  migration file exists; its SQL creates only the foundation namespace and no business table.

### AC-A2BF-008 — portable Docker development setup exists

- Verification: `backend/Dockerfile` and `backend/docker-compose.yml` exist; the compose file defines
  a PostgreSQL service with a named data volume and a backend service wired by `KEEPLAB_*`
  environment variables; no production secret and no cloud-specific binding is present.
  `docker compose -f backend/docker-compose.yml config` parses successfully **if** a container
  runtime is available; otherwise `DOCKER_RUNTIME_SMOKE = SKIPPED_TOOL_UNAVAILABLE` is recorded and
  A2 is not blocked.

### AC-A2BF-009 — nothing later-phase was implemented

- Verification: source inspection of the created backend tree shows no authentication, registration,
  password, passkey, token, session, user/credential table, JWT/OAuth, Google/Firebase integration,
  notes API, sync API, outbox, cursor, conflict, revision, attachment or collaboration code, and no
  Tencent Cloud resource or credential.

### AC-A2BF-010 — one verification pass and an untouched Android product

- Verification: `./gradlew -p backend test build` run once, PASS; after any deterministic failure
  only the failed task re-run; every `frozen_inputs` file re-hashed byte-identical; the scope scan
  shows every created/modified file under `KeepLab-Relay/backend/**` and no change under
  `KeepLab-Relay/app/**`.

## 9. Required guard classifications (validated in this phase, simulated)

| Write target | Required |
|---|---|
| `KeepLab-Relay/backend/settings.gradle.kts` | ALLOW |
| `KeepLab-Relay/backend/build.gradle.kts` | ALLOW |
| `KeepLab-Relay/backend/src/main/kotlin/.../Application.kt` | ALLOW |
| `KeepLab-Relay/backend/src/main/resources/db/migration/V1__*.sql` | ALLOW |
| `KeepLab-Relay/backend/Dockerfile`, `docker-compose.yml`, `.env.example` | ALLOW |
| `KeepLab-Relay/backend/build/...` | ALLOW |
| `Google-Android-Agent-Development-Stack/reports/...` | ALLOW |
| `.../orchestration/hermes/evidence/keeplab-a2-backend-foundation/...` | ALLOW |
| `KeepLab-Relay/app/src/main/java/...` (any) | BLOCK |
| `KeepLab-Relay/app/build.gradle.kts` | BLOCK |
| `KeepLab-Relay/settings.gradle.kts`, `build.gradle.kts`, `gradle/libs.versions.toml` | BLOCK |
| `KeepLab-Relay/gradle/...`, `gradlew`, `gradlew.bat`, `gradle.properties` | BLOCK |
| `KeepLab-Relay/Dockerfile`, `KeepLab-Relay/docker-compose.yml` (root-level) | BLOCK |
| `KeepLab-Relay/server/...`, `infra/...`, `cloud/...`, `firebase/...` | BLOCK |
| `KeepLab-Relay/specs/...`, `verification/...`, `MISSION.md` | BLOCK |
| `Testapp/...`, `PowerAi/...`, `KeepLab-Relay-evidence/...` | BLOCK |
| `.../evaluation_adapter/contract_guard.py` | BLOCK |
| this contract package itself | BLOCK |
| every earlier A0/A1 contract package | BLOCK |

**Guard scope, stated plainly.** The frozen guard classifies write *targets*, not tool choice.
`adb`, `./gradlew`, `docker compose`, a container run and Hermes config/core paths (outside the
project root) are not blocked by any path list, so the device prohibition, the cloud-provisioning
prohibition, the "no root Gradle change" rule and the Hermes-core prohibition are enforced by this
contract's stop conditions. They are not weaker for that: violating one is a `CONTRACT_DEVIATION`.

## 10. Readiness gates

| Gate | Result |
|---|---|
| acceptance | PASS |
| boundaries | PASS |
| hashes | PASS |
| backend_path | PASS (ABSENT — no conflict) |
| traceability | PASS |
| guard_simulation | PASS |
