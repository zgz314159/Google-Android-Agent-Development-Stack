# Acceptance Criteria — Phase-45 thin bounded Campaign Supervisor contract

## Acceptance Criteria

### AC-PHASE45SUP-001 — The only authorized write surface is the Supervisor package and its evidence directory

- Given: the generated implementation contract is read
- When: `allowed_paths` is inspected
- Then: it contains exactly `Google-Android-Agent-Development-Stack/orchestration/hermes/supervisor/` and `Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/campaign-supervisor/` and no other entry
- Verification: read `allowed_paths` from implementation-contract.json and assert it equals the two authorized directories
- PC1 Step: PC1-S01

### AC-PHASE45SUP-002 — The control plane and product surfaces stay forbidden and Bridge is reused read-only

- Given: the generated implementation contract is read
- When: `allowed_paths` and `forbidden_paths` are compared, and the Bridge files are hashed
- Then: `orchestration/hermes/bridge/`, `orchestration/hermes/evaluation_adapter/`, `orchestration/hermes/HERMES-LOCK.json`, `specification/`, `verification/`, `verification-benchmark/`, `evaluation/`, `references/`, `probes/`, `.hermes.md`, `reports/contracts/`, `KeepLab-Relay/`, `KeepLab-Relay-evidence/`, `Testapp/` and `PowerAi/` appear in `forbidden_paths` and in no allowed path, no allowed path overlaps any forbidden path, and every Bridge file's sha256 is unchanged
- Verification: assert each forbidden entry is present, assert the compiler reports zero E_PATH_CONFLICT and zero E_PROJECT_ESCAPE errors, and assert Bridge file hashes equal their pre-run values
- PC1 Step: PC1-S02

### AC-PHASE45SUP-003 — The campaign lock admits exactly one worker

- Given: a campaign run holds the campaign lock
- When: a second Supervisor process attempts to start the same campaign
- Then: the second process is refused with a lock-busy outcome, performs no dispatch and does not modify Bridge or campaign state
- Verification: hold the lock in one process, attempt a second acquisition and assert it is refused
- PC1 Step: PC1-S03

### AC-PHASE45SUP-004 — Per-campaign state is persisted with the required fields and permissions

- Given: a campaign has run at least one iteration
- When: the private state root `~/.local/state/hermes-chatgpt-supervisor/<campaign-id>/` is inspected
- Then: `state.json`, `journal.jsonl` and `campaign.lock` exist, the directory mode is 0700, the state and journal file modes are 0600 where practical, writes are atomic replace plus fsync, and `state.json` records `campaign_id`, `milestone`, `status`, `started_at`, `deadline`, `max_rounds`, `round_count`, `initial_sequence`, `last_seen_assistant_sha256`, `last_dispatched_task_id`, `last_bridge_result_sha256` and `terminal_outcome`
- Verification: read back the persisted state and assert every declared field is present and the permissions are correct
- PC1 Step: PC1-S04

### AC-PHASE45SUP-005 — State and journal survive a restart without a duplicate dispatch

- Given: a campaign persisted a state in which the latest assistant response was already seen or dispatched
- When: the Supervisor restarts for the same campaign
- Then: it resumes from the persisted `last_seen_assistant_sha256` and does not dispatch the same assistant response again
- Verification: restart against the persisted state and assert no second bridge round is invoked for an already-seen response
- PC1 Step: PC1-S05

### AC-PHASE45SUP-006 — The same assistant response is never processed twice

- Given: a NEW assistant response has been observed and its sha256 recorded
- When: the next poll returns a response with the same sha256
- Then: the response is ignored, no Bridge round is invoked and no state change beyond the waiting status occurs
- Verification: drive two polls with the same fake response and assert exactly zero bridge calls on the second
- PC1 Step: PC1-S06

### AC-PHASE45SUP-007 — A new exact expected task invokes the Bridge exactly once

- Given: a NEW response contains exactly one valid Bridge task envelope whose sequence, nonce and in_reply_to equal the Bridge expected values, the campaign is RUNNING and the Bridge status permits a new round
- When: the Supervisor processes the response
- Then: it invokes `bridge_cli.py round` exactly once, reads Bridge status afterwards, persists the result hash and the incremented round count, and returns to waiting
- Verification: with a fake bridge round, assert exactly one invocation and the persisted result hash and round count
- PC1 Step: PC1-S07

