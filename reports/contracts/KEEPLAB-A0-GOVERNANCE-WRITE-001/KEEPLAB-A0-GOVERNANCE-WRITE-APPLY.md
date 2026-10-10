# KEEPLAB-A0-GOVERNANCE-WRITE-APPLY

**Execution prompt — future task. NOT executed by the contract-creation phase.**

| | |
|---|---|
| Contract | `KEEPLAB-A0-GOVERNANCE-WRITE-001` |
| Contract package | `/mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack/reports/contracts/KEEPLAB-A0-GOVERNANCE-WRITE-001` |
| Package declaration | `CONTRACT_PACKAGE: READ_ONLY_INPUT` |
| Phase | `A0_GOVERNANCE_WRITE` |
| Human authorization | D-15 `YES_BOUNDED_ACCOUNT_NETWORK_UNLOCK` (+ D-02/D-03/D-07/D-08/D-09), 2026-10-06 |
| Stops after | A0. **A1 and A2 must not start.** |

---

## 0. Prohibitions that bind every step

- Do **not** modify the contract package. It is `READ_ONLY_INPUT`.
- Do **not** modify `contract_guard.py`, the hook configuration, Hermes core, the active
  frozen P0B-CLOSE contract, or any project-wide guard default.
- Do **not** disable, patch, bypass or skip the guard; do not rename files to evade
  classification; do not write outside the project and copy back.
- Do **not** broaden this contract's allowed paths. Needing a path it does not grant is a
  STOP and a new human-approved contract.
- Do **not** touch `KeepLab-Relay/app/**`, Gradle files, `.factory/**`, `HANDOFF.md`,
  `AGENTS.md`, the frozen P0B packages, `Testapp/`, `PowerAi/`, `KeepLab-Relay-evidence/`,
  the frozen `verification/**` subtrees, or the Android device.
- Do **not** start A1 or A2, and do **not** resolve D-14.

---

## 1. Activate the contract (same guard, different package)

The Contract Guard resolves its package as
`os.environ.get("HERMES_CONTRACT_PACKAGE") or DEFAULT_PACKAGE`. The hook subprocess
inherits the Hermes process environment, so point the Hermes process at this package
**before** starting the apply session:

```bash
export HERMES_CONTRACT_PACKAGE=/mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack/reports/contracts/KEEPLAB-A0-GOVERNANCE-WRITE-001
```

Verify activation:

1. Load the guard module (`orchestration/hermes/evaluation_adapter/contract_guard.py`) and
   call `load_contract(package_dir)`; assert `contract_id == "KEEPLAB-A0-GOVERNANCE-WRITE-001"`
   and `integrity == "MANIFEST_OK"`. Anything else is `INVALID_CONTRACT` → STOP.
2. Assert the guard source is unmodified:
   `sha256(contract_guard.py) == e418fc28b08ac7afe4fdd42ec44d572ddaa2f23f6200de300ecac211404b3746`.
   A different hash means the contract was validated against a different guard → STOP.
3. Confirm the hook config still wires the same fail-closed `pre_tool_call` hook.

## 2. Verify the contract package is intact

Re-hash every entry of the package `manifest.json` and compare. A mismatch or a missing
artifact is `CONTRACT_PACKAGE_TAMPERED` → STOP. Do not repair the package.

## 3. Verify the governance inputs are not stale

Re-hash and compare against `expected_before_hashes`:

| File | Expected sha256 |
|---|---|
| `KeepLab-Relay/MISSION.md` | `9e9107b1f31491b1400eaccaa3faac269c02e8b41911ef2b430d035a3ae6b06a` |
| `KeepLab-Relay/FACTORY_RULES.md` | `7e6c489751a9f4ebbeb2d91005e56aa5ee06eb80fab65b7b623218f49ea268d1` |
| `KeepLab-Relay/specs/google-keep-parity/ROADMAP.md` | `58d6505b1456ac2ee1e0463317894ea10fc0e50d7e10fbf353b88373d9cb0d47` |

Any drift → STOP with **`STALE_GOVERNANCE_INPUT`**. Never re-baseline the expected hashes
to match the filesystem, and never silently patch a newer or different file.

## 4. Read the human-approved A0 records

Read, and treat as the authoritative amendment text:

- `orchestration/hermes/evidence/keeplab-human-architecture-decisions-a0/human-approval.json`
- `orchestration/hermes/evidence/keeplab-human-architecture-decisions-a0/governance-amendment-proposal.json`
- `orchestration/hermes/evidence/keeplab-human-architecture-decisions-a0/governance-diff.json`
- `orchestration/hermes/evidence/keeplab-human-architecture-decisions-a0/verification.json`
- `reports/KEEPLAB-A0-BOUNDED-ACCOUNT-NETWORK-GOVERNANCE.md`

