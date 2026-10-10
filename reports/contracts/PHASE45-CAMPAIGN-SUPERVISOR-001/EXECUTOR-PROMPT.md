# EXECUTOR PROMPT — PHASE45-CAMPAIGN-SUPERVISOR

You are the execution agent for a FROZEN Implementation Contract. Work from the contract
and the listed `read_first` files. Do not re-do reconnaissance, re-choose architecture, or
re-plan decisions this contract has already frozen.

## 0. Verify the frozen contract
- Contract: `implementation-contract.json` (contract_id `PHASE45-CAMPAIGN-SUPERVISOR-001`, version `0.1.0`)
- Package manifest: `manifest.json` — sha256 of every authored artifact
- Recompute the manifest hashes. If any artifact differs, emit `CONTRACT_CHANGED` and STOP
  (unless this session was explicitly launched with `--accept-contract-update`).
- Confirm `READY.json` reports `status == READY`.

## 1. Read, in this order
1. `implementation-contract.json`
2. `project-context.json` (then ONLY the `read_first` files it lists)
3. `requirements.md`, `acceptance.md`, `design.md`, `DESIGN.md`, `tasks.md`
4. `verification-intent.json`

## 2. Recon budget
- `broad repo scan = forbidden`.
- Read only these 7 `read_first` files:
  1. Google-Android-Agent-Development-Stack/orchestration/hermes/bridge/bridge_cli.py
  2. Google-Android-Agent-Development-Stack/orchestration/hermes/bridge/protocol.py
  3. Google-Android-Agent-Development-Stack/orchestration/hermes/bridge/bridge_state.py
  4. Google-Android-Agent-Development-Stack/orchestration/hermes/bridge/chatgpt_adapter.py
  5. Google-Android-Agent-Development-Stack/orchestration/hermes/bridge/contract_executor.py
  6. Google-Android-Agent-Development-Stack/orchestration/hermes/README.md
  7. Google-Android-Agent-Development-Stack/orchestration/hermes/INTEGRATION.md
- Extend to a targeted search ONLY for `CONTRACT_GAP`, `CONTRACT_CONTRADICTION`, a missing
  dependency, or compile evidence that requires one extra file. Record `EXTRA_RECON_REASON`
  (file + why) for every extension.

## 3. Execute tasks in dependency order
  TASK-01  Create `orchestration/hermes/supervisor/` with `__init__.py`, `campaign_protocol.py`, `campaign_state.py`, `campaign_supervisor.py`, `campaign_cli.py` and `tests/test_campaign_supervisor.py`, using only the Python standard library and wrapping the existing Bridge / adapter interfaces rather than copying them.  (depends: none)
  TASK-02  Implement `campaign_state.py` so that each campaign persists `state.json`, `journal.jsonl` and `campaign.lock` under `~/.local/state/hermes-chatgpt-supervisor/<campaign-id>/` with directory mode 0700, state/journal file mode 0600 where practical, atomic replace plus fsync, and the fields `campaign_id`, `milestone`, `status`, `started_at`, `deadline`, `max_rounds`, `round_count`, `initial_sequence`, `last_seen_assistant_sha256`, `last_dispatched_task_id`, `last_bridge_result_sha256` and `terminal_outcome`.  (depends: TASK-01)
  TASK-03  Implement the per-campaign exclusive lock in `campaign_state.py` so that only one Supervisor process may own a campaign and a second process is refused with a lock-busy outcome without touching Bridge or campaign state.  (depends: TASK-01)
  TASK-04  Implement `campaign_supervisor.py` with the new-response sha256 guard, the classification of each new response (no control / one candidate bridge task / campaign terminal / malformed or ambiguous), the requirement that the campaign is RUNNING and the Bridge status permits a round, the sequence / nonce / in_reply_to match against the Bridge expected values, exactly one `bridge_cli.py round` invocation per valid new task, the read-back of Bridge status after each round, the startup reconciliation of a durable Bridge pending result, and the fail-closed pause on any Bridge safety state.  (depends: TASK-01, TASK-02, TASK-03)
  TASK-05  Implement `campaign_protocol.py` with the campaign-terminal envelope whose open and close markers are composed at runtime from their components, strict JSON decoding that rejects duplicate keys and unknown fields, rejection of multiple campaign envelopes and of any response containing both a campaign-terminal envelope and an executable Bridge task envelope, and validation that `campaign_id`, `milestone` and `in_reply_to` equal the current campaign, the current milestone and the Bridge `state.last_result_sha256`.  (depends: TASK-01)
  TASK-06  Implement `campaign_cli.py` with `status --campaign-id ID` and `run` accepting `--campaign-id`, `--milestone`, `--start-sequence`, `--start-nonce`, `--start-in-reply-to`, `--max-rounds`, `--max-wall-seconds` and `--poll-seconds` with conservative defaults, run to completion in the foreground until CLOSED / PAUSED / safety stop / limit, enforce `max_rounds` and `max_wall_seconds` by persisting PAUSED with outcome LIMIT_REACHED, and emit compact progress lines only.  (depends: TASK-04)
  TASK-07  Implement `tests/test_campaign_supervisor.py` covering the enumerated cases using injected fake `read_latest_assistant`, `bridge_status`, `bridge_round` and clock / sleep seams, with no real Chrome, no real ChatGPT, no real Hermes and no live Bridge state.  (depends: TASK-01)
  TASK-08  After the package and its tests exist, run ONE combined deterministic verification that confirms the unit tests pass, the exact CLI help/interface exists, campaign protocol strictness passes, persistence/restart passes, duplicate prevention passes and bounded limits pass, and write `verification.json` and `supervisor-tests.log` under `orchestration/hermes/evidence/campaign-supervisor/`, where `verification.json` records `verdict`, `bridge_modified`, `sequence_5_consumed` and `m5_manifest_unchanged`.  (depends: TASK-02, TASK-04, TASK-05, TASK-06, TASK-07)

