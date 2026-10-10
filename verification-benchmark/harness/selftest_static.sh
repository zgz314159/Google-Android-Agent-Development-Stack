#!/usr/bin/env bash
# Static hardening self-test: bash syntax, Python compile, unit tests. No device required.
set -euo pipefail
HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

fail=0

echo "== bash -n =="
for f in "$HARNESS_DIR"/*.sh; do
  if bash -n "$f"; then echo "OK  $(basename "$f")"; else echo "FAIL $(basename "$f")"; fail=1; fi
done

echo "== py_compile =="
if python3 -m py_compile "$HARNESS_DIR"/*.py; then echo "OK  python modules"; else echo "FAIL py_compile"; fail=1; fi

echo "== unit tests =="
if python3 -m unittest discover -s "$HARNESS_DIR/tests" -t "$HARNESS_DIR" -v; then
  echo "OK  unit tests"
else
  echo "FAIL unit tests"; fail=1
fi

echo "== timeout / watchdog =="
TO_OUT="$(HARNESS_DIR="$HARNESS_DIR" bash -c 'source "$HARNESS_DIR/lib.sh"; set -e; with_timeout 1 timeout_probe sleep 5' 2>&1 || true)"
if printf '%s' "$TO_OUT" | grep -q 'TIMEOUT_STAGE=timeout_probe'; then
  echo "OK  with_timeout emits TIMEOUT_STAGE"
else
  echo "FAIL with_timeout did not emit TIMEOUT_STAGE"; echo "$TO_OUT"; fail=1
fi

RS_TMP="$(mktemp -d)"
HARNESS_DIR="$HARNESS_DIR" OUT="$RS_TMP" RUN_ID=T JOURNEY=J1 ENGINE=B \
  bash -c 'source "$HARNESS_DIR/lib.sh"; stage instrumentation' >/dev/null 2>&1 || true
if python3 -c "import json,sys;d=json.load(open('$RS_TMP/run-state.json'));assert d['stage']=='instrumentation' and d['last_progress_at'] and d['started_at']" 2>/dev/null; then
  echo "OK  run-state heartbeat written"
else
  echo "FAIL run-state heartbeat"; fail=1
fi
rm -rf "$RS_TMP"

if [ "$fail" -ne 0 ]; then
  echo "SELFTEST_STATIC=FAIL"
  exit 1
fi
echo "SELFTEST_STATIC=PASS"
