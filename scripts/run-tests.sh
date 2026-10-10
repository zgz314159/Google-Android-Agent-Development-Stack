#!/usr/bin/env bash
# run-tests.sh — the single offline gate runner.
#
# Guarantees that running the gates does NOT write generated material into the project:
#   * python bytecode -> $STACK_CACHE_ROOT/python-pycache   (PYTHONPYCACHEPREFIX)
#   * pytest cache    -> disabled                           (PYTEST_ADDOPTS=-p no:cacheprovider)
#   * Gradle caches   -> $STACK_CACHE_ROOT/gradle-user-home (GRADLE_USER_HOME)
#   * probe builds    -> $STACK_CACHE_ROOT (settings.gradle.kts redirects build dirs)
#
# Usage:
#   scripts/run-tests.sh [--root DIR] [--no-layout]
#     --root DIR   run the gates against another tree (e.g. a clean copy)
#     --no-layout  skip the verify-layout before/after checks
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
PY="${PYTHON:-python3}"
eval "$(PYTHON="$PY" "$HERE/stack-paths.sh" export)"

ROOT="$REPO"
DO_LAYOUT=1
while [ $# -gt 0 ]; do
  case "$1" in
    --root) ROOT="$2"; shift 2 ;;
    --no-layout) DO_LAYOUT=0; shift ;;
    -h|--help) sed -n '2,14p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

export PYTHONPYCACHEPREFIX="$STACK_CACHE_ROOT/python-pycache"
export PYTEST_ADDOPTS="-p no:cacheprovider"
export GRADLE_USER_HOME="$STACK_CACHE_ROOT/gradle-user-home"
mkdir -p "$PYTHONPYCACHEPREFIX" "$GRADLE_USER_HOME"

if [ "$DO_LAYOUT" = "1" ]; then
  echo "== layout BEFORE tests =="
  "$HERE/verify-layout.sh" --root "$ROOT" --quiet || { echo "LAYOUT_BEFORE=FAIL"; exit 1; }
  echo "LAYOUT_BEFORE=PASS"
fi

FAILS=0
run() { # run <label> <cmd...>
  local label="$1"; shift
  ( cd "$ROOT" && "$@" ) >/dev/null 2>&1
  local rc=$?
  printf '%-34s exit=%d\n' "$label" "$rc"
  [ "$rc" -eq 0 ] || FAILS=$((FAILS + 1))
}

run "bridge"            bash -c "cd orchestration/hermes/bridge && python3 -m unittest discover -s tests -p 'test_*.py'"
run "supervisor"        bash -c "cd orchestration/hermes/supervisor && python3 -m unittest discover -s tests -p 'test_*.py'"
run "evaluation"        python3 -m unittest discover -s evaluation/tests -p 'test_*.py'
run "evaluation-cc"     python3 -m unittest discover -s evaluation/commandcode/tests -p 'test_*.py'
run "verification-unit" python3 -m unittest discover -s verification/tests/unit -p 'test_*.py'
run "verification-smoke" bash verification/tests/smoke/selftest_static.sh
run "benchmark-harness" bash -c "cd verification-benchmark/harness && python3 -m unittest discover -s tests -p 'test_*.py'"
run "paths-and-tools"   python3 -m unittest discover -s scripts/tests -p 'test_*.py'
run "reference-replay"  python3 verification/reference-replay/tests/test_replay_offline.py
run "compiler"          python3 -m unittest discover -s specification/tests -p 'test_*.py'

if [ "$DO_LAYOUT" = "1" ]; then
  echo "== layout AFTER tests =="
  "$HERE/verify-layout.sh" --root "$ROOT" --quiet || { echo "LAYOUT_AFTER=FAIL"; exit 1; }
  echo "LAYOUT_AFTER=PASS"
fi

if [ "$FAILS" -eq 0 ]; then echo "GATES=PASS"; else echo "GATES=FAIL ($FAILS)"; fi
exit "$FAILS"
