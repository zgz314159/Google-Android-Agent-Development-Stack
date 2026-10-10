# Verification Compression Benchmark

P0 study: replace `Agent → tap → screenshot → model inspect` with batch, deterministic,
failure-only verification, and quantify the T7 compression on a physical Redmi Note 7 Pro.

Start at **`reports/FINAL-VERIFICATION-COMPRESSION-BENCHMARK.md`**.

## Layout

```
benchmark-apk.json                  frozen app APK identity (sha256, package, copy)
frozen/app-debug-frozen.apk         the exact APK A/B/C installed
journeys/J1..J3-*.md                journey definitions + real-UI mapping
maestro/J1..J3.yaml                 Engine C flows (+ INTENTIONAL-FAIL.yaml)
harness/run_engine_b.sh             Engine B run (fixture → seed → measure → collect)
harness/run_engine_c.sh             Engine C run (Maestro + companion DB oracle)
harness/collect_failure.sh          provider-explicit failure bundle (layout → uiautomator → dumpsys)
harness/emit_run.py                 run → benchmark-run.json + verification-result.json
harness/measure.py                  → results/summary.json + summary.csv (allowlist-driven)
harness/stage1.sh                   warm-ups + 18 measured runs (extended to 24 B/C)
results/<RUN_ID>/                   per-run artifacts (executor, logcat, bench/, failure/)
results/summary.{json,csv}          aggregated comparison (measured B/C only + control separate)
results/baseline-manifest.json      audit-frozen allowlist: measurement_class per run
results/normalized-benchmark.json   Evaluation Core adapter output
reports/00-RECON.md                 read-only reconnaissance
reports/RUN-INVENTORY.md            full per-run inventory (audit)
reports/FINAL-VERIFICATION-COMPRESSION-AUDIT.md  audit → correct → freeze
reports/FINAL-VERIFICATION-COMPRESSION-BENCHMARK.md
```

## Reproduce

```bash
# one Engine B / Engine C run
bash harness/run_engine_b.sh J2 1
bash harness/run_engine_c.sh J2 1

# aggregate
python3 harness/measure.py
```

Requires: the frozen APK installed, `adb` device `87296ada`, Maestro on PATH for Engine C, and the
androidTest APK built once (`./gradlew :app:assembleDebugAndroidTest` in the worktree copy).

## Key facts

- Frozen APK sha256: `a8858bd1f57b328a5042a120023508ced8e1cbbf68446bab3ce0e5e80f6fdf06`
- Isolation: filesystem copy (`NO_WORKTREE`; repository has no commits).
- Engine B is UiAutomator-only (Compose UI Test is blocked on API 36).
- PASS path model calls: 0 for B and C. Failure path: automatic evidence bundle.
