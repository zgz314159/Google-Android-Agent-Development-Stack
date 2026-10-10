#!/usr/bin/env bash
# Input capability smoke. Tiny, bounded, and never a verification metric.
#
#   input_smoke.sh <uiautomator|maestro>
#
# Verifies only that (a) a UI element is locatable and (b) text input with a fixed ASCII
# probe round-trips. uiautomator -> INPUT_SMOKE_CLASS instrumentation; maestro ->
# INPUT_SMOKE_FLOW. Failure stops the run before any journey.
#
# Environment: TEST_PKG, RUNNER, INPUT_SMOKE_CLASS, INPUT_SMOKE_FLOW, OUT.
set -euo pipefail
ANDROID_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib_android.sh
source "$ANDROID_DIR/lib_android.sh"

ENGINE_ARG="${1:?usage: input_smoke.sh uiautomator|maestro}"
case "$ENGINE_ARG" in uiautomator|maestro) : ;; *) echo "engine must be uiautomator or maestro" >&2; exit 2 ;; esac
ENGINE="$ENGINE_ARG"
resolve_serial || die "no device for input smoke" input_smoke

OUT_DIR="${OUT:-$VERIFY_STATE_DIR}"
mkdir -p "$OUT_DIR"
TEST_PKG="${TEST_PKG:-}"
RUNNER="${RUNNER:-androidx.test.runner.AndroidJUnitRunner}"

if [ "$ENGINE" = "uiautomator" ]; then
  [ -n "${INPUT_SMOKE_CLASS:-}" ] || die "INPUT_SMOKE_CLASS not set for uiautomator input smoke" input_smoke
  set +e
  adb_timeout "$INSTR_TO" input_smoke shell am instrument -w \
    -e class "$INPUT_SMOKE_CLASS" "$RUNNER" > "$OUT_DIR/input-smoke.txt" 2>&1
  rc=$?
  set -e
  if [ "$rc" -ne 0 ] || ! grep -Eq 'OK \([0-9]+ tests?\)' "$OUT_DIR/input-smoke.txt"; then
    printf 'INPUT_SMOKE_FAIL\n' >&2
    die "input capability smoke failed ($ENGINE, rc=$rc)" input_smoke
  fi
else
  [ -n "${INPUT_SMOKE_FLOW:-}" ] || die "INPUT_SMOKE_FLOW not set for maestro input smoke" input_smoke
  command -v maestro >/dev/null 2>&1 || die "maestro not on PATH" input_smoke
  set +e
  with_timeout "$INSTR_TO" input_smoke maestro --device "$SERIAL" test --no-ansi \
    --no-reinstall-driver --format JUNIT --output "$OUT_DIR/input-smoke.xml" \
    "$INPUT_SMOKE_FLOW" > "$OUT_DIR/input-smoke.txt" 2>&1
  rc=$?
  set -e
  if [ "$rc" -ne 0 ]; then
    printf 'INPUT_SMOKE_FAIL\n' >&2
    die "input capability smoke failed ($ENGINE, rc=$rc)" input_smoke
  fi
fi

python3 - "$OUT_DIR/input-smoke.json" "$ENGINE" <<'PY'
import json, sys
from datetime import datetime, timezone
path, engine = sys.argv[1:3]
json.dump({
    "engine": engine,
    "probe": "VC-SMOKE-ASCII-0123",
    "outcome": "PASS",
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
}, open(path, "w"), indent=2)
PY
echo "INPUT_SMOKE=PASS engine=$ENGINE"
