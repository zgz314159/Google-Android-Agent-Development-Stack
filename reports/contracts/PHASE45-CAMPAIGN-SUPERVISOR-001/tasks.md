# Tasks — Phase-45 thin bounded Campaign Supervisor contract

## Tasks

### TASK-01 — Create the stdlib-only Supervisor package skeleton

- Goal: Create `orchestration/hermes/supervisor/` with `__init__.py`, `campaign_protocol.py`, `campaign_state.py`, `campaign_supervisor.py`, `campaign_cli.py` and `tests/test_campaign_supervisor.py`, using only the Python standard library and wrapping the existing Bridge / adapter interfaces rather than copying them.
_Boundary:_ The Supervisor package directory only. No Bridge module is edited, copied or vendored, and no framework, plugin system or scheduler abstraction is introduced.
_Depends:_ none
- Allowed Paths: `Google-Android-Agent-Development-Stack/orchestration/hermes/supervisor/`
- Acceptance: AC-PHASE45SUP-001, AC-PHASE45SUP-002, AC-PHASE45SUP-018
- Verification: assert the six declared files exist, assert every import resolves to the standard library or to a bridge package read-only, and assert no Bridge file hash changed
- Done When: the package imports cleanly stdlib-only and every declared module exists

### TASK-02 — Implement the durable per-campaign state store

- Goal: Implement `campaign_state.py` so that each campaign persists `state.json`, `journal.jsonl` and `campaign.lock` under `~/.local/state/hermes-chatgpt-supervisor/<campaign-id>/` with directory mode 0700, state/journal file mode 0600 where practical, atomic replace plus fsync, and the fields `campaign_id`, `milestone`, `status`, `started_at`, `deadline`, `max_rounds`, `round_count`, `initial_sequence`, `last_seen_assistant_sha256`, `last_dispatched_task_id`, `last_bridge_result_sha256` and `terminal_outcome`.
_Boundary:_ The private Supervisor state root only. Bridge state is read, never written, and no Bridge state file is edited.
_Depends:_ TASK-01
- Allowed Paths: `Google-Android-Agent-Development-Stack/orchestration/hermes/supervisor/`
- Acceptance: AC-PHASE45SUP-004, AC-PHASE45SUP-005
- Verification: write, restart and read back the campaign state and assert every field survives and the seen-assistant hash is reused after restart
- Done When: a restarted Supervisor reads the persisted state and does not duplicate a dispatch

### TASK-03 — Implement the single campaign lock

- Goal: Implement the per-campaign exclusive lock in `campaign_state.py` so that only one Supervisor process may own a campaign and a second process is refused with a lock-busy outcome without touching Bridge or campaign state.
_Boundary:_ The campaign lock file only. The Bridge's own lock is never taken over or replaced.
_Depends:_ TASK-01
- Allowed Paths: `Google-Android-Agent-Development-Stack/orchestration/hermes/supervisor/`
- Acceptance: AC-PHASE45SUP-003
- Verification: hold the lock in one process and assert a second acquisition is refused and performs no dispatch
- Done When: two concurrent workers for one campaign cannot both run

### TASK-04 — Implement the bounded scheduling loop and dispatch policy

- Goal: Implement `campaign_supervisor.py` with the new-response sha256 guard, the classification of each new response (no control / one candidate bridge task / campaign terminal / malformed or ambiguous), the requirement that the campaign is RUNNING and the Bridge status permits a round, the sequence / nonce / in_reply_to match against the Bridge expected values, exactly one `bridge_cli.py round` invocation per valid new task, the read-back of Bridge status after each round, the startup reconciliation of a durable Bridge pending result, and the fail-closed pause on any Bridge safety state.
_Boundary:_ Scheduling and dispatch only. The Supervisor never executes a contract, never sends a ChatGPT message and never edits Bridge state.
_Depends:_ TASK-01, TASK-02, TASK-03
- Allowed Paths: `Google-Android-Agent-Development-Stack/orchestration/hermes/supervisor/`
- Acceptance: AC-PHASE45SUP-006, AC-PHASE45SUP-007, AC-PHASE45SUP-008, AC-PHASE45SUP-011, AC-PHASE45SUP-012, AC-PHASE45SUP-016
- Verification: with injected fake `read_latest_assistant`, `bridge_status` and `bridge_round`, assert exactly one round for a new valid task, no round for a repeated or mismatched response, and a PAUSED fail-closed outcome for every malformed or safety-state input
- Done When: every dispatch decision is driven by the injected seams and no live Bridge call is made in a test

