#!/usr/bin/env bash
# Root-only install from a root-exclusive extracted copy. Never reads the external workspace.
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { printf 'INSTALL_FAILED: root required\n' >&2; exit 1; }
SRC="$(cd "$(dirname "$0")" && pwd)"
WRAPPER="$SRC/run_registered_task"
[ -f "$WRAPPER" ] && [ ! -L "$WRAPPER" ] || { printf 'INSTALL_FAILED: wrapper missing\n' >&2; exit 1; }
EXPECTED_WRAPPER_SHA=f97b8f26d11e699101d6395af5599f85de4034c2fca06e63662973caf376b57c
GOT="$(sha256sum "$WRAPPER" | awk '{print $1}')"
[ "$GOT" = "$EXPECTED_WRAPPER_SHA" ] || { printf 'INSTALL_FAILED: wrapper hash mismatch\n' >&2; exit 1; }
TARGET_DIR=/usr/local/lib/aegl-bridge
TARGET="$TARGET_DIR/run_registered_task"
SUDOERS=/etc/sudoers.d/aegl-bridge-run-registered-task
[ ! -e "$TARGET_DIR" ] || { printf 'INSTALL_FAILED: target dir exists: %s\n' "$TARGET_DIR" >&2; exit 1; }
[ ! -e "$SUDOERS" ] || { printf 'INSTALL_FAILED: sudoers file exists: %s\n' "$SUDOERS" >&2; exit 1; }
command -v visudo >/dev/null 2>&1 || { printf 'INSTALL_FAILED: visudo missing\n' >&2; exit 1; }
install -d -o root -g root -m 0755 "$TARGET_DIR"
install -o root -g root -m 0755 "$WRAPPER" "$TARGET"
cat > "$SUDOERS" <<'EOS'
zhong ALL=(root) NOPASSWD: /usr/local/lib/aegl-bridge/run_registered_task
EOS
chown root:root "$SUDOERS"
chmod 0440 "$SUDOERS"
visudo -cf "$SUDOERS"
[ "$(stat -c '%U:%G %a' "$TARGET")" = "root:root 755" ] || { printf 'INSTALL_FAILED: target mode\n' >&2; exit 1; }
[ "$(stat -c '%U:%G %a' "$SUDOERS")" = "root:root 440" ] || { printf 'INSTALL_FAILED: sudoers mode\n' >&2; exit 1; }
printf 'INSTALL_TARGET=%s\n' "$TARGET"
printf 'INSTALL_SUDOERS=%s\n' "$SUDOERS"
printf 'INSTALL=OK\n'
