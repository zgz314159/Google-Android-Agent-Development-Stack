# Requirements — Phase-45 thin bounded Campaign Supervisor contract

## Requirements

### REQ-PHASE45SUP-001 — The Supervisor is a thin layer and the Bridge stays the sole authority

- Statement: The generated contract must list exactly `Google-Android-Agent-Development-Stack/orchestration/hermes/supervisor/` and `Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/campaign-supervisor/` in `allowed_paths` and no other project path, and its `forbidden_paths` must cover the Bridge, the evaluation adapter, `HERMES-LOCK.json`, the Specification Compiler, the Android verification layers, the evaluation core, `references/`, `probes/`, `.hermes.md`, `reports/contracts/`, KeepLab, `Testapp` and `PowerAi`, with no allowed path overlapping any forbidden path. The Supervisor must reuse the existing Bridge interfaces read-only and must not introduce a second task-authorization layer, execute a Hermes contract itself, or send any ChatGPT message itself.
- Conditions: When the Contract Guard activates this package for the Supervisor implementation session, and whenever the Supervisor performs a round.
- Expected: A write under `supervisor/` or the campaign evidence directory is allowed; every other project path is blocked. The Bridge files are byte-identical to their pre-run hashes after the session.
- Edge case: No parent directory above the two authorized directories is allow-listed, so the authorization cannot widen into the Bridge or the control plane.
- Acceptance: AC-PHASE45SUP-001, AC-PHASE45SUP-002
- Tasks: TASK-01, TASK-08

### REQ-PHASE45SUP-002 — Exactly one Supervisor process may own a campaign

- Statement: The Supervisor must acquire exactly one campaign lock per campaign before doing any work, so a second Supervisor process for the same campaign is refused rather than run concurrently.
- Conditions: When a campaign run starts, or when a second process attempts to start the same campaign.
- Expected: The first process owns the campaign; the second is refused with a lock-busy outcome and does not touch Bridge or the campaign state.
- Edge case: A stale lock left by a crashed process must be resolved by the operating-system lock semantics, never by silently deleting another live owner's lock.
- Acceptance: AC-PHASE45SUP-003
- Tasks: TASK-03

### REQ-PHASE45SUP-003 — Campaign state is durable and resumable

- Statement: The Supervisor must persist per-campaign state under the private state root `~/.local/state/hermes-chatgpt-supervisor/<campaign-id>/` as `state.json`, `journal.jsonl` and `campaign.lock`, with directory permissions `0700` and state/journal file permissions `0600` where practical, using atomic replace plus fsync so that a restart resumes from the persisted seen-assistant hash without duplicating a dispatch.
- Conditions: On every state transition and on startup of a restarted Supervisor.
- Expected: The persisted fields `campaign_id`, `milestone`, `status`, `started_at`, `deadline`, `max_rounds`, `round_count`, `initial_sequence`, `last_seen_assistant_sha256`, `last_dispatched_task_id`, `last_bridge_result_sha256` and `terminal_outcome` survive a restart, and a restart uses the persisted `last_seen_assistant_sha256` as the new-response guard.
- Edge case: A torn or absent state file must fail closed to a paused campaign rather than re-dispatch.
- Acceptance: AC-PHASE45SUP-004, AC-PHASE45SUP-005
- Tasks: TASK-02

### REQ-PHASE45SUP-004 — The latest assistant response hash is the primary new-response guard

- Statement: The Supervisor must poll the LATEST COMPLETED ChatGPT assistant response through the existing adapter READ seam, compute its sha256, and never process the same assistant response twice; an already-seen hash must be ignored without any Bridge call.
- Conditions: On every poll iteration.
- Expected: A repeated assistant response produces no dispatch, no Bridge invocation and no state change beyond the waiting status.
- Edge case: A response that is a duplicate of the response already recorded as dispatched must not produce a second `bridge_cli.py round`.
- Acceptance: AC-PHASE45SUP-006
- Tasks: TASK-04

### REQ-PHASE45SUP-005 — One valid new task envelope dispatches exactly one Bridge round

- Statement: When a NEW assistant response contains exactly one valid Bridge task envelope, the Supervisor must read the current Bridge status and challenge, require that the campaign is RUNNING and that the Bridge status permits a new round, require that the envelope's sequence, nonce and in_reply_to equal the Bridge expected values, and then invoke the existing `bridge_cli.py round` exactly once — never executing the contract itself.
- Conditions: When a new response carries an executable Bridge task envelope.
- Expected: Exactly one Bridge round is invoked; after it returns the Supervisor reads Bridge status and persists the result hash and the incremented round count; it then waits for the next assistant response.
- Edge case: Any sequence, nonce or in_reply_to mismatch — or a Bridge status that does not permit a new round — must pause the campaign without invoking the Bridge.
- Acceptance: AC-PHASE45SUP-007, AC-PHASE45SUP-008
- Tasks: TASK-04

