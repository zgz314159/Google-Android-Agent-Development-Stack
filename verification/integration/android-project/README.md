# Android project integration bootstrap (v1.0.1)

`bootstrap_project.py` removes the repeated "find / understand / copy / hand-edit" step for
the Verification Layer's generic device-side support when onboarding a project.

```bash
python3 verification/integration/android-project/bootstrap_project.py \
  --project /path/to/android-project [--app-module app] [--dry-run] [--json]
```

## What it installs (generic layer support only)

Into `<project>/<module>/src/androidTest/java/dev/androidstack/verification/`, copied from
`verification/android/uiautomator/`:

| File | Role |
|---|---|
| `TimingLogger.kt` | `VerificationEnv` + `TimingLogger` — `events-<runId>.jsonl` spans |
| `JourneyBase.kt` | journey base: `action{}` / `observe{}` + fail-closed `verify()` |
| `UiDriver.kt` | UiAutomator helpers, package injected |
| `FailureBundleRule.kt` | in-process failure bundle on assertion failure |

And ensures `androidTestImplementation("androidx.test.uiautomator:uiautomator:2.4.0")`.

## What it never does

It does **not** generate project semantics: `FixtureSeeder`, the journey, the DB oracle, the
selectors or the acceptance criteria stay owned by the Specification Contract + the project.

## Guarantees

| Property | How |
|---|---|
| Idempotent | first run `INSTALL`; an unchanged second run `NO-OP` (nothing rewritten) |
| Non-destructive | existing files are compared, never overwritten |
| Drift-aware | a project-edited support file is reported as `INTEGRATION_DRIFT` and left as-is |
| No duplicate dependency | an existing coordinate or version-catalog alias is detected and kept |
| Provenance | `.verification/integration-manifest.json` records layer version, per-file sha256, source/destination paths and the dependency change |

## Exit codes

`0` INSTALL/NO-OP · `3` INTEGRATION_DRIFT · `2` usage/validation error.
