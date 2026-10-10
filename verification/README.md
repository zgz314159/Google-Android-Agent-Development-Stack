# Verification Layer — v1.0.1

A reusable, deterministic, project-agnostic verification layer for Android projects. It turns
a **Story / Acceptance Criteria** into a machine-readable **Verification Plan**, drives the
real app on a physical device with a deterministic UiAutomator executor, and emits a
**compact record on PASS** or a **complete evidence bundle on FAIL** — with a standardized
handoff to the Evaluation Layer.

```
Story / Acceptance Criteria
   -> Verification Plan / Journey Spec
   -> Verification Layer
   -> Android physical device
   -> Deterministic verification
   -> PASS -> compact record   |   FAIL -> evidence bundle
   -> Evaluation Layer   (automatic finalization / metrics)
```

## Contents

```
contracts/   machine-readable schemas (plan, result, failure-bundle, run-state)
core/        project-agnostic python + shell utilities (incl. run_capture.sh)
android/     Android adapter (preflight, lifecycle, IME, install, cleanup, evidence)
             + device-side uiautomator support sources
runner/      run_verification.sh + orchestrator.py
adapters/    evaluation/ verification_adapter.py (handoff to Evaluation Core)
challengers/ maestro/ (reference only)
integration/ android-project/bootstrap_project.py (pinned project bootstrap)
             + autofinalizer/ (systemd --user units + installer)
examples/    keeplab/ (reference / fixture)
tests/       unit / fixtures / smoke
docs/        ARCHITECTURE, contracts, INTEGRATION-GUIDE
```

## What is the Verification Layer?

It is the **host-side** half of a deterministic verification system: preflight, APK
provenance, device lifecycle, deterministic IME, install, executor lifecycle,
timeout/watchdog, fail-fast, evidence capture, result schema, cleanup, and evaluation
handoff. It is one thing you reuse across projects; it is not a per-project set of scripts.

## Why UiAutomator?

`UiAutomator 2.4.0` is the production default because it is deterministic, drives the real
accessibility tree (no Espresso/InputManager dependency), and supports batched
failure-only verification with zero model calls on the PASS path. It is the engine proven
stable across the frozen 27-run benchmark. Compose UI Test is blocked on the observed
Android 16 / API 36 environment (see below).

## What belongs to the project vs the layer?

| Project supplies | The layer owns |
|---|---|
| Journey (UI actions + assertions) | Preflight |
| Fixture (deterministic DB setup) | Install / device lifecycle / IME |
| Oracle (DB/domain ground truth) | Executor lifecycle |
| Selectors (stable automation identity) | Timeout / watchdog / fail-fast |
| Package metadata + APK paths | Evidence / provenance / result schema / cleanup / evaluation handoff |

The project plugin is a normal `androidTest` APK. The layer addresses its classes **by name**
through the plan — the project never copies the harness.

## How to define a verification plan?

Create a `verification-plan.json` validated by `contracts/verification-plan.schema.json`.
Minimal shape:

```json
{
  "verification_id": "MYAPP-LOGIN-J1",
  "project": "MyApp",
  "android": {
    "package_name": "com.example.myapp",
    "apk": "/abs/app-debug.apk",
    "test_apk": "/abs/app-debug-androidTest.apk",
    "expected_app_sha256": "<64-hex>"
  },
  "engine": "uiautomator",
  "journey": { "id": "J1", "test_class": "com.example.myapp.verify.LoginJourneyTest" },
  "fixture": { "class": "com.example.myapp.verify.FixtureSeeder", "method": "seedLogin" },
  "input_smoke": { "class": "com.example.myapp.verify.InputSmokeTest" },
  "evidence_policy": "failure-only"
}
```

See `docs/INTEGRATION-GUIDE.md` for the full six-step onboarding.

## How to run?

```bash
verification/runner/run_verification.sh <verification-plan.json>
# offline (no device):
verification/runner/run_verification.sh <verification-plan.json> --dry-run
```

## What happens on PASS?

A **compact** `verification-result.json` is written: identity + provenance (app/test APK
sha256, layer/runner version, device), measurements (`setup_wall_ms`, `total_wall_ms`,
`t7a/t7b/t7c`), and check outcomes (ui / database / process / visual). No screenshots or
logcat are kept. Exit code `0`.

## What happens on FAIL?

The run **stops at the first unexpected failure** (fail-fast), collects a **complete
evidence bundle** (`failure/`), validates it with `core/evidence_completeness.py`, and writes
a failed `verification-result.json` (with `failure.stage`/`marker`). Exit code non-zero.
A bundle never fakes formats: JSON stays `.json`; the uiautomator XML stays `layout.xml`.

