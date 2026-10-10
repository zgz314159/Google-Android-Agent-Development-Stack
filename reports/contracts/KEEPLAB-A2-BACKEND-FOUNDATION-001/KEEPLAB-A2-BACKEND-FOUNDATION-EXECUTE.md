# KEEPLAB-A2-BACKEND-FOUNDATION-EXECUTE

**Contract:** `KEEPLAB-A2-BACKEND-FOUNDATION-001` (READ_ONLY_INPUT — this package is never edited)
**Phase:** `A2_BACKEND_FOUNDATION`
**Mode:** PLAN ONCE → EXECUTE → VERIFY ONCE → PASS = STOP · FAIL = fix the failed path only
**Authorization:** D-07 `KOTLIN_KTOR` · D-08 `TENCENT_CLOUD + PORTABLE_DOCKER` · D-09 `POSTGRESQL` · D-15 `YES_BOUNDED_ACCOUNT_NETWORK_UNLOCK`
**Data stage:** `EXPERIMENTAL` — `CLEAN_FOUNDATION > BACKWARD_COMPATIBILITY`

---

## 0. Stop conditions — read before anything else

STOP and report (never work around) if:

1. Any required write falls outside `allowed_paths` or targets a forbidden path → `CONTRACT_DEVIATION`.
2. Any `frozen_inputs` file has drifted → `STALE_BACKEND_FOUNDATION_INPUT`.
3. `KeepLab-Relay/backend/` already contains unrelated implementation → `A2_BACKEND_PATH_CONFLICT`; do not overwrite it.
4. The independent backend project cannot work without a root Gradle change → `A2_ROOT_GRADLE_CHANGE_REQUIRED` with the exact file and change; do not make it.
5. The existing wrapper genuinely cannot run the backend build → `A2_BACKEND_WRAPPER_REQUIRED` with the proof; do not silently add a second wrapper.
6. Any Android product file, Android Gradle file, Room/entity/DAO code or Android UI would have to change.
7. Any authentication, registration, password, passkey, token, session, user/credential table or Google/Firebase integration would be needed.
8. Any notes API, sync API, outbox, delta cursor, conflict resolution, revision protocol, attachment or collaboration feature would be needed.
9. Any Tencent Cloud resource would have to be provisioned, any cloud credential used, or any cloud-specific binding introduced.
10. A real secret would have to be written, committed or echoed into evidence.
11. A business table would have to be created merely to prove migrations work.
12. The device would have to be touched, or `adb` / an instrumentation run used.
13. The guard source, the hook configuration, Hermes core, the frozen P0B-CLOSE contract, an A0/A1 package or this package would have to be modified.
14. The contract package manifest does not verify.
15. Allowed paths would have to be broadened to finish.
16. The gate fails and the fix would reach outside `allowed_paths`.
17. The same failure survives two genuine fixes → `REPEATED_FAILURE`, then ONE root-cause analysis; do not restart A2 from zero.
18. A second review, second audit, post-PASS cleanup or re-run of a passing task is being considered after PASS.
19. A minor wording/naming/warning issue is being turned into a new contract → append it compactly to `reports/KEEPLAB-MINOR-BACKLOG.md` instead.

**Explicitly out of scope for this phase:** A3, A4, any authentication or sync work, any Android
product work, any device work, any cloud provisioning, Google Keep work, Testapp, PowerAi.

---

## 1. Activation

```
export HERMES_CONTRACT_PACKAGE=/mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack/reports/contracts/KEEPLAB-A2-BACKEND-FOUNDATION-001
```

Same unmodified guard, same fail-closed `pre_tool_call` hook, different package. Verify
`contract_guard.py` sha256 = `e418fc28b08ac7afe4fdd42ec44d572ddaa2f23f6200de300ecac211404b3746`
before starting; a different hash is a STOP.

---

## 2. PLAN ONCE

1. Verify the contract package: re-hash the five manifest entries against `manifest.json` (must be
   `MANIFEST_OK`). Do not rewrite, re-hash or extend the package.
2. Re-hash every file in `frozen_inputs.files` and assert byte-identity. Any drift is
   `STALE_BACKEND_FOUNDATION_INPUT`.