### TASK-05 — Implement the strict campaign-terminal envelope protocol

- Goal: Implement `campaign_protocol.py` with the campaign-terminal envelope whose open and close markers are composed at runtime from their components, strict JSON decoding that rejects duplicate keys and unknown fields, rejection of multiple campaign envelopes and of any response containing both a campaign-terminal envelope and an executable Bridge task envelope, and validation that `campaign_id`, `milestone` and `in_reply_to` equal the current campaign, the current milestone and the Bridge `state.last_result_sha256`.
_Boundary:_ Campaign protocol only. The Bridge task protocol is reused as-is and is never extended for milestone close.
_Depends:_ TASK-01
- Allowed Paths: `Google-Android-Agent-Development-Stack/orchestration/hermes/supervisor/`
- Acceptance: AC-PHASE45SUP-009, AC-PHASE45SUP-010, AC-PHASE45SUP-011, AC-PHASE45SUP-013
- Verification: assert a valid campaign envelope is accepted, and that wrong id / wrong milestone / stale in_reply_to / unknown field / duplicate key / multiple envelopes / mixed envelope responses are each rejected
- Done When: a validated terminal campaign envelope persists terminal state and exits without invoking a Bridge round

### TASK-06 — Implement bounded autonomy and the CLI

- Goal: Implement `campaign_cli.py` with `status --campaign-id ID` and `run` accepting `--campaign-id`, `--milestone`, `--start-sequence`, `--start-nonce`, `--start-in-reply-to`, `--max-rounds`, `--max-wall-seconds` and `--poll-seconds` with conservative defaults, run to completion in the foreground until CLOSED / PAUSED / safety stop / limit, enforce `max_rounds` and `max_wall_seconds` by persisting PAUSED with outcome LIMIT_REACHED, and emit compact progress lines only.
_Boundary:_ The CLI surface only. No log-streaming framework, no background daemon and no unbounded loop.
_Depends:_ TASK-04
- Allowed Paths: `Google-Android-Agent-Development-Stack/orchestration/hermes/supervisor/`
- Acceptance: AC-PHASE45SUP-014, AC-PHASE45SUP-015, AC-PHASE45SUP-017
- Verification: assert `--help` exposes both subcommands and all run flags, and assert a run stops at the round or wall limit with LIMIT_REACHED
- Done When: the exact CLI interface exists and no run exceeds its bounds

### TASK-07 — Implement the deterministic fake-driven test suite

- Goal: Implement `tests/test_campaign_supervisor.py` covering the enumerated cases using injected fake `read_latest_assistant`, `bridge_status`, `bridge_round` and clock / sleep seams, with no real Chrome, no real ChatGPT, no real Hermes and no live Bridge state.
_Boundary:_ Test source only. No production module is modified to make a test pass, and no live transport is contacted.
_Depends:_ TASK-01
- Allowed Paths: `Google-Android-Agent-Development-Stack/orchestration/hermes/supervisor/`
- Acceptance: AC-PHASE45SUP-019, AC-PHASE45SUP-020
- Verification: `python3 -m unittest discover -s tests -p "test_*.py"` from the Supervisor directory exits 0 with zero failures and zero errors
- Done When: every enumerated case passes offline and deterministically

### TASK-08 — Run the single combined Supervisor verification and write evidence

- Goal: After the package and its tests exist, run ONE combined deterministic verification that confirms the unit tests pass, the exact CLI help/interface exists, campaign protocol strictness passes, persistence/restart passes, duplicate prevention passes and bounded limits pass, and write `verification.json` and `supervisor-tests.log` under `orchestration/hermes/evidence/campaign-supervisor/`, where `verification.json` records `verdict`, `bridge_modified`, `sequence_5_consumed` and `m5_manifest_unchanged`.
_Boundary:_ The campaign evidence directory and read-only comparison only. No Bridge round, no browser send, no KeepLab write and no contract-package write occur during the verification.
_Depends:_ TASK-02, TASK-04, TASK-05, TASK-06, TASK-07
- Allowed Paths: `Google-Android-Agent-Development-Stack/orchestration/hermes/supervisor/`, `Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/campaign-supervisor/`
- Acceptance: AC-PHASE45SUP-021
- Verification: recompute the Bridge file hashes and compare against their pre-run values, confirm the Specification Compiler files and the M5 contract manifest are unchanged, confirm live Bridge sequence 5 is still unconsumed, and assert the evidence JSON reports verdict PASS with bridge_modified false and sequence_5_consumed false
- Done When: the two evidence files exist and report the required verdict, with PASS followed by an immediate stop
