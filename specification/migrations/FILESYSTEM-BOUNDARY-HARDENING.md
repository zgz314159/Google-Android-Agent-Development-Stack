# Filesystem Boundary Hardening and Portable Host Recovery

## Mission

Repair the filesystem layout of `Google-Android-Agent-Development-Stack` so that copying the project directory to another Ubuntu host preserves the complete authored project, while generated state, test output, caches, logs, screenshots, APKs, browser profiles, credentials, and other mutable artifacts are written outside `/home/zhong/Projects`.

This is a filesystem-boundary and portability task. It is not authorization to execute a campaign, send a ChatGPT message, advance a bridge sequence, implement Phase 4.6 transport, or modify KeepLab-Relay.

## Non-negotiable model

The project root contains reproducible, reviewable project material:

- source code and scripts;
- test source, fixtures, schemas, and acceptance rules;
- authored specifications and durable design documents;
- configuration templates without secrets;
- dependency locks, checksums, patches, and bootstrap/import/export tools.

The project root must not receive generated or host-specific material:

- live runtime state, PID/socket/lock files, bridge/supervisor state, or telemetry;
- test and benchmark results, evidence bundles, generated reports, screenshots, recordings, logs, or APK outputs;
- Gradle/Python/Node/browser caches, virtual environments, build directories, `__pycache__`, or `.pytest_cache`;
- credentials, provider secrets, cookies, browser profiles, or other private host configuration.

Do not misclassify test source as temporary output. Tests and fixtures belong in the project; the output produced when tests run does not.

## Required directory contract

Implement one central path contract with environment-variable overrides and no hard-coded username. Defaults must follow XDG conventions:

```text
PROJECT_ROOT = discovered from the checked-out source tree
STACK_STATE_ROOT = ${ANDROID_AGENT_STACK_STATE_ROOT:-${XDG_STATE_HOME:-$HOME/.local/state}/google-android-agent-stack}
STACK_DATA_ROOT = ${ANDROID_AGENT_STACK_DATA_ROOT:-${XDG_DATA_HOME:-$HOME/.local/share}/google-android-agent-stack}
STACK_CACHE_ROOT = ${ANDROID_AGENT_STACK_CACHE_ROOT:-${XDG_CACHE_HOME:-$HOME/.cache}/google-android-agent-stack}
STACK_CONFIG_ROOT = ${ANDROID_AGENT_STACK_CONFIG_ROOT:-${XDG_CONFIG_HOME:-$HOME/.config}/google-android-agent-stack}
HERMES_HOME = ${HERMES_HOME:-$HOME/.hermes}
```

Use these roots consistently:

- `STACK_STATE_ROOT`: bridge/supervisor/browser automation state, live telemetry, locks, PIDs, sockets, and resumable host state;
- `STACK_DATA_ROOT/artifacts`: evidence, evaluation sessions, benchmark results, screenshots, APKs, and generated reports;
- `STACK_CACHE_ROOT`: disposable downloads, build caches, temporary baselines, and reconstructed third-party reference checkouts when appropriate;
- `STACK_CONFIG_ROOT`: non-secret host configuration; secrets may remain under `HERMES_HOME` with restrictive permissions;
- `HERMES_HOME`: installed Hermes runtime, profiles, tools, provider state, and secret material. This is not automatically project source.

Create a small shared path implementation usable by Python and shell callers. Prefer a checked-in declarative configuration or one canonical implementation plus a shell query command over duplicated constants.

## Hermes source-integrity decision

The project currently locks Hermes at commit `af90026...` and installs it under `/home/zhong/.hermes/hermes-agent`. Determine which of these two cases is true and record evidence:

1. **Clean pinned third-party runtime**: the checkout matches the complete commit in `orchestration/hermes/HERMES-LOCK.json`, with no project-specific tracked modifications. It may stay under `HERMES_HOME`; the project must be able to recreate it from its lock and bootstrap script.
2. **Project-owned Hermes changes**: any project-specific tracked/untracked code exists only under `HERMES_HOME`. Preserve it immediately as reviewed source, a patch series, or a vendored component inside the project. No unique implementation may exist only in a hidden user directory.

Do not copy credentials, tokens, cookies, caches, provider history, or virtual environments into the project. Do not print secret values in logs or reports.

## Current known violations to audit

At minimum inspect and classify the following. The approximate sizes are only discovery hints and must be recalculated:

- `orchestration/hermes/evidence` (about 34 MB);
- `orchestration/hermes/runtime` (about 2.1 MB);
- `verification/.state`;
- `verification-benchmark/results` (about 23 MB);
- generated JSON/log data under `verification-benchmark/reports`;
- probe `.gradle`, `build`, and `local.properties` files;
- all `__pycache__`, `.pytest_cache`, build, virtual-environment, and cache directories;
- `/home/zhong/Projects/_evaluation` (about 36 MB), which is not a project and must not remain a runtime-output root;
- mixed authored and generated content under `reports`;
- project-specific hard-coded `/home/zhong/...` and obsolete `/mnt/AndroidDev/...` paths;
- `references` (about 510 MB), which must be classified separately as authored vendored input, pinned third-party source, or reconstructible cache. Do not move it blindly.

