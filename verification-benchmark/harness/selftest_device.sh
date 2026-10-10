#!/usr/bin/env bash
# On-device hardening self-test. Minimal by design — no A/B/C re-run, no compression recompute.
#
#   1. Engine B J1 x1 (diagnostic)                 -> PASS result
#   2. Engine B intentional failure x1 (diagnostic) -> fail-fast + complete failure bundle
#   3. Engine C isolation smoke                    -> cleanup + IME switch + Maestro input smoke
#   4. baseline guard                              -> frozen 27-run baseline unchanged
#
# Every run uses BENCH_DIAGNOSTIC=1 (measurement_class=diagnostic, excluded_from_baseline)
# and lands in results/HARDEN-* so it can never enter the measured set.
set -uo pipefail
HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "$HARNESS_DIR/lib.sh"

SERIAL=${SERIAL:-87296ada}; export SERIAL
export BENCH_DIAGNOSTIC=1
REPORTS="$BASE/reports/hardening"
mkdir -p "$REPORTS" "$HARNESS_DIR/.state"

B_SMOKE="SKIP"; FAILFAST="SKIP"; BUNDLE="SKIP"; ISOLATION="SKIP"; PREFLIGHT="SKIP"; BASELINE="SKIP"

PREFLIGHT="FAIL"
if with_timeout "$PREFLIGHT_TO" preflight bash "$HARNESS_DIR/preflight.sh" B; then
  PREFLIGHT="PASS"
  echo "=================================================="
  echo "[1/4] Engine B J1 diagnostic smoke"
  if BENCH_DIAGNOSTIC=1 RUN_ID_OVERRIDE=HARDEN-B-J1-smoke \
       bash "$HARNESS_DIR/run_engine_b.sh" J1 1; then
    B_SMOKE="PASS"
  else
    B_SMOKE="FAIL"
  fi

  echo "=================================================="
  echo "[2/4] Engine B intentional failure (fail-fast + bundle)"
  SENTINEL="$HARNESS_DIR/.state/failfast-sentinel"; rm -f "$SENTINEL"
  (
    set -e
    BENCH_DIAGNOSTIC=1 SKIP_SEED=1 SKIP_SMOKE=1 \
    BENCH_TEST_CLASS=com.keeplab.app.benchmark.IntentionalFailureTest \
    BENCH_LAUNCH_TEST=com.keeplab.app.benchmark.IntentionalFailureTest \
    RUN_ID_OVERRIDE=HARDEN-B-INTENTIONAL-FAIL \
      bash "$HARNESS_DIR/run_engine_b.sh" J1 9
    touch "$SENTINEL"
  )
  FF_RC=$?
  if [ ! -f "$SENTINEL" ] && [ "$FF_RC" -ne 0 ]; then FAILFAST="PASS"; else FAILFAST="FAIL"; fi
  echo "fail-fast: rc=$FF_RC sentinel_absent=$([ ! -f "$SENTINEL" ] && echo yes || echo no)"

  BUNDLE_DIR="$RESULTS_DIR/HARDEN-B-INTENTIONAL-FAIL/failure"
  if python3 "$HARNESS_DIR/evidence_completeness.py" "$BUNDLE_DIR"; then BUNDLE="PASS"; else BUNDLE="FAIL"; fi

  echo "=================================================="
  echo "[3/4] Engine C isolation smoke (cleanup + IME switch + Maestro input)"
  if bash "$HARNESS_DIR/cleanup_engine.sh" C \
     && bash "$HARNESS_DIR/cleanup_engine.sh" C --check-only \
     && bash "$HARNESS_DIR/ime.sh" C \
     && bash "$HARNESS_DIR/input_smoke.sh" C; then
    ISOLATION="PASS"
  else
    ISOLATION="FAIL"
  fi
else
  echo "preflight failed; skipping device smoke" >&2
fi

echo "=================================================="
echo "[4/4] baseline guard"
if python3 "$HARNESS_DIR/baseline_guard.py"; then BASELINE="PASS"; else BASELINE="FAIL"; fi

python3 - "$REPORTS/device-smoke.json" "$PREFLIGHT" "$B_SMOKE" "$FAILFAST" "$BUNDLE" "$ISOLATION" "$BASELINE" <<'PY'
import json, sys
from datetime import datetime, timezone
path, *vals = sys.argv[1:]
keys = ["preflight", "engine_b_j1_smoke", "fail_fast", "evidence_completeness",
        "engine_c_isolation", "baseline_unchanged"]
d = dict(zip(keys, vals))
d["outcome"] = "PASS" if all(v == "PASS" for v in vals) else "FAIL"
d["timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
json.dump(d, open(path, "w"), indent=2)
print(json.dumps(d, indent=2))
PY

echo "SELFTEST_DEVICE=$( [ "$PREFLIGHT" = PASS ] && [ "$B_SMOKE" = PASS ] && [ "$FAILFAST" = PASS ] && [ "$BUNDLE" = PASS ] && [ "$ISOLATION" = PASS ] && [ "$BASELINE" = PASS ] && echo PASS || echo FAIL )"
