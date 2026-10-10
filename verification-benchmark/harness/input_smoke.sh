#!/usr/bin/env bash
# Input capability smoke. Tiny, bounded, and never a benchmark metric.
#
#   input_smoke.sh <B|C>
#
# Verifies only that (a) a UI element is locatable and (b) text input with a fixed ASCII
# probe round-trips. Engine B -> UiAutomator ACTION_SET_TEXT (InputSmokeTest); Engine C ->
# Maestro inputText (maestro/INPUT-SMOKE.yaml). Failure stops the run before any Journey.
set -euo pipefail
HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "$HARNESS_DIR/lib.sh"

ENGINE_ARG="${1:?usage: input_smoke.sh B|C}"
case "$ENGINE_ARG" in B|b|C|c) : ;; *) echo "engine must be B or C" >&2; exit 2 ;; esac
ENGINE="$ENGINE_ARG"
resolve_serial || die "no device for input smoke" input_smoke

OUT_DIR="${OUT:-$HARNESS_DIR/.state}"
mkdir -p "$OUT_DIR"

if [ "$ENGINE" = "B" ] || [ "$ENGINE" = "b" ]; then
  set +e
  adb_timeout "$INSTR_TO" input_smoke shell am instrument -w \
    -e class com.keeplab.app.benchmark.InputSmokeTest "$RUNNER" \
    > "$OUT_DIR/input-smoke.txt" 2>&1
  rc=$?
  set -e
  # `am instrument -w` reports OK (N tests); the round-trip assertion lives inside the test.
  if [ "$rc" -ne 0 ] || ! grep -Eq 'OK \([0-9]+ tests?\)' "$OUT_DIR/input-smoke.txt"; then
    printf 'INPUT_SMOKE_FAIL\n' >&2
    die "input capability smoke failed (Engine B, rc=$rc)" input_smoke
  fi
else
  export PATH="$PATH:${MAESTRO_BIN:-$HOME/.maestro/bin}"
  set +e
  with_timeout "$MAESTRO_TO" input_smoke maestro --device "$SERIAL" test --no-ansi \
    --no-reinstall-driver --format JUNIT --output "$OUT_DIR/input-smoke.xml" \
    "$BASE/maestro/INPUT-SMOKE.yaml" > "$OUT_DIR/input-smoke.txt" 2>&1
  rc=$?
  set -e
  if [ "$rc" -ne 0 ]; then
    printf 'INPUT_SMOKE_FAIL\n' >&2
    die "input capability smoke failed (Engine C, rc=$rc)" input_smoke
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