Search live writers, not only existing files. Include at least:

- `evaluation/commandcode/finalize_session.py`;
- `verification/integration/autofinalizer/install.sh` and installed hooks;
- Hermes bridge, supervisor, telemetry, guard-audit, and evidence writers;
- verification and verification-benchmark harnesses;
- Android probe build configuration;
- tests whose expected paths encode the old layout.

## Implementation requirements

1. Produce a machine-readable inventory that assigns every relevant path one class: `SOURCE`, `TEST_SOURCE`, `AUTHORED_DOC`, `THIRD_PARTY_INPUT`, `MUTABLE_STATE`, `PERSISTENT_ARTIFACT`, `CACHE`, or `SECRET_CONFIG`.
2. Add the central XDG path contract and migrate every active writer to it. Preserve explicit CLI and environment overrides where they already exist.
3. Replace `/home/zhong/Projects/_evaluation` as the default evaluation destination with `STACK_DATA_ROOT/artifacts/evaluation`.
4. Keep unit/integration test code and stable fixtures in the project. Make test runs use temporary directories or external artifact roots.
5. Add a root `.gitignore` covering generated classes without ignoring authored source, locks, manifests, or fixtures. The absence of an initialized `.git` directory does not remove this requirement.
6. Add or repair these reproducible host tools under the project:
   - `scripts/bootstrap-host.sh`: install/verify the exact locked Hermes revision, create provider/profile templates, and prepare the Playwright environment without downloading Chromium unless explicitly requested;
   - `scripts/export-host-state.sh`: create a checksummed migration archive outside the project, excluding secrets by default and clearly listing any optional secret export mode;
   - `scripts/import-host-state.sh`: verify checksums, reject path traversal, preserve safe permissions, and restore state without advancing a campaign;
   - `scripts/verify-layout.sh`: fail when known generated outputs or absolute host paths reappear inside the project;
   - optionally `scripts/build-portable-bundle.sh`: package authored project material, dependency manifests, and bootstrap tools, not caches or ordinary generated artifacts.
7. Update documentation to distinguish copying the project from migrating private host state. A source copy must be sufficient to rebuild the runtime; resuming a live campaign additionally requires an explicit state export/import.
8. Add tests for path resolution, environment overrides, archive safety, layout enforcement, and bootstrap dry-run behavior.
9. Keep the prior Gradle requirement: first-time Gradle downloads must use an accessible China-mainland mirror with checksum verification and a documented official fallback.

## Existing artifacts: safe migration policy

Do not delete, rename, or destructively move existing evidence during the first pass.

First:

1. calculate file counts, byte sizes, and SHA-256 manifests;
2. identify references to each old path;
3. copy or archive eligible generated data to `STACK_DATA_ROOT/artifacts/migration-archive/<timestamp>/`;
4. verify the destination manifest byte-for-byte;
5. emit a proposed cleanup plan listing every original path.

Leave originals in place until a human approves cleanup. Future writes, however, must immediately use the new external roots.

## Verification gates

Run all applicable offline tests after the migration. The result is not complete unless all of the following are demonstrated:

- bridge and supervisor suites still pass;
- evaluation, verification, benchmark, and path-contract tests pass;
- `scripts/verify-layout.sh` passes on a clean generated-output-free copy;
- a bootstrap dry run resolves the pinned Hermes revision without modifying a campaign;
- an export/import round trip succeeds in temporary directories with matching checksums;
- a test run produces outputs only under temporary/XDG roots;
- secret scans show that no secret was copied into the project or report;
- no ChatGPT message was sent and no bridge/campaign sequence changed.

## Deliverables

Checked into the project:

- path-contract implementation and tests;
- `.gitignore`;
- bootstrap/export/import/layout-verification scripts;
- dependency locks and any required project-owned Hermes patch source;
- concise durable documentation.

Written outside the project under `STACK_DATA_ROOT/artifacts/filesystem-hardening/<timestamp>/`:

- full audit inventory in JSON;
- checksum manifests;
- test logs and generated reports;
- proposed cleanup/move plan;
- final machine-readable result.

End the terminal response with this exact compact report structure:

```text
FILESYSTEM_BOUNDARY_RESULT
verdict: PASS | PARTIAL | FAIL
project_root: <path>
state_root: <path>
data_root: <path>
cache_root: <path>
config_root: <path>
hermes_source_class: CLEAN_PINNED_RUNTIME | PROJECT_CHANGES_PRESERVED | UNRESOLVED
live_writers_migrated: <count>
layout_violations_remaining: <count>
tests: <summary>
campaign_state_changed: NO
chatgpt_message_sent: NO
cleanup_performed: NO
external_report: <absolute path>
next_human_action: <one sentence>
```
