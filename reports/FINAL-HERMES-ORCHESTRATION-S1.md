# FINAL — S1: Hermes Orchestration Integration

Generated: 2026-10-05 (closure) · Root: `/mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack`
Scope: Hermes orchestration kernel + native Command Code parallel benchmark + deterministic
device replay. **Read-only w.r.t. product code.** No P0B / P1 started.

This revision **closes the Physical Device Replay Gate** that was the only open item in the
previous S1 revision. Sections A–H and the previously proven PASS results are unchanged and
not re-litigated here.

---

## A. Why S1 exists

P0A (KeepLab Google Keep parity) completed, but its Evaluation Core v0.2.3 record exposed two
real problems: the agent was a **mechanical device executor** (`LLM → adb tap → screencap →
LLM inspect → …`), and it used **zero** Command Code native subagents. S1 makes the agent a
verification/exception handler and wires in the native parallel path.

## B. P0A historical bottleneck (motivation only)

`/mnt/AndroidDev/Projects/_evaluation/KeepLab-Relay/KEEPLAB-RELAY-P0A-…/run.json`

| Metric | Value |
|---|---|
| task_elapsed_wall | 15553.906 s (≈4h19m) |
| agent_owned_wall | 15511.860 s |
| T7 (Device/Verification) | 12180.796 s (**78.5%**) |
| T7c | 10651.649 s (**68.7%**) |
| total model requests | 277 (T7: 226) |
| WAIT_DEVICE | 12180.796 s |
| tools: `agent` / `agent_output` | **absent** |
| Background Jobs | **0** |

Top consumers are literal `adb … input tap … sleep … screencap` spans.

## C. Command Code native subagents — used?

**YES.** Three real built-in `agent` (explore) calls in one parent turn, `run_in_background=true`.

## D. Subagent parallel evidence

| | |
|---|---|
| parent session | `890973b0-dc3f-4445-b519-701fc8e54632` (cmdc 1.74.1) |
| started / completed | 3 / 3 |
| max concurrent | 3 |
| parallel overlap | 89.622 s (conservative) |
| subagent writes | 0 |
| raw proof | three `agent` tool_use parts in one JSONL row, identical timestamp |

## E. Hermes exact version / commit

- Upstream: `NousResearch/hermes-agent` (official), branch `main`
- Commit: `af90026aa09949579bd423d24def3d38f743cde0`
- Version: `vgit.af90026 (2026.9.24)` · latest stable tag `v2026.9.24` (v0.21.5)
- Required official fixes present: `779aecb62` (model discovery), `30d14a3f7` (429 classification)
- Frozen: `orchestration/hermes/HERMES-LOCK.json` · **no core patch**
- **This closure round: not reinstalled, not updated, not re-benchmarked.**

## F. CommandCode provider result

**PASS.** `commandcode` + `deepseek/deepseek-v4.1-flash` → response `HERMES_COMMANDCODE_OK`,
exit 0, ≈9.2 s. `hermes doctor` = PASS_WITH_DOCUMENTED_NONBLOCKING_WARNING.

## G. Hermes delegation result

**PASS.** Root `20261004_234211_d5c6af`: children 3, completed 3, max concurrent 3,
overlap 12.078 s, 0 writes. (First attempt refused by `delegation.oneshot_max_children=2`;
raised to 4 — reported honestly.)

## H. Kanban DAG result

**PASS.** Board `s1-probe`: A/B/C ready, D (`--parent A --parent B --parent C`) **todo/blocked**
→ after A/B/C `done`, D becomes **ready**.

## I. Device interaction architecture — before / after

- **Before:** `LLM → tap → sleep → screencap → LLM → tap …`, 226 T7 requests, 78.5% wall.
- **After:** one command → Maestro selector flow → device → compact result; **0 per-step LLM,
  0 vision** on the PASS path.

## J. 3 flows × 3 — DEVICE REPLAY GATE (CLOSED)

**PASS — 9/9.** Device `87296ada` attached; Google Keep present. Two runner invocations this
round:

