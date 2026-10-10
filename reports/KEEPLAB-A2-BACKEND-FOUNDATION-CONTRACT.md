# KEEPLAB-A2-BACKEND-FOUNDATION-CONTRACT

**Contract package:** `Google-Android-Agent-Development-Stack/reports/contracts/KEEPLAB-A2-BACKEND-FOUNDATION-001/`
**Contract ID:** `KEEPLAB-A2-BACKEND-FOUNDATION-001`
**Phase:** `A2_BACKEND_FOUNDATION` — TEMPORARY EXECUTION CONTRACT
**Date:** 2026-10-06 (CST)
**Status:** READY · **A2 itself: NOT EXECUTED**
**Scope of this task:** contract creation + targeted discovery only. No A2 implementation, no A3, no A4, no device work, no cloud provisioning.

## 1. Phase state

| Phase | State |
|---|---|
| A0 | READY |
| A1 | PASS |
| A2 | READY_FOR_SEPARATE_CONTRACT → **this package authorizes it** |
| A3 | BLOCKED_BY_HUMAN_DECISIONS (D-01, D-04, D-10) |
| A4 | NOT_STARTED |

A0 and A1 are not reopened. A3 blockers are not solved here.

## 2. Human decisions in force

| Decision | Value |
|---|---|
| D-07 | `KOTLIN` + `KTOR` |
| D-08 | `TENCENT_CLOUD` + `PORTABLE_DOCKER` |
| D-09 | `POSTGRESQL` |
| D-15 | `YES_BOUNDED_ACCOUNT_NETWORK_UNLOCK` (phase-gated) |

KeepLab Android stays `LOCAL_FIRST`: Room is the local SSOT, account and network remain optional
for local use, Google/Firebase identity stays forbidden.

## 3. Project data stage

`EXPERIMENTAL` — for local data **and** backend data. No production users, no production backend
data. Therefore `CLEAN_FOUNDATION > BACKWARD_COMPATIBILITY`: no production migration/rollback
complexity is authored, the backend database may be recreated during development, and no
compatibility shim is kept for disposable backend rows.

## 4. Targeted discovery result

Only the KeepLab-Relay repository root, the named Gradle files, the wrapper, `.gitignore`, the
(absent) backend directory and the three named architecture reports were inspected. No Android UI,
no feature source, no Testapp, no PowerAi, no Google Keep reference material.

| Item | Finding |
|---|---|
| `KeepLab-Relay/backend/` | **ABSENT** — never existed; no `A2_BACKEND_PATH_CONFLICT` |
| `KeepLab-Relay/server/`, `infra/` | absent |
| `settings.gradle.kts` | `rootProject.name = "KeepLab"`, `include(":app")`, `include(":benchmark")` — Android-only, `FAIL_ON_PROJECT_REPOS`, AGP plugin resolution |
| `build.gradle.kts` (root) | comment-only |
| `gradle/libs.versions.toml` | Android-scoped catalog (Kotlin 2.3.21, AGP 9.2.1, Room 2.8.4) — **not** a backend version source |
| wrapper | `gradlew` present, Gradle **9.5.1** (`gradle-9.5.1-bin.zip`) |
| `.gitignore` | already ignores `.env` / `.env.*` with `!.env.example`, plus `build/`, `.gradle/`, `local.properties` |
| JDK | OpenJDK **21.0.12.1** available |
| Docker | **not installed** → `DOCKER_RUNTIME_SMOKE = SKIPPED_TOOL_UNAVAILABLE` |
| `psql` | not installed |
| git baseline | **no commits** → `git diff` unusable; verification is sha256-based |
| architecture reports | present under the Stack repo `reports/` (`ARCHITECTURE-SPEC`, `IMPLEMENTATION-ROADMAP`, `DATA-MODEL`) |

**Conclusion:** an independent backend Gradle project is viable and **no repository-root Gradle
change is required** (`ROOT_ANDROID_GRADLE_MODIFIED = NO`).

## 5. Backend target

```
/mnt/AndroidDev/Projects/KeepLab-Relay/backend/     INDEPENDENT_GRADLE_PROJECT
  settings.gradle.kts · build.gradle.kts · (optional) gradle.properties
  src/main/kotlin/<pkg>/{Application.kt, config/, db/, routes/}
  src/main/resources/{application.conf, db/migration/}
  src/test/kotlin/<pkg>/
  Dockerfile · docker-compose.yml · .env.example · .dockerignore
```

