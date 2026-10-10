#!/usr/bin/env bash
# Reference Replay entry point. Deterministic external-app replay (Maestro).
#
#   run_reference_replay.sh [--flows R1,R2,R3] [--runs 3] [--serial 87296ada]
#
# Thin wrapper: all logic lives in replay.py (stdlib only). Exit code is non-zero
# unless every run is PASS.
set -euo pipefail
RR_RUNNER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$RR_RUNNER_DIR/replay.py" "$@"
