# Reference Replay

A thumbs-thin, deterministic **external-app replay** layer that reuses the existing
Verification Layer (it is **not** a second verification engine).

Purpose: replay a small, frozen set of **non-destructive** journeys against a
third-party reference app (Google Keep) on a physical device with **zero per-step LLM
calls**. It exists to replace the P0A anti-pattern:

```
LLM -> adb tap -> screenshot -> LLM inspect -> decision -> adb tap -> ...
```

with a single deterministic command:

```
runner -> Maestro flow -> device -> compact result
```

## Non-goals

- Not a product implementation, not P0B/P1, not KeepLab app code.
- Not a new automation engine: Maestro is the executor; UiAutomator remains the
  production default for apps we own. The Layer's `runner/orchestrator.py` is untouched.
- Not a general computer-use / vision-navigation framework. No OCR, no coordinate agent.

## Layout

```
flows/       Maestro YAML flows (R1/R2/R3) + flows.json manifest
runner/      run_reference_replay.sh (entry) + replay.py (engine, stdlib only)
contracts/   replay-result.schema.json (compact per-run result)
tests/       static policy tests + offline harness tests + device-lock test
```

## Policy (frozen)

- **Selector first.** Text / id / semantics selectors only. No coordinate taps.
- **No direct ADB UI input** in the replay path (`adb shell input tap|swipe|text`).
- **No `assertWithAI`** and no vision in the PASS path.
- **No sleep-driven polling.** Maestro `extendedWaitUntil` / automatic settle only.
- **Vision last.** AI/vision is allowed only for exploration or FAIL evidence.
- **One device, capacity 1.** Every run acquires `device:<serial>` via
  `verification/core/device_lock.sh` (flock). A second concurrent run fails closed
  with `DEVICE_BUSY`.
- **Explore -> Freeze -> Replay.** A new/unknown UI is explored once by an agent, then
  converted to a frozen Maestro flow and replayed. The same target is never re-explored
  free-form a second time.

## Usage

```bash
# all flows, 3 runs each, on the reference device
verification/reference-replay/runner/run_reference_replay.sh --flows R1,R2,R3 --runs 3 --serial 87296ada

# one flow
verification/reference-replay/runner/run_reference_replay.sh --flows R1 --runs 1
```

Each run emits one compact JSON result (see `contracts/replay-result.schema.json`) and
appends to `<out>/index.json`. Exit code is non-zero if any run is not `PASS`.

### Fail-fast (default, S1.1)

The official gate is fail-fast: the **first non-`PASS` run stops the batch**. Evidence is
still flushed (`result.json` + `runs/<FLOW>-<n>/evidence/` for the failed run, plus
`index.json`), and the runner exits non-zero (5). `index.json` carries additive batch
metadata — `planned_runs`, `executed_runs`, `stopped_early`, `stop_reason`, `first_failure`
— which older consumers can ignore.

```bash
# diagnostic ONLY: run the whole planned batch after a failure (never the official gate)
verification/reference-replay/runner/run_reference_replay.sh --flows R1,R2,R3 --runs 3 --continue-on-fail
```

Retry semantics after a failure: fix the failed flow, then re-run **that flow only**
(R1 fails → fix R1 → re-run R1 × 3). A frozen-PASS flow is never re-run. See
`orchestration/hermes/DEVICE-EXECUTION-POLICY.md`.

### Screenshot reporting

Real Maestro nests captures as
`<out>/runs/<FLOW>-<n>/maestro/<timestamp>/<FLOWNAME>/takeScreenshot/<name>.png`.
The runner discovers that layout recursively (a flat `maestro/takeScreenshot/*.png` layout
is still accepted), records the lexicographically-last capture in
`result.json.screenshot_path`, and stores its real SHA-256 in `result.json.screenshot_sha256`.
When no capture exists both fields stay `null` — a path is never fabricated.

## Device availability

If the target serial is not attached (`adb get-state != device`), every run is emitted
as `result = BLOCKED` with `failure.reason = DEVICE_UNAVAILABLE` and the runner exits
non-zero. It never fabricates a PASS.

## Status

Flows are authored against selectors that MUST be validated on the physical device
before being treated as frozen (see the Explore -> Freeze -> Replay policy). Until a
device is attached and the flows pass, they are marked `UNVERIFIED_ON_DEVICE`.
