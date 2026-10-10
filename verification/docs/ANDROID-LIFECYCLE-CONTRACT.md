# Android Lifecycle Contract (v1.0.0)

## 1. Host / instrumentation separation (mandatory)

| Phase | Owner |
|---|---|
| APK install, test APK install | Host |
| force-stop (before `am instrument`) | Host |
| orientation, theme (night mode), stay-awake | Host |
| IME selection | Host |
| logcat capture / clear | Host |
| `am instrument` invocation | Host |
| artifact pull | Host |
| cleanup, provenance, timeout/watchdog | Host |
| UI actions, assertions, DB/domain oracle, journey timing | Instrumentation |

**Instrumentation never `am force-stop`s the target app.** It runs inside the app's process
and would kill itself. The host force-stops host-side first.

## 2. Deterministic preconditions (applied by the host before the journey)

- orientation: portrait, rotation locked (`accelerometer_rotation=0`, `user_rotation=0`)
- theme: light (`cmd uimode night no`)
- display: stay-awake on
- IME: engine-specific, verified as the *current* IME before every run

## 3. Device-state snapshot / restore

Before applying preconditions the host snapshots: `stay_on_while_plugged_in`,
`accelerometer_rotation`, `user_rotation`, night mode, `default_input_method`. On **every**
exit path (PASS, FAIL, timeout, interrupt) the host restores them. A restore failure is
recorded separately (`LIFECYCLE_RESTORE=PARTIAL`) and never masks the primary outcome.

## 4. IME determinism

`android/ime.sh <engine>`: verify exists → enable → set → verify current. Failure is fatal
(`IME_UNAVAILABLE` / `IME_SET_FAILED`). The previous run's IME is never assumed.

| engine | IME component |
|---|---|
| `uiautomator` | `com.google.android.inputmethod.latin/com.android.inputmethod.latin.LatinIME` |
| `maestro` | `com.android.inputmethod.latin/.LatinIME` |

## 5. Executor isolation

`android/cleanup_engine.sh <engine> [--check-only]` force-stops only known verification/tool
packages and verifies no UiAutomation holder survives
(`UIAUTOMATION_CONFLICT_SUSPECTED` + `CLEANUP_INCOMPLETE` → STOP). Engine runs never
interleave: a Maestro run is always a separate plan.

## 6. Timeout / watchdog

Every stage is bounded. On timeout the stage prints `TIMEOUT_STAGE=<stage>` and the run
records it in `run-state.json` (`stage`, `started_at`, `last_progress_at`, `cleanup_at`), so
a hang is attributable to a stage. `cleanup_at` is set without clobbering the failing stage.

## 7. Secure keyguard

A showing secure keyguard yields `DEVICE_LOCKED_REQUIRES_OWNER_UNLOCK` and stops. The layer
never attempts to bypass a PIN/pattern lock.
