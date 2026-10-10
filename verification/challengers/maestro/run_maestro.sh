#!/usr/bin/env bash
# Maestro challenger runner (reference-only; NOT the production default).
#
#   run_maestro.sh <flow.yaml>
#
# Kept deliberately outside the production UiAutomator lifecycle: it is invoked only when a
# verification plan declares `engine: maestro`, and it never shares a run with a UiAutomator
# journey. Writes maestro.xml + maestro.txt into $OUT so the host can collect them.
#
# Environment: SERIAL (required), OUT (required), INSTR_TO (optional timeout seconds).
set -euo pipefail
CHALLENGER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../core/lib_common.sh
source "$CHALLENGER_DIR/../../core/lib_common.sh"

FLOW="${1:?usage: run_maestro.sh <flow.yaml>}"
: "${SERIAL:?SERIAL must be set}"
: "${OUT:?OUT must be set}"
INSTR_TO="${INSTR_TO:-600}"

export PATH="$PATH:$HOME/.maestro/bin"
command -v maestro >/dev/null 2>&1 || { echo "MAESTRO_NOT_FOUND" >&2; exit 127; }

with_timeout "$INSTR_TO" instrumentation maestro --device "$SERIAL" test --no-ansi \
  --no-reinstall-driver --format JUNIT --output "$OUT/maestro.xml" "$FLOW"
