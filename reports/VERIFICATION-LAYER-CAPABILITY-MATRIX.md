# Verification Layer Capability Matrix (v1.0.0)

Proves no hardened capability was lost in the promotion from
`verification-benchmark/harness` (Harness v1.0) to `verification/` (Layer v1.0.0).

Status legend: **PORTED** (extracted + generalized + tested) · **N/A** (benchmark-only).

| Old Harness Capability | New Verification Layer Component | Test | Status |
|---|---|---|---|
| Device preflight | `android/preflight.sh` | `selftest_static` (syntax) + device smoke | PORTED |
| Fail-fast | `core/lib_common.sh` (`die`/`STAGE_FAIL`) + `runner/orchestrator.py` | `test_dry_run`, failure path via device smoke | PORTED |
| Engine isolation | `android/cleanup_engine.sh` | device smoke (`--check-only`) | PORTED |
| Deterministic IME | `android/ime.sh` | device smoke (`IME_SET`/`IME_VERIFIED`) | PORTED |
| Host/device lifecycle separation | `docs/ANDROID-LIFECYCLE-CONTRACT.md` + orchestrator | contract doc + device smoke | PORTED |
| Stable install / instrumentation runner | `android/install.sh` + orchestrator `am instrument` | device smoke | PORTED |
| UiAutomation cleanup | `android/cleanup_engine.sh` (`UIAUTOMATION_CONFLICT_SUSPECTED`) | device smoke | PORTED |
| Evidence fallback (android_cli → xml → screenshot/logcat) | `android/collect_failure.sh` + `android/evidence/layout.sh` | `test_evidence_completeness` | PORTED |
| Failure bundle completeness | `core/evidence_completeness.py` | `test_evidence_completeness` | PORTED |
| Run-state / idempotency | `runner/orchestrator.py` `RunState` + `contracts/run-state.schema.json` | `contracts`, device smoke | PORTED |
| Timeout / watchdog | `core/lib_common.sh` (`with_timeout`, `TIMEOUT_STAGE`) | `selftest_static` marker check | PORTED |
| Result schema validation | `core/schema.py`, `core/validate_result.py` | `test_schema` | PORTED |
| Selector contract | `docs/VERIFICATION-SELECTOR-CONTRACT.md` | doc + example selectors | PORTED |
| Evaluation adapter | `adapters/evaluation/verification_adapter.py` | `test_verification_adapter` | PORTED |
| Crash attribution | `core/result_emit.py` (`detect_app_crash`, package-scoped) | `test_result_emit` | PORTED |
| APK provenance | `core/provenance.py` | `test_provenance` | PORTED |
| Deterministic device-state restore | `android/lifecycle.sh` | device smoke (`LIFECYCLE_RESTORE`) | PORTED |
| Machine-readable health/report | `core/result_emit.py` + `verification-result.json` | `test_result_emit` | PORTED |
| Verification-plan contract | `contracts/verification-plan.schema.json` + `core/plan_validate.py` | `test_plan_validate` | PORTED |
| Runner entry | `runner/run_verification.sh` + `orchestrator.py` | `test_dry_run` | PORTED |
| KeepLab decoupling | `tests/unit/test_decoupling_audit.py` | audit | PORTED |
| Engine A control runner | (benchmark-only) | — | N/A |
| `stage1.sh` benchmark orchestrator | (benchmark-only) | — | N/A |
| `measure.py` aggregation | (benchmark-only) | — | N/A |
| `baseline_guard.py` frozen invariants | (benchmark-only; still runnable) | baseline guard | N/A |
| 27-run frozen baseline data | (benchmark-only) | baseline guard | N/A |

**P0 capability loss: NONE.**
