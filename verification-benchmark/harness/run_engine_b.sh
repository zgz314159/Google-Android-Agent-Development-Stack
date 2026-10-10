#!/usr/bin/env bash
# Engine B (native UiAutomator) measured run for one journey/iteration.
#
# v1.0 hardening: preflight + engine-cleanup + APK-provenance guards, idempotent install,
# deterministic IME contract, input smoke, bounded stages, run-state watchdog,
# fail-fast, and device-state restore on every exit path.
#
# Setup (fixture reset/seed, installs, orientation/theme) is timed separately as
# setup_wall_ms and never mixed into T7.
#
# Diagnostic/self-test knobs (never used by the frozen benchmark):
#   BENCH_DIAGNOSTIC=1     -> run id HARDEN-B-<J>-<i>, measurement_class=diagnostic
#   RUN_ID_OVERRIDE=<id>   -> explicit run id
#   BENCH_TEST_CLASS=<fqcn>-> override the measured instrumentation class
#   BENCH_LAUNCH_TEST=<fqcn>, SKIP_SEED=1, SKIP_SMOKE=1
set -euo pipefail
HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "$HARNESS_DIR/lib.sh"

SERIAL=${SERIAL:-87296ada}
JOURNEY=${1:?usage: run_engine_b.sh J1|J2|J3 [iteration]}
ITER=${2:-1}
ENGINE=B

if is_diagnostic; then
  RUN_ID="${RUN_ID_OVERRIDE:-HARDEN-B-${JOURNEY}-${ITER}}"
else
  RUN_ID="${RUN_ID_OVERRIDE:-${JOURNEY}-B-${ITER}}"
fi
OUT="${OUT_OVERRIDE:-$RESULTS_DIR/$RUN_ID}"
mkdir -p "$OUT"
export SERIAL JOURNEY ENGINE RUN_ID OUT

PRIMARY_OUTCOME=UNKNOWN
install_cleanup_trap

FROZEN_SHA="$(python3 -c "import json;print(json.load(open('$BASE/benchmark-apk.json'))['sha256'])")"
EXPECTED_APK_SHA="${EXPECTED_APK_SHA:-$FROZEN_SHA}"
export EXPECTED_APK_SHA

# ---- guards (outside T7 setup) ----
stage preflight
with_timeout "$PREFLIGHT_TO" preflight bash "$HARNESS_DIR/preflight.sh" B

stage cleanup_engine
bash "$HARNESS_DIR/cleanup_engine.sh" B

stage provenance
set +e
python3 "$HARNESS_DIR/apk_provenance.py" --app "$APP_APK" --test "$TEST_APK" \
  --expected-app "$EXPECTED_APK_SHA" --harness-version "$HARNESS_VERSION" \
  --runner-version "$RUNNER_VERSION" --json "$OUT/provenance.json" --require-test \
  > "$OUT/provenance.txt" 2>&1
PROV_RC=$?
set -e
[ "$PROV_RC" -eq 0 ] || { cat "$OUT/provenance.txt" >&2; die "APK provenance failed" provenance; }
APK_SHA="$(python3 -c "import json;print(json.load(open('$OUT/provenance.json'))['apk_sha256'])")"
TEST_APK_SHA="$(python3 -c "import json;print(json.load(open('$OUT/provenance.json')).get('test_apk_sha256',''))")"

# ---- setup (not counted in T7) ----
stage setup
S0=$(ns)
adb_ shell settings put system accelerometer_rotation 0 >/dev/null 2>&1 || true
adb_ shell settings put system user_rotation 0 >/dev/null 2>&1 || true
adb_ shell cmd uimode night no >/dev/null 2>&1 || true
adb_ shell svc power stayon true >/dev/null 2>&1 || true

stage ime
bash "$HARNESS_DIR/ime.sh" B

stage install
install_idempotent "$APP_APK" "$PKG"
install_idempotent "$TEST_APK" "$TEST_PKG"
require_package "$PKG"
require_package "$TEST_PKG"

