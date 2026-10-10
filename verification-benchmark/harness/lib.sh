#!/usr/bin/env bash
# Verification harness shared library (v1.0).
#
# Sourced by every harness script. Callers MUST `set -euo pipefail` before sourcing so
# failures are fatal; this library provides the explicit, expected-failure escape hatches
# (timeouts, test failures) instead of blanket `|| true`.
#
# Responsibilities:
#   * paths / constants / engine -> IME mapping
#   * adb helper + bounded execution (`with_timeout`)
#   * fail-fast (`die`) + run-state heartbeat (`stage`, `run-state.json`)
#   * device-state snapshot/restore (orientation / theme / stay-awake / IME)
#   * idempotent install + package verification
#   * APK provenance (sha256 verify)
#   * cleanup trap that never masks the primary outcome
#
# This file is sourced, not executed. Do not add side effects that run at source time
# beyond read-only constant computation.

HARNESS_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE="$(cd "$HARNESS_LIB_DIR/.." && pwd)"
HARNESS_DIR="$HARNESS_LIB_DIR"

# Host-owned output/state roots (OUTSIDE the project), via the canonical path contract.
_HARNESS_REPO="$(cd "$BASE/.." && pwd)"
_harness_stack_q() { "$_HARNESS_REPO/scripts/stack-paths.sh" query "$1" 2>/dev/null; }
STATE_DIR="${HARNESS_STATE_DIR:-$(_harness_stack_q STACK_STATE_ROOT)/verification-benchmark}"
RESULTS_DIR="${HARNESS_RESULTS_DIR:-$(_harness_stack_q STACK_DATA_ROOT)/artifacts/verification-benchmark/results}"

WT="${WT:-$(_harness_stack_q STACK_CACHE_ROOT)/keeplab-verification-worktrees}"
ANDROID_CLI="${ANDROID_CLI:-$(command -v android || echo "$HOME/.local/bin/android")}"

PKG="${PKG:-com.keeplab.app}"
TEST_PKG="com.keeplab.app.test"
RUNNER="$TEST_PKG/androidx.test.runner.AndroidJUnitRunner"

APP_APK="${APP_APK:-$BASE/frozen/app-debug-frozen.apk}"
TEST_APK="${TEST_APK:-$WT/app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk}"

HARNESS_VERSION="$(cat "$HARNESS_DIR/VERSION" 2>/dev/null || echo unknown)"
RUNNER_VERSION="androidx.test.runner.AndroidJUnitRunner"

# ---- timeouts (seconds) ----
PREFLIGHT_TO="${PREFLIGHT_TO:-30}"
INSTALL_TO="${INSTALL_TO:-300}"
INSTR_TO="${INSTR_TO:-600}"
EVIDENCE_TO="${EVIDENCE_TO:-120}"
CLEANUP_TO="${CLEANUP_TO:-60}"
MAESTRO_TO="${MAESTRO_TO:-600}"
SEED_TO="${SEED_TO:-120}"
SHELL_TO="${SHELL_TO:-30}"
PROVENANCE_TO="${PROVENANCE_TO:-60}"

# ---- run identity (set by the runner before using stage/state functions) ----
RUN_ID="${RUN_ID:-}"
JOURNEY="${JOURNEY:-}"
ENGINE="${ENGINE:-}"
OUT="${OUT:-}"
BENCH_DIAGNOSTIC="${BENCH_DIAGNOSTIC:-0}"
EXPECTED_APK_SHA="${EXPECTED_APK_SHA:-}"

PRIMARY_OUTCOME="${PRIMARY_OUTCOME:-UNKNOWN}"
CLEANUP_OUTCOME="${CLEANUP_OUTCOME:-NOT_RUN}"
_CLEANUP_DONE=0
_RUN_STATE_STARTED_AT=""

# ---------------------------------------------------------------------------
# logging
# ---------------------------------------------------------------------------
log() { printf '[%s] %s\n' "$(date -u +%H:%M:%SZ)" "$*" >&2; }

