# DEVICE-EXECUTION-POLICY

Frozen. Governs every interaction with the physical reference device **`87296ada`**
(Redmi Note 7 Pro, API 36). Motivation: P0A spent **78.5%** of agent-owned wall
(12180.8 s of 15511.9 s) in a per-step `tap → sleep → screencap → LLM inspect` loop
(226 model requests in T7). This policy removes that loop from the normal path.

## Execution modes

| Mode | Name | When |
|---|---|---|
| **MODE 1** | **DETERMINISTIC** (default) | The journey/flow is known and frozen. Selector-driven executor only. **0 LLM calls per step, 0 vision.** |
| MODE 2 | EXPLORATION | Unknown UI, first-time flow creation, or a flow that has become invalid. Agent exploration allowed. |
| MODE 3 | EXCEPTION | A deterministic (MODE 1) run FAILED. The agent inspects the produced evidence once, minimally fixes, and re-runs only the failed flow. **Added in S1.1: the runner stops at the first deterministic failure (fail-fast) instead of continuing the batch.** |

A normal task is MODE 1.

## Executors (reuse, never rewrite)

- Apps **we own source for** (KeepLab): **UiAutomator 2.4** is the production default.
- **External reference apps** (Google Keep): **Maestro** (selector-driven, auto-wait,
  screenshot, physical device). See `verification/reference-replay/`.

Do **not** build a new automation engine, OCR clicker, AI coordinate agent, or vision
navigation framework.

## Direct ADB UI input (forbidden on the normal path)

Forbidden as UI automation:

- `adb shell input tap`
- `adb shell input swipe`
- `adb shell input text`

Allowed adb (device lifecycle / non-UI):

- `install`, explicit `uninstall`, `am start`, `force-stop`, `logcat`, `settings`, `wm`,
  package inspection, authorized database extraction, device metadata, lifecycle,
  `adb reverse`.

If a coordinate tap is ever unavoidable it must be an explicitly documented exception
(why no selector is possible) and is audited by the static policy test.

## No sleep-driven UI loop

Forbidden normal flow: `tap → sleep 2 → screenshot → tap → sleep 2 → screenshot`.
Use Maestro automatic settle / `assertVisible` / `extendedWaitUntil`, or UiAutomator
`device.wait(Until…, timeout)`. A fixed sleep is allowed only for a documented non-UI
external dependency.

## Failure policy (fail-fast) — added in S1.1

The official verification gate is **FAIL-FAST**. This section is normative for the
reference-replay runner (`verification/reference-replay/runner/replay.py`).

Normal PASS path:

```
Hermes -> ONE deterministic runner invocation -> compact result (index.json)
```

First deterministic failure:

```
FIRST FAIL
  -> the runner STOPS immediately (no further R1-2/R1-3/R2/R3 runs)
  -> failure evidence is still flushed: runs/<FLOW>-<n>/result.json,
     runs/<FLOW>-<n>/evidence/ (logcat slice, dumpsys activity, metadata.json),
     and <out>/index.json (with stopped_early/stop_reason/first_failure)
  -> the runner exits NON-ZERO (5)
  -> Hermes Exception Handler reads the failed step, Maestro output, hierarchy,
     screenshot and logcat — once
  -> minimal fix
  -> re-run ONLY the failed FLOW
```

Retry semantics (a fixed flow invalidates its old PASS):

- R1 fails -> fix R1 -> re-run **R1 x 3** (the old R1 PASS cannot be mixed with the
  changed flow). Only after R1 is 3/3 again does the batch continue to R2.
- R2 fails -> fix R2 -> re-run **R2 x 3** only. Never re-run a frozen-PASS R1.
- Same for R3.

Diagnostic escape hatch: `--continue-on-fail` runs the whole planned batch after a
failure. It exists ONLY to collect a failure distribution; it is **not** the
official gate and must never be used to declare a device PASS.

Forbidden in the exception path: the `screenshot -> LLM -> tap -> screenshot` loop.
AI vision is allowed on FAIL evidence inspection, never as per-step navigation.

## Escalation ladder (vision last)

- **LEVEL 0** selector / semantics / accessibility
- **LEVEL 1** deterministic screenshot hash / visual assertion (only if explicitly required)
- **LEVEL 2** layout dump / hierarchy evidence
- **LEVEL 3** AI vision

Normal PASS stops at LEVEL 0/1. AI vision is **FAIL/exploration only**.
`assertWithAI` must never appear in the default PASS path.

## Explore → Freeze → Replay

1. Unknown UI: agent explores (MODE 2).
2. A successful journey is converted to a Maestro flow or UiAutomator journey.
3. The flow is **frozen** (recorded with `workflow_id`, version, target app, reference
   version, selectors, assertions, evidence, `last_validated`).
4. Thereafter it is **replayed** (MODE 1). The same target is never re-explored free-form.

## Resource lock

Any deterministic device run must first acquire `device:<serial>`
(`verification/core/device_lock.sh`, flock, capacity 1). A second runner fails/wait clearly
with `DEVICE_BUSY`. No two agents may touch the device at once.
