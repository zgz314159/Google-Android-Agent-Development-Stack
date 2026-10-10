# Device Replay Benchmark (S1)

Generated: 2026-10-05 · Device: **`87296ada`** · App: `com.google.android.keep`
Orchestrator: **Hermes**, profile `android-stack`, provider `commandcode`, model `deepseek/deepseek-v4.1-flash`

## Verdict

**DEVICE REPLAY: PASS — 9/9** (R1 3/3, R2 3/3, R3 3/3). The device was attached; the
deterministic Maestro path ran end-to-end with **0 model requests, 0 visual LLM calls,
0 direct adb UI inputs** per device step.

| Gate | Requirement | Result |
|---|---|---|
| DEVICE ATTACHED | `87296ada` = `device` | **PASS** |
| GOOGLE KEEP | installed | **PRESENT** (`pm path` → base + 3 splits) |
| FLOW R1 | 3/3 PASS | **3/3 PASS** |
| FLOW R2 | 3/3 PASS | **3/3 PASS** |
| FLOW R3 | 3/3 PASS | **3/3 PASS** |
| TOTAL | 9/9 PASS | **9/9 PASS** |
| DEVICE LOCK | capacity 1 | **PASS** |
| MODEL REQUESTS DURING DEVICE STEPS | 0 | **0** |
| VISUAL LLM CALLS | 0 | **0** |
| DIRECT ADB UI INPUTS | 0 | **0** |
| FAIL-CLOSED | on deterministic FAIL | **TRIGGERED** (invocation #1, 0/9) then cleared after fix |
| CONTROLLED FAIL CLOSED | test | **PASS** (offline harness) |
| REFERENCE-REPLAY STATIC/SELFTESTS | PASS | **PASS** |

## Runner invocations (device runs)

| # | Command | Result | Exit | Wall |
|---|---|---|---|---|
| 1 (pre-fix) | `run_reference_replay.sh --flows R1,R2,R3 --runs 3 --serial 87296ada` | 0/9 PASS (9 FAIL) → **FAIL CLOSED** | 5 | 290 s |
| 2 (post-fix) | same command (official gate) | **9/9 PASS** | 0 | 241 s |

Pre-fix evidence: `verification/reference-replay/.runs/S1-close/`
Post-fix evidence: `verification/reference-replay/.runs/S1-postfix-003958/`

## Post-fix per-run results (`S1-postfix-003958/index.json`)

| Flow | Run | Result | Assertions | exit | wall_ms |
|---|---|---|---|---|---|
| R1 | 1 | PASS | 3/3 | 0 | 29061 |
| R1 | 2 | PASS | 3/3 | 0 | 25409 |
| R1 | 3 | PASS | 3/3 | 0 | 26608 |
| R2 | 1 | PASS | 3/3 | 0 | 27483 |
| R2 | 2 | PASS | 3/3 | 0 | 27220 |
| R2 | 3 | PASS | 3/3 | 0 | 26362 |
| R3 | 1 | PASS | 3/3 | 0 | 26840 |
| R3 | 2 | PASS | 3/3 | 0 | 26219 |
| R3 | 3 | PASS | 3/3 | 0 | 25674 |

`totals = {runs: 9, pass: 9, fail: 0, blocked: 0, visual_llm_calls: 0,
model_requests_during_device_steps: 0, direct_adb_ui_inputs: 0}`.

## What happened (this session)

1. **Preflight PASS.** `adb devices -l` → `87296ada device`; `get-state` → `device`;
   `pm path com.google.android.keep` → installed.
2. **Invocation #1 → FAIL CLOSED (0/9).** All nine runs failed at the **same first
   selector**: `extendedWaitUntil visible: "Search"` after `launchApp` (Maestro:
   `Assertion is false: "Search" is visible`). Root cause: the flows used **English text
   selectors**, but the reference device UI locale is **`zh-Hans-CN`** (home header
   `已置顶`, search hint empty, drawer items `已归档`/`设置`). The flows were shipped
   `validated_on_device: false` and had never been walked on device.
3. **Minimal flow-only fix.** Selectors replaced with **locale-independent resource IDs**
   (see table below); no flow structure, assertions count, or non-destructive intent
   changed. One return step hardened: R1's post-search return taps the on-screen search
   back button instead of system `back`, because the focused search field/IME consumes the
   first `back` and the search surface did not dismiss (confirmed from the captured
   hierarchy at `R1-HOME-SEARCH/screen-hierarchy/step-012-*.json`).
4. **Invocation #2 → 9/9 PASS** (official gate, exit 0).
5. **Static/selftests PASS** — see below.

No `assertWithAI`, no coordinate tap, no `inputText`/`eraseText`, no `sleep`, no
`adb shell input …` was introduced. All detection used selector-driven Maestro flows.

## Selector fix (text → resource ID)

| Step | Before | After |
|---|---|---|
| home ready | text `"Search"` | id `…:id/open_search_bar_text_view_container` |
| open search | text `"Search"` | id `…:id/open_search_bar_text_view_container` |
| search surface | text `"Search"` | id `…:id/search_actionbar_query_text` |
| open drawer | text/cdesc `"Open navigation drawer"` | id `…:id/menu_button` |
| archive row | text `"Archive"` | id `…:id/drawer_navigation_archive` |
| archive surface | text `"Archive"` | id `…:id/search` (Archive-only id) |
| settings row | text `"Settings"` | id `…:id/drawer_link_settings` |
| settings surface | text `"Settings"` | id `…:id/settings_scroll` |
| return from search | `back` | id `…:id/search_actionbar_back_button` |

Archive/Settings/Search "surface" anchors are IDs that exist **only** on that surface
(verified by diffing the four captured hierarchies); they are locale-independent.

## Device resource lock

- Resource `device:87296ada`, capacity 1, `flock` (`verification/core/device_lock.sh`).
- Lock file present during runs: `.state/locks/device-87296ada.lock` (holder pid `176056`).
- Test: second holder → `DEVICE_BUSY`; acquire-after-release → OK → `DEVICE_LOCK_TEST=PASS`.
- The nine runs are strictly serial inside one runner invocation; no Hermes child, no
  Command Code child, and no parallel shell worker touched adb/Maestro concurrently.

## Static / selftests (reference-replay only)

```
== static policy ==   REPLAY_POLICY=PASS
== device lock ==     DEVICE_LOCK_TEST=PASS
== offline harness == REPLAY_OFFLINE_TEST=PASS
REFERENCE_REPLAY_TESTS=PASS
```

Static policy confirms: no `adb … input tap|swipe|text`, no `assertWithAI`, no
coordinate tap without exception marker, no destructive text entry, no arbitrary sleep.

## Honesty notes

- **No "speedup %" is claimed.** These are 3 read-only journeys, not a matched A/B
  against P0A. The device-path claim with evidence is architectural: the deterministic
  path performs **0 model requests / 0 visual calls** per step.
- **The flows were edited this session** (selector-only). They are Stack-side reference
  fixtures, not product code; KeepLab `app/**` was not touched.
- **Known limitation — screenshot reporting:** the flows emit screenshots
  (`takeScreenshot: R1-home` … → 18 PNGs on disk across 9 runs, e.g.
  `.runs/S1-postfix-003958/runs/R1-1/maestro/*/R1-HOME-SEARCH/takeScreenshot/R1-home.png`),
  but the compact `result.json` records `screenshot_path = null`. Cause: `runner/replay.py`
  globs `<maestro_out>/takeScreenshot/*.png` while Maestro writes
  `<maestro_out>/<timestamp>/<FLOW-NAME>/takeScreenshot/*.png` (one level deeper). This is
  a **pre-existing runner reporting gap**, not a flow failure; the runner was intentionally
  not modified (out of this round's scope). `screenshot_sha256` is therefore also null.
- **Flows are now Keep-version-bound:** the IDs used belong to the current Google Keep
  expressive-redesign UI. A future Keep UI change can invalidate them again (Explore →
  Freeze → Replay).
