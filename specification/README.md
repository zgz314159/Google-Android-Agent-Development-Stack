# Specification & Design Compiler Layer — P0

**Version:** 0.1.0 · **Status:** READY

A thin, offline, deterministic layer that compiles a change request into an
**Android Implementation Contract**: a package of plain files that a downstream
execution agent can read and act on without re-doing reconnaissance, re-choosing
architecture, or re-planning.

This is **not** a framework. It is: collect → normalize → cross-reference → validate →
freeze → package.

## What it is

```
change request ──▶ spec-package/ ──▶ deterministic validation ──▶ Implementation Contract
                                                                        │
                                                                  READY / NOT READY
```

The package (see `contracts/`) is:

```
spec-package/
├── PRODUCT.md                # what the product is, the change, scope & non-goals
├── requirements.md           # ID'd requirements (what, not how)
├── design.md                 # implementation architecture + File Structure Plan
├── tasks.md                  # 5–8 dependency-ordered tasks with boundaries
├── DESIGN.md                 # UI / visual / interaction ground truth
├── acceptance.md             # ID'd, deterministic PASS definitions
├── project-context.json      # read_first + relevant/forbidden paths + toolchain
├── verification-intent.json  # spec→verification bridge
├── implementation-contract.json   # the compiled contract (generated)
├── manifest.json             # sha256 of every authored artifact (generated)
└── READY.json                # readiness gate result (generated)
```

`EXECUTOR-PROMPT.md` is generated alongside the contract for the next session.

## What is deterministic

`compiler/build_contract.py` and `compiler/validate_package.py` never call an LLM,
never touch the network, and never guess missing content. Given the same inputs they
produce byte-identical outputs. The validator declares **stable rule ids** (e.g.
`E_HASH_MISMATCH`, `E_READ_FIRST_MISSING`) so a failure names its exact reason.

The LLM/human role is to *author* the plain-language artifacts. The compiler only
collects, normalizes, cross-references, validates, hashes and freezes them.

## Usage

Python 3, standard library only (no pip, no venv — same convention as `evaluation/`).

```bash
P=specification/compiler

# 1. hash every authored artifact into manifest.json
python3 $P/hash_manifest.py <spec-package-dir>

# 2. compile the implementation contract (+ EXECUTOR-PROMPT.md)
python3 $P/build_contract.py <spec-package-dir>

# 3. validate all gates and emit READY.json
python3 $P/validate_package.py <spec-package-dir> --project-root <project-root>
#    exit 0 = READY, 1 = NOT READY, 2 = error
```

Self-tests:

```bash
python3 -m unittest discover -s specification/tests -v
```

## Design invariants

- **Offline & portable.** Plain files, `python3`, stdlib only.
- **Deterministic validation.** No LLM, no network, no inferred content.
- **READY requires all gates PASS.** `unresolved_questions` must be empty for READY.
- **Freeze by hash.** READY records the contract + manifest + artifact hashes; a
  downstream executor verifies them and stops with `CONTRACT_CHANGED` if they differ.
- **Brownfield first.** `mode = brownfield`: the contract *reuses* existing mechanisms
  and forbids rebuilding them. Greenfield is an extension point (`docs/ARCHITECTURE.md`).
- **Optional visual layer.** Stitch screens / AI Studio reference APK are declared with
  an explicit `not_required` value — never left for an agent to guess. See
  `docs/BROWNFIELD-INTEGRATION.md`.

## Layout

```
specification/
├── VERSION
├── contracts/     JSON Schemas: implementation-contract, readiness, package-manifest
├── templates/     authoring skeletons for the six markdown artifacts
├── compiler/      spec_lib.py (shared core) + hash_manifest / build_contract / validate_package
├── tests/         stdlib unittest + fixtures (positive and negative)
└── docs/          ARCHITECTURE.md, BROWNFIELD-INTEGRATION.md
```

See `docs/ARCHITECTURE.md` for the design and `docs/BROWNFIELD-INTEGRATION.md` for how a
brownfield Android project produces a package.