Invocation: `cd /mnt/AndroidDev/Projects/KeepLab-Relay && ./gradlew -p backend <tasks>`
(the existing wrapper is reused; a second wrapper is a STOP).

## 6. What A2 builds

- Ktor (Netty) application entry point; JSON serialization; structured configuration; centralized error handling.
- `GET /health` — no authentication, server-alive, **does not touch the database**.
- `GET /ready` — readiness incl. database reachability through a **small injectable abstraction** (success/failure both deterministic).
- PostgreSQL connectivity: **HikariCP + PostgreSQL JDBC driver**, pool init / `SELECT 1` probe / clean close. **No ORM.**
- Migration foundation: **Flyway**, exactly one foundation-only migration (`CREATE SCHEMA IF NOT EXISTS keeplab;`).
- Configuration from `KEEPLAB_HTTP_PORT`, `KEEPLAB_DB_URL`, `KEEPLAB_DB_USER`, `KEEPLAB_DB_PASSWORD`; `.env.example` placeholders only; **no `.env`**.
- Portable Docker dev setup: multi-stage `Dockerfile` + `docker-compose.yml` (PostgreSQL service with a **named volume** + backend service). Nothing is deployed or provisioned.

## 7. What A2 must not do

login · registration · passwords · passkeys · tokens · sessions · JWT/OAuth · Credential Manager ·
Google/Firebase Auth · notes API · sync API · outbox · delta cursor · conflict resolution ·
revision protocol · attachments · collaboration · business tables · Tencent Cloud provisioning ·
Android product changes · device work.

D-01, D-04 and D-10 are **not** decided or pre-empted here.

## 8. Write surface

| Path | Decision |
|---|---|
| `KeepLab-Relay/backend/` | ALLOW (whole new-directory surface) |
| `Google-Android-Agent-Development-Stack/reports/` | ALLOW |
| `.../orchestration/hermes/evidence/keeplab-a2-backend-foundation/` | ALLOW |
| `KeepLab-Relay/app/**`, all Android Gradle files, `gradle/`, `gradlew`, `local.properties` | BLOCK |
| `KeepLab-Relay/{Dockerfile,docker-compose.yml,docker/,server/,infra/,cloud/,firebase/}` | BLOCK |
| `KeepLab-Relay/{specs,verification,harness,docs,factory,MISSION.md,…}` | BLOCK |
| `Testapp/`, `PowerAi/`, `KeepLab-Relay-evidence/` | BLOCK |
| `.../evaluation_adapter/contract_guard.py`, `.../HERMES-LOCK.json`, `.hermes.md` | BLOCK |
| `reports/contracts/` (this package and every earlier package) | BLOCK |

## 9. Verification gate (A2)

```
cd /mnt/AndroidDev/Projects/KeepLab-Relay
./gradlew -p backend test build            # mandatory, run ONCE
docker compose -f backend/docker-compose.yml config   # optional, once, if available
```

Loop: **PLAN ONCE → EXECUTE → VERIFY ONCE → PASS = STOP.** FAIL → fix the failed path only,
re-run only the failed task. Two surviving fixes → `REPEATED_FAILURE` + one root-cause analysis.
No post-PASS review, no second audit, no full repository scan.

## 10. Validation of this package (one pass, done)

| Check | Result |
|---|---|
| manifest integrity (`guard.load_contract`) | `MANIFEST_OK` |
| frozen inputs re-hashed | 10/10 byte-identical |
| backend path state | ABSENT (no conflict) |
| write decision table | 17/17 ALLOW + 30/30 BLOCK as required |
| terminal decision cases | 11/11 as required |
| hook-level activation (`main()`) | 6/6 (exit 0 allow / exit 2 block) |
| Android app + backend prefix boundaries | PASS |
| **CONTRACT VALIDATION** | **PASS** |

Evidence: `orchestration/hermes/evidence/keeplab-a2-backend-foundation/guard-simulation.json`
and `…/before-hash.json`. Same unmodified guard (`p0b-close-1`,
sha256 `e418fc28b08ac7afe4fdd42ec44d572ddaa2f23f6200de300ecac211404b3746`), same fail-closed
`pre_tool_call` hook, activated by `HERMES_CONTRACT_PACKAGE` only.

## 11. Next

`KEEPLAB-A2-BACKEND-FOUNDATION-EXECUTE` (separate, explicitly-authorized task).
On A2 PASS: stop. A3 remains `BLOCKED_BY_HUMAN_DECISIONS`.
