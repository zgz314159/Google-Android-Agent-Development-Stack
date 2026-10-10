# Integration Guide — adding a project to the Verification Layer

Goal: a project supplies a journey, fixture, oracle, selectors and package metadata. The
project never copies the harness.

## Step 0 — Bootstrap the generic layer support (v1.0.1)

```bash
python3 verification/integration/android-project/bootstrap_project.py --project /path/to/android-project
```

This installs the pinned, generic device-side support sources (`TimingLogger`, `JourneyBase`,
`UiDriver`, `FailureBundleRule`) into the project's `androidTest` source set and ensures the
UiAutomator test dependency, then writes `.verification/integration-manifest.json`. It is
idempotent (a second run is `NO-OP`), never overwrites a project-edited file (it reports
`INTEGRATION_DRIFT` and leaves it alone), and never duplicates the dependency. It does **not**
generate project semantics — the fixture, journey, oracle, selectors and acceptance are
project-owned (Steps 1–4).

## Step 1 — Add stable selectors

Give every key interaction node a stable identity per
`docs/VERIFICATION-SELECTOR-CONTRACT.md` (prefer `testTag`/resource id, then
`contentDescription`). This ships with the feature, in the same change.

## Step 2 — Define a fixture

A deterministic setup that writes the app's real state **without UI taps** (direct DB/API).
Run by the host before the journey as a separate `am instrument`; its wall time is setup,
never mixed into T7.

```kotlin
@RunWith(AndroidJUnit4::class)
class FixtureSeeder {
    @Test fun seedLogin() { /* reset + seed deterministically */ }
}
```

## Step 3 — Define a journey

Subclass `JourneyBase` (from `android/uiautomator/`), drive the UI inside `action {}` blocks,
assert inside `observe {}` blocks, and finish with the terminal oracle.

```kotlin
class LoginJourneyTest : JourneyBase() {
    private val ui = UiDriver(appPackage)
    @get:Rule val failureBundle = FailureBundleRule { Verifier.verify(ctx, VerificationEnv.journey()) }

    @Test fun login() {
        TimingLogger.begin(ctx, VerificationEnv.runId(), VerificationEnv.journey())
        action("launch") { ui.launchApp(device, ctx, By.text("Sign in")) }
        action("submit") { /* ... */ }
        assertEquals("PASS", verify().getString("outcome"))
        TimingLogger.runEnd()
    }
    override fun verify() = Verifier.write(ctx, VerificationEnv.journey())
}
```

## Step 4 — Define an oracle

A terminal, DB/domain ground-truth decision (never "the UI looked right"). It writes
`verify-part.json` into the app's external files `bench/` dir. For engines that cannot read
the DB themselves (Maestro), expose a separate class (e.g. `DbProbe`) and declare it as
`oracle.class`.

## Step 5 — Create `verification-plan.json`

Validate against `contracts/verification-plan.schema.json`. At minimum: `verification_id`,
`project`, `android` (package + APK paths + expected app sha), `engine`, `journey`. Add
`fixture`, `oracle`, `input_smoke`, `timeouts`, `evidence_policy` as needed.

```bash
python3 verification/core/plan_validate.py myapp/verification-plan.json
```

## Step 6 — Run the Verification Layer

```bash
verification/runner/run_verification.sh myapp/verification-plan.json
```

- PASS → compact `verification-result.json`, exit `0`.
- FAIL → `failure/` bundle + completeness validation, exit non-zero.
- To hand off to the Evaluation Layer:
  `python3 verification/adapters/evaluation/verification_adapter.py --result <result> --output <handoff>.json`.

## Step 7 — Never mask the execution exit code (v1.0.1)

A build/test/verification command must not end in `| tail`: the pipeline's status becomes
`tail`'s `0`, and a real failure disappears — from CI and from the Evaluation layer. Use:

```bash
set -o pipefail
./gradlew :app:testDebugUnitTest 2>&1 | tail -40
```

```bash
verification/core/run_capture.sh build.log ./gradlew :app:testDebugUnitTest
```

`run_capture.sh` runs the command, writes the full output to the log, prints the tail
separately, and exits with the command's **real** status.

## Evidence requirement (fail-closed)

A `uiautomator` journey (or any plan declaring an `oracle`) must produce
`bench/verify-part.json`. If it is missing, malformed, has `database.checked != true`, its
oracle outcome is not `PASS`, or `database.outcome != PASS`, the layer emits `outcome=FAIL`
with a `failure.marker` (`REQUIRED_VERIFICATION_EVIDENCE_MISSING` /
`VERIFICATION_EVIDENCE_SCHEMA_INVALID` / `VERIFICATION_ORACLE_FAIL`) and a complete failure
bundle. Absence of evidence is never PASS. Override with `"require_verify_part": false` only
for a journey with no DB/domain ground truth. `JourneyBase.verify()` must be overridden; its
un-overridden default verdict is FAIL.

## Checklist

- [ ] bootstrap run (`bootstrap_project.py`) is `INSTALL`/`NO-OP`
- [ ] key nodes have stable identities
- [ ] fixture is deterministic and UI-free
- [ ] journey asserts inside `observe {}` / oracle
- [ ] journey overrides `verify()` (never relies on the FAIL default)
- [ ] oracle asserts real state, not pixels
- [ ] instrumentation never force-stops the app
- [ ] plan validates
- [ ] no build/test command ends in `| tail` (use `set -o pipefail` or `run_capture.sh`)
- [ ] `--dry-run` passes offline before the first device run
