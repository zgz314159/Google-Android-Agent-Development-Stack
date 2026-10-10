#!/usr/bin/env bash
# Verification Layer - host-level device resource lock (NEW, additive).
#
# A physical Android device is an EXCLUSIVE MUTABLE RESOURCE with capacity 1. Two
# deterministic device runs (UiAutomator, Maestro, or reference replay) must never
# touch the same serial concurrently. This file is the minimal host-side guard:
# an advisory `flock(2)` keyed on the device serial.
#
# Scope: host-side mutual exclusion only. It does NOT replace the layer's
# on-device UiAutomation-holder conflict checks (cleanup_engine.sh) - both apply.
#
# Resource name: device:<serial>  (capacity = 1)
#
# Sourced, not executed. Callers MUST `set -euo pipefail` before sourcing.
#
#   device_lock_acquire <serial> [wait_secs] [lock_dir]
#       Acquire the exclusive lock for <serial>. wait_secs=0 => non-blocking
#       (fail fast with DEVICE_BUSY); wait_secs>0 => bounded wait. Returns 0 on
#       success, 1 on DEVICE_BUSY/TIMEOUT. The lock is held on an open fd and is
#       released automatically when the calling process exits.
#   device_lock_release
#       Explicit release (optional; process exit releases anyway).
#   device_lock_holder <serial> [lock_dir]
#       Print the holder pid recorded in the lock file, if any.

DEVICE_LOCK_FD=""
DEVICE_LOCK_SERIAL=""
DEVICE_LOCK_FILE=""

# Lock files live OUTSIDE the project tree: an explicit VERIFY_STATE_DIR, else the
# XDG stack state root via the path contract, else the XDG default. Never the checkout.
device_lock_state_root() {
  if [ -n "${VERIFY_STATE_DIR:-}" ]; then printf '%s' "$VERIFY_STATE_DIR"; return; fi
  local q="${VERIFY_ROOT:-.}/../scripts/stack-paths.sh"
  if [ -x "$q" ]; then
    local r; r="$("$q" query STACK_STATE_ROOT 2>/dev/null)" && [ -n "$r" ] && { printf '%s/verification' "$r"; return; }
  fi
  printf '%s/verification' "${ANDROID_AGENT_STACK_STATE_ROOT:-${XDG_STATE_HOME:-$HOME/.local/state}/google-android-agent-stack}"
}

# device_lock_acquire <serial> [wait_secs] [lock_dir]
device_lock_acquire() {
  local serial="${1:?device_lock_acquire: serial required}"
  local wait="${2:-0}"
  local lock_dir="${3:-$(device_lock_state_root)/locks}"
  mkdir -p "$lock_dir"
  DEVICE_LOCK_SERIAL="$serial"
  DEVICE_LOCK_FILE="$lock_dir/device-${serial}.lock"
  # Open (create if absent) the lock file and attach a private fd.
  exec {DEVICE_LOCK_FD}>"$DEVICE_LOCK_FILE" || {
    printf 'DEVICE_LOCK_OPEN_FAIL serial=%s file=%s\n' "$serial" "$DEVICE_LOCK_FILE" >&2
    return 1
  }
  local rc=0
  if [ "$wait" -gt 0 ] 2>/dev/null; then
    flock -w "$wait" "$DEVICE_LOCK_FD" || rc=1
  else
    flock -n "$DEVICE_LOCK_FD" || rc=1
  fi
  if [ "$rc" -ne 0 ]; then
    local holder
    holder="$(device_lock_holder "$serial" "$lock_dir")"
    printf 'DEVICE_BUSY serial=%s holder=%s\n' "$serial" "${holder:-unknown}" >&2
    exec {DEVICE_LOCK_FD}>&-
    DEVICE_LOCK_FD=""
    DEVICE_LOCK_SERIAL=""
    return 1
  fi
  # Record the holder pid for diagnostics (fd stays open; flock released on exit).
  printf '%s\n' "$$" >&"$DEVICE_LOCK_FD" 2>/dev/null || true
  printf 'DEVICE_LOCK_ACQUIRED serial=%s\n' "$serial" >&2
  return 0
}

device_lock_release() {
  [ -n "$DEVICE_LOCK_FD" ] || return 0
  flock -u "$DEVICE_LOCK_FD" 2>/dev/null || true
  eval "exec ${DEVICE_LOCK_FD}>&-" 2>/dev/null || true
  DEVICE_LOCK_FD=""
  DEVICE_LOCK_SERIAL=""
  return 0
}

# device_lock_holder <serial> [lock_dir]
device_lock_holder() {
  local serial="${1:?serial required}"
  local lock_dir="${2:-$(device_lock_state_root)/locks}"
  [ -f "$lock_dir/device-${serial}.lock" ] && cat "$lock_dir/device-${serial}.lock" 2>/dev/null || true
}
