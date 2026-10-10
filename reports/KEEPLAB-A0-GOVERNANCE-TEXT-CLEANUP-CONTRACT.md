# KEEPLAB-A0-GOVERNANCE-TEXT-CLEANUP-CONTRACT

**Phase:** contract creation + validation. **Not** a governance mutation, **not** implementation.
**Date:** 2026-10-06 (CST) · **Task:** create and validate the narrow temporary execution
contract that closes the residual descriptive inconsistency **OBS-1**.

## 1. Result in one paragraph

`MISSION.md` already carries the authoritative `BOUNDED_ACCOUNT_NETWORK_POLICY` (invariant
v2, 2026-10-06), but one earlier descriptive sentence — *"Everything lives on the device:
no account, no sync, no network."* — still stated the pre-D-15 absolute position. It was
recorded as **OBS-1** because it fell outside the exact previously-approved amendment
sequence. A new temporary execution contract — `KEEPLAB-A0-GOVERNANCE-TEXT-CLEANUP-001` —
was authored and validated under the same already-authorized Stack reports location and the
same unmodified Contract Guard. It authorizes exactly **one** semantic sentence replacement
inside `KeepLab-Relay/MISSION.md` plus two evidence locations, blocks everything else
(including itself and the prior A0 package), freezes the post-A0 `MISSION.md` hash, and
ships an APPLY prompt that was **not** executed. **No governance file, no product source,
no guard, no hook config and no existing contract was modified.**

## 2. Why this is a separate contract

`MISSION.md` is protected by the active frozen contract `KEEPLAB-P0B-CLOSE-001`
(`forbidden_paths` lists `KeepLab-Relay/MISSION.md`), so a write to it is blocked today.
Rather than weaken that boundary, this phase reuses the already-validated mechanism from
`KEEPLAB-A0-GOVERNANCE-WRITE-001`: the same guard, pointed at a different package through
its own supported environment switch. The change is also too small to reopen the A0
governance-write contract, and the frozen decision set must not be re-opened — hence a new,
minimal contract.

## 3. Supported switch mechanism (from source, not memory)

| Question | Answer |
|---|---|
| Does a supported package override exist? | **YES** |
| Exact mechanism | `HERMES_CONTRACT_PACKAGE` environment variable |
| Guard code | `contract_guard.py:475` — `package_dir = os.environ.get("HERMES_CONTRACT_PACKAGE") or DEFAULT_PACKAGE` |
| Default package | `/mnt/AndroidDev/Projects/KeepLab-Relay/specs/p0b-close-benchmarkability` |
| CLI flag? | none — `argv` is unused |
| Per-hook `env:` key in `hooks:` config? | **not supported** |
| How the hook sees the variable | `shell_hooks._spawn` → `build_subprocess_env(...)` snapshots `os.environ`; the hook subprocess inherits the Hermes process environment |
| Guard source modified | **NO** (`e418fc28…b3746`) |
| Hook config modified | **NO** |

Activation for the future apply session:

```bash
export HERMES_CONTRACT_PACKAGE=/mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack/reports/contracts/KEEPLAB-A0-GOVERNANCE-TEXT-CLEANUP-001
```

## 4. Frozen input

| File | sha256 | State |
|---|---|---|
| `KeepLab-Relay/MISSION.md` | `f857295d…d128cd` | FROZEN post-A0, verified live, **MATCH** |
| `KeepLab-Relay/FACTORY_RULES.md` | `7e6c4897…68d1` | protected, unchanged |
| `KeepLab-Relay/specs/google-keep-parity/ROADMAP.md` | `5ab14973…4aef2` | protected (post-A0), unchanged |

The old sentence occurs **exactly once** (`MISSION.md` line 11); the new sentence occurs
**zero** times. `BOUNDED_ACCOUNT_NETWORK_POLICY` is present (line 89).

## 5. The authorized change

**Old:** `Everything lives on the device: no account, no sync, no network.`
**New:** `KeepLab remains local-first: local notes require no account or network; optional account and sync capabilities are allowed only inside an explicitly human-approved, phase-gated contract.`

Inline replacement, no re-flowing; the resulting file must equal
`original.replace(OLD, NEW, 1)`. No other line may change and no other semantic change is
authorized. D-15's meaning is unchanged.

## 6. Validation

Two independent checks were run against the **unmodified** guard:

1. **Hook-path simulation** — 31 payloads through `contract_guard.py` as a subprocess with
   `HERMES_CONTRACT_PACKAGE` selecting the package. **31/31 matched expectation** (6 ALLOW +
   23 BLOCK on the new contract, plus 2 control cases against the current contract
   confirming `MISSION.md` is blocked today and `reports/` is allowed today). No protected
   file was written.
2. **Loader validation** — the new package imported through the guard's own `load_contract`
   and `classify`: `contract_id` correct, `integrity = MANIFEST_OK`, `source_root` correct,
   3 allowed paths / 50 forbidden paths, 14 required classifications correct, and all 9
   protected reference files byte-identical.

Representative labels: `MISSION.md → ALLOW/GOVERNANCE_WRITE_TARGET`,
`reports/ → ALLOW/EVIDENCE_OUTPUT`, `FACTORY_RULES.md → BLOCK/FORBIDDEN`,
`app/src/main → BLOCK/PRODUCTION_IMMUTABLE`, the package itself →
`BLOCK/CONTRACT_PACKAGE_READ_ONLY`.

## 7. Boundaries held

No governance file, product source, Gradle file, Room schema, `.factory/**`, `HANDOFF.md`,
`AGENTS.md`, `FACTORY.md`, frozen P0B contract, prior A0 contract, guard source, hook
configuration or Hermes core was modified. No backend, Docker, PostgreSQL or cloud
resource was created. The Android device was not touched and `adb` was not run. D-14
remains `HUMAN_DECISION_PENDING`.

**Stated limitation:** the task asks to BLOCK "Hermes configuration/core". Those files live
outside the guard's `source_root` (`/home/zhong/.hermes/...`), which the guard labels
`OUT_OF_CONTRACT_SCOPE/ALLOW` by design. They cannot be blocked by a path pattern without
patching the guard (forbidden). They are therefore protected by an explicit hard
prohibition and STOP condition in the contract and APPLY prompt, and their sha256 is frozen
in the contract; the limitation is recorded rather than hidden.

## 8. Evidence

`orchestration/hermes/evidence/keeplab-a0-governance-text-cleanup-contract/` —
`current-state.json`, `before-hash.json`, `guard-loader-analysis.json`,
`guard-simulation.json`, `contract-package-manifest.json`, `apply-prompt-manifest.json`,
`verification.json`.

## 9. Next

Run `KEEPLAB-A0-GOVERNANCE-TEXT-CLEANUP-APPLY` (the authored-but-unexecuted prompt). It
stops after the cleanup. It must not start A1 or A2. A0 remains `READY`; A1 remains
`READY_FOR_SEPARATE_CONTRACT`.