| # | Result | Exit | Wall |
|---|---|---|---|
| 1 (pre-fix) | 0/9 PASS (9 FAIL) → **FAIL CLOSED** | 5 | 290 s |
| 2 (post-fix, official) | **9/9 PASS** (R1 3/3, R2 3/3, R3 3/3) | 0 | 241 s |

**Failure and fix (exception handling, selector-only):** all nine pre-fix runs failed at the
*same* first selector (`visible: "Search"`): the flows used **English text selectors** while
the reference-device UI locale is **`zh-Hans-CN`**, and the flows had shipped
`validated_on_device: false` (never walked on device). The fix replaced text selectors with
**locale-independent resource IDs** (already captured from the app), and hardened R1's return
step to tap the on-screen search back button (system `back` is consumed by the focused search
field). No structural change, no coordinate tap, no `assertWithAI`, no adb UI input.

Full detail: `reports/DEVICE-REPLAY-BENCHMARK.md` ·
`verification/reference-replay/.runs/S1-close/` (pre-fix FAIL, fail-closed) ·
`verification/reference-replay/.runs/S1-postfix-003958/` (post-fix PASS).

## K–M. Deterministic-path counters

model requests during device steps = **0**; visual LLM calls = **0**; direct adb UI inputs = **0**
(by design, enforced by the static policy test, and observed in all 9 post-fix results).

## N. Device lock

**PASS.** `verification/core/device_lock.sh` (`flock`, resource `device:<serial>`, capacity 1).
Lock file `.state/locks/device-87296ada.lock` held during the run (pid `176056`). Test: second
holder → `DEVICE_BUSY`; acquire-after-release → OK. The nine device runs were strictly serial.

## O. Controlled fail evidence