# Save/restore the caller's errexit state so library helpers never leak `set -e` into a
# caller that deliberately runs without it (e.g. the self-test orchestrator).
_SHLIB_HAD_E=0
_save_shflags() { _SHLIB_HAD_E=0; case "$-" in *e*) _SHLIB_HAD_E=1 ;; esac; }
_restore_shflags() { if [ "$_SHLIB_HAD_E" = 1 ]; then set -e; else set +e; fi; }

# ---------------------------------------------------------------------------
# device / adb
# ---------------------------------------------------------------------------
adb_() { adb -s "${SERIAL:?SERIAL must be set before using adb_}" "$@"; }

# Bounded adb for use with the external `timeout` binary (shell functions are not execable).
adb_timeout() { local secs="$1" stg="$2"; shift 2; with_timeout "$secs" "$stg" adb -s "${SERIAL:?SERIAL unset}" "$@"; }

# monotonic-ish and wall-clock helpers
ns() { date +%s%N; }
now_utc() { date -u +%Y-%m-%dT%H:%M:%SZ; }

# Resolve SERIAL when unset: require exactly one attached device in `device` state.
resolve_serial() {
  if [ -n "${SERIAL:-}" ]; then return 0; fi
  local ids
  ids="$(adb devices | awk 'NR>1 && $2=="device" {print $1}')"
  local n
  n="$(printf '%s\n' "$ids" | grep -c . || true)"
  if [ "$n" -ne 1 ]; then
    printf 'PREFLIGHT_FAIL\n'
    printf 'ADB_DEVICE_COUNT=%s (expected exactly 1)\n' "$n" >&2
    return 1
  fi
  SERIAL="$ids"
  export SERIAL
}

# Run a command with a hard timeout. On timeout prints TIMEOUT_STAGE and returns 124.
# Usage: with_timeout <secs> <stage> <cmd...>
with_timeout() {
  local secs="$1" stg="$2"; shift 2
  local rc
  _save_shflags
  set +e
  timeout --signal=TERM --kill-after=10 "$secs" "$@"
  rc=$?
  _restore_shflags
  if [ "$rc" -eq 124 ] || [ "$rc" -eq 137 ]; then
    printf 'TIMEOUT_STAGE=%s\n' "$stg" >&2
    return 124
  fi
  return "$rc"
}

# ---------------------------------------------------------------------------
# fail-fast + run-state heartbeat
# ---------------------------------------------------------------------------
run_state_write() {
  local stg="$1"
  [ -n "$OUT" ] || return 0
  [ -d "$OUT" ] || mkdir -p "$OUT"
  local now
  now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  [ -n "$_RUN_STATE_STARTED_AT" ] || _RUN_STATE_STARTED_AT="$now"
  python3 - "$OUT/run-state.json" "$stg" "$JOURNEY" "$ENGINE" "$RUN_ID" "$_RUN_STATE_STARTED_AT" "$now" <<'PY'
import json, sys
path, stage, journey, engine, run_id, started, now = sys.argv[1:8]
try:
    with open(path) as fh:
        d = json.load(fh)
except Exception:
    d = {}
d.update({
    "stage": stage,
    "journey": journey or None,
    "engine": engine or None,
    "run_id": run_id or None,
    "started_at": started,
    "last_progress_at": now,
})
with open(path, "w") as fh:
    json.dump(d, fh, indent=2)
PY
}

# stage <name> : update the heartbeat, used as the watchdog trail.
stage() {
  log "stage=$1"
  run_state_write "$1"
}

# Record cleanup time WITHOUT clobbering the last substantive stage, so a failure/timeout
# remains visible in run-state.json ("know where it got stuck").
run_state_mark_cleanup() {
  [ -n "$OUT" ] && [ -d "$OUT" ] || return 0
  local now; now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  python3 - "$OUT/run-state.json" "$now" <<'PY'
import json, sys
path, now = sys.argv[1:3]
try:
    d = json.load(open(path))
except Exception:
    d = {}
d["cleanup_at"] = now
json.dump(d, open(path, "w"), indent=2)
PY
}

