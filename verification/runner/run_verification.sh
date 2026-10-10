#!/usr/bin/env bash
# Verification Layer runner — single user entry point.
#
#   run_verification.sh <verification-plan.json> [--run-root DIR] [--dry-run]
#                       [--skip-input-smoke] [--skip-cleanup]
#
# Validates the plan, drives the bounded verification flow on the target device, and emits
# a compact verification-result.json on PASS or a failure bundle on FAIL. Exit code is 0
# for PASS, non-zero otherwise.
set -euo pipefail

RUNNER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$RUNNER_DIR/orchestrator.py" "$@"
