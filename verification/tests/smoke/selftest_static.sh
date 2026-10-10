#!/usr/bin/env bash
# Static self-test: bash syntax, Python compile, JSON schemas, unit tests, plan validation,
# decoupling audit. No device required.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERIFY="$(cd "$HERE/../.." && pwd)"

fail=0

echo "== bash -n =="
while IFS= read -r f; do
  if bash -n "$f"; then echo "OK  ${f#"$VERIFY"/}"; else echo "FAIL ${f#"$VERIFY"/}"; fail=1; fi
done < <(find "$VERIFY/runner" "$VERIFY/android" "$VERIFY/core" "$VERIFY/challengers" "$VERIFY/integration" -name '*.sh' 2>/dev/null | sort)

echo "== py_compile =="
if python3 -m py_compile $(find "$VERIFY/core" "$VERIFY/runner" "$VERIFY/adapters" "$VERIFY/integration" "$VERIFY/tests" -name '*.py' 2>/dev/null); then
  echo "OK  python modules"
else
  echo "FAIL py_compile"; fail=1
fi

echo "== json schemas parse =="
for f in "$VERIFY"/contracts/*.schema.json; do
  if python3 -c "import json,sys;json.load(open(sys.argv[1]))" "$f"; then echo "OK  $(basename "$f")"; else echo "FAIL $(basename "$f")"; fail=1; fi
done

echo "== unit tests =="
if python3 -m unittest discover -s "$VERIFY/tests/unit" -t "$VERIFY" -v; then
  echo "OK  unit tests"
else
  echo "FAIL unit tests"; fail=1
fi

echo "== example plan validation =="
for plan in "$VERIFY"/examples/keeplab/verification-plan*.json; do
  if python3 "$VERIFY/core/plan_validate.py" "$plan" >/dev/null; then echo "OK  $(basename "$plan")"; else echo "FAIL $(basename "$plan")"; fail=1; fi
done

echo "== decoupling audit =="
if python3 "$VERIFY/tests/unit/test_decoupling_audit.py" | grep -q 'DECOUPLING_AUDIT=PASS'; then
  echo "OK  decoupling audit"
else
  echo "FAIL decoupling audit"; fail=1
fi

echo "== timeout / watchdog =="
TO_OUT="$(VERIFY_ROOT="$VERIFY" bash -c 'source "$1/core/lib_common.sh"; set -e; with_timeout 1 timeout_probe sleep 5' _ "$VERIFY" 2>&1 || true)"
if printf '%s' "$TO_OUT" | grep -q 'TIMEOUT_STAGE=timeout_probe'; then
  echo "OK  with_timeout emits TIMEOUT_STAGE"
else
  echo "FAIL with_timeout did not emit TIMEOUT_STAGE"; echo "$TO_OUT"; fail=1
fi

if [ "$fail" -ne 0 ]; then
  echo "SELFTEST_STATIC=FAIL"
  exit 1
fi
echo "SELFTEST_STATIC=PASS"
