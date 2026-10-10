# DeepSeek task: migrated Hermes stack audit and safe recovery

You are operating on a project copied from another Ubuntu computer. Work as a migration-recovery
engineer, not as a feature developer. First understand the whole system, then make only the safe
repairs explicitly authorized below, verify them once, and return a compact evidence-backed report.

## Current host and known facts

- Current projects root: `/home/zhong/Projects`
- Stack root: `/home/zhong/Projects/Google-Android-Agent-Development-Stack`
- Product root: `/home/zhong/Projects/KeepLab-Relay`
- Command Code 1.74.1 is authenticated and `deepseek/deepseek-v4.1-flash` is available.
- KeepLab Android currently builds, its 183 tests pass, and the debug APK has been installed and
  launched on the attached Sony XQ-DQ72.
- KeepLab backend currently builds; 97 tests pass; `/health` was verified with HTTP 200.
- Bridge unit tests currently pass 85/85; Supervisor tests pass 32/32.
- The copied Stack root has no `.git` directory.
- `/home/zhong/.hermes/hermes-agent` is absent.
- The old dedicated Chrome profile and the planned Playwright runtime/state directories are absent.
- `orchestration/hermes/browser/` is absent: Phase 4.6 Playwright transport migration was not
  implemented on this copy.
- Live source still hard-codes `/mnt/AndroidDev/Projects` and still requires raw CDP on port 9333.
- The original old-host bridge incident was sequence 5 / ERROR with a pending result for
  `KEEPLAB-M5-A8-EXECUTE-005`. The copied host-local bridge state was not present. A diagnostic
  `bridge_cli.py status` on this machine lazily created a fresh sequence-1 IDLE state at
  `~/.local/state/hermes-chatgpt-bridge`; this fresh state is NOT authoritative recovery state and
  MUST NOT be used to start a new campaign.
- Historical evidence and Command Code transcripts may contain proof of the former sequence-5
  state under:
  - `/home/zhong/Projects/_evaluation/_hermes_staging/`
  - `orchestration/hermes/evidence/phase45-incident-recovery/`
  - other copied evidence under `orchestration/hermes/evidence/`

## System architecture to preserve

The intended closed loop is:

`ChatGPT control conversation -> Campaign Supervisor -> Bridge -> Hermes upstream -> Command Code
provider -> DeepSeek -> deterministic verification -> HERMES_RESULT_V1 -> ChatGPT`

Preserve the existing strict `HERMES_TASK_V1` / `HERMES_RESULT_V1` protocol, Contract Guard,
append-only journal semantics, one-send/no-blind-resend rule, and Supervisor architecture.

The planned Phase 4.6 direction is:

`Supervisor -> Bridge -> Unix socket -> Playwright-owned persistent Google Chrome -> ChatGPT Web`

Raw CDP/9333 may remain only as an explicit manual fallback. There must be no automatic fallback.

## Absolute prohibitions

Do NOT:

1. run `bridge_cli.py round`, `recover`, or `resolve-send-uncertain`;
2. run `campaign_cli.py run`;
3. send, type, or resend anything in ChatGPT Web;
4. consume or fabricate sequence 5 or sequence 6;
5. treat the newly created sequence-1 state as canonical;
6. reconstruct state from guesses, partial prose, or hashes alone;
7. run either old `/tmp/phase46-*.sh` script;
8. create `/mnt/AndroidDev` compatibility symlinks to hide portability defects;
9. delete or overwrite copied evidence, logs, state, browser profiles, or user data;
10. initialize Git, create commits, install Docker, or change OS-wide settings;
11. print, copy, or include secrets/API keys/cookies in output;
12. modify KeepLab product code, governance files, frozen protocol semantics, or historical evidence.

## Phase A — mandatory audit before edits

Read at minimum:

- `orchestration/hermes/README.md`
- `orchestration/hermes/INTEGRATION.md`
- `orchestration/hermes/HERMES-LOCK.json`
- `.hermes.md`
- the Bridge and Supervisor source plus their tests
- `orchestration/hermes/evidence/phase45-incident-recovery/verification.json`
- the latest relevant `_evaluation/_hermes_staging/*.jsonl` transcripts

Build an evidence table covering:

- portable repository source;
- host-local Hermes installation/configuration;
- Command Code provider availability;
- dedicated Chrome profile and login state;
- Browser Harness/raw CDP state;
- Playwright runtime/daemon state;
- Bridge state/journal/pending result;
- Supervisor state;
- Git/baseline assumptions;
- every old absolute path in live executable code/config (exclude historical evidence from repair).

Search all copied locations for an exact, byte-recoverable sequence-5 state set consisting of
`state.json`, `journal.jsonl`, and `pending_result.json`. Evidence is exact only if identity fields,
sequence, nonce, in-reply-to, result envelope, hashes, and cross-file consistency all validate
through the existing protocol code. Merely finding values in prose is not sufficient.