### REQ-PHASE45SUP-006 — Campaign termination uses a separate strict envelope and never calls a Bridge round

- Statement: The Supervisor must define a separate strict assistant-side campaign-terminal envelope whose open marker is composed at runtime from three `<` characters joined with `HERMES_CAMPAIGN_V1` and three `>` characters, and whose close marker is composed the same way from `END_HERMES_CAMPAIGN_V1`; the envelope carries exactly the strict JSON fields `protocol`, `campaign_id`, `milestone`, `status`, `outcome` and `in_reply_to`, with `protocol` equal to `HERMES_CAMPAIGN_V1`, `status` in `CLOSED`/`PAUSED` and `outcome` in `PASS`/`BLOCKED`/`FAILED`/`HUMAN_REQUIRED`/`SAFETY_STOP`/`LIMIT_REACHED`. A validated terminal campaign envelope must persist terminal state, journal it and exit without calling `bridge_cli.py round`, leaving the Bridge in `WAITING_FOR_GPT` with its next sequence available.
- Conditions: When the assistant emits a campaign-terminal envelope, or a campaign run ends.
- Expected: The campaign closes or pauses with the declared outcome; the Bridge is not invoked for a terminal response and remains `WAITING_FOR_GPT` rather than permanently latching `STOPPED`.
- Edge case: `campaign_id` must equal the current campaign, `milestone` must equal the current milestone and `in_reply_to` must equal the Bridge `state.last_result_sha256`; any mismatch is rejected.
- Acceptance: AC-PHASE45SUP-009, AC-PHASE45SUP-010
- Tasks: TASK-05

### REQ-PHASE45SUP-007 — Unknown, duplicate-key, ambiguous and mixed control fail closed

- Statement: The Supervisor must reject unknown fields, duplicate JSON keys, multiple campaign envelopes, and any response containing both a campaign-terminal envelope and an executable Bridge task envelope; a response with no Bridge task and no campaign terminal must be marked seen and ignored; any malformed or ambiguous executable control must pause the campaign fail-closed without invoking the Bridge.
- Conditions: When parsing each NEW assistant response.
- Expected: A malformed or ambiguous control pause the campaign with a journaled reason; a control-free response is marked seen and the loop continues.
- Edge case: A response carrying both envelope kinds must be rejected for both, never partially honoured.
- Acceptance: AC-PHASE45SUP-011, AC-PHASE45SUP-013
- Tasks: TASK-04, TASK-05

### REQ-PHASE45SUP-008 — Bridge safety states pause the campaign and are never auto-repaired

- Statement: The Supervisor may continue only from a normal `WAITING_FOR_GPT` / idle-ready Bridge state; if the Bridge reports `AWAITING_APPROVAL`, `RECOVERY_REQUIRED`, `SEND_UNCERTAIN`, `STOPPED` or `ERROR`, the Supervisor must persist `PAUSED`, journal the reason and exit non-zero, never auto-repairing and never editing Bridge state.
- Conditions: Before dispatching any round and after any round returns.
- Expected: A safety state ends the campaign in `PAUSED` with a non-zero exit and an unmodified Bridge state.
- Edge case: A Bridge durable pending result on Supervisor startup is reconciled by invoking `bridge_cli.py round` exactly once for the Bridge's own startup reconciliation; afterwards a `WAITING_FOR_GPT` result may continue while `RECOVERY_REQUIRED` / `SEND_UNCERTAIN` / `ERROR` pause and exit.
- Acceptance: AC-PHASE45SUP-012, AC-PHASE45SUP-016
- Tasks: TASK-04

### REQ-PHASE45SUP-009 — Autonomy is bounded and limits pause the campaign

- Statement: The CLI must accept `--campaign-id`, `--milestone`, `--start-sequence`, `--start-nonce`, `--start-in-reply-to`, `--max-rounds`, `--max-wall-seconds` and `--poll-seconds` with conservative defaults, and when the maximum round count or the wall deadline is reached the Supervisor must persist `PAUSED`, set the outcome to `LIMIT_REACHED` and exit.
- Conditions: On each iteration and on every dispatch.
- Expected: No run exceeds `max_rounds` dispatches or `max_wall_seconds`; reaching either limit ends the campaign in `PAUSED` with outcome `LIMIT_REACHED`.
- Edge case: A poll interval must never be so aggressive that it becomes a busy loop, and the wall deadline is enforced even when no new response ever arrives.
- Acceptance: AC-PHASE45SUP-014, AC-PHASE45SUP-015
- Tasks: TASK-06

### REQ-PHASE45SUP-010 — The CLI exposes exactly the required status and run interfaces

