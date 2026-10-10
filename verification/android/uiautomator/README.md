# Verification Layer — device-side support sources

These Kotlin sources implement the interface the Verification Layer expects from a
project's `androidTest` APK. They are **reference sources**: copy the ones you need into
your project's `androidTest` source set (there is no packaged AAR yet — see the known
limitations in `docs/ARCHITECTURE.md`).

| File | Role |
|---|---|
| `TimingLogger.kt` | `VerificationEnv` + `TimingLogger` — writes `events-<runId>.jsonl` for T7 decomposition. |
| `JourneyBase.kt` | Base class for a journey test: `action{}` / `observe{}` spans + terminal `verify()` hook. |
| `UiDriver.kt` | Small UiAutomator helpers with the app package **injected** (never hardcoded). |
| `FailureBundleRule.kt` | JUnit `TestWatcher` that emits the failure bundle on assertion failure. |

## Contract (host consumes these artifacts)

Read by `core/result_emit.py`:

- `bench/events-<runId>.jsonl` — one JSON object per line:
  `{"kind","name","run_id","journey","elapsed_realtime_ns","epoch_ms"}`.
  Span kinds: `ACTION_START/END`, `ASSERT_START/END`, `EVIDENCE_START/END`, `RUN_START/END`.
- `bench/verify-part.json` — terminal oracle output:
  `{"journey","outcome","database":{"checked","checks":[{"name","expected","actual","pass"}]}}`.

Failure bundle written by `FailureBundleRule` into `bench/failure/` (the host merges it into
`<run-dir>/failure/`): `failed-assertion.json`, `screenshot.png`, `db-state.json`, `metadata.json`.

## Hard rules

- Instrumentation **never** `am force-stop`s the target app — it runs in the app's process
  and would kill itself. The host force-stops before `am instrument`.
- Do not write events or `verify-part.json` from an input-capability smoke — a smoke must
  never enter the metric.
- Prefer a stable `testTag`/resource id or `contentDescription` for every interaction node;
  see `docs/VERIFICATION-SELECTOR-CONTRACT.md`.
