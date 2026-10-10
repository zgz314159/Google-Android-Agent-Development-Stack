#!/usr/bin/env bash
# run_capture.sh — exit-code-preserving command runner (v1.0.1).
#
#   run_capture.sh <logfile> <cmd> [args...]
#
# Runs <cmd>, streams its combined output to <logfile>, renders the tail to stderr, and
# exits with <cmd>'s REAL exit status. It exists so a human/agent/CI never writes
# `cmd | tail`, which silently replaces the upstream exit code with tail's 0 and hides
# build/test/verification failures from the Evaluation layer.
#
#   Intended (correct):   run_capture.sh build.log ./gradlew ...   # rc = gradle rc
#   Forbidden (masking):  ./gradlew ... 2>&1 | tail               # rc = tail's 0
#
# Environment:
#   RUN_CAPTURE_TAIL   lines of tail to show (default 40)
set -uo pipefail

log="${1:?usage: run_capture.sh <logfile> <cmd> [args...]}"
shift
[ "$#" -ge 1 ] || { printf 'usage: run_capture.sh <logfile> <cmd> [args...]\n' >&2; exit 2; }

"$@" >"$log" 2>&1
rc=$?

tail -n "${RUN_CAPTURE_TAIL:-40}" "$log" >&2
exit "$rc"