**PASS** (offline harness): Maestro stub with a failing assertion → `result=FAIL`,
non-zero exit, evidence bundle (`evidence/metadata.json`) written. This round additionally
produced a **real on-device fail-closed** record: 9/9 FAIL at a non-matching selector
(invocation #1) — `reports/…/.runs/S1-close/` — which supersedes the earlier "no device"
limitation.

## P. Files changed

Previously added (unchanged): as listed in the prior revision — `.hermes.md`,
`orchestration/hermes/*`, `verification/core/device_lock.sh`,
`verification/reference-replay/{README,contracts,tests,runner}`, the five `reports/*` docs,
`reports/evidence/device-replay-attempt.txt`.

**This closure round (flow/selector-only + reports):**
```
verification/reference-replay/flows/R1-search.yaml     (selectors: text -> resource-id; return step)
verification/reference-replay/flows/R2-archive.yaml    (selectors: text -> resource-id)
verification/reference-replay/flows/R3-settings.yaml   (selectors: text -> resource-id)
verification/reference-replay/flows/flows.json         (policy.validated_on_device: false -> true)
reports/DEVICE-REPLAY-BENCHMARK.md                     (rewritten: PASS 9/9)
reports/FINAL-HERMES-ORCHESTRATION-S1.md               (this file: section J + final block)
```
No runner code, contracts, or tests were modified. KeepLab `app/**` UNCHANGED.

## Q. Product code unchanged

KeepLab `app/**` UNCHANGED (`find … -newermt` → 0 files). Testapp / PowerAi not present
(unchanged). Google Keep user data untouched — flows are read-only navigation (no
`inputText`/`eraseText`; static policy PASS). P0B / P1 NOT started. Stack root is **not** a
git repo (reported, not initialized).

## R. Known limitations

- **Screenshot reporting gap (runner):** flows emit 18 PNGs across 9 runs, but
  `result.json.screenshot_path` is `null` because `runner/replay.py` globs
  `<out>/takeScreenshot/*.png` while Maestro writes `<out>/<ts>/<FLOW>/takeScreenshot/*.png`.
  Pre-existing, not fixed this round (out of scope); does not affect the 9/9 gate.
- **Flows are Keep-version-bound:** the resource IDs target the current Google Keep
  expressive-redesign UI; a future Keep UI change can invalidate them (Explore → Freeze →
  Replay). They are now locale-independent for this reference device.
- Subagent overlap is a conservative estimate (the `agent` tool exposes no structured child
  start/end); it would be `NOT_AVAILABLE` under a stricter standard.
- Evaluation Core v0.2.3 cannot yet see `agent_id`/subagent overlap; a v0.2.4 addition is
  recommended (additive, version-bumped) but was intentionally not done here.

## S. Ready for P0B?

**READY.** Hermes kernel + orchestration: READY. Device replay: **READY (9/9 PASS on
`87296ada`)**. The previously blocking "device offline + unvalidated flows" conditions are
resolved.

---

```
S1 — HERMES END-TO-END DEVICE CLOSURE
=====================================

ORCHESTRATOR:                  HERMES
PROFILE:                       android-stack
PROVIDER:                      commandcode
MODEL:                         deepseek/deepseek-v4.1-flash

DEVICE:                        87296ada
DEVICE ATTACHED:               YES
GOOGLE KEEP:                   PRESENT

FLOW R1:                       3/3 PASS
FLOW R2:                       3/3 PASS
FLOW R3:                       3/3 PASS
TOTAL:                         9/9 PASS

MODEL REQUESTS DURING DEVICE STEPS: 0
VISUAL LLM CALLS:              0
DIRECT ADB UI INPUTS:          0

DEVICE LOCK:                   PASS
FAIL-CLOSED:                   PASS (on-device, invocation #1: 0/9) 
VERIFICATION STATIC:           PASS

HERMES DEVICE STEP-BY-STEP CONTROL: NO
HERMES REINSTALLED:            NO
HERMES UPDATED:                NO
KEEPLAB PRODUCTION MODIFIED:   NO
P0B STARTED:                   NO
P1 STARTED:                    NO

DEVICE LOOP FIX:               PASS

END-TO-END
HERMES → RUNNER → MAESTRO → DEVICE:
PASS

S1 FINAL STATUS:               READY

NEXT:                          P0B

=====================================
```

### Evidence / provenance

| Field | Value |
|---|---|
| orchestrator | Hermes |
| profile | `android-stack` |
| provider | `commandcode` |
| model | `deepseek/deepseek-v4.1-flash` |
| Hermes session id | `20261005_001816_3eedd8` |
| Hermes version | `vgit.af90026 (2026.9.24)` (unchanged) |
| runner invocation count | 2 (1 pre-fix FAIL, 1 post-fix PASS) |
| runner wall time (official) | 241 s |
| runner wall time (pre-fix) | 290 s |
| model_requests_during_device_steps | 0 |
| visual_llm_calls | 0 |
| direct_adb_ui_inputs | 0 |
| post-fix run dir | `verification/reference-replay/.runs/S1-postfix-003958/` |
| pre-fix run dir | `verification/reference-replay/.runs/S1-close/` |

REPORT:
/mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack/reports/FINAL-HERMES-ORCHESTRATION-S1.md

---

## Resolved in S1.1

S1's own results above are unchanged. Three evidenced S1 limitations were closed in S1.1
(`reports/S1.1-HERMES-RUNTIME-HARDENING.md`):

1. **Screenshot reporting** — `result.json.screenshot_path` / `screenshot_sha256` were
   `null` because the runner assumed a flat `maestro/takeScreenshot/*.png` while Maestro
   nests `maestro/<timestamp>/<FLOW>/takeScreenshot/*.png`. Fixed by recursive discovery;
   verified on the real device (`verification/reference-replay/.runs/S1.1-screenshot-smoke/`,
   R1 × 1 PASS, path non-null, SHA-256 verifies).
2. **Fail-fast** — a failing run no longer continues the batch. Default is fail-fast with
   evidence + index flushed and a non-zero exit; `--continue-on-fail` is the explicit
   diagnostic opt-out.
3. **Hermes sessions in the Auto-Finalizer** — the Auto-Finalizer no longer knows only
   `~/.commandcode/projects/*/*.jsonl`: a completed Hermes ROOT session (including the S1
   session `20261005_001816_3eedd8`) is now discoverable, normalizable and finalizable
   through the same canonical path, triggered by a thin `on_session_finalize` hook.
