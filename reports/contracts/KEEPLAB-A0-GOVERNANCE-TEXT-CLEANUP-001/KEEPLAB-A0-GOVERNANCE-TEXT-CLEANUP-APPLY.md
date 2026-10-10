# KEEPLAB-A0-GOVERNANCE-TEXT-CLEANUP-APPLY

**Execution prompt — future task. NOT executed by the contract-creation phase.**

| | |
|---|---|
| Contract | `KEEPLAB-A0-GOVERNANCE-TEXT-CLEANUP-001` |
| Contract package | `/mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack/reports/contracts/KEEPLAB-A0-GOVERNANCE-TEXT-CLEANUP-001` |
| Package declaration | `CONTRACT_PACKAGE: READ_ONLY_INPUT` |
| Phase | `A0_GOVERNANCE_TEXT_CLEANUP` |
| Human authorization | D-15 `YES_BOUNDED_ACCOUNT_NETWORK_UNLOCK` (already recorded), 2026-10-06 |
| Observation | OBS-1 (residual pre-D-15 descriptive sentence in MISSION.md) |
| Stops after | A0. **A1 and A2 must not start.** |

---

## 0. Prohibitions that bind every step

- Do **not** modify the contract package. It is `READ_ONLY_INPUT`.
- Do **not** modify `contract_guard.py`, the hook configuration, Hermes core, the active
  frozen P0B-CLOSE contract, or the earlier A0 governance-write contract.
- Do **not** disable, patch, bypass or skip the guard; do not rename files to evade
  classification; do not write outside the project and copy back.
- Do **not** broaden this contract's allowed paths. Needing a path it does not grant is a
  STOP and a new human-approved contract.
- Do **not** touch `KeepLab-Relay/FACTORY_RULES.md`, `KeepLab-Relay/specs/google-keep-parity/ROADMAP.md`,
  `KeepLab-Relay/app/**`, Gradle files, `.factory/**`, `HANDOFF.md`, `AGENTS.md`,
  `FACTORY.md`, the frozen P0B packages, `Testapp/`, `PowerAi/`, `KeepLab-Relay-evidence/`,
  the frozen `verification/**` subtrees, or the Android device.
- Do **not** perform any semantic expansion of D-15 and do **not** fix any second-order
  prose inconsistency you may notice elsewhere in MISSION.md. If one seems to require a
  change, that is a STOP and a separate human-approved contract, not part of this task.
- Do **not** start A1 or A2, and do **not** resolve D-14.

---

## 1. Activate the contract (same guard, different package)

The Contract Guard resolves its package as
`os.environ.get("HERMES_CONTRACT_PACKAGE") or DEFAULT_PACKAGE`. The hook subprocess
inherits the Hermes process environment, so point the Hermes process at this package
**before** starting the apply session:

```bash
export HERMES_CONTRACT_PACKAGE=/mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack/reports/contracts/KEEPLAB-A0-GOVERNANCE-TEXT-CLEANUP-001
```

**Step 1 — verify contract id and MANIFEST_OK.** Load the guard module
(`orchestration/hermes/evaluation_adapter/contract_guard.py`) and call
`load_contract(package_dir)`; assert `contract_id == "KEEPLAB-A0-GOVERNANCE-TEXT-CLEANUP-001"`
and `integrity == "MANIFEST_OK"`. Anything else is `INVALID_CONTRACT` → STOP.

**Step 2 — verify guard hash/config.** Assert the guard source is unmodified:
`sha256(contract_guard.py) == e418fc28b08ac7afe4fdd42ec44d572ddaa2f23f6200de300ecac211404b3746`.
A different hash means the contract was validated against a different guard → STOP. Confirm
the hook config (`~/.hermes/profiles/android-stack/config.yaml`) still wires the same
fail-closed `pre_tool_call` hook and record its sha256.

## 2. Verify the contract package is intact

Re-hash every entry of the package `manifest.json` and compare. A mismatch or a missing
artifact is `CONTRACT_PACKAGE_TAMPERED` → STOP. Do not repair the package.

## 3. Verify the input is not stale

**Step 3 — verify current MISSION.md sha256.**

Re-hash and compare against the frozen post-A0 hash:

| File | Expected sha256 |
|---|---|
| `KeepLab-Relay/MISSION.md` | `f857295dd502ee64736fac04bc5e076874bcdb06a468ca1edad1eb7152d128cd` |

Any drift → STOP with **`STALE_GOVERNANCE_INPUT`**. Never re-baseline the expected hash to
match the filesystem, and never silently patch a newer or different file.

## 4. Verify the mutation is exactly the authorized one

**Step 4 — verify the old sentence occurs exactly once.**

```
OLD = "Everything lives on the device: no account, no sync, no network."
```

Assert `old_count == 1` and `new_count == 0`, where

```
NEW = "KeepLab remains local-first: local notes require no account or network; optional account and sync capabilities are allowed only inside an explicitly human-approved, phase-gated contract."
```

`0` or `>1` occurrences of OLD, or any existing occurrence of NEW, is a STOP.

Record the byte offset of the single occurrence and the line number it sits on as the
pre-apply snapshot.

## 5. Replace only that sentence

**Step 5 — replace only that sentence.**

