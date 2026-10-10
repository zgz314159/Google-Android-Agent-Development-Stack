# FINAL — Verification Layer v1.0.1

Generated: 2026-10-04 · Root: `/mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack`
Layer: **v1.0.0 → v1.0.1** · Scope: Verification correctness / integration hardening
Baseline: KeepLab Experiment B1 (PASS) · Evaluation Core v0.2.3 (frozen, unchanged)

This round fixes the two correctness/integration problems B1 exposed and adds a generic
project bootstrap. It does **not** start B2, Phase D, a Specification Compiler v0.2, T2
optimization, or Stitch integration.

---

## 1. Problem A — false PASS (fail-open) — FIXED

B1 verification run #2: the journey inherited `JourneyBase.verify()`, which returned a
hard-coded `PASS`. No `verify-part.json` was produced (`database.checked = false`), yet the
whole run was reported **PASS**. That is fail-open.

**First principle applied:** absence of required evidence ≠ PASS.

Two independent, defense-in-depth fixes:

1. **Host evidence gate** (`core/result_emit.py`). On PASS derivation, for a run that
   requires a terminal oracle, the gate requires **all** of:
   - `bench/verify-part.json` exists,
   - it is valid JSON,
   - `database.checked == true`,
   - oracle `outcome == "PASS"`,
   - `database.outcome == "PASS"`.

   Any gap ⇒ `outcome = FAIL` and `failure.marker ∈ {REQUIRED_VERIFICATION_EVIDENCE_MISSING,
   VERIFICATION_EVIDENCE_SCHEMA_INVALID, VERIFICATION_ORACLE_FAIL}`, **plus a mechanically
   produced failure bundle** (`failure/failed-assertion.json` + `failure/gate.json`) that the
   normal collector completes and validates — no later human inspection required.

   What counts as "requires an oracle": `engine == uiautomator`, or any plan declaring an
   `oracle`, unless the plan explicitly sets `"require_verify_part": false`. **Fail-closed by
   default**, explicit opt-out only.

2. **`JourneyBase.verify()` default is FAIL** (`android/uiautomator/JourneyBase.kt`). An
   un-overridden `verify()` returns `outcome=FAIL` with `error="verify() not implemented…"`,
   never PASS. (It is kept `open` rather than `abstract` so the supported separate-`oracle`
   path still compiles, but it can no longer mint a PASS.)

Covered by `tests/unit/test_fail_closed.py`: missing verify-part → FAIL; malformed → FAIL;
`database.checked=false` → FAIL; oracle FAIL → FAIL; genuine complete evidence → PASS;
explicit opt-out → PASS; UI failure still → FAIL.

## 2. Problem B — shell exit-code integrity — FIXED

B1 used `./gradlew … 2>&1 | tail -40`; the pipeline status became `tail`'s `0`, hiding a real
failure from the Evaluation layer.

- New generic helper `core/run_capture.sh <log> <cmd…>`: runs the command, captures the
  **real** exit status, writes the full output to `<log>`, renders the tail separately, and
  exits with the command's status (never tail's).
- Guidance: `docs/INTEGRATION-GUIDE.md` now bans `cmd | tail` in build/test/verification
  examples and shows both `set -o pipefail` and `run_capture.sh`.
- The layer's own stages already used captured return codes (`orchestrator.run_stage` →
  subprocess `returncode`); the shell helpers already `set -euo pipefail`.

Covered by `tests/unit/test_exit_integrity.py` (upstream rc=7 preserved; zero preserved;
`false | tail` demonstrates the mask while `set -o pipefail; false | tail` restores it; a
static guard asserts no layer helper runs its primary command as `… | tail`).

## 3. Project integration bootstrap — ADDED

New `integration/android-project/bootstrap_project.py` (+ README). It:
1. validates the project (Android Gradle module + `app/src/androidTest`),
2. installs the layer's **pinned, generic** device-side support into
   `app/src/androidTest/java/dev/androidstack/verification/`
   (`TimingLogger`, `JourneyBase`, `UiDriver`, `FailureBundleRule`),
3. ensures `androidTestImplementation("androidx.test.uiautomator:uiautomator:2.4.0")`
   without duplicating an existing coordinate or version-catalog alias,
4. emits `.verification/integration-manifest.json` — layer version, per-file sha256,
   source/destination paths, dependency action.

Guarantees: **idempotent** (fresh → `INSTALL`; second run → `NO-OP`, nothing rewritten);
**non-destructive** (a project-edited file is reported `INTEGRATION_DRIFT` and left as-is);
**no business semantics** — the fixture, journey, DB oracle, selectors and acceptance stay
with the Specification Contract + the project.

Covered by `tests/unit/test_bootstrap_project.py`: fresh install; idempotent second run with
no duplicate dependency; drift detected and not overwritten; invalid project rejected; alias
present ⇒ `PRESENT`.

## 4. Files changed (Verification Layer only)