Before any edit, write a timestamped migration baseline under:

`reports/migration-recovery/`

Include SHA-256 hashes and copies of every live source/config file you intend to edit. Do not copy
secret files or browser data.

## Phase B — authorized safe repairs

After Phase A, you may perform only these repairs:

1. Replace old-host absolute paths in live executable source/config with paths derived from the
   current file location, the project root, `Path.home()`, or explicit environment variables.
   Preserve historical evidence unchanged.
2. Update affected unit tests so they test portable path behavior instead of requiring
   `/mnt/AndroidDev/Projects`.
3. Restore the exact pinned upstream Hermes Agent from `HERMES-LOCK.json` into the declared user
   install location, using the official upstream source and exact frozen commit. Do not patch Hermes
   core and do not auto-update beyond the lock.
4. Restore the `android-stack` Hermes profile and Command Code provider integration without exposing
   secret values. If required credentials are unavailable, report the missing credential by name
   only and stop that substep.
5. Create an isolated project-local or user-local Playwright Python runtime as required by the
   Phase 4.6 design. Use the installed Google Chrome; do not download a second Chromium build.
6. Implement the bounded Phase 4.6 Playwright transport only if the existing source/contracts and
   tests provide enough exact specification. Required capabilities are: one durable browser owner,
   persistent dedicated profile, Unix-socket client, health gate, semantic result ACK, separation of
   RESULT_DELIVERED from GPT_RESPONSE_PENDING, read-only reconcile-delivered, bounded restart, and
   30-second heartbeat. Unit tests must not require a live browser.
7. Run one coherent offline verification pass: Bridge tests, Supervisor tests, new browser transport
   tests, import/compile checks, and Hermes provider smoke only if it sends no ChatGPT Web message.

Do not start a visible browser or require a human login during this task. If profile/login creation is
the only remaining step, report it as `HUMAN_LOGIN_REQUIRED` with the exact command to run later.

## State recovery decision gate

- If an exact consistent copy of the old sequence-5 state exists, do not restore it automatically.
  Report its paths, hashes, validation result, and a proposed atomic restore command for human review.
- If exact state does not exist, report `ORIGINAL_CHAIN_STATE=NOT_RECOVERABLE_EXACTLY` and give two
  clearly separated options:
  A. abandon the old campaign and initialize a new human-approved campaign from a newly compiled
     contract;
  B. return to the old computer and export the three authoritative bridge files plus Supervisor state.
- In either case, do not advance any chain in this task.

## Verification discipline

Avoid repeated micro-tests. Perform bounded reads, one coherent implementation pass, then one final
deterministic verification pass. Do not claim PASS from file existence alone.

## Required output artifacts

Write:

- `reports/migration-recovery/DEEPSEEK-RECOVERY-REPORT.md`
- `reports/migration-recovery/deepseek-recovery-report.json`

The JSON must contain at least:

- `verdict`: `READY_FOR_HUMAN_CUTOVER`, `PARTIALLY_REPAIRED`, or `BLOCKED`
- `architecture_summary`
- `facts_before`
- `changed_files`
- `installed_runtime`
- `tests` with counts and exit codes
- `old_absolute_paths_remaining_in_live_code`
- `bridge_state_classification`
- `exact_sequence5_backup_found`
- `human_actions_required`
- `next_safe_command`
- `prohibitions_observed`

Finish the terminal response with exactly this compact block, filling real values:

```text
DEEPSEEK_MIGRATION_RECOVERY_REPORT_V1
VERDICT=<READY_FOR_HUMAN_CUTOVER|PARTIALLY_REPAIRED|BLOCKED>
STACK_ROOT=/home/zhong/Projects/Google-Android-Agent-Development-Stack
KEEP_LAB=<PASS|FAIL|NOT_RERUN>
BRIDGE_TESTS=<passed>/<total>
SUPERVISOR_TESTS=<passed>/<total>
PLAYWRIGHT_TRANSPORT=<PASS|FAIL|NOT_IMPLEMENTED>
HERMES_PINNED_RUNTIME=<PASS|FAIL|BLOCKED>
COMMANDCODE_DEEPSEEK=<PASS|FAIL|BLOCKED>
ORIGINAL_CHAIN_STATE=<EXACT_BACKUP_FOUND|NOT_RECOVERABLE_EXACTLY|INVALID>
LIVE_SEND_ATTEMPTED=NO
CHAIN_ADVANCED=NO
REPORT_MD=/home/zhong/Projects/Google-Android-Agent-Development-Stack/reports/migration-recovery/DEEPSEEK-RECOVERY-REPORT.md
REPORT_JSON=/home/zhong/Projects/Google-Android-Agent-Development-Stack/reports/migration-recovery/deepseek-recovery-report.json
NEXT_SAFE_COMMAND=<one command or HUMAN_DECISION_REQUIRED>
END_DEEPSEEK_MIGRATION_RECOVERY_REPORT_V1
```

