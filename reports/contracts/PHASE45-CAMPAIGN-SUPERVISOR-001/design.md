# Implementation Design — Phase-45 thin bounded Campaign Supervisor contract

## Architecture

No Bridge architecture is added or changed. This change adds one **new, thin, stdlib-only**
scheduling layer AROUND the existing, already-PASS one-round Bridge:

- `orchestration/hermes/bridge/` is the GPT <-> Hermes control kernel. It is the ONLY authority
  for HERMES task schema validation, nonce / sequence / in_reply_to, replay, risk, contract
  validation, the self-modification gate, Contract Guard execution, the durable result
  transaction and the browser result send. It is READ-ONLY here and is reused through its
  existing public interfaces:
  - `bridge_state.load_state()` / `BridgeState.as_dict()` — read the current chain state
    (`expected_sequence`, `expected_nonce`, `expected_in_reply_to`, `status`,
    `last_result_sha256`) ;
  - `bridge_state.read_pending()` and the `bridge_cli.py round` startup reconciliation — resolve a
    durable pending result;
  - `bridge_state.bridge_lock` — the Bridge's own single-worker guard;
  - `bridge_cli.py round` (or `bridge_cli.run_round`) — invoke exactly ONE round;
  - `chatgpt_adapter.read_latest_assistant()` — the deterministic READ seam for the LATEST
    COMPLETED assistant response and its sha256.
- `orchestration/hermes/supervisor/` is the NEW package this contract authorizes:
  - `campaign_protocol.py` — the strict campaign-terminal envelope (extraction, strict JSON
    decoding with duplicate-key rejection, field/value validation) and the campaign vocabulary.
    It is a SEPARATE protocol from the Bridge task protocol; it never reuses the Bridge task
    envelope for milestone close.
  - `campaign_state.py` — the private per-campaign state store (`state.json`, `journal.jsonl`,
    `campaign.lock`), atomic replace + fsync, `0700`/`0600` permissions, and the campaign lock.
  - `campaign_supervisor.py` — the bounded loop: new-response guard, dispatch policy, chain
    matching, startup reconciliation, fail-closed pausing, limits.
  - `campaign_cli.py` — the `status` and `run` subcommands.
  - `tests/test_campaign_supervisor.py` — the deterministic fake-driven suite.
- `orchestration/hermes/evidence/campaign-supervisor/` is the one other directory this package may
  write. It holds `verification.json` and `supervisor-tests.log`.

