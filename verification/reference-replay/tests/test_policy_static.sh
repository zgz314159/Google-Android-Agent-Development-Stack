#!/usr/bin/env bash
# Static policy gate for the reference replay path.
#
# Fails (non-zero) if the replay path contains:
#   * direct adb UI input   : `adb ... input tap|swipe|text`
#   * assertWithAI / vision in the PASS path
#   * coordinate taps without an explicit exception marker
#   * destructive text entry in the non-destructive flows
#
# Emits REPLAY_POLICY=PASS|FAIL.
set -euo pipefail
RR_HOME="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fail=0
note() { printf '  - %s\n' "$1" >&2; fail=1; }

scan() { # scan <label> <regex> <paths...>
  local label="$1" rx="$2"; shift 2
  local hits
  hits="$(grep -RnE "$rx" "$@" 2>/dev/null || true)"
  if [ -n "$hits" ]; then note "$label"; printf '%s\n' "$hits" >&2; fi
}

FLOWS=("$RR_HOME"/flows/*.yaml)
RUNNER=("$RR_HOME"/runner)
LIB=("$RR_HOME"/lib)
PATHS=("${FLOWS[@]}" "${RUNNER[@]}")
[ -d "$LIB" ] && PATHS+=("${LIB[@]}")

# 1. No direct adb UI input anywhere in the replay path.
scan "DIRECT_ADB_UI_INPUT" 'adb[^|]*input[[:space:]]+(tap|swipe|text)' "${PATHS[@]}"

# 2. No assertWithAI / vision in the PASS path (checked in the executed flows).
scan "ASSERT_WITH_AI" 'assertWithAI' "${FLOWS[@]}"

# 3. Coordinate taps must carry an explicit exception marker.
coord="$(grep -RnE '(^|[[:space:]])(point|coordinate)[[:space:]]*:' "${FLOWS[@]}" 2>/dev/null || true)"
if [ -n "$coord" ]; then
  while IFS= read -r line; do
    file="${line%%:*}"; lno="${line#*:}"; lno="${lno%%:*}"
    lo=$(( lno > 4 ? lno - 4 : 1 ))
    ctx="$(sed -n "${lo},$((lno+1))p" "$file")"
    case "$ctx" in
      *EXCEPTION*|*exception*) : ;;
      *) note "COORDINATE_TAP_WITHOUT_EXCEPTION ($file:$lno)"; printf '%s\n' "$line" >&2 ;;
    esac
  done <<< "$coord"
fi

# 4. Non-destructive flows must not type/erase text.
scan "DESTRUCTIVE_TEXT_INPUT" '^[[:space:]]*-[[:space:]]*(inputText|eraseText)\b' "${FLOWS[@]}"

# 5. No arbitrary sleep-driven polling (Maestro has no sleep; guard shell sleeps).
scan "ARBITRARY_SLEEP" '[^a-zA-Z0-9_]sleep[[:space:]]+[0-9]' "${PATHS[@]}"

if [ "$fail" -ne 0 ]; then echo "REPLAY_POLICY=FAIL" >&2; exit 1; fi
echo "REPLAY_POLICY=PASS"