### AC-PHASE45SUP-008 — A mismatch pauses the campaign without invoking the Bridge

- Given: a NEW response carries a task whose sequence, nonce or in_reply_to does not equal the Bridge expected value, or the Bridge status does not permit a new round
- When: the Supervisor processes the response
- Then: the campaign is paused fail-closed and `bridge_cli.py round` is not invoked
- Verification: drive each mismatch and assert zero bridge calls and a PAUSED outcome
- PC1 Step: PC1-S08

### AC-PHASE45SUP-009 — A valid campaign terminal envelope closes the campaign

- Given: the Assistant emits a valid campaign-terminal envelope with `protocol` equal to `HERMES_CAMPAIGN_V1`, status `CLOSED` and outcome `PASS`, whose `campaign_id`, `milestone` and `in_reply_to` match the current campaign, milestone and Bridge `state.last_result_sha256`
- When: the Supervisor parses it
- Then: it persists terminal state, journals it and exits with `CAMPAIGN_CLOSED outcome=PASS`, without invoking `bridge_cli.py round`, leaving the Bridge `WAITING_FOR_GPT`
- Verification: feed a valid terminal envelope and assert zero bridge calls, CLOSED/PASS persisted, and Bridge remains WAITING_FOR_GPT
- PC1 Step: PC1-S09

### AC-PHASE45SUP-010 — Wrong id, wrong milestone or stale in_reply_to is rejected

- Given: a campaign-terminal envelope whose `campaign_id` differs from the current campaign, or whose `milestone` differs from the current milestone, or whose `in_reply_to` differs from the Bridge `state.last_result_sha256`
- When: the Supervisor validates it
- Then: the terminal envelope is rejected and the campaign does not close on it
- Verification: drive each of the three mismatches and assert rejection
- PC1 Step: PC1-S10

### AC-PHASE45SUP-011 — Malformed or ambiguous control pauses fail-closed

- Given: a NEW response whose executable control is malformed (bad JSON, unknown field, duplicate key) or ambiguous (multiple envelopes)
- When: the Supervisor parses it
- Then: the campaign is paused fail-closed with a journaled reason and the Bridge is not invoked
- Verification: drive a malformed and an ambiguous response and assert PAUSED with zero bridge calls
- PC1 Step: PC1-S11

### AC-PHASE45SUP-012 — Bridge safety states pause the campaign

- Given: the Bridge reports one of `AWAITING_APPROVAL`, `RECOVERY_REQUIRED`, `SEND_UNCERTAIN`, `STOPPED` or `ERROR`
- When: the Supervisor checks Bridge status before or after a round
- Then: it persists PAUSED, journals the reason, exits non-zero, never auto-repairs and never edits Bridge state
- Verification: drive each safety status and assert PAUSED plus a non-zero exit and unchanged Bridge state
- PC1 Step: PC1-S12

### AC-PHASE45SUP-013 — A task and a campaign terminal in the same response is rejected

- Given: a single assistant response contains both a valid campaign-terminal envelope and an executable Bridge task envelope
- When: the Supervisor parses it
- Then: the response is rejected, no Bridge round is invoked and the campaign pauses fail-closed
- Verification: feed the mixed response and assert rejection with zero bridge calls
- PC1 Step: PC1-S13

### AC-PHASE45SUP-014 — Max rounds pauses the campaign

- Given: a campaign with `max_rounds` reached
- When: the next dispatch would exceed the bound
- Then: the Supervisor persists PAUSED with outcome `LIMIT_REACHED` and exits without a further bridge round
- Verification: drive exactly `max_rounds` dispatches and assert the next iteration pauses with LIMIT_REACHED
- PC1 Step: PC1-S14

### AC-PHASE45SUP-015 — The wall deadline pauses the campaign

- Given: a campaign whose `started_at` plus `max_wall_seconds` has elapsed through the injected clock
- When: the loop checks the deadline
- Then: the Supervisor persists PAUSED with outcome `LIMIT_REACHED` and exits even when no new response arrived
- Verification: advance the fake clock past the deadline and assert PAUSED with LIMIT_REACHED
- PC1 Step: PC1-S15

