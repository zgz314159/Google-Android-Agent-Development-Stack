#!/usr/bin/env bash
# Verification Layer — shared, project-agnostic shell library (v1.0.1).
#
# Sourced by every Android helper script. Callers MUST `set -euo pipefail` before
# sourcing: this library provides the explicit, expected-failure escape hatches
# (bounded timeouts, machine-readable stage markers) instead of blanket `|| true`.
#
# Responsibilities (no device/adb knowledge here — see android/lib_android.sh):
#   * paths / version / run identity constants
#   * bounded execution (`with_timeout`) with `TIMEOUT_STAGE=<stage>`
#   * fail-fast (`die`) with `STAGE_FAIL` + `HARNESS_ERROR`
#   * small logging + clock helpers
#
# This file is sourced, not executed. It must stay free of side effects beyond
# read-only constant computation.

VERIFY_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERIFY_ROOT="$(cd "$VERIFY_LIB_DIR/.." && pwd)"
VERIFY_CORE="$VERIFY_ROOT/core"
VERIFY_ANDROID="$VERIFY_ROOT/android"
VERIFY_VERSION="$(cat "$VERIFY_ROOT/VERSION" 2>/dev/null || echo unknown)"

# Host-owned state/output roots (OUTSIDE the project). Resolved through the canonical
# path contract; override VERIFY_STATE_DIR / VERIFY_RUN_ROOT to relocate.
VERIFY_STACK_ROOT="$(cd "$VERIFY_ROOT/.." && pwd)"
_verify_stack_q() { "$VERIFY_STACK_ROOT/scripts/stack-paths.sh" query "$1" 2>/dev/null; }
VERIFY_STATE_DIR="${VERIFY_STATE_DIR:-$(_verify_stack_q STACK_STATE_ROOT)/verification}"
VERIFY_RUN_ROOT="${VERIFY_RUN_ROOT:-$(_verify_stack_q STACK_DATA_ROOT)/artifacts/verification/runs}"

# Run identity (set by the orchestrator before invoking a stage) --------------------
VERIFICATION_ID="${VERIFICATION_ID:-}"
PROJECT="${PROJECT:-}"
ENGINE="${ENGINE:-}"
JOURNEY="${JOURNEY:-}"
RUN_ID="${RUN_ID:-}"
OUT="${OUT:-}"

# ---------------------------------------------------------------------------
# logging + clocks
# ---------------------------------------------------------------------------
log() { printf '[%s] %s\n' "$(date -u +%H:%M:%SZ)" "$*" >&2; }
now_utc() { date -u +%Y-%m-%dT%H:%M:%SZ; }
ns() { date +%s%N; }

# ---------------------------------------------------------------------------
# bounded execution
# ---------------------------------------------------------------------------
# with_timeout <secs> <stage> <cmd...>
# On timeout prints TIMEOUT_STAGE=<stage> and returns 124. Shell functions are not
# execable, so callers that need a shell function must call `adb_timeout` instead.
with_timeout() {
  local secs="$1" stg="$2"; shift 2
  local rc
  set +e
  timeout --signal=TERM --kill-after=10 "$secs" "$@"
  rc=$?
  set -e
  if [ "$rc" -eq 124 ] || [ "$rc" -eq 137 ]; then
    printf 'TIMEOUT_STAGE=%s\n' "$stg" >&2
    return 124
  fi
  return "$rc"
}

# ---------------------------------------------------------------------------
# fail-fast
# ---------------------------------------------------------------------------
# die <message> [stage] : print machine-readable markers and exit non-zero.
die() {
  local msg="$1" stg="${2:-unknown}"
  printf 'STAGE_FAIL=%s\n' "$stg" >&2
  printf 'HARNESS_ERROR=%s\n' "$msg" >&2
  exit 1
}