3. Confirm `KeepLab-Relay/backend/` is still absent (or empty of unrelated implementation).
4. Read: this prompt, `acceptance.md`, `KeepLab-Relay/settings.gradle.kts`,
   `KeepLab-Relay/gradle/wrapper/gradle-wrapper.properties`, `KeepLab-Relay/MISSION.md`,
   `reports/KEEPLAB-AUTH-SYNC-ARCHITECTURE-SPEC.md` §23/§23.1, and the A2 row of
   `reports/KEEPLAB-AUTH-SYNC-IMPLEMENTATION-ROADMAP.md`.
5. Write the short plan (task order TASK-01 → TASK-05, files to create, the commands to run).
   Then execute. Do not re-plan after starting; do not re-read the same files repeatedly.

**Host facts confirmed at authoring time:** JDK 21 present; Gradle wrapper 9.5.1; **no Docker
installed**; no `psql`; `KeepLab-Relay` is a git repo with **no commits** (so change evidence is
sha256-based, not `git diff`).

---

## 3. EXECUTE

### TASK-01 — independent backend project + Ktor server foundation

Create `KeepLab-Relay/backend/` as an **independent** Gradle project:

- `backend/settings.gradle.kts` — `rootProject.name` for the backend, `mavenCentral()` repositories,
  its own `pluginManagement`. It must NOT reference the Android build, the Android version catalog
  or AGP.
- `backend/build.gradle.kts` — Kotlin/JVM + Ktor application plugin/`application` main class,
  Netty engine, content negotiation + JSON, logging, test dependencies (JUnit/Kotlin test +
  `ktor-server-test-host`). Resolve current stable, mutually compatible versions from public
  repositories; the Android `gradle/libs.versions.toml` is **not** a version source.
- `backend/gradle.properties` only if a JVM/daemon property is genuinely needed — with `-p backend`
  the repository-root `gradle.properties` is not read.
- `src/main/kotlin/<pkg>/Application.kt` — `main()` (embeddedServer on the configured port) plus
  the application module function used by `testApplication`.
- `src/main/kotlin/<pkg>/config/` — structured configuration from `KEEPLAB_HTTP_PORT`,
  `KEEPLAB_DB_URL`, `KEEPLAB_DB_USER`, `KEEPLAB_DB_PASSWORD` with non-secret defaults.
- `src/main/kotlin/<pkg>/routes/` — `GET /health` (no auth, **no database touch**, server-alive
  body) and `GET /ready` (readiness through the injectable probe from TASK-02).
- Centralized error handling (`StatusPages` or equivalent); raw exceptions never leak.
- `src/main/resources/application.conf` — HOCON with environment substitution.
- `backend/.env.example` — placeholders only. **Never** create `backend/.env`.

Do not create unnecessary layers. No `accounts`/`users` table, no auth middleware, no stub product
endpoint.

### TASK-02 — PostgreSQL + Flyway foundation

- `src/main/kotlin/<pkg>/db/` — one explicit DB component using **HikariCP** + the **PostgreSQL
  JDBC driver**: build the pool from configuration, expose a `SELECT 1` readiness probe behind a
  small interface (e.g. `DatabaseReadiness` / functional type) so `/ready` is testable with a fake,
  and close the pool cleanly on shutdown. **No ORM**, no domain repository.
- A pool failure must degrade `/ready` only — `/health` must stay independent of the database.
- Flyway configured against `src/main/resources/db/migration/` (migrate-on-start or an explicit
  entry point — record which).
- Exactly one migration, `V1__…sql`, whose only content is a foundation namespace, e.g.
  `CREATE SCHEMA IF NOT EXISTS keeplab;`. **No business table.**

### TASK-03 — portable Docker development setup

- `backend/Dockerfile` — multi-stage (build stage + slim JRE runtime), no embedded credentials,
  exposes the configured HTTP port.
- `backend/docker-compose.yml` — a `postgres` service (public official image, obvious
  development-only placeholder credentials, **named volume** for its data directory) and a
  `backend` service (built from the Dockerfile, wired by `KEEPLAB_*` environment variables,
  depends on the database, port mapped).
- `backend/.dockerignore`.
- Portable to other normal container hosts: no Tencent-proprietary image, no cloud volume driver,
  no managed-service binding, no cloud credential. **Deploy nothing.**

### TASK-04 — small deterministic test suite

`backend/src/test/kotlin/…` covering exactly:

- `/health` returns success (and does not require the database);
- configuration parsing from the expected environment variables;
- `/ready` **success** and `/ready` **failure** through a fake readiness probe;
- the application starts under `testApplication` (or an equivalent deterministic harness).

No live PostgreSQL required. Do not build a huge testing framework.