The Supervisor is a WAKE-UP / SCHEDULING layer only. It never executes a Hermes contract, never
sends a ChatGPT message and never bypasses the Bridge. There is exactly ONE task-authorization
layer (the Bridge's) and it is not duplicated.

What is REUSED and must not be rebuilt: the whole Bridge kernel (protocol, state, replay journal,
lock, gates, Contract Guard execution, result transaction, browser send), the deterministic
ChatGPT adapter READ seam, and the Specification Compiler that produced this package.

## Data Flow

1. `campaign_cli.py run` acquires the campaign lock for `--campaign-id`, snapshots the initial
   Bridge challenge (`expected_sequence` / `expected_nonce` / `expected_in_reply_to` /
   `last_result_sha256`) and creates the campaign state with `status = RUNNING`.
2. On startup it checks for a durable Bridge pending result. If one exists it invokes
   `bridge_cli.py round` exactly once as the Bridge's own startup reconciliation; a resulting
   `WAITING_FOR_GPT` lets the campaign continue, while `RECOVERY_REQUIRED` / `SEND_UNCERTAIN` /
   `ERROR` pause the campaign and exit non-zero.
3. Each poll iteration reads the LATEST COMPLETED assistant response through the existing adapter
   READ seam and computes its sha256. If the sha256 equals the persisted
   `last_seen_assistant_sha256`, the response is ignored (no Bridge call) and the loop waits.
4. A NEW response is classified:
   - no Bridge task and no campaign terminal -> mark the sha seen, continue waiting;
   - exactly one candidate Bridge task -> require the campaign is `RUNNING`, require the Bridge
     status permits a new round, require sequence / nonce / in_reply_to equal the Bridge expected
     values, then invoke the existing `bridge_cli.py round` exactly once;
   - campaign terminal -> validate it, persist terminal state, journal it and exit;
   - malformed or ambiguous -> pause fail-closed, never invoke the Bridge.
5. After a round returns, the Supervisor reads Bridge status, persists `last_bridge_result_sha256`
   and `round_count`, and returns to waiting for the next NEW response. A Bridge result of
   FAILED/BLOCKED is NOT itself a retry: the Supervisor waits for GPT's next new response unless
   the Bridge itself entered a safety state.
6. When `max_rounds` or the wall deadline is reached the campaign persists `PAUSED` with outcome
   `LIMIT_REACHED` and exits.

## File Structure Plan

**MUST TOUCH**

| File | Role | Expected change |
| --- | --- | --- |
| `orchestration/hermes/supervisor/__init__.py` | package marker | created |
| `orchestration/hermes/supervisor/campaign_protocol.py` | campaign-terminal envelope + vocabulary | created |
| `orchestration/hermes/supervisor/campaign_state.py` | per-campaign state, journal, lock | created |
| `orchestration/hermes/supervisor/campaign_supervisor.py` | bounded scheduling loop | created |
| `orchestration/hermes/supervisor/campaign_cli.py` | `status` and `run` CLI | created |
| `orchestration/hermes/supervisor/tests/test_campaign_supervisor.py` | deterministic fake-driven suite | created |
| `orchestration/hermes/evidence/campaign-supervisor/verification.json` | combined verification result | created |
| `orchestration/hermes/evidence/campaign-supervisor/supervisor-tests.log` | unit-test log | created |

**MAY TOUCH**

| File | Role | Expected change |
| --- | --- | --- |
| `orchestration/hermes/evidence/campaign-supervisor/__pycache__/` | bytecode cache | regenerated only if a helper module is imported from that directory |
| `orchestration/hermes/supervisor/__pycache__/` | bytecode cache | regenerated by a test/import run |

**MUST NOT TOUCH**

- `orchestration/hermes/bridge/` — the control kernel; the ONLY task-authorization authority.
- `orchestration/hermes/evaluation_adapter/` — the Contract Guard and its hooks.
- `orchestration/hermes/HERMES-LOCK.json` — the pinned Hermes revision.
- `specification/` — the Specification Compiler.
- `verification/`, `verification-benchmark/` — the Android verification layer and device lock.
- `evaluation/` — the evaluation core.
- `references/`, `probes/` — frozen reference material.
- `.hermes.md` — project governance context.
- `reports/contracts/` — every contract package, this one included.
- KeepLab product code, `Testapp/`, `PowerAi/` — out of scope.

## Selector Contract

No Android UI is touched. The compiler schema requires a selector contract regardless, so these
entries are **deterministic filesystem identity markers**, not on-screen widgets. The Supervisor
performs zero device interaction and zero visual judgment.

| name | state it identifies |
| --- | --- |
| `campaign_supervisor_package_present` | the Supervisor package exists under orchestration/hermes/supervisor/ |
| `campaign_state_file_present` | a per-campaign state.json exists under the private state root |
| `campaign_lock_present` | a per-campaign campaign.lock exists under the private state root |
| `campaign_evidence_dir_present` | the campaign evidence directory exists under orchestration/hermes/evidence/campaign-supervisor/ |

## Contract Metadata

```json
{
  "decisions": [
    {
      "id": "DEC-001",
      "statement": "The Supervisor is a wake-up / scheduling layer only; the Bridge remains the sole authority for task schema, nonce / sequence / in_reply_to, replay, risk, contract validation, the self-modification gate, Contract Guard execution, the durable result transaction and the browser send.",
      "rationale": "Those gates are already implemented, tested and PASS in the one-round bridge; moving any of them into a new layer would create a second authorization path and invalidate the bridge evidence."
    },
    {
      "id": "DEC-002",
      "statement": "The Supervisor reuses the existing Bridge interfaces and the deterministic ChatGPT adapter READ seam read-only, wraps them, and never copies or reimplements them; it never executes a Hermes contract and never sends a ChatGPT message.",
      "rationale": "A single writer (the Bridge) is what makes replay, chain and send semantics sound; a duplicate sender or a second contract executor would break that."
    },
    {
      "id": "DEC-003",
      "statement": "The latest completed assistant response sha256 is the primary new-response guard, while the Bridge's sequence / nonce / replay state remains authoritative for what may be executed.",
      "rationale": "Hashing the whole response is a cheap, deterministic way to never act twice on the same GPT turn, and it complements rather than replaces the Bridge chain."
    },
    {
      "id": "DEC-004",
      "statement": "Campaign termination uses a separate strict envelope whose marker constants are composed at runtime from their components; a terminal campaign response never invokes bridge_cli.py round, so the Bridge stays WAITING_FOR_GPT with its next sequence available.",
      "rationale": "Reusing the Bridge task protocol for milestone close would either latch the Bridge STOPPED and block the next milestone, or require a Bridge change that this contract forbids."
    },
    {
      "id": "DEC-005",
      "statement": "The Supervisor fails closed: unknown fields, duplicate keys, multiple or mixed envelopes, and every Bridge safety state (AWAITING_APPROVAL, RECOVERY_REQUIRED, SEND_UNCERTAIN, STOPPED, ERROR) pause the campaign, journal the reason and exit non-zero, with no auto-repair and no manual Bridge-state edit.",
      "rationale": "An ambiguous control or a safety state means the deterministic path is unavailable; continuing would either guess or duplicate work."
    },
    {
      "id": "DEC-006",
      "statement": "Autonomy is bounded by max_rounds, max_wall_seconds and poll_seconds, with conservative defaults; reaching a bound persists PAUSED with outcome LIMIT_REACHED and exits.",
      "rationale": "There must be no infinite autonomy and no while-true bridge replay; every campaign is a bounded period of autonomy for exactly one milestone."
    },
    {
      "id": "DEC-007",
      "statement": "Per-campaign state lives under the private root ~/.local/state/hermes-chatgpt-supervisor/<campaign-id>/ as state.json, journal.jsonl and campaign.lock, written with atomic replace plus fsync and 0700/0600 permissions, and exactly one Supervisor process may own a campaign.",
      "rationale": "The seen hash, the round count and the terminal outcome must survive a restart, and the campaign lock is what prevents two scheduling workers from racing the same milestone."
    }
  ],
  "assumptions": [
    {
      "id": "ASM-001",
      "statement": "bridge_cli.py round and its bridge_state / adapter interfaces are importable and stable enough to be wrapped without modification."
    },
    {
      "id": "ASM-002",
      "statement": "The Bridge already accepts one valid task envelope per round; the Supervisor only decides WHEN to invoke that round, never WHAT it validates."
    },
    {
      "id": "ASM-003",
      "statement": "The Assistant's campaign-terminal envelope and the Bridge task envelope are mutually exclusive per response, and the campaign-terminal marker cannot be produced by the Bridge."
    }
  ],
  "data_change": {
    "schema_version_current": 0,
    "schema_version_target": 0,
    "migration_required": false,
    "notes": "No persisted product schema is touched. The only durable artifacts are the private per-campaign state under the Supervisor state root and the two evidence files under the campaign evidence directory."
  },
  "ui_change": {
    "surfaces": [],
    "selectors_added": [
      "campaign_supervisor_package_present",
      "campaign_state_file_present",
      "campaign_lock_present",
      "campaign_evidence_dir_present"
    ]
  },
  "selector_contract": [
    {
      "name": "campaign_supervisor_package_present",
      "compose_test_tag": "campaign_supervisor_package_present",
      "uiautomator": "By.res(\"campaign_supervisor_package_present\")",
      "state": "Supervisor package present under orchestration/hermes/supervisor/",
      "required": true
    },
    {
      "name": "campaign_state_file_present",
      "compose_test_tag": "campaign_state_file_present",
      "uiautomator": "By.res(\"campaign_state_file_present\")",
      "state": "per-campaign state.json present under the private Supervisor state root",
      "required": true
    },
    {
      "name": "campaign_lock_present",
      "compose_test_tag": "campaign_lock_present",
      "uiautomator": "By.res(\"campaign_lock_present\")",
      "state": "per-campaign campaign.lock present under the private Supervisor state root",
      "required": true
    },
    {
      "name": "campaign_evidence_dir_present",
      "compose_test_tag": "campaign_evidence_dir_present",
      "uiautomator": "By.res(\"campaign_evidence_dir_present\")",
      "state": "campaign evidence directory present under orchestration/hermes/evidence/campaign-supervisor/",
      "required": true
    }
  ],
  "stop_conditions": [
    "A required write falls outside supervisor/ or the campaign evidence directory, or targets a forbidden path: STOP, CONTRACT_DEVIATION.",
    "Satisfying the Supervisor would require modifying bridge/, evaluation_adapter/, specification/, HERMES-LOCK.json, .hermes.md, KeepLab, Testapp or PowerAi: STOP, ABSOLUTE_BLOCK_VIOLATION.",
    "Satisfying the Supervisor would require a second task-authorization layer, a duplicate protocol implementation or a second Chrome/CDP stack: STOP, DUPLICATE_AUTHORITY_FORBIDDEN.",
    "The Supervisor would have to execute a Hermes contract directly or send a ChatGPT message itself: STOP, BRIDGE_BYPASS_FORBIDDEN.",
    "The design would need an unbounded loop or autonomy without max-rounds / wall limits: STOP, UNBOUNDED_AUTONOMY_FORBIDDEN.",
    "A campaign-terminal response would require calling bridge_cli.py round: STOP, CAMPAIGN_TERMINAL_MUST_NOT_ROUND."
  ]
}
```