stage reset
adb_ shell rm -rf "/sdcard/Android/data/$PKG/files/bench" >/dev/null 2>&1 || true
adb_ shell am force-stop "$PKG" >/dev/null 2>&1 || true

# input capability smoke (never a benchmark metric)
if [ "${SKIP_SMOKE:-0}" != "1" ]; then
  stage input_smoke
  bash "$HARNESS_DIR/input_smoke.sh" B
fi

if [ "${SKIP_SEED:-0}" != "1" ]; then
  stage seed
  adb_timeout "$SEED_TO" seed shell am instrument -w \
    -e class "com.keeplab.app.benchmark.FixtureSeeder#seed$JOURNEY" "$RUNNER" \
    > "$OUT/seed.txt" 2>&1 || die "fixture seed failed" seed
fi
S1=$(ns)
SETUP_MS=$(( (S1 - S0) / 1000000 ))

# ---- measured run (T7) ----
stage instrumentation
MEASURED_CLASS="${BENCH_TEST_CLASS:-com.keeplab.app.benchmark.${JOURNEY}JourneyTest}"
adb_ logcat -c >/dev/null 2>&1 || true
T0=$(ns)
set +e
adb_timeout "$INSTR_TO" instrumentation shell am instrument -w \
  -e class "$MEASURED_CLASS" -e runId "$RUN_ID" -e journey "$JOURNEY" "$RUNNER" \
  > "$OUT/executor.txt" 2>&1
INSTR_RC=$?
set -e
T1=$(ns)
TOTAL_MS=$(( (T1 - T0) / 1000000 ))

stage collect
adb_ logcat -d > "$OUT/logcat.txt" 2>&1 || true
adb_ shell am force-stop "$PKG" >/dev/null 2>&1 || true
rm -rf "$OUT/bench"; mkdir -p "$OUT/bench"
adb_ pull "/sdcard/Android/data/$PKG/files/bench/." "$OUT/bench" >/dev/null 2>&1 || true

stage emit
EMIT_ARGS=(--run-id "$RUN_ID" --engine B --journey "$JOURNEY" --iteration "$ITER"
  --bench-dir "$OUT/bench" --out "$OUT"
  --setup-ms "$SETUP_MS" --total-ms "$TOTAL_MS" --apk-sha256 "$APK_SHA"
  --test-apk-sha256 "$TEST_APK_SHA" --harness-version "$HARNESS_VERSION"
  --runner-version "$RUNNER_VERSION"
  --device-serial "$SERIAL" --device-model "Redmi Note 7 Pro" --api "${API:-36}")
if [ -n "${BENCH_LAUNCH_TEST:-}" ]; then EMIT_ARGS+=(--launch-test "$BENCH_LAUNCH_TEST"); fi
if is_diagnostic; then EMIT_ARGS+=(--measurement-class diagnostic --excluded-from-baseline); fi
python3 "$HARNESS_DIR/emit_run.py" "${EMIT_ARGS[@]}"

OUTCOME="$(python3 -c "import json;print(json.load(open('$OUT/benchmark-run.json')).get('outcome'))")"
PRIMARY_OUTCOME="$OUTCOME"
write_outcome_json

if [ "$INSTR_RC" -eq 124 ]; then
  printf 'TIMEOUT_STAGE=instrumentation\n' >&2
  stage failure_bundle
  bash "$HARNESS_DIR/collect_failure.sh" "$OUT" || true
  die "instrumentation timeout for $RUN_ID" instrumentation
fi

if [ "$OUTCOME" != "PASS" ]; then
  stage failure_bundle
  bash "$HARNESS_DIR/collect_failure.sh" "$OUT" || echo "EVIDENCE_INCOMPLETE" >&2
  die "run $RUN_ID outcome=$OUTCOME" fail
fi

stage done
echo "$RUN_ID: PASS (setup=${SETUP_MS}ms t7=${TOTAL_MS}ms)"
