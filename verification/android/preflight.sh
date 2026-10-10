#!/usr/bin/env bash
# Device preflight. MUST run before any real-device verification.
#
#   preflight.sh <uiautomator|maestro>
#
# Checks adb/serial/state, device awake + unlocked, stay-awake, orientation, theme,
# target IME availability, and package/storage sanity. Writes a machine-readable
# preflight-result.json. Exits non-zero on PREFLIGHT_FAIL.
#
# A secure PIN/pattern keyguard is NEVER bypassed: it yields
# DEVICE_LOCKED_REQUIRES_OWNER_UNLOCK and stops.
#
# Environment: PKG (required), TEST_PKG (optional), EXPECTED_DEVICE/EXPECTED_API
# (optional), SERIAL (optional), OUT (optional; result dir), VERIFY_STATE_DIR.
set -euo pipefail
ANDROID_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib_android.sh
source "$ANDROID_DIR/lib_android.sh"

ENGINE_ARG="${1:?usage: preflight.sh uiautomator|maestro}"
case "$ENGINE_ARG" in uiautomator|maestro) : ;; *) echo "engine must be uiautomator or maestro" >&2; exit 2 ;; esac
ENGINE="$ENGINE_ARG"

PKG="${PKG:?PKG must be set}"
TEST_PKG="${TEST_PKG:-$PKG.test}"
STATE_DIR="${VERIFY_STATE_DIR}"
mkdir -p "$STATE_DIR"
RESULT_FILE="${OUT:-$STATE_DIR}/preflight-result.json"
NOTES=()
fail_note() { NOTES+=("$1"); }

# ---------------------------------------------------------------- adb
adb_ready=false
serial_unique=false
if ! adb devices >/dev/null 2>&1; then
  fail_note "adb not available"
else
  adb_ready=true
  if [ -n "${SERIAL:-}" ]; then
    line="$(adb devices | awk -v s="$SERIAL" '$1==s{print $2}')"
    if [ "$line" = "device" ]; then serial_unique=true
    else fail_note "serial $SERIAL state=${line:-missing}"; fi
  else
    ids="$(adb devices | awk 'NR>1 && $2=="device"{print $1}')"
    n="$(printf '%s\n' "$ids" | grep -c . || true)"
    if [ "$n" -eq 1 ]; then SERIAL="$ids"; serial_unique=true
    else fail_note "expected exactly 1 device in state=device, found $n"; fi
  fi
fi
export SERIAL

# ---------------------------------------------------------------- identity
api=""; model=""; abi=""
if [ "$serial_unique" = true ]; then
  set +e
  api="$(adb_ shell getprop ro.build.version.sdk 2>/dev/null | tr -d '\r')"
  model="$(adb_ shell getprop ro.product.model 2>/dev/null | tr -d '\r')"
  abi="$(adb_ shell getprop ro.product.cpu.abi 2>/dev/null | tr -d '\r')"
  set -e
  if [ -n "${EXPECTED_DEVICE:-}" ] && [ "$model" != "$EXPECTED_DEVICE" ]; then
    fail_note "device model '$model' != expected '$EXPECTED_DEVICE'"
  fi
  if [ -n "${EXPECTED_API:-}" ] && [ "$api" != "$EXPECTED_API" ]; then
    fail_note "api '$api' != expected '$EXPECTED_API'"
  fi
fi

# ---------------------------------------------------------------- screen / keyguard
awake=false; display_on=false; keyguard_locked=false
if [ "$serial_unique" = true ]; then
  if ! adb_ shell dumpsys power 2>/dev/null | grep -m1 'mWakefulness=' | grep -q 'Awake'; then
    set +e; adb_ shell input keyevent KEYCODE_WAKEUP >/dev/null 2>&1; set -e
    sleep 1
  fi
  set +e
  wake="$(adb_ shell dumpsys power 2>/dev/null | grep -m1 'mWakefulness=' | tr -d '\r')"
  dsp="$(adb_ shell dumpsys display 2>/dev/null | grep -m1 'mScreenState=' | tr -d '\r')"
  kg="$(adb_ shell dumpsys window 2>/dev/null | grep -m1 -E 'mKeyguardShowing=' | tr -d '\r')"
  set -e
  printf '%s' "$wake" | grep -q 'Awake' && awake=true
  printf '%s' "$dsp" | grep -q 'mScreenState=ON' && display_on=true
  if [ -z "$kg" ]; then
    set +e; kg="$(adb_ shell dumpsys window policy 2>/dev/null | grep -m1 'mShowingLockscreen=' | tr -d '\r')"; set -e
  fi
  printf '%s' "$kg" | grep -q '=true' && keyguard_locked=true
  set +e; kg2="$(adb_ shell dumpsys window 2>/dev/null | grep -m1 'mShowingLockscreen=' | tr -d '\r')"; set -e
  printf '%s' "$kg2" | grep -q '=true' && keyguard_locked=true
  if [ "$keyguard_locked" = true ]; then
    printf 'DEVICE_LOCKED_REQUIRES_OWNER_UNLOCK\n' >&2
    fail_note "keyguard is showing (secure lock); owner must unlock"
  fi
  if [ "$awake" != true ]; then fail_note "device is not awake"; fi
