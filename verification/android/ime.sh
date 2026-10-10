#!/usr/bin/env bash
# Deterministic IME contract.
#
#   ime.sh <uiautomator|maestro>
#
# Promotes the IME from an implicit debugging condition to a formal precondition:
# verify exists -> enable -> set -> verify current. Failure is fatal (STOP) — the
# previous engine's IME is never assumed to persist.
#
# uiautomator -> Google LatinIME (ACTION_SET_TEXT); maestro -> AOSP LatinIME (inputText).
set -euo pipefail
ANDROID_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib_android.sh
source "$ANDROID_DIR/lib_android.sh"

ENGINE_ARG="${1:?usage: ime.sh uiautomator|maestro}"
case "$ENGINE_ARG" in uiautomator|maestro) : ;; *) echo "engine must be uiautomator or maestro" >&2; exit 2 ;; esac
ENGINE="$ENGINE_ARG"

resolve_serial || { printf 'IME_UNAVAILABLE\n' >&2; exit 1; }

COMP="$(ime_component_for "$ENGINE")"
PKGIME="$(ime_pkg_for "$ENGINE")"

set +e
ime_available "$COMP" "$PKGIME"; avail=$?
set -e
if [ "$avail" -ne 0 ]; then
  printf 'IME_UNAVAILABLE\n' >&2
  die "IME not available for engine $ENGINE: $COMP" ime
fi

with_timeout "$SHELL_TO" ime adb -s "$SERIAL" shell ime enable "$COMP" >/dev/null 2>&1 || die "ime enable failed: $COMP" ime
with_timeout "$SHELL_TO" ime adb -s "$SERIAL" shell ime set "$COMP" >/dev/null 2>&1 || die "ime set failed: $COMP" ime

ime_matches() {
  case "$1" in
    "$(ime_pkg_for "$2")"/*) return 0 ;;
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