### TASK-05 — one verification pass + evidence

Run the mandatory gate **once**:

```
cd /mnt/AndroidDev/Projects/KeepLab-Relay
./gradlew -p backend test build
```

Optional, at most once each, only if genuinely available and cheap:

```
docker compose -f backend/docker-compose.yml config
```

If no container runtime exists → record `DOCKER_RUNTIME_SMOKE = SKIPPED_TOOL_UNAVAILABLE` and
continue. This never blocks A2.

Then: re-hash the `frozen_inputs` files (byte-identity required), run the scope scan (every
created/modified file under `KeepLab-Relay/backend/**`; nothing changed under `KeepLab-Relay/app/**`),
run the secret scan, and write the evidence + report under
`orchestration/hermes/evidence/keeplab-a2-backend-foundation/` and `reports/`.

---

## 4. VERIFY ONCE

The acceptance criteria in `acceptance.md` §8 are the gate. Verify each one **once**, from the
artefacts on disk and the single build/test run:

| Criterion | Evidence |
|---|---|
| AC-A2BF-001 | `./gradlew -p backend build` succeeds; `KeepLab-Relay/settings.gradle.kts` byte-identical |
| AC-A2BF-002 | application starts under `testApplication`; serialization, config, error handling wired |
| AC-A2BF-003 | `/health` success test passes; database not queried on that path |
| AC-A2BF-004 | `/ready` reachable ⇒ success; unreachable ⇒ non-success; process alive |
| AC-A2BF-005 | `KEEPLAB_*` configuration resolves; `.env.example` placeholders only; no `.env`; secret scan clean |
| AC-A2BF-006 | HikariCP + PostgreSQL JDBC pool init / `SELECT 1` probe / clean close |
| AC-A2BF-007 | Flyway wired; exactly one migration; foundation namespace only |
| AC-A2BF-008 | Dockerfile + docker-compose.yml (postgres + backend, named volume); `SKIPPED_TOOL_UNAVAILABLE` if no runtime |
| AC-A2BF-009 | no auth, session, token, notes API, sync, outbox, cursor, conflict, attachment or collaboration code; no cloud resource |
| AC-A2BF-010 | gate run once, PASS; frozen inputs byte-identical; scope scan clean |

**PASS = STOP.** Do not run a second review, a second audit, a post-PASS cleanup, a full-repository
scan, or the Android build.

---

## 5. FAIL path

1. Read the failure **once** (build/test output, the failing step).
2. Fix **only** the failed path, inside `KeepLab-Relay/backend/**`.
3. Re-run **only** the failed task (e.g. `./gradlew -p backend test`), not the whole phase.
4. Same failure after two genuine fixes → `REPEATED_FAILURE`, then ONE root-cause analysis.
5. Never restart A2 from zero. Never fix outside `allowed_paths`.

---

## 6. Final report (short)

```
KEEPLAB-A2-BACKEND-FOUNDATION-EXECUTE
=====================================
BACKEND PATH: /mnt/AndroidDev/Projects/KeepLab-Relay/backend/
BACKEND PATH STATE BEFORE: ABSENT / CONFLICT
BACKEND PROJECT: INDEPENDENT_GRADLE_PROJECT
ROOT ANDROID GRADLE MODIFIED: NO / YES
GATE: ./gradlew -p backend test build → PASS / FAIL
BACKEND TESTS: <n> passed / <n> failed
/health: PASS / FAIL
/ready (reachable / unreachable): PASS / FAIL
POSTGRESQL (HikariCP + JDBC): CONFIGURED / ABSENT
FLYWAY + INITIAL MIGRATION: PRESENT / ABSENT
DOCKERFILE / DOCKER-COMPOSE: PRESENT / ABSENT
DOCKER_RUNTIME_SMOKE: PASS / SKIPPED_TOOL_UNAVAILABLE / FAIL
SECRET SCAN: CLEAN / FINDING
ANDROID APP TOUCHED: NO / YES
AUTH IMPLEMENTED: NO / YES
SYNC IMPLEMENTED: NO / YES
CLOUD PROVISIONED: NO / YES
DEVICE: NOT_USED
STATUS: PASS / FAIL / <STOP CODE>
NEXT: <none — A3 stays BLOCKED_BY_HUMAN_DECISIONS>
=====================================
```

Stop after printing it. Do not start A3. Do not reopen A0 or A1. Do not run a post-PASS audit.