# die <message> [stage] : record failure, print a machine-readable marker, exit non-zero.
die() {
  local msg="$1" stg="${2:-}"
  [ -n "$stg" ] && run_state_write "$stg"
  printf 'STAGE_FAIL=%s\n' "${stg:-unknown}" >&2
  printf 'HARNESS_ERROR=%s\n' "$msg" >&2
  exit 1
}

# ---------------------------------------------------------------------------
# device-state snapshot / restore (orientation, theme, stay-awake, IME)
# ---------------------------------------------------------------------------
state_file() { echo "$STATE_DIR/${SERIAL}.state.json"; }

state_snapshot() {
  mkdir -p "$STATE_DIR"
  local f; f="$(state_file)"
  local stay accel rot night ime
  _save_shflags
  set +e
  stay="$(adb_ shell settings get global stay_on_while_plugged_in 2>/dev/null | tr -d '\r')"
  accel="$(adb_ shell settings get system accelerometer_rotation 2>/dev/null | tr -d '\r')"
  rot="$(adb_ shell settings get system user_rotation 2>/dev/null | tr -d '\r')"
  night="$(adb_ shell cmd uimode night 2>/dev/null | tr -d '\r')"
  ime="$(adb_ shell settings get secure default_input_method 2>/dev/null | tr -d '\r')"
  _restore_shflags
  python3 - "$f" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$stay" "$accel" "$rot" "$night" "$ime" <<'PY'
import json, sys
path, ts, stay, accel, rot, night, ime = sys.argv[1:8]
json.dump({
    "captured_at": ts,
    "stay_on_while_plugged_in": stay,
    "accelerometer_rotation": accel,
    "user_rotation": rot,
    "night_mode": night,
    "default_input_method": ime,
}, open(path, "w"), indent=2)
PY
  log "state snapshot -> $f"
}

# state_restore : best-effort restore; returns non-zero on any restore failure.
state_restore() {
  local f; f="$(state_file)"
  [ -f "$f" ] || { log "no state snapshot to restore"; return 0; }
  local stay accel rot night ime
  stay="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("stay_on_while_plugged_in",""))' "$f")"
  accel="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("accelerometer_rotation",""))' "$f")"
  rot="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("user_rotation",""))' "$f")"
  night="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("night_mode",""))' "$f")"
  ime="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("default_input_method",""))' "$f")"
  local rc=0
  _save_shflags
  set +e
  [ -n "$stay" ] && [ "$stay" != "null" ] && adb_ shell settings put global stay_on_while_plugged_in "$stay" >/dev/null 2>&1 || rc=1
  [ -n "$accel" ] && [ "$accel" != "null" ] && adb_ shell settings put system accelerometer_rotation "$accel" >/dev/null 2>&1 || true
  [ -n "$rot" ] && [ "$rot" != "null" ] && adb_ shell settings put system user_rotation "$rot" >/dev/null 2>&1 || true
  case "$night" in
    *yes*) adb_ shell cmd uimode night yes >/dev/null 2>&1 || true ;;
    *no*)  adb_ shell cmd uimode night no  >/dev/null 2>&1 || true ;;
  esac
  if [ -n "$ime" ] && [ "$ime" != "null" ] && [ "$ime" != "null" ]; then
    adb_ shell ime set "$ime" >/dev/null 2>&1 || true
  fi
  _restore_shflags
  return "$rc"
}

# ---------------------------------------------------------------------------
# install / package verification
# ---------------------------------------------------------------------------
pkg_installed() { adb_ shell pm path "$1" 2>/dev/null | grep -q '^package:'; }

# install_idempotent <apk> <pkg> : checked `-r` install + post-install presence check.
install_idempotent() {
  local apk="$1" pkg="$2"
  [ -f "$apk" ] || die "apk not found: $apk" install
  local out rc
  _save_shflags
  set +e
  out="$(adb_timeout "$INSTALL_TO" install install -r "$apk" 2>&1)"
  rc=$?
  _restore_shflags
  if [ "$rc" -ne 0 ]; then
    printf '%s\n' "$out" >&2
    die "install failed for $apk (rc=$rc)" install
  fi
  if ! pkg_installed "$pkg"; then
    die "package $pkg missing after install of $apk" install
  fi
  log "installed $pkg from $(basename "$apk")"
}