## How does the Evaluation Layer receive data?

`adapters/evaluation/verification_adapter.py` normalizes `verification-result.json` into a
T7-attributable handoff document for **Evaluation Core v0.2.1**. The adapter is read-only and
add-only: it never rewrites the core, never calls a model, never touches the network. Daily
auto-finalization is provided by the `systemd --user` timer in `integration/autofinalizer/`.

## Why is Maestro a challenger?

Maestro proved valuable as a **reference/comparison** engine, but it does not expose
per-command monotonic timestamps and is a separate execution model. Keeping it under
`challengers/` guarantees it can never affect the production UiAutomator lifecycle. A
Maestro run is always a separate plan.

## Why is Compose UI Test deferred?

Observed Android 16 / API 36 Espresso/InputManager compatibility gap
(`InputManager.getInstance()` `NoSuchMethodException`). UiAutomator drives the Compose
accessibility tree successfully, so Compose UI Test is recorded as **DEFERRED** and not
retried in this version. Revisit as an independent spike if the environment changes.

## How to add a new project?

1. Add stable selectors (`testTag`/resource id, `contentDescription`) to the feature.
2. Define a deterministic fixture.
3. Define a journey (UI actions + assertions).
4. Define an oracle (DB/domain ground truth).
5. Create `verification-plan.json`.
6. Run `run_verification.sh <plan>`.

Full detail: `docs/INTEGRATION-GUIDE.md`.

## Fail-closed evidence (v1.0.1)

Absence of required evidence is **not** PASS. If a run must produce a terminal oracle
result, the layer refuses to emit PASS without it.

- A `uiautomator` journey — or any plan that declares an `oracle` — requires
  `bench/verify-part.json`. A plan may opt out with `"require_verify_part": false`.
- On PASS derivation the host gate requires all of: the file exists, it is valid JSON,
  `database.checked == true`, `oracle outcome == PASS`, and `database.outcome == PASS`.
  Anything missing ⇒ `outcome=FAIL` and `failure.marker` one of
  `REQUIRED_VERIFICATION_EVIDENCE_MISSING` / `VERIFICATION_EVIDENCE_SCHEMA_INVALID` /
  `VERIFICATION_ORACLE_FAIL`, **plus a mechanically-produced failure bundle** (no human
  inspection needed).
- `JourneyBase.verify()`'s default (un-overridden) verdict is `FAIL`, never `PASS` — a
  journey that forgets its oracle cannot pass, at either the journey or the host level.

Regression fixtures live in `tests/unit/test_fail_closed.py`.

## Project bootstrap (v1.0.1)

```bash
python3 verification/integration/android-project/bootstrap_project.py --project /path/to/android-project
```

Installs the layer's pinned, generic device-side support sources (`TimingLogger`,
`JourneyBase`, `UiDriver`, `FailureBundleRule`) into the project's `androidTest` set and
ensures the UiAutomator test dependency. It is idempotent (second run = `NO-OP`), never
overwrites a project-modified file (reports `INTEGRATION_DRIFT` instead), never duplicates
a dependency, and writes an integration manifest to `.verification/integration-manifest.json`
with the layer version, support-file hashes, destination paths and dependency change.
It does **not** generate project semantics (fixture / journey / oracle / selectors /
acceptance) — those stay with the Specification Contract and the project.

## Exit-code integrity (v1.0.1)

`cmd | tail` replaces the upstream status with `tail`'s `0` and hides build/test failures
from the Evaluation layer. The layer's own execution uses captured return codes; for
human/agent/CI shell use `core/run_capture.sh <log> <cmd...>`, which preserves the real
exit status and renders the tail separately (see `docs/INTEGRATION-GUIDE.md`).

## How to debug a failure?

1. Read `<run-dir>/failure/metadata.json` (`layout_provider`, artifact availability).
2. Read `failed-assertion.json` (in-process assertion) and `executor-output.txt`.
3. Inspect `logcat.txt`, `screenshot.png`, `layout.json`/`layout.xml`.
4. Check `run-state.json` for the exact failing `stage` and `cleanup_at`.
5. `TIMEOUT_STAGE=<stage>` pinpoints a bounded stage that hung.

`run-state.json` and the machine markers (`STAGE_FAIL`, `TIMEOUT_STAGE`, `APK_SHA_MISMATCH`,
`UIAUTOMATION_CONFLICT_SUSPECTED`, …) are the deterministic debugging trail.