Record the live `sha256` + `mtime` of each of the three governance files as the
pre-apply snapshot.

## 5. Apply the minimal approved governance changes

### 5.1 `KeepLab-Relay/MISSION.md` — supersede the absolute prohibition

Apply exactly the proposal's amendments `seq 1..4`:

- Hard invariant 1: replace the absolute "Local-first, no network" wording with the
  versioned **`BOUNDED_ACCOUNT_NETWORK_POLICY`** (invariant v2, 2026-10-06), preserving:
  LOCAL_FIRST mandatory; account optional for local notes; network optional for local
  notes; offline read mandatory; offline write mandatory; existing local notes protected
  (never silently assigned, uploaded, deleted or merged into an account); Room remains the
  local SSOT and the device remains the UI source of truth; remote sync optional and never
  the canonical UI data source; Google/Firebase identity forbidden unless separately
  human-approved.
- The "Sync and identity" out-of-scope entry: narrowed to "*outside an explicitly
  human-approved, phase-gated contract* (optional extension; never required for local use)".
- Allowed evolutions: append the bounded account/network phase entry.
- Governance-change note: record that changing invariant 1 now requires a human commit
  carrying the D-15 bounded scope and limits.

### 5.2 `KeepLab-Relay/FACTORY_RULES.md` — conditional, expected byte-identical

Change it **only if** its current text categorically prohibits account/network work.
The reviewed text does not. If no categorical conflict is present, **leave the file
byte-identical** and record `FACTORY_RULES_AMENDMENT_REQUIRED: false`. If an amendment
does turn out to be required, it must be minimal and must preserve irreversible-change
protection, human-approval requirements, the fail-closed guard, the no-silent-data-loss
rule and the phase/contract gates.

### 5.3 `KeepLab-Relay/specs/google-keep-parity/ROADMAP.md` — one status update

Apply the proposal's `seq 6`: set the RISK-GOV-001 **account/network** governance status to
`RESOLVED_BY_BOUNDED_HUMAN_UNLOCK` with date `2026-10-06`, approved decision
`D-15 = YES_BOUNDED_ACCOUNT_NETWORK_UNLOCK`, scope "account/network architecture phases
only", limits "phase-gated · local-first · own-backend · no Google/Firebase by default",
and an explicit residual naming P3-large-screen, P4-rich-text, P5-attachments/link and
P7-ecosystem as still gated by their own items.

**No unrelated roadmap risk, phase, matrix ID or sequencing line may change.**

## 6. Verify the result

1. **Semantic diff.** MISSION.md declares the bounded policy and still declares every
   preserved property in §5.1; FACTORY_RULES.md is byte-identical unless a categorical
   conflict was found and recorded; ROADMAP.md changed only inside RISK-GOV-001's
   account/network status.
2. **Byte diff.** Record `sha256` + `mtime` for all three files after the write and assert
   that no *other* file changed: re-scan `KeepLab-Relay/app/**`, `KeepLab-Relay/**/*.gradle*`,
   `.factory/**`, the frozen P0B packages, `Testapp/`, `PowerAi/`, `KeepLab-Relay-evidence/`,
   the frozen `verification/**` subtrees and `contract_guard.py` and record zero changes.
3. **No implementation content.** Confirm the diff introduces no endpoint, schema, vendor
   sub-choice or stack detail beyond the already-approved D-07/D-08/D-09 values.
4. **Governance agreement.** Confirm MISSION.md and ROADMAP.md agree on the bounded policy;
   disagreement is `GOVERNANCE_INCONSISTENT` → STOP.
5. **Package untouched.** Re-verify the package manifest — the apply session must not have
   written into its own contract.

## 7. Evidence and status

Write to `orchestration/hermes/evidence/keeplab-a0-governance-write/` (and a report under
`reports/`): `pre-apply-hashes.json`, `package-integrity.json`, `guard-activation.json`,
`governance-diff-applied.json`, `post-apply-hashes.json`, `unchanged-scope-scan.json`,
`verification.json`.

Set **A0 = READY** only after the three canonical governance files agree and §6 passes.

Report afterwards:

```
A0: READY
A1: READY_FOR_SEPARATE_CONTRACT
A2: READY_FOR_SEPARATE_CONTRACT
A3: BLOCKED_BY_HUMAN_DECISIONS
D-01 / D-04 / D-10: PENDING
D-14: HUMAN_DECISION_PENDING
IMPLEMENTATION_AUTHORIZATION_MODEL: PHASE_GATED
IMPLEMENTATION_AUTHORIZATION: NOT_GRANTED
```

## 8. Stop

Stop after A0. Do not start A1. Do not start A2. Do not open the device. Do not touch
product source, Gradle, Room, backend, Docker, PostgreSQL or any cloud resource.
