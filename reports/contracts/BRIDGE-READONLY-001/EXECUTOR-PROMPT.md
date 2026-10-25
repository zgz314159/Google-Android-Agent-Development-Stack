# EXECUTOR PROMPT — BRIDGE-READONLY

You are the execution agent for a FROZEN Implementation Contract. Work from the contract
and the listed `read_first` files. Do not re-do reconnaissance, re-choose architecture, or
re-plan decisions this contract has already frozen.

## 0. Verify the frozen contract
- Contract: `implementation-contract.json` (contract_id `BRIDGE-READONLY-001`, version `0.1.0`)
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
- Read only these 1 `read_first` files:
  1. project/README.md
- Extend to a targeted search ONLY for `CONTRACT_GAP`, `CONTRACT_CONTRADICTION`, a missing
  dependency, or compile evidence that requires one extra file. Record `EXTRA_RECON_REASON`
  (file + why) for every extension.

## 3. Execute tasks in dependency order
  TASK-01  Run `id -un`, `pwd`, `git rev-parse HEAD` and `uname -s` in `/var/tmp/BRIDGE-READONLY-001/project`; write exactly four labeled lines to `EVIDENCE.txt` in this order: `id -un: <actual>`, `pwd: <actual>`, `git rev-parse HEAD: <actual>`, `uname -s: <actual>`; no other lines or files.  (depends: none)

## 4. Boundaries
Allowed paths:
  - project
Forbidden paths:
  - (none declared)
Frozen decisions (do not reopen): DEC-001, DEC-002.

## 5. If the contract is wrong
If a contract fact contradicts the source, a required file is missing, an assumption is
wrong, an acceptance is impossible, or a boundary is unsafe:
  STOP → emit `CONTRACT_DEVIATION` with evidence. Do NOT silently redesign.

## 6. Verify and hand off
1. Run every CLI check below exactly as declared, in order.
2. Record the actual command, actual output, expected result and failure condition in `EVIDENCE.txt`.
3. A zero process exit alone is NOT a PASS; the expected result must be observed in the actual output.
4. If any check fails: STOP, record the failure, and do not synthesize or repair evidence.
5. On PASS: make NO further tool call, search, read, audit, repeated verification or exploratory check. Produce the Phase C report in the FINAL ASSISTANT RESPONSE using only evidence already collected in this session, emit the compact final task result, and STOP immediately.

CLI checks:
  - identity: `id -un` — expected: aegl-ai; on failure: stop; record the actual command, exit code and output; do not synthesize EVIDENCE.txt
  - worktree: `pwd` — expected: /var/tmp/BRIDGE-READONLY-001/project; on failure: stop; record the actual value; do not synthesize EVIDENCE.txt
  - revision: `git rev-parse HEAD` — expected: the frozen task commit recorded in PREP-BINDING.json under the trusted contract package; the contract must not embed its own commit SHA; on failure: stop; record the actual command, exit code and output; do not synthesize EVIDENCE.txt
  - operating-system: `uname -s` — expected: Linux; on failure: stop; record the actual value; do not synthesize EVIDENCE.txt
  - evidence: `test -s EVIDENCE.txt && cat EVIDENCE.txt` — expected: exactly four labeled lines in this order, with no extra lines: `id -un: aegl-ai`, `pwd: /var/tmp/BRIDGE-READONLY-001/project`, `git rev-parse HEAD: <PREP-BINDING.json commit>`, `uname -s: Linux`; on failure: stop; record the failure; do not synthesize or repair EVIDENCE.txt

After this session (POST-SESSION observers, not in-session steps):
- `on_session_finalize` / Auto-Finalizer are POST-SESSION observers.
- Do NOT invoke, inspect, wait for, or verify Auto-Finalizer from inside this Hermes session.
- Auto-Finalizer runs only AFTER this Hermes session exits and is NOT an in-session acceptance
  criterion.

## Stop conditions
  - Any write outside the disposable worktree: STOP, CONTRACT_DEVIATION.
  - Any synthesized or missing evidence: STOP, EVIDENCE_MISSING.
  - Any formal source, contract, compiler, guard, launcher, profile or host change: STOP, ABSOLUTE_BLOCK_VIOLATION.