### AC-PHASE45SUP-016 — Pending-result startup reconciliation calls the Bridge once

- Given: a durable Bridge pending result exists on Supervisor startup
- When: the campaign starts
- Then: `bridge_cli.py round` is invoked exactly once for the Bridge's own startup reconciliation; a resulting `WAITING_FOR_GPT` lets the campaign continue, while `RECOVERY_REQUIRED`, `SEND_UNCERTAIN` or `ERROR` pauses and exits
- Verification: seed a fake pending result and assert exactly one reconciliation round and the correct continuation or pause
- PC1 Step: PC1-S16

### AC-PHASE45SUP-017 — The exact CLI interface exists and emits compact progress

- Given: the Supervisor CLI is invoked
- When: `status --campaign-id ID` and `run` with all declared flags are called
- Then: both subcommands exist with the exact flags, `run` stays in the foreground until CLOSED / PAUSED / safety stop / limit, and the output is compact progress lines only
- Verification: assert `--help` exposes both subcommands and all run flags, and assert the run output uses the compact progress vocabulary
- PC1 Step: PC1-S17

### AC-PHASE45SUP-018 — The package is stdlib-only with the declared module set

- Given: the Supervisor package directory
- When: its files and imports are inspected
- Then: `__init__.py`, `campaign_protocol.py`, `campaign_state.py`, `campaign_supervisor.py`, `campaign_cli.py` and `tests/test_campaign_supervisor.py` exist, every import resolves to the standard library or to a read-only Bridge module, no third-party dependency is required, and no framework is added
- Verification: assert the six files exist and that imports are stdlib-only
- PC1 Step: PC1-S18

### AC-PHASE45SUP-019 — Tests use injected fakes only

- Given: the Supervisor test suite
- When: it runs
- Then: it drives the Supervisor exclusively through injected fake `read_latest_assistant`, `bridge_status`, `bridge_round` and clock / sleep seams, opens no real Chrome, no real ChatGPT, no real Hermes and no live Bridge state
- Verification: assert no test imports or constructs a live transport and no browser or network is opened
- PC1 Step: PC1-S19

### AC-PHASE45SUP-020 — The enumerated cases are covered

- Given: the Supervisor test suite
- When: it is run offline
- Then: it covers the same-response-twice guard, the exact-expected-task single dispatch, sequence / nonce / in_reply_to mismatch pausing, control-free responses being marked seen, malformed and ambiguous tasks pausing fail-closed, a valid campaign PASS closing without a Bridge call, wrong id / wrong milestone / stale in_reply_to rejection, a task plus campaign terminal being rejected, AWAITING_APPROVAL / RECOVERY_REQUIRED / SEND_UNCERTAIN / ERROR pausing, max_rounds and max_wall_seconds pausing, restart reusing the persisted seen hash without duplicate dispatch, pending-result reconciliation calling the Bridge once, a successful reconciliation resuming waiting, the campaign lock preventing two workers, and state/journal persistence surviving a restart
- Verification: run the suite and assert all enumerated cases pass with zero failures and zero errors
- PC1 Step: PC1-S20

### AC-PHASE45SUP-021 — One combined verification writes the required evidence

- Given: the Supervisor package and its tests exist
- When: the single combined Supervisor verification runs
- Then: it confirms the unit tests pass, the exact CLI help/interface exists, campaign protocol strictness passes, persistence/restart passes, duplicate prevention passes and bounded limits pass, and it writes `verification.json` and `supervisor-tests.log` under `orchestration/hermes/evidence/campaign-supervisor/`, where `verification.json` records `verdict` `PASS`, `bridge_modified` false, `sequence_5_consumed` false and `m5_manifest_unchanged` true, and it proves the Bridge files, the Specification Compiler files and the M5 contract manifest are unchanged, live Bridge sequence 5 is still unconsumed, and no live browser send, no Bridge round and no KeepLab write occurred
- Verification: read the evidence JSON and assert the required verdict fields and the read-only comparisons
- PC1 Step: PC1-S21
