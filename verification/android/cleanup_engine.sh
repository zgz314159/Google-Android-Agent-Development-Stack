#!/usr/bin/env bash
# Executor cleanup + isolation guard.
#
#   cleanup_engine.sh <uiautomator|maestro> [--check-only]
#
# Targets ONLY known verification/tool processes (never indiscriminate system kills) so a
# subsequent UiAutomation registration cannot collide with a leftover one
# ("UiAutomationService already registered"). If a conflicting process survives cleanup the
# script STOPS (non-zero) rather than letting the next run go blind.
#
# Environment: PKG (required), TEST_PKG (optional).
set -euo pipefail
ANDROID_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib_android.sh
source "$ANDROID_DIR/lib_android.sh"

ENGINE_ARG="${1:?usage: cleanup_engine.sh uiautomator|maestro [--check-only]}"
shift || true
CHECK_ONLY=0
[ "${1:-}" = "--check-only" ] && CHECK_ONLY=1
case "$ENGINE_ARG" in uiautomator|maestro) : ;; *) echo "engine must be uiautomator or maestro" >&2; exit 2 ;; esac
ENGINE="$ENGINE_ARG"

PKG="${PKG:?PKG must be set}"
TEST_PKG="${TEST_PKG:-$PKG.test}"

resolve_serial || exit 1

# Known verification/tool packages we own.
KNOWN_PKGS=("$PKG" "$TEST_PKG" "dev.mobile.maestro" "dev.mobile.maestro.test" \
  "com.android.cli" "com.android.cli.interact.instrumentation")

# Conflict patterns: a live UiAutomation holder for our packages/tools.
CONFLICT_RE="$(printf '%s' "$TEST_PKG" | sed 's/\./\\./g')|uiautomator|dev\.mobile\.maestro|com\.android\.cli\.interact\.instrumentation"

leftover_processes() {
  set +e
  adb_ shell ps -A 2>/dev/null | tr -d '\r' | grep -E "$CONFLICT_RE" | grep -v grep
  set -e
}

if [ "$CHECK_ONLY" -eq 0 ]; then
  for p in "${KNOWN_PKGS[@]}"; do
    set +e
    adb_ shell pm path "$p" >/dev/null 2>&1
    present=$?
    set -e
    if [ "$present" -eq 0 ]; then
      log "force-stop $p"
      with_timeout "$CLEANUP_TO" cleanup adb -s "$SERIAL" shell am force-stop "$p" >/dev/null 2>&1 || true
    fi
  done
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    [ -z "$(leftover_processes)" ] && break
    sleep 1
  done
fi

left="$(leftover_processes || true)"
if [ -n "$left" ]; then
  printf 'UIAUTOMATION_CONFLICT_SUSPECTED\n' >&2
  printf '%s\n' "$left" >&2
  printf 'CLEANUP_INCOMPLETE\n' >&2
  exit 1
fi

if [ -n "$OUT" ]; then
  mkdir -p "$OUT"
  python3 - "$OUT/cleanup.json" "$ENGINE" "$CHECK_ONLY" <<'PY'
import json, sys
from datetime import datetime, timezone
path, engine, check_only = sys.argv[1:4]
json.dump({
    "engine": engine,
    "check_only": check_only == "1",
    "leftover_processes": [],
    "outcome": "OK",
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
}, open(path, "w"), indent=2)
PY
fi

echo "ENGINE_CLEANUP=OK engine=$ENGINE check_only=$CHECK_ONLY"
