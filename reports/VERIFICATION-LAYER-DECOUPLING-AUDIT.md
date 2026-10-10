# Verification Layer Decoupling Audit

Proves the production Verification Layer is free of KeepLab identity and business semantics.
Enforced by `verification/tests/unit/test_decoupling_audit.py` (runs in `selftest_static.sh`).

Date: 2026-10-03 · Layer: `verification/` v1.0.0

## Result

```
DECOUPLING_AUDIT=PASS
```

## Method

Scans every text file under `verification/` (`.sh .py .json .md .kt .yaml .yml`), **excluding**
`examples/`, `challengers/`, `tests/`, `.runs/`, `.state/`, `__pycache__/`, for:

| Token class | Pattern |
|---|---|
| KeepLab package | `com\.keeplab` |
| KeepLab database | `keeplab\.db` |
| KeepLab fixtures | `VC-J[123]-` |
| benchmark run ids | `HARDEN-[BC]-` |
| KeepLab business literals | `"(Work\|Archive\|Trash)"` |

Any hit in the production tree fails the audit.

## Findings

- Production core (`core/`, `runner/`, `adapters/`, `contracts/`, `android/*.sh`,
  `android/uiautomator/*.kt`, `integration/`) contains **no** KeepLab hardcodes.
- `examples/keeplab/` (reference only) is the single place KeepLab identity is allowed, and it
  also carries the migrated Kotlin sources.
- `docs/ARCHITECTURE.md` references the benchmark harness by *file name* in its migration
  mapping (`run_engine_b.sh`, …) but contains no `com.keeplab` / `keeplab.db` / `VC-*` /
  `HARDEN-*` tokens.

## Notes

- Generic identifiers such as `J1` appear only as *plan/example journey ids* and in the
  benchmark-only migration mapping; they carry no KeepLab business semantics.
- The benchmark harness `verification-benchmark/` intentionally still contains KeepLab
  references — it is historical evidence, not production.

## Conclusion

`KEEP LAB DECOUPLING = PASS`.