| File | Change |
| --- | --- |
| `VERSION` | `1.0.0` → `1.0.1` |
| `core/result_emit.py` | fail-closed evidence gate + mechanical gate bundle |
| `core/plan_validate.py` | validate optional `require_verify_part` |
| `core/run_capture.sh` | **new** exit-code-preserving runner |
| `core/lib_common.sh` | version comment |
| `contracts/verification-plan.schema.json` | optional `require_verify_part` |
| `android/uiautomator/JourneyBase.kt` | `verify()` default → FAIL |
| `runner/orchestrator.py` | recognise the new gate markers |
| `integration/android-project/bootstrap_project.py` | **new** |
| `integration/android-project/README.md` | **new** |
| `tests/unit/test_fail_closed.py` | **new** |
| `tests/unit/test_exit_integrity.py` | **new** |
| `tests/unit/test_bootstrap_project.py` | **new** |
| `tests/smoke/selftest_static.sh` | compiles `integration/`, validates all example plans |
| `README.md`, `docs/INTEGRATION-GUIDE.md` | fail-closed / bootstrap / exit-integrity docs |
| `examples/keeplab/verification-plan.physical-b1.json` | **new** physical smoke plan (project-coupled, in the excluded reference dir) |

## 5. Tests

`verification/tests/smoke/selftest_static.sh` → **`SELFTEST_STATIC=PASS`**

- unit suite: **57 tests, 0 failures** (38 previous + 19 new)
- example plans (3) validate; decoupling audit PASS; timeout/watchdog PASS.

## 6. Physical device closure smoke

The B1 closure had run on `emulator-5554` (API 37) and therefore was **not** a physical-device
proof. A single reference smoke closes that gap, reusing the **completed B1 APK/test APK
unchanged** (app `617913…`, test `f010b9…`) and the production layer.

- Plan: `verification/examples/keeplab/verification-plan.physical-b1.json`
  (`verification_id = KEEPLAB-PIN-NOTES-B1-PHYSICAL`, `measurement_class = diagnostic`,
  `excluded_from_baseline = true`).
- Device: **`87296ada` — Redmi Note 7 Pro, API 36**.
- Engine: **uiautomator**, journey **PC1-PIN-NOTE**.

**Result: PASS** (`verification/.runs/KEEPLAB-PIN-NOTES-B1-PHYSICAL/verification-result.json`)

```
outcome              PASS
verification_layer   1.0.1
engine               uiautomator
device               {'serial': '87296ada', 'model': 'Redmi Note 7 Pro', 'api': '36'}
ui.reachable         true
database.checked     true    database.outcome PASS   (7/7 oracle checks)
process              crashed=false executor_ok=true
visual               failure-only, 0 screenshots   → zero visual LLM judgement
total_wall_ms        23253   (t7a 1256.5 / t7b 10503.5 / t7c 8895.4)
```

The same 7 on-device SQLite/Room checks passed as in B1: schema-version 2, note count
preserved, target pinned in SQLite, ordering counterparts unpinned, archive/restore preserves
pin.

## 7. Frozen layers

| Layer | Touched? |
| --- | --- |
| `specification/**` | NO |
| `evaluation/**` (Evaluation Core v0.2.3) | NO |
| `verification-benchmark/**` | NO |
| B1 product implementation (KeepLab) | NO — APKs byte-identical (`617913…`, `f010b9…`) |
| B1 frozen contract | NO — sha256 unchanged (`1ddcb5…`, `ee6c32…`) |
| Testapp / PowerAi | NO |

Changed area is `verification/**` only.

## 8. Evaluation

Evaluation Core **v0.2.3** is frozen and untouched. The Auto-Finalizer (systemd `--user`
timer, operational) records this task normally; no manual `analyze_session.py` run.

## 9. Final gate

```
VERIFICATION LAYER v1.0.1
=========================

FAIL-CLOSED DEFAULT:
PASS

MISSING VERIFY:
FAILS CLOSED

MISSING VERIFY-PART:
FAILS CLOSED

DATABASE CHECK REQUIRED:
ENFORCED

ORACLE FAILURE:
PROPAGATES

GENUINE PASS:
PASS

PIPELINE EXIT INTEGRITY:
PASS

PROJECT BOOTSTRAP:
PASS

BOOTSTRAP IDEMPOTENT:
PASS

INTEGRATION DRIFT:
DETECTED

B1 PRODUCT MODIFIED:
NO

B1 CONTRACT MODIFIED:
NO

SPECIFICATION LAYER MODIFIED:
NO

EVALUATION CORE MODIFIED:
NO

PHYSICAL DEVICE:
87296ada

PHYSICAL PC1:
PASS

DATABASE ORACLE:
PASS

VISUAL LLM JUDGEMENT:
0

VERIFICATION VERSION:
1.0.1

PHYSICAL DEVICE CLOSURE:
PROVEN

STATUS:
READY

REPORT:
/mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack/reports/FINAL-VERIFICATION-LAYER-v1.0.1.md
```

Stop. B2 is not started.