- Replace the single OLD occurrence with NEW, **inline**, leaving every other byte of the
  file untouched. Do **not** re-flow, re-wrap or re-indent any line.
- The applied result must be exactly:

  ```
  result == original_text.replace(OLD, NEW, 1)
  ```

  Assert this before writing. If they differ, the edit is not the authorized one → STOP.

## 6. Verify the result

**Step 6 — verify the new sentence occurs exactly once.** After the write, assert
`new_count == 1` and `old_count == 0`.

**Step 7 — verify BOUNDED_ACCOUNT_NETWORK_POLICY still exists.** Assert
`"BOUNDED_ACCOUNT_NETWORK_POLICY" in mission_text`. If it is gone, the edit damaged the
authoritative policy → STOP.

**Step 8 — verify no other MISSION content changed.** Re-read the file and assert it is
byte-for-byte equal to `original_text.replace(OLD, NEW, 1)`. Diff old vs new line by line
and assert that **exactly one** line differs — the line that carried the old sentence.
Every other line, including its trailing newline, must be identical. Record
`lines_changed == 1`, `mission_bytes_delta`, and
`mission_sha256_before` / `mission_sha256_after`.

**Step 9 — verify all other protected files unchanged.** Re-hash and assert byte-identity:

| File | Expected sha256 |
|---|---|
| `KeepLab-Relay/FACTORY_RULES.md` | `7e6c489751a9f4ebbeb2d91005e56aa5ee06eb80fab65b7b623218f49ea268d1` |
| `KeepLab-Relay/specs/google-keep-parity/ROADMAP.md` | `5ab14973778852e8021ecd522237f1561221b9164e345697dab8228b2314aef2` |
| `KeepLab-Relay/HANDOFF.md` | `cc79c153e903e6be486a104e2a87170abaf67829f90d95a60f895a735457413b` |
| `KeepLab-Relay/AGENTS.md` | `41ef7ae5c5e72ae09811f55d58e51b105d8fea1ff437ac35aeca62642e73c10e` |
| `KeepLab-Relay/FACTORY.md` | `03644f960c6d6f44484f0da23d7304908e2555c219143ffc1ddd9c1d71b453db` |
| `KeepLab-Relay/build.gradle.kts` | `ba09d5f46d33a5feff2236f53f482d87f2608e7153950695bd7e1333d7c6fae8` |
| `KeepLab-Relay/settings.gradle.kts` | `6513bf224002bb5691e72e7a933ee766d2dab58c47b3d075a9fc77cd913a0ae7` |
| `KeepLab-Relay/app/build.gradle.kts` | `20dd51e5d8bb8cababcac06fecad3e9d8b5771418eb88b0ba132409c5014e298` |
| `KeepLab-Relay/gradle.properties` | `0a3448fbcc780cc608e0adaa28c10cfe77cc7ba6592da689c15ab34b70c76680` |
| `.../evaluation_adapter/contract_guard.py` | `e418fc28b08ac7afe4fdd42ec44d572ddaa2f23f6200de300ecac211404b3746` |
| `.../contracts/KEEPLAB-A0-GOVERNANCE-WRITE-001/implementation-contract.json` | `4decb2894e259aaa4eb067c426af4a3607ea18f09b531a52d53c62aea5b3d1d9` |
| `.../contracts/KEEPLAB-A0-GOVERNANCE-WRITE-001/project-context.json` | `4ca9aab711ffecba9f5ce2032f5748dbc0acc03e5660b0356f454cb3d5e3aaff` |
| `KeepLab-Relay/specs/p0b-close-benchmarkability/implementation-contract.json` | `b07a0388afdd257ee2185ca7d275f956d2a92e240d31db4904d85f3a57e65c50` |

Also re-scan `KeepLab-Relay/app/**`, `KeepLab-Relay/**/*.gradle*`, `.factory/**`, the frozen
P0B packages, `Testapp/`, `PowerAi/`, `KeepLab-Relay-evidence/`, the frozen `verification/**`
subtrees and Hermes core, and record zero changes.

**Step 10 — stop.** Do not proceed to anything else.

## 7. Evidence and status

Write to
`orchestration/hermes/evidence/keeplab-a0-governance-text-cleanup/` (and a report under
`reports/`): `pre-cleanup-hashes.json`, `package-integrity.json`, `guard-activation.json`,
`cleanup-diff-applied.json`, `post-cleanup-hashes.json`, `unchanged-scope-scan.json`,
`verification.json`.

Set the cleanup **PASS** only after §6 passes and MISSION.md and the bounded policy agree.

Report afterwards:

```
KEEPLAB-A0-GOVERNANCE-TEXT-CLEANUP-APPLY
A0: READY
OBS-1: RESOLVED
A1: READY_FOR_SEPARATE_CONTRACT
A2: READY_FOR_SEPARATE_CONTRACT
A3: BLOCKED_BY_HUMAN_DECISIONS
D-14: HUMAN_DECISION_PENDING
IMPLEMENTATION_AUTHORIZATION_MODEL: PHASE_GATED
IMPLEMENTATION_AUTHORIZATION: NOT_GRANTED
```

## 8. Stop

Stop after the cleanup. Do not start A1. Do not start A2. Do not open the device. Do not
touch product source, Gradle, Room, backend, Docker, PostgreSQL or any cloud resource.
