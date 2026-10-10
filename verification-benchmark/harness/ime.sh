#!/usr/bin/env bash
# Deterministic IME contract. Promotes the IME from an implicit debugging condition to a
# formal precondition:
#
#   ime.sh <B|C>
#
# Engine B needs the Google IME (UiAutomator ACTION_SET_TEXT); Engine C needs the AOSP
# LatinIME (Maestro inputText). Verify exists -> enable -> set -> verify current. Failure
# is fatal (STOP) — we never assume the previous engine's IME is still correct.
set -euo pipefail
HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "$HARNESS_DIR/lib.sh"

ENGINE_ARG="${1:?usage: ime.sh B|C}"
case "$ENGINE_ARG" in B|b|C|c) : ;; *) echo "engine must be B or C" >&2; exit 2 ;; esac
ENGINE="$ENGINE_ARG"

resolve_serial || { printf 'IME_UNAVAILABLE\n' >&2; exit 1; }

COMP="$(ime_component_for "$ENGINE")"
PKG="$(ime_pkg_for "$ENGINE")"

# verify exists
set +e
if ! ime_available "$COMP" "$PKG"; then
  set -e
  printf 'IME_UNAVAILABLE\n' >&2
  die "IME not available for engine $ENGINE: $COMP" ime
fi
set -e

# enable + set (bounded)
with_timeout "$SHELL_TO" ime adb -s "$SERIAL" shell ime enable "$COMP" >/dev/null 2>&1 || die "ime enable failed: $COMP" ime
with_timeout "$SHELL_TO" ime adb -s "$SERIAL" shell ime set "$COMP" >/dev/null 2>&1 || die "ime set failed: $COMP" ime

# verify current IME matches (small bounded settle for the IME service)
ime_matches() {
  local cur="$1" eng="$2" pkg
  pkg="$(ime_pkg_for "$eng")"
  case "$cur" in
    "$pkg"/*) return 0 ;;
    *) return 1 ;;
  esac
}

cur=""
for _ in 1 2 3 4 5; do
  cur="$(ime_current 2>/dev/null || true)"
  if ime_matches "$cur" "$ENGINE"; then break; fi
  sleep 1
done

if ! ime_matches "$cur" "$ENGINE"; then
  printf 'IME_SET_FAILED=expected:%s actual:%s\n' "$COMP" "$cur" >&2
  die "IME verification failed for engine $ENGINE (current=$cur)" ime
fi

echo "IME_SET=$COMP"
echo "IME_VERIFIED=$cur"