## 4. Boundaries
Allowed paths:
  - Google-Android-Agent-Development-Stack/orchestration/hermes/supervisor/
  - Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/campaign-supervisor/
Forbidden paths:
  - Google-Android-Agent-Development-Stack/orchestration/hermes/bridge/
  - Google-Android-Agent-Development-Stack/orchestration/hermes/evaluation_adapter/
  - Google-Android-Agent-Development-Stack/orchestration/hermes/HERMES-LOCK.json
  - Google-Android-Agent-Development-Stack/specification/
  - Google-Android-Agent-Development-Stack/verification/
  - Google-Android-Agent-Development-Stack/verification-benchmark/
  - Google-Android-Agent-Development-Stack/evaluation/
  - Google-Android-Agent-Development-Stack/references/
  - Google-Android-Agent-Development-Stack/probes/
  - Google-Android-Agent-Development-Stack/.hermes.md
  - Google-Android-Agent-Development-Stack/reports/contracts/
  - KeepLab-Relay/
  - KeepLab-Relay-evidence/
  - Testapp/
  - PowerAi/
Frozen decisions (do not reopen): DEC-001, DEC-002, DEC-003, DEC-004, DEC-005, DEC-006, DEC-007.

## 5. If the contract is wrong
If a contract fact contradicts the source, a required file is missing, an assumption is
wrong, an acceptance is impossible, or a boundary is unsafe:
  STOP → emit `CONTRACT_DEVIATION` with evidence. Do NOT silently redesign.

## 6. Verify and hand off
1. Run the targeted tests named in `tasks.md`.
2. Build the Verification Plan (engine `maestro`,
   journey `PHASE45-CAMPAIGN-SUPERVISOR-LOCAL`).
3. Run the deterministic Verification Layer exactly once.
4. On PASS: make NO further tool call, search, read, audit, repeated verification or
   exploratory check. Produce the Phase C report in the FINAL ASSISTANT RESPONSE using only
   evidence already collected in this session, emit the compact final task result, and STOP
   immediately.
5. On FAIL: repair only the failed contract item and re-run only the work that repair
   invalidated. Do not repeat unaffected PASS work.

After this session (POST-SESSION observers, not in-session steps):
- `on_session_finalize` / Auto-Finalizer are POST-SESSION observers.
- Do NOT invoke, inspect, wait for, or verify Auto-Finalizer from inside this Hermes session.
- Auto-Finalizer runs only AFTER this Hermes session exits and is NOT an in-session acceptance
  criterion.

## Stop conditions
  - A required write falls outside supervisor/ or the campaign evidence directory, or targets a forbidden path: STOP, CONTRACT_DEVIATION.
  - Satisfying the Supervisor would require modifying bridge/, evaluation_adapter/, specification/, HERMES-LOCK.json, .hermes.md, KeepLab, Testapp or PowerAi: STOP, ABSOLUTE_BLOCK_VIOLATION.
  - Satisfying the Supervisor would require a second task-authorization layer, a duplicate protocol implementation or a second Chrome/CDP stack: STOP, DUPLICATE_AUTHORITY_FORBIDDEN.
  - The Supervisor would have to execute a Hermes contract directly or send a ChatGPT message itself: STOP, BRIDGE_BYPASS_FORBIDDEN.
  - The design would need an unbounded loop or autonomy without max-rounds / wall limits: STOP, UNBOUNDED_AUTONOMY_FORBIDDEN.
  - A campaign-terminal response would require calling bridge_cli.py round: STOP, CAMPAIGN_TERMINAL_MUST_NOT_ROUND.
