# Command Code Native Subagent Benchmark (S1)

Generated: 2026-10-04 · Parent session: `890973b0-dc3f-4445-b519-701fc8e54632` · Host: Command Code `cmdc 1.74.1`

## Purpose

P0A (KeepLab Google Keep parity, 4h19m wall) used **zero** Command Code native subagents
(no `agent` / `agent_output` tool calls; Background Jobs = 0). S1 must prove the native
parallel path is actually used, and measure it honestly.

## Method

Three real built-in `agent` tool calls (`subagent_type: explore`), issued **in a single
parent turn** in one message, each with `run_in_background = true`. Read-only scopes,
non-overlapping:

| Agent | Scope | Task |
|---|---|---|
| A | `verification/**` | DEVICE-PIPELINE-AUDIT |
| B | `evaluation/**` | SUBAGENT-OBSERVABILITY-AUDIT |
| C | `specification/**` + root docs | HERMES-INTEGRATION-AUDIT |

Not simulated: no shell-launched `cmdc` processes, no sequential invocation.

## Evidence (raw session JSONL, read in place)

The three `agent` tool_use parts reside in **one message row** (`row 14`), all with the
**same timestamp** `2026-10-04T15:23:26.386Z` — a genuine parallel batch at the protocol
level. Each result returned `agent_id: bg-N-…`.

| Agent id | Type | Task | Status | Duration | Tool uses |
|---|---|---|---:|---:|---:|
| `bg-1-31296fd3` | explore | Device pipeline audit | completed | 97.885 s | 44 |
| `bg-2-a21eebb5` | explore | Subagent observability audit | completed | 89.622 s | 18 |
| `bg-3-8a8f3722` | explore | Hermes integration audit | completed | 124.119 s | 50 |

Raw evidence: `orchestration/hermes/evidence/cc-native-subagents.json`.

## Gates

| Gate | Requirement | Result |
|---|---|---|
| SUBAGENT TOOL USED | yes | **YES** (`agent`) |
| SUBAGENTS STARTED | 3 | **3** |
| SUBAGENTS COMPLETED | 3 | **3** |
| MAX CONCURRENT | ≥ 2 | **3** |
| PARALLEL OVERLAP | > 0 | **89.622 s** (conservative = min duration) |
| SUBAGENT WRITES | 0 | **0** |

**NATIVE PARALLEL: PASS**

## Honesty notes

- The `agent` tool does not expose structured per-child start/end timestamps; overlap is
  computed conservatively as the minimum child duration, since all three were launched in
  one turn. If a stricter proof were required, that figure is `NOT_AVAILABLE`.
- Subagent writes were 0: all three prompts were read-only and their outputs confirm
  "no files modified".

## Comparison to P0A

P0A: `agent` calls = 0, `agent_output` calls = 0, background jobs = 0.
S1: 3 parallel native subagents, 3 completed, 0 writes, 89.6 s concurrent wall.