- Statement: The Supervisor must implement `python3 orchestration/hermes/supervisor/campaign_cli.py status --campaign-id ID` and `python3 orchestration/hermes/supervisor/campaign_cli.py run --campaign-id ID --milestone MILESTONE --start-sequence N --start-nonce NONCE --start-in-reply-to HASH --max-rounds N --max-wall-seconds N --poll-seconds N`, where `run` stays in the foreground until `CLOSED`, `PAUSED`, a safety stop or a limit, and emits compact progress lines such as `CAMPAIGN_WAITING_FOR_GPT`, `CAMPAIGN_DISPATCH sequence=N task_id=...`, `CAMPAIGN_ROUND_COMPLETE result_sha256=...` and `CAMPAIGN_CLOSED outcome=PASS`, with no giant log-streaming framework.
- Conditions: When the CLI is invoked.
- Expected: Both subcommands exist with the exact flags; `run` blocks until a terminal campaign state and prints compact progress only.
- Edge case: `status` must report the persisted campaign state without acquiring the run lock or mutating anything.
- Acceptance: AC-PHASE45SUP-017
- Tasks: TASK-06

### REQ-PHASE45SUP-011 — The package is stdlib-only with the declared module set and no framework

- Statement: The Supervisor package must consist of `__init__.py`, `campaign_protocol.py`, `campaign_state.py`, `campaign_supervisor.py`, `campaign_cli.py` and `tests/test_campaign_supervisor.py`, must use only the Python standard library, and must not add a framework, plugin system, scheduler abstraction or configuration language beyond this single use case.
- Conditions: When the package is created and imported.
- Expected: All declared modules exist; imports are stdlib-only; no third-party dependency is required.
- Edge case: The Bridge modules are wrapped, not vendored; no Bridge source is copied into the Supervisor package.
- Acceptance: AC-PHASE45SUP-018
- Tasks: TASK-01

### REQ-PHASE45SUP-012 — Deterministic tests use injected fakes and cover the enumerated cases

- Statement: Every test must drive the Supervisor through injected or fake `read_latest_assistant`, `bridge_status`, `bridge_round` and clock/sleep seams, with no real Chrome, no real ChatGPT, no real Hermes and no live Bridge state, and must cover at least: same response never dispatched twice; a new exact expected task invokes the Bridge exactly once; sequence / nonce / in_reply_to mismatch pauses without invoking the Bridge; a control-free assistant response is marked seen and ignored; a malformed task pauses fail-closed; an ambiguous task pauses fail-closed; a valid campaign `PASS` closes without a Bridge call; a campaign with the wrong id is rejected; a campaign with the wrong milestone is rejected; a campaign with a stale in_reply_to is rejected; a response with both a task and a campaign terminal is rejected; `AWAITING_APPROVAL`, `RECOVERY_REQUIRED`, `SEND_UNCERTAIN` and `ERROR` each pause; `max_rounds` pauses; `max_wall_seconds` pauses; a restart uses the persisted seen hash and does not duplicate dispatch; pending-result startup reconciliation calls the Bridge once; a successful reconciliation resumes waiting; the campaign lock prevents two workers; and state/journal persistence survives a restart.
- Conditions: When the Supervisor test suite is run.
- Expected: All enumerated cases pass offline and deterministically; no test opens a browser, a network socket or a live Bridge state directory.
- Edge case: The Bridge's own existing tests are not re-run except a read-only import-compatibility check if strictly required.
- Acceptance: AC-PHASE45SUP-019, AC-PHASE45SUP-020
- Tasks: TASK-07

### REQ-PHASE45SUP-013 — One combined verification writes compact evidence

- Statement: After implementation the Supervisor must be verified by ONE combined deterministic verification that confirms the unit tests pass, the exact CLI help/interface exists, campaign protocol strictness passes, persistence/restart passes, duplicate prevention passes and bounded limits pass; and it must write `verification.json` and `supervisor-tests.log` under `orchestration/hermes/evidence/campaign-supervisor/`, where `verification.json` records `verdict`, `bridge_modified`, `sequence_5_consumed` and `m5_manifest_unchanged`. The verification must also prove the Bridge files are byte-identical to their pre-run hashes, the Specification Compiler files and the M5 contract manifest are unchanged, live Bridge sequence 5 is still unconsumed, and no live browser send, no Bridge round and no KeepLab write occurred.
- Conditions: When the single combined Supervisor verification runs.
- Expected: Evidence exists; `verdict` is `PASS`; `bridge_modified` is `false`; `sequence_5_consumed` is `false`; `m5_manifest_unchanged` is `true`.
- Edge case: If verification fails, only the failed item is repaired and only the invalidated work is re-run; PASS is followed by an immediate stop with no post-PASS exploration.
- Acceptance: AC-PHASE45SUP-021
- Tasks: TASK-08
