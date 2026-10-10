#!/usr/bin/env bash
# Engine C (Maestro) measured run for one journey/iteration.
#
# Maestro does not expose per-command monotonic timestamps, so t7b_ms is written as null
# (never estimated). t7c_ms is the host-measured duration of the shared DB oracle probe.
#
# v1.0 hardening mirrors Engine B: preflight + cleanup + provenance guards, idempotent
# install, deterministic IME contract, input smoke, bounded stages, run-state watchdog,
# fail-fast, and device-state restore on every exit path.
set -euo pipefail
export PATH="$PATH:${MAESTRO_BIN:-$HOME/.maestro/bin}"
HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "$HARNESS_DIR/lib.sh"

SERIAL=${SERIAL:-87296ada}
JOURNEY=${1:?usage: run_engine_c.sh J1|J2|J3 [iteration]}
ITER=${2:-1}
ENGINE=C

if is_diagnostic; then
  RUN_ID="${RUN_ID_OVERRIDE:-HARDEN-C-${JOURNEY}-${ITER}}"
else
  RUN_ID="${RUN_ID_OVERRIDE:-${JOURNEY}-C-${ITER}}"
fi
OUT="${OUT_OVERRIDE:-$RESULTS_DIR/$RUN_ID}"
mkdir -p "$OUT" "$OUT/bench"
export SERIAL JOURNEY ENGINE RUN_ID OUT

PRIMARY_OUTCOME=UNKNOWN
install_cleanup_trap

FROZEN_SHA="$(python3 -c "import json;print(json.load(open('$BASE/benchmark-apk.json'))['sha256'])")"
EXPECTED_APK_SHA="${EXPECTED_APK_SHA:-$FROZEN_SHA}"
export EXPECTED_APK_SHA

# ---- guards (outside T7 setup) ----
stage preflight
with_timeout "$PREFLIGHT_TO" preflight bash "$HARNESS_DIR/preflight.sh" C

stage cleanup_engine
bash "$HARNESS_DIR/cleanup_engine.sh" C

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
bash "$HARNESS_DIR/ime.sh" C

stage install
install_idempotent "$APP_APK" "$PKG"
install_idempotent "$TEST_APK" "$TEST_PKG"
require_package "$PKG"
require_package "$TEST_PKG"

stage reset
adb_ shell rm -rf "/sdcard/Android/data/$PKG/files/bench" >/dev/null 2>&1 || true
adb_ shell am force-stop "$PKG" >/dev/null 2>&1 || true

if [ "${SKIP_SMOKE:-0}" != "1" ]; then
  stage input_smoke
  bash "$HARNESS_DIR/input_smoke.sh" C
fi

if [ "${SKIP_SEED:-0}" != "1" ]; then
  stage seed
  adb_timeout "$SEED_TO" seed shell am instrument -w \
    -e class "com.keeplab.app.benchmark.FixtureSeeder#seed$JOURNEY" "$RUNNER" \
    > "$OUT/seed.txt" 2>&1 || die "fixture seed failed" seed
fi
S1=$(ns)
SETUP_MS=$(( (S1 - S0) / 1000000 ))

# ---- measured Maestro flow (T7) ----
stage instrumentation
adb_ logcat -c >/dev/null 2>&1 || true
FLOW="${BENCH_MAESTRO_FLOW:-$BASE/maestro/$JOURNEY.yaml}"
M0=$(ns)
set +e
with_timeout "$MAESTRO_TO" instrumentation maestro --device "$SERIAL" test --no-ansi \
  --no-reinstall-driver --format JUNIT --output "$OUT/maestro.xml" "$FLOW" \
  > "$OUT/maestro.txt" 2>&1
MAESTRO_RC=$?
set -e
M1=$(ns)
MAESTRO_MS=$(( (M1 - M0) / 1000000 ))

# ---- shared terminal oracle (Engine C cannot read the DB itself) ----
stage oracle
D0=$(ns)
set +e
adb_timeout "$SEED_TO" oracle shell am instrument -w -e class com.keeplab.app.benchmark.DbProbe \
  -e journey "$JOURNEY" "$RUNNER" > "$OUT/dbprobe.txt" 2>&1
DB_RC=$?
set -e
D1=$(ns)

stage collect
adb_ logcat -d > "$OUT/logcat.txt" 2>&1 || true
adb_ shell am force-stop "$PKG" >/dev/null 2>&1 || true
rm -rf "$OUT/bench"; mkdir -p "$OUT/bench"
adb_ pull "/sdcard/Android/data/$PKG/files/bench/." "$OUT/bench" >/dev/null 2>&1 || true

# Synthesize the evidence span so t7c is provable from host monotonic time.
printf '{"kind":"EVIDENCE_START","name":"db-oracle","run_id":"%s","journey":"%s","elapsed_realtime_ns":%s}\n' \
  "$RUN_ID" "$JOURNEY" "$D0" > "$OUT/bench/events-$RUN_ID.jsonl"
printf '{"kind":"EVIDENCE_END","name":"db-oracle","run_id":"%s","journey":"%s","elapsed_realtime_ns":%s}\n' \
  "$RUN_ID" "$JOURNEY" "$D1" >> "$OUT/bench/events-$RUN_ID.jsonl"

OUTCOME=FAIL
if [ "$MAESTRO_RC" -eq 0 ] && grep -q '"outcome": "PASS"' "$OUT/bench/verify-part.json" 2>/dev/null; then
  OUTCOME=PASS
fi
TOTAL_MS=$(( MAESTRO_MS + (D1 - D0) / 1000000 ))

stage emit
EMIT_ARGS=(--run-id "$RUN_ID" --engine C --journey "$JOURNEY" --iteration "$ITER"
  --bench-dir "$OUT/bench" --out "$OUT"
  --setup-ms "$SETUP_MS" --total-ms "$TOTAL_MS" --apk-sha256 "$APK_SHA"
  --test-apk-sha256 "$TEST_APK_SHA" --harness-version "$HARNESS_VERSION"
  --runner-version "$RUNNER_VERSION"
  --device-serial "$SERIAL" --device-model "Redmi Note 7 Pro" --api "${API:-36}"
  --outcome "$OUTCOME")
if is_diagnostic; then EMIT_ARGS+=(--measurement-class diagnostic --excluded-from-baseline); fi
python3 "$HARNESS_DIR/emit_run.py" "${EMIT_ARGS[@]}"

PRIMARY_OUTCOME="$OUTCOME"
write_outcome_json

if [ "$MAESTRO_RC" -eq 124 ]; then
  printf 'TIMEOUT_STAGE=instrumentation\n' >&2
  stage failure_bundle
  bash "$HARNESS_DIR/collect_failure.sh" "$OUT" || true
  die "maestro timeout for $RUN_ID" instrumentation
fi

if [ "$OUTCOME" != "PASS" ]; then
  stage failure_bundle
  bash "$HARNESS_DIR/collect_failure.sh" "$OUT" || echo "EVIDENCE_INCOMPLETE" >&2
  die "run $RUN_ID outcome=$OUTCOME" fail
fi

stage done
echo "$RUN_ID: PASS (setup=${SETUP_MS}ms t7=${TOTAL_MS}ms)"
