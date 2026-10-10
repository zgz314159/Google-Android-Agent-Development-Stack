# ARCHITECTURE — Specification & Design Compiler P0

## 1. Purpose

Compile a change request into an **Android Implementation Contract**: a frozen, plain-file
package a downstream execution agent can consume without re-doing reconnaissance,
re-choosing architecture, or re-planning.

The compiler is deliberately thin. It does not invent product decisions. It **collects,
normalizes, cross-references, validates, freezes and packages** artifacts that an
LLM/human authored.

## 2. The deterministic / non-deterministic boundary

| Deterministic (code) | Non-deterministic (LLM/human) |
| --- | --- |
| `hash_manifest.py` — sha256 of every authored artifact | authoring `PRODUCT.md`, `requirements.md`, … |
| `build_contract.py` — parse IDs, normalize refs, assemble the contract, render the prompt | deciding *what* the change is |
| `validate_package.py` — every gate, rule id, traceability matrix | challenge/refinement of the contract |

The compiler never calls an LLM, never touches the network, and never guesses a missing
value: a missing required input is a hard failure.

## 3. Artifact roles

| Artifact | Role | Source |
| --- | --- | --- |
| `PRODUCT.md` | product context + change request + scope/non-goals + contract metadata block | authored |
| `requirements.md` | ID'd requirements (`REQ-*`), parseable | authored |
| `design.md` | implementation architecture + File Structure Plan + design metadata block | authored |
| `tasks.md` | ID'd tasks (`TASK-*`) with `_Boundary:_` / `_Depends:_` | authored |
| `DESIGN.md` | UI / visual / interaction ground truth | authored |
| `acceptance.md` | ID'd acceptance criteria (`AC-*`) | authored |
| `project-context.json` | `read_first`, relevant/forbidden paths, toolchain, DB | authored |
| `verification-intent.json` | spec→verification bridge | authored |
| `implementation-contract.json` | the compiled contract | **generated** |
| `manifest.json` | sha256 / size / role of every authored artifact | **generated** |
| `READY.json` | readiness gate result | **generated** |
| `EXECUTOR-PROMPT.md` | the next session's startup contract | **generated** |

The two **metadata blocks** are fenced ```json blocks under `## Contract Metadata` in
`PRODUCT.md` (experiment, feature, scope, non-goals, unresolved questions) and `design.md`
(decisions, assumptions, data change, UI change, selector contract, stop conditions). They
are the only machine-readable inputs besides the two JSON artifacts; everything else is
parsed from strict markdown headings.

## 4. Pipeline

```
author 8 artifacts
   │  python3 hash_manifest.py  <pkg>      → manifest.json      (inputs only)
   │  python3 build_contract.py <pkg>      → implementation-contract.json + EXECUTOR-PROMPT.md
   ▼  python3 validate_package.py <pkg>    → validation-report.json (+ READY.json if all gates PASS)
READY  ──▶  next session reads EXECUTOR-PROMPT.md
```

`manifest.json` covers **authored** artifacts only, which breaks the chicken-and-egg with
the generated contract: the contract embeds the manifest hashes as `artifact_hashes`.

## 5. Validation gates and rule ids

| Gate | Rule ids |
| --- | --- |
| `schema` | `E_ARTIFACT_MISSING`, `E_SCHEMA_INVALID`, `E_SECTION_MISSING`, `E_CONTRACT_REF_MISSING` |
| `traceability` | `E_DUP_REQ_ID`, `E_DUP_AC_ID`, `E_DUP_TASK_ID`, `E_MISSING_DEPENDENCY`, `E_ORPHAN_ACCEPTANCE`, `E_UNRESOLVED_QUESTIONS` |
| `boundaries` | `E_MISSING_BOUNDARY`, `E_MISSING_ALLOWED_PATHS`, `E_PATH_CONFLICT`, `E_PROJECT_ESCAPE`, `E_READ_FIRST_MISSING`, `E_MISSING_SELECTOR` |
| `acceptance` | `E_AC_UNDEFINED`, `E_REQ_NO_ACCEPTANCE`, `E_AC_UNMAPPED` |
| `hashes` | `E_HASH_MISMATCH`, `E_MANIFEST_INCONSISTENT` |

Status is `READY` iff **all five gates PASS** — and, therefore, iff
`unresolved_questions == []`. `READY.json` is written only then; otherwise it is removed.
The report also carries the **traceability matrix** (`REQ → AC → TASK → PC1 step`) and the
`contract_sha256` / `manifest_sha256`.

## 6. The JSON Schema checker

`spec_lib.schema_errors` implements a small draft-07 subset (the keywords listed in
`_SUPPORTED`). A schema using an unsupported keyword raises `SchemaError` rather than being
silently ignored — the three schema files in `contracts/` stay inside the supported set.

## 7. Freeze & hand-off

After READY, the contract records `contract_version`, and the report records the contract
and manifest hashes. The next session recomputes them and stops with `CONTRACT_CHANGED`
if they differ (unless launched with `--accept-contract-update`; P0 defines the behaviour
but does not implement the flag — see `EXECUTOR-PROMPT.md`).

## 8. Extension points

- **Greenfield:** the same pipeline applies. `mode = greenfield`,
  `experiment_type = SPEC_FIRST_GREENFIELD`, `design_source` may be `stitch` /
  `ai_studio_reference`, and `data_change.schema_version_current = 0` with
  `migration_required = false`. No code path in the compiler is brownfield-specific; the
  difference lives entirely in the authored artifacts.
- **Stitch / AI Studio:** reserved manifest fields in `design.md`'s metadata block
  (`design_source`, `stitch_used`, `reference_apk`). Deferred — see
  `BROWNFIELD-INTEGRATION.md`.
- **Verification / Evaluation:** `verification-intent.json` is consumed by the Verification
  Layer (`verification/runner/run_verification.sh`) and attributed to phase T7 by the
  Evaluation Core. The compiler itself is project-agnostic.

## 9. Known limitations (P0)

- The markdown parsers are strict: a requirement/task/criterion outside the documented
  shape is invisible to the compiler (this is intentional — strict beats clever).
- `--accept-contract-update` is defined but not implemented.
- No cross-package/global index; each package is validated in isolation.
- `specification/**` is not yet a recognised phase in the Evaluation Core rule table, so
  authoring wall may classify as `UNKNOWN` (recorded as `EVALUATION_TAXONOMY_GAP`).