require_package() {
  if ! pkg_installed "$1"; then
    die "required package not installed: $1" verify
  fi
}

# ---------------------------------------------------------------------------
# APK provenance
# ---------------------------------------------------------------------------
apk_sha() { sha256sum "$1" | awk '{print $1}'; }

# verify_apk_sha <apk> <expected> : STOP on mismatch (expected may be empty = record only).
verify_apk_sha() {
  local apk="$1" expected="$2"
  [ -f "$apk" ] || die "apk not found for provenance: $apk" provenance
  local got; got="$(apk_sha "$apk")"
  if [ -n "$expected" ] && [ "$got" != "$expected" ]; then
    printf 'APK_SHA_MISMATCH=expected:%s actual:%s\n' "$expected" "$got" >&2
    die "APK provenance mismatch for $apk" provenance
  fi
  printf '%s' "$got"
}

# ---------------------------------------------------------------------------
# IME contract (Engine B -> Google IME, Engine C -> AOSP LatinIME)
# ---------------------------------------------------------------------------
ime_component_for() {
  case "$1" in
    B|b) echo "com.google.android.inputmethod.latin/com.android.inputmethod.latin.LatinIME" ;;
    C|c) echo "com.android.inputmethod.latin/.LatinIME" ;;
    *) return 1 ;;
  esac
}

ime_pkg_for() {
  case "$1" in
    B|b) echo "com.google.android.inputmethod.latin" ;;
    C|c) echo "com.android.inputmethod.latin" ;;
    *) return 1 ;;
  esac
}

# get_ime <list|id> : parse `ime list -s` or `settings get secure default_input_method`.
ime_current() {
  adb_ shell settings get secure default_input_method 2>/dev/null | tr -d '\r'
}

ime_available() {
  local comp="$1" pkg="$2"
  adb_ shell ime list -s 2>/dev/null | tr -d '\r' | grep -qx "$comp" && return 0
  adb_ shell pm path "$pkg" >/dev/null 2>&1 && return 0
  return 1
}

# ---------------------------------------------------------------------------
# dev/diagnostic helpers
# ---------------------------------------------------------------------------
is_diagnostic() { [ "$BENCH_DIAGNOSTIC" = "1" ] || [ "$BENCH_DIAGNOSTIC" = "true" ]; }

write_outcome_json() {
  [ -n "$OUT" ] || return 0
  mkdir -p "$OUT"
  python3 - "$OUT/outcome.json" "$PRIMARY_OUTCOME" "$CLEANUP_OUTCOME" <<'PY'
import json, sys
path, primary, cleanup = sys.argv[1:4]
json.dump({"primary_outcome": primary, "cleanup_outcome": cleanup},
          open(path, "w"), indent=2)
PY
}

# ---------------------------------------------------------------------------
# cleanup trap (never masks the primary outcome)
# ---------------------------------------------------------------------------
harness_cleanup() {
  local rc=$?
  if [ "${_CLEANUP_DONE:-0}" = "1" ]; then return "$rc"; fi
  _CLEANUP_DONE=1
  _save_shflags
  set +e
  if [ -n "${SERIAL:-}" ] && [ -n "$OUT" ]; then
    log "cleanup: force-stop $PKG (host-side)"
    run_state_mark_cleanup
    with_timeout "$CLEANUP_TO" cleanup adb -s "$SERIAL" shell am force-stop "$PKG" >/dev/null 2>&1
    if state_restore; then
      [ "$PRIMARY_OUTCOME" = "UNKNOWN" ] && CLEANUP_OUTCOME="OK" || CLEANUP_OUTCOME="OK"
    else
      CLEANUP_OUTCOME="FAIL"
    fi
    write_outcome_json
  fi
  _restore_shflags
  return "$rc"
}

# install_cleanup_trap : call once, after OUT is set.
install_cleanup_trap() {
  trap 'harness_cleanup' EXIT INT TERM
}
