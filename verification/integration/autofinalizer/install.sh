#!/usr/bin/env bash
# Auto-Finalizer user-service installer (Evaluation Core v0.2.1).
#
#   install.sh install|uninstall|enable|disable|start|stop|status
#
# Installs a systemd --user timer + oneshot service that periodically runs the
# non-invasive Auto-Finalizer `scan`. Non-root, bounded, crash-safe (the timer
# re-fires), and it never touches Command Code internals or /etc.
#
# Only ~/.config/systemd/user/ is written.
set -euo pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STACK="$(cd "$SELF_DIR/../../.." && pwd)"
PROJECTS="$(cd "$STACK/.." && pwd)"
UNIT_DIR="$HOME/.config/systemd/user"
SERVICE="commandcode-autofinalizer.service"
TIMER="commandcode-autofinalizer.timer"
OUTPUT_ROOT="${AUTOFINALIZER_OUTPUT_ROOT:-$("$STACK/scripts/stack-paths.sh" query STACK_EVALUATION_OUTPUT_ROOT 2>/dev/null)}"
if [ -z "$OUTPUT_ROOT" ]; then
  echo "FATAL: cannot resolve STACK_EVALUATION_OUTPUT_ROOT from the path contract" >&2
  echo "       set AUTOFINALIZER_OUTPUT_ROOT or fix scripts/stack-paths.sh" >&2
  exit 2
fi

if [ "$(id -u)" -eq 0 ]; then
  echo "refusing to run as root; this is a user-level service (use a normal user session)" >&2
  exit 2
fi

PYTHON="$(command -v python3 || true)"
if [ -z "$PYTHON" ]; then echo "python3 not found on PATH" >&2; exit 2; fi

usage() { echo "usage: install.sh install|uninstall|enable|disable|start|stop|status" >&2; exit 2; }
[ $# -eq 1 ] || usage
ACTION="$1"

render_service() {
  mkdir -p "$UNIT_DIR"
  sed -e "s|__PYTHON__|$PYTHON|g" \
      -e "s|__STACK__|$STACK|g" \
      -e "s|__HOME__|$HOME|g" \
      -e "s|__OUTPUT_ROOT__|$OUTPUT_ROOT|g" \
      "$SELF_DIR/commandcode-autofinalizer.service.in" > "$UNIT_DIR/$SERVICE"
  cp "$SELF_DIR/$TIMER" "$UNIT_DIR/$TIMER"
}

case "$ACTION" in
  install)
    render_service
    systemctl --user daemon-reload
    echo "installed: $UNIT_DIR/$SERVICE, $UNIT_DIR/$TIMER"
    echo "next: $0 enable"
    ;;
  uninstall)
    systemctl --user disable --now "$TIMER" >/dev/null 2>&1 || true
    rm -f "$UNIT_DIR/$SERVICE" "$UNIT_DIR/$TIMER"
    systemctl --user daemon-reload
    echo "uninstalled"
    ;;
  enable)
    systemctl --user enable --now "$TIMER"
    systemctl --user list-timers --no-pager "$TIMER" || true
    ;;
  disable)
    systemctl --user disable --now "$TIMER"
    echo "disabled"
    ;;
  start)
    # run a single scan now
    systemctl --user start "$SERVICE"
    echo "one scan started"
    ;;
  stop)
    systemctl --user stop "$TIMER"
    echo "stopped"
    ;;
  status)
    systemctl --user status --no-pager "$SERVICE" || true
    echo "---"
    systemctl --user list-timers --no-pager "$TIMER" || true
    ;;
  *) usage ;;
esac
