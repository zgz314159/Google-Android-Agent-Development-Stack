# Command Code Native Subagent Observability (S1)

Generated: 2026-10-04 · Evaluation Core **v0.2.3** (`evaluation/commandcode/core.py:28`)

This records what a native subagent looks like in the raw Command Code JSONL, and whether
Evaluation Core v0.2.3 can see it. **No parser was changed**; a throwaway prototype lived in
the scratchpad only.

## Raw event shapes (observed, parent session `890973b0-…`)

**Parallel batch** — three `agent` tool_use parts in one message row, identical timestamp:

```json
{"type":"message","timestamp":"2026-10-04T15:23:26.386Z","message":{"role":"assistant",
 "content":[{"type":"tool_use","id":"call_00_…","name":"agent",
   "input":{"description":"Device pipeline audit","subagent_type":"explore",
            "run_in_background":true,"prompt":"…"}}, …]}}
```

**agent result** (returns the id; no structured field, text only) — separate row:

```
row 15  ts=2026-10-04T15:23:26.386Z
Background agent launched.
agent_id: bg-1-31296fd3
The agent is working in the background — do not duplicate its work. Use the agent_output tool…
```

**agent_output** — `{type:"tool_use","name":"agent_output","input":{"action":…, "agent_id":…}}`,
with result text either a status roster or a completion payload:

```
row 45  ts=2026-10-04T15:26:36.546Z
bg-1-31296fd3 [completed] explore: Device pipeline audit
bg-2-a21eebb5 [completed] explore: Subagent observability audit
bg-3-8a8f3722 [completed] explore: Hermes integration audit
```

```
row 43  ts=2026-10-04T15:26:27.549Z
agent_id: bg-2-a21eebb5
agent: explore
description: Subagent observability audit
status: completed

# SUBAGENT-OBSERVABILITY-AUDIT
…
```

### Extractable today (raw)

| Field | Where |
|---|---|
| `agent_id` | `agent` tool_result text (`agent_id: bg-N-…`) |
| `subagent_type` | `agent` tool_use `input.subagent_type` |
| `run_in_background` | `agent` tool_use `input.run_in_background` |
| started_at | `agent` tool_use row timestamp |
| completed_at | `agent_output` result row timestamp with `status: completed` |
| status | `agent_output` result text |
| parallel overlap | interval sweep over (started_at, completed_at) |

## What Evaluation Core v0.2.3 recognizes

- **Parser**: `evaluation/commandcode/core.py` (`load_session` :133, `index_calls` :452;
  parts `text`/`tool_use`/`tool_result`; `meta.source` `user|model|tool|steering`).
- `agent` / `agent_output` are known **only as phase-rule names**
  (`evaluation/commandcode/phase_rules.json:28,34,40,76`) and `subagent_type` is read for
  phase mapping (`core.py:597,619`).
- **Absent**: `agent_id`, subagent start/completed timestamps, background-subagent tracking,
  and subagent parallel-overlap. `agent_id` appears nowhere in `evaluation/**`. Tool stats
  are name-level counts only (`core.py:1203-1207`).

## Gap analysis

| Capability | v0.2.3 | Thin hook |
|---|---|---|
| Recognize `agent` call | generic only | already `core.py:461` |
| `agent_output` result parse | name only | alongside `_parse_result_signals()` `core.py:502` |
| `agent_id` | absent | extend `Call` `core.py:436-449`; read from result text |
| start/completed | absent | row timestamps already available (`row_index`/`result_row`) |
| parallel overlap | absent (bg overlap `NOT_AVAILABLE`) | interval reducer near `_background_metrics()` `core.py:1300` |
| subagent stats | name count only | extend `tool_stats` `core.py:1203-1207` |

## Decision

This round **does not change Evaluation Core**. The raw shapes above are stable and text
carries `agent_id`/`status`, so a v0.2.4 addition (additive, observer-only) is feasible and
worth doing as a separate, version-bumped task. Prototype parser used here lived in the
scratchpad and was not committed.
