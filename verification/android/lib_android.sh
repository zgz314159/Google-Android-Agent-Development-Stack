#!/usr/bin/env bash
# Verification Layer — Android adapter library (v1.0.0).
#
# Sourced by every android/*.sh helper. Provides device/adb primitives, device-state
# snapshot/restore, idempotent install, and the deterministic IME mapping. All
# project identity (package name, APK paths, serial) is supplied by the orchestrator
# via environment — nothing is hardcoded here.
#
# Sourced, not executed.

# Source the project-agnostic base first (it defines VERIFY_ROOT/VERIFY_VERSION).
_ANDROID_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../core/lib_common.sh
source "$_ANDROID_LIB_DIR/../core/lib_common.sh"

# ---- device / adb ---------------------------------------------------------
adb_() { adb -s "${SERIAL:?SERIAL must be set before using adb_}" "$@"; }

# Bounded adb for use with the external `timeout` binary.
adb_timeout() { local secs="$1" stg="$2"; shift 2; with_timeout "$secs" "$stg" adb -s "${SERIAL:?SERIAL unset}" "$@"; }

# resolve_serial : if SERIAL is unset, require exactly one attached device in `device` state.
resolve_serial() {
  if [ -n "${SERIAL:-}" ]; then return 0; fi
  local ids n
  ids="$(adb devices | awk 'NR>1 && $2=="device" {print $1}')"
  n="$(printf '%s\n' "$ids" | grep -c . || true)"
  if [ "$n" -ne 1 ]; then
    printf 'ADB_DEVICE_COUNT=%s (expected exactly 1)\n' "$n" >&2
    return 1
  fi
  SERIAL="$ids"
  export SERIAL
}

# ---- timeouts (overridable by the plan through the environment) -----------
PREFLIGHT_TO="${PREFLIGHT_TO:-30}"
INSTALL_TO="${INSTALL_TO:-300}"
INSTR_TO="${INSTR_TO:-600}"
ORACLE_TO="${ORACLE_TO:-120}"
EVIDENCE_TO="${EVIDENCE_TO:-120}"
CLEANUP_TO="${CLEANUP_TO:-60}"
SHELL_TO="${SHELL_TO:-30}"

# ---- package / state helpers ----------------------------------------------
STATE_FILE="${STATE_FILE:-${STATE_DIR:-$VERIFY_STATE_DIR}/$SERIAL.state.json}"

pkg_installed() { adb_ shell pm path "$1" 2>/dev/null | grep -q '^package:'; }

require_package() {
  if ! pkg_installed "$1"; then die "required package not installed: $1" verify; fi
}

# install_idempotent <apk> <pkg>
install_idempotent() {
  local apk="$1" pkg="$2" out rc
  [ -f "$apk" ] || die "apk not found: $apk" install
  set +e
  out="$(adb_timeout "$INSTALL_TO" install install -r "$apk" 2>&1)"
  rc=$?
  set -e
  if [ "$rc" -ne 0 ]; then
    printf '%s\n' "$out" >&2
    die "install failed for $apk (rc=$rc)" install
  fi
  if ! pkg_installed "$pkg"; then
    die "package $pkg missing after install of $apk" install
  fi
  log "installed $pkg from $(basename "$apk")"
}

# ---- device-state snapshot / restore (orientation, theme, stay-awake, IME) --
state_snapshot() {
  mkdir -p "$(dirname "$STATE_FILE")"
  local stay accel rot night ime
  set +e
  stay="$(adb_ shell settings get global stay_on_while_plugged_in 2>/dev/null | tr -d '\r')"
  accel="$(adb_ shell settings get system accelerometer_rotation 2>/dev/null | tr -d '\r')"
  rot="$(adb_ shell settings get system user_rotation 2>/dev/null | tr -d '\r')"
  night="$(adb_ shell cmd uimode night 2>/dev/null | tr -d '\r')"
  ime="$(adb_ shell settings get secure default_input_method 2>/dev/null | tr -d '\r')"
  set -e
  python3 - "$STATE_FILE" "$(now_utc)" "$stay" "$accel" "$rot" "$night" "$ime" <<'PY'
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
  log "state snapshot -> $STATE_FILE"
}

# state_restore : best-effort; returns non-zero if stay-awake restore failed.
state_restore() {
  [ -f "$STATE_FILE" ] || { log "no state snapshot to restore"; return 0; }
  local stay accel rot night ime rc=0
  stay="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("stay_on_while_plugged_in",""))' "$STATE_FILE")"
  accel="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("accelerometer_rotation",""))' "$STATE_FILE")"
  rot="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("user_rotation",""))' "$STATE_FILE")"
  night="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("night_mode",""))' "$STATE_FILE")"
  ime="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("default_input_method",""))' "$STATE_FILE")"
  set +e
  [ -n "$stay" ] && [ "$stay" != "null" ] && adb_ shell settings put global stay_on_while_plugged_in "$stay" >/dev/null 2>&1 || rc=1
  [ -n "$accel" ] && [ "$accel" != "null" ] && adb_ shell settings put system accelerometer_rotation "$accel" >/dev/null 2>&1 || true
  [ -n "$rot" ] && [ "$rot" != "null" ] && adb_ shell settings put system user_rotation "$rot" >/dev/null 2>&1 || true
  case "$night" in
    *yes*) adb_ shell cmd uimode night yes >/dev/null 2>&1 || true ;;
    *no*)  adb_ shell cmd uimode night no  >/dev/null 2>&1 || true ;;
  esac
  [ -n "$ime" ] && [ "$ime" != "null" ] && adb_ shell ime set "$ime" >/dev/null 2>&1 || true
  set -e
  return "$rc"
}

# ---- deterministic IME (engine -> component) ------------------------------
ime_component_for() {
  case "$1" in
    uiautomator) echo "com.google.android.inputmethod.latin/com.android.inputmethod.latin.LatinIME" ;;
    maestro)     echo "com.android.inputmethod.latin/.LatinIME" ;;
    *) return 1 ;;
  esac
}
ime_pkg_for() {
  case "$1" in
    uiautomator) echo "com.google.android.inputmethod.latin" ;;
    maestro)     echo "com.android.inputmethod.latin" ;;
    *) return 1 ;;
  esac
}
ime_current() { adb_ shell settings get secure default_input_method 2>/dev/null | tr -d '\r'; }
ime_available() {
  local comp="$1" pkg="$2"
  adb_ shell ime list -s 2>/dev/null | tr -d '\r' | grep -qx "$comp" && return 0
  adb_ shell pm path "$pkg" >/dev/null 2>&1 && return 0
  return 1
}