fi

# ---------------------------------------------------------------- snapshot + apply state
stay_prev=""; orientation_ready=false; theme_ready=false
if [ "$serial_unique" = true ]; then
  state_snapshot
  stay_prev="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("stay_on_while_plugged_in",""))' "$STATE_FILE" 2>/dev/null || echo "")"
  set +e; adb_ shell svc power stayon true >/dev/null 2>&1; set -e
  set +e
  adb_ shell settings put system accelerometer_rotation 0 >/dev/null 2>&1
  adb_ shell settings put system user_rotation 0 >/dev/null 2>&1
  a="$(adb_ shell settings get system accelerometer_rotation 2>/dev/null | tr -d '\r')"
  r="$(adb_ shell settings get system user_rotation 2>/dev/null | tr -d '\r')"
  set -e
  if [ "$a" = "0" ] && [ "$r" = "0" ]; then orientation_ready=true
  else fail_note "orientation not applied (accelerometer_rotation=$a user_rotation=$r)"; fi
  set +e
  adb_ shell cmd uimode night no >/dev/null 2>&1
  night="$(adb_ shell cmd uimode night 2>/dev/null | tr -d '\r')"
  set -e
  if printf '%s' "$night" | grep -qi 'no'; then theme_ready=true
  else fail_note "theme not light after 'cmd uimode night no' ($night)"; fi
fi

# ---------------------------------------------------------------- IME availability
ime_ok=false; ime_comp=""; ime_cur=""; ime_pkg=""
if [ "$serial_unique" = true ]; then
  ime_comp="$(ime_component_for "$ENGINE")"
  ime_pkg="$(ime_pkg_for "$ENGINE")"
  set +e
  ime_cur="$(ime_current)"
  ime_available "$ime_comp" "$ime_pkg" && ime_ok=true || ime_ok=false
  set -e
  if [ "$ime_ok" != true ]; then
    printf 'IME_UNAVAILABLE\n' >&2
    fail_note "IME for engine $ENGINE not available: $ime_comp"
  fi
fi

# ---------------------------------------------------------------- package / storage sanity
target_installed=false; test_installed=false; free_mb=""
if [ "$serial_unique" = true ]; then
  set +e
  adb_ shell pm path "$PKG" >/dev/null 2>&1 && target_installed=true
  adb_ shell pm path "$TEST_PKG" >/dev/null 2>&1 && test_installed=true
  free_k="$(adb_ shell df -k /data 2>/dev/null | awk 'NR==2{print $4}' | tr -d '\r')"
  set -e
  if [[ "$free_k" =~ ^[0-9]+$ ]]; then free_mb=$(( free_k / 1024 )); fi
  if [ -n "$free_mb" ] && [ "$free_mb" -lt 500 ]; then
    fail_note "low free space on /data: ${free_mb} MB"
  fi
fi

# ---------------------------------------------------------------- outcome + JSON
outcome=PASS
[ "${#NOTES[@]}" -eq 0 ] || outcome=FAIL

python3 - "$RESULT_FILE" "$outcome" "$SERIAL" "$api" "$model" "$abi" \
  "$awake" "$display_on" "$keyguard_locked" "$ime_ok" "$ime_comp" "$ime_cur" \
  "$orientation_ready" "$theme_ready" "$adb_ready" "$serial_unique" "$stay_prev" \
  "$target_installed" "$test_installed" "$free_mb" "$ENGINE" "${NOTES[@]:-}" <<'PY'
import json, sys
from datetime import datetime, timezone
path, outcome, serial, api, model, abi, awake, display_on, keyguard, ime_avail, ime_comp, ime_cur, \
    orient, theme, adb_ready, serial_unique, stay_prev, target_inst, test_inst, free_mb, engine = sys.argv[1:22]
notes = [n for n in sys.argv[22:] if n]
json.dump({
    "outcome": outcome,
    "device_serial": serial,
    "api": api,
    "device_model": model,
    "abi": abi,
    "engine": engine,
    "awake": awake == "true",
    "display_on": display_on == "true",
    "keyguard_locked": keyguard == "true",
    "ime_available": ime_avail == "true",
    "ime_component": ime_comp,
    "ime_current": ime_cur,
    "orientation_ready": orient == "true",
    "theme_ready": theme == "true",
    "adb_ready": adb_ready == "true",
    "serial_unique": serial_unique == "true",
    "stay_on_previous": stay_prev,
    "target_pkg_installed": target_inst == "true",
    "test_pkg_installed": test_inst == "true",
    "free_space_mb": int(free_mb) if free_mb.isdigit() else None,
    "notes": notes,
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
}, open(path, "w"), indent=2)
PY

echo "PREFLIGHT_$outcome serial=$SERIAL api=$api model=$model engine=$ENGINE"
echo "PREFLIGHT_RESULT=$RESULT_FILE"
if [ "$outcome" != "PASS" ]; then
  printf 'PREFLIGHT_FAIL\n' >&2
  for n in "${NOTES[@]:-}"; do [ -n "$n" ] && printf '  - %s\n' "$n" >&2; done
  exit 1
fi
exit 0
