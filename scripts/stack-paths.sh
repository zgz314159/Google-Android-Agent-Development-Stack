#!/usr/bin/env bash
# Shell query command for the canonical Stack filesystem path contract.
#
# This is a thin wrapper over scripts/lib/stack_paths.py (the single source of truth);
# it never re-implements the resolution logic.
#
# Usage:
#   scripts/stack-paths.sh                # JSON of every root
#   scripts/stack-paths.sh query NAME     # one resolved path
#   scripts/stack-paths.sh export         # eval-able `export NAME=value` lines
#   scripts/stack-paths.sh ensure [NAME]  # create the contract roots (0700)
#
# Source the roots into the current shell:
#   eval "$(scripts/stack-paths.sh export)"
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${PYTHON:-python3}"
exec "$PY" "$HERE/lib/stack_paths.py" "$@"
