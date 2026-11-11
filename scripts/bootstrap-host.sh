#!/usr/bin/env bash
# bootstrap-host.sh — rebuild the host runtime from the project's immutable locks.
#
# Installs/verifies the EXACT Hermes revision pinned in
# orchestration/hermes/HERMES-LOCK.json, creates non-secret provider/profile templates
# under the XDG config root, and prepares the Playwright virtual environment.
#
# Chromium is NOT downloaded. Use --with-chromium only if you explicitly want it.
#
# Usage:
#   scripts/bootstrap-host.sh [--dry-run] [--with-chromium]
#
# Notes:
#   * Never advances a campaign and never touches bridge/campaign state.
#   * Never prints secret values; the API key is read from the environment or HERMES_HOME/.env.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
PY="${PYTHON:-python3}"

DRY_RUN=0
WITH_CHROMIUM=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --with-chromium) WITH_CHROMIUM=1 ;;
    -h|--help) sed -n '2,16p' "$0"; exit 0 ;;
    *) echo "unknown argument: $arg" >&2; exit 2 ;;
  esac
done

# ---- resolve the path contract (single source of truth) -------------------- #
eval "$(PYTHON="$PY" "$REPO/scripts/stack-paths.sh" export)"

LOCK="$REPO/orchestration/hermes/HERMES-LOCK.json"
read_lock() { "$PY" - "$LOCK" "$1" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1]))
print(doc.get(sys.argv[2], ""))
PY
}
COMMIT="$(read_lock commit_sha)"
UPSTREAM="$(read_lock upstream)"
BRANCH="$(read_lock branch)"
AGENT_DIR="$HERMES_HOME/hermes-agent"

run() { # run a command, or print it under --dry-run
  if [ "$DRY_RUN" = "1" ]; then printf 'DRY-RUN: %s\n' "$*"; else "$@"; fi
}

echo "bootstrap-host.sh"
echo "  PROJECT_ROOT       = $PROJECT_ROOT"
echo "  HERMES_HOME        = $HERMES_HOME"
echo "  STACK_STATE_ROOT   = $STACK_STATE_ROOT"
echo "  STACK_DATA_ROOT    = $STACK_DATA_ROOT"
echo "  STACK_CACHE_ROOT   = $STACK_CACHE_ROOT"
echo "  STACK_CONFIG_ROOT  = $STACK_CONFIG_ROOT"
echo "  Hermes pin         = ${COMMIT:-<missing>} (${BRANCH:-main}) from ${UPSTREAM:-<missing>}"
echo "  dry_run=$DRY_RUN with_chromium=$WITH_CHROMIUM"

echo
echo "[1/4] contract roots"
run "$PY" "$REPO/scripts/lib/stack_paths.py" ensure

echo
echo "[2/4] pinned Hermes runtime at $AGENT_DIR"
if [ -z "$COMMIT" ]; then echo "FATAL: HERMES-LOCK.json has no commit_sha" >&2; exit 1; fi
if [ -d "$AGENT_DIR/.git" ]; then
  have="$(git -C "$AGENT_DIR" rev-parse HEAD 2>/dev/null || echo none)"
  if [ "$have" = "$COMMIT" ]; then
    echo "  already at pinned commit $COMMIT"
  else
    echo "  checkout $COMMIT (was $have)"
    run git -C "$AGENT_DIR" fetch --all --tags
    run git -C "$AGENT_DIR" checkout "$COMMIT"
  fi
else
  echo "  clone $UPSTREAM -> $AGENT_DIR, checkout $COMMIT"
  run git clone "$UPSTREAM" "$AGENT_DIR"
  run git -C "$AGENT_DIR" checkout "$COMMIT"
  echo "  NOTE: run the official installer / dependency stage for this checkout before use"
fi
if [ "$DRY_RUN" = "0" ] && [ -d "$AGENT_DIR" ]; then
  got="$(git -C "$AGENT_DIR" rev-parse HEAD 2>/dev/null || echo none)"
  [ "$got" = "$COMMIT" ] || { echo "FATAL: Hermes HEAD $got != pinned $COMMIT" >&2; exit 1; }
fi

echo
echo "[3/4] provider/profile templates under $STACK_CONFIG_ROOT"
TPL_DIR="$REPO/orchestration/hermes/templates"
render() { # render <template> <dest>
  local t="$1" dest="$2"
  if [ "$DRY_RUN" = "1" ]; then
    printf 'DRY-RUN: render %s -> %s\n' "$t" "$dest"
  else
    sed -e "s|__STACK_ROOT__|$REPO|g" \
        -e "s|__HERMES_HOME__|$HERMES_HOME|g" \
        -e "s|__STACK_STATE_ROOT__|$STACK_STATE_ROOT|g" \
        -e "s|__STACK_DATA_ROOT__|$STACK_DATA_ROOT|g" "$t" > "$dest"
  fi
}
if [ -d "$TPL_DIR" ]; then
  run mkdir -p "$STACK_CONFIG_ROOT/profiles/android-stack"
  for t in "$TPL_DIR"/android-stack.*.template; do
    [ -e "$t" ] || continue
    dest="$STACK_CONFIG_ROOT/profiles/android-stack/$(basename "$t" | sed 's/^android-stack\.//; s/\.template$//')"
    render "$t" "$dest"
  done
  for t in "$TPL_DIR"/provider.env.template; do
    [ -e "$t" ] || continue
    dest="$HERMES_HOME/.env"
    if [ -e "$dest" ]; then echo "  keep existing $dest (do not overwrite credentials)"; else render "$t" "$dest"; fi
  done
else
  echo "  (no templates directory; nothing to render)"
fi
echo "  provider credential expected by name: COMMANDCODE_API_KEY (in $HERMES_HOME/.env); never printed"

echo
echo "[4/4] Playwright runtime"
PW_VENV="$STACK_STATE_ROOT/playwright/venv"
if [ -x "$PW_VENV/bin/python" ]; then
  echo "  venv already present: $PW_VENV"
else
  run "$PY" -m venv "$PW_VENV"
fi
run "$PW_VENV/bin/python" -m pip install --disable-pip-version-check --no-input playwright
if [ "$WITH_CHROMIUM" = "1" ]; then
  echo "  installing Chromium (explicitly requested)"
  run "$PW_VENV/bin/python" -m playwright install chromium
else
  echo "  Chromium NOT downloaded; use the installed Google Chrome via channel=\"chrome\""
fi

echo
if [ "$DRY_RUN" = "1" ]; then echo "bootstrap-host.sh: DRY RUN complete (no changes)"; else echo "bootstrap-host.sh: OK"; fi
