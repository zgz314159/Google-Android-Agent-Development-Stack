#!/usr/bin/env bash
# Layout evidence provider with an explicit, never-faked fallback chain.
#
#   layout.sh <out-dir>
#
# Provider priority:
#   1. Android CLI layout  -> layout.json    (layout_provider=android_cli)
#   2. uiautomator dump    -> layout.xml     (layout_provider=uiautomator_xml)  [XML stays .xml]
#   3. neither             -> layout_provider=unavailable
#
# Prints `LAYOUT_PROVIDER=<value>` and, when unavailable, `LAYOUT_UNAVAILABLE_REASON=<text>`.
# Requires the device to be resolved (SERIAL) and reachable; callers guard device_ok.
set -euo pipefail
EVIDENCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANDROID_DIR="$(cd "$EVIDENCE_DIR/.." && pwd)"
# shellcheck source=../lib_android.sh
source "$ANDROID_DIR/lib_android.sh"

F="${1:?usage: layout.sh <out-dir>}"
mkdir -p "$F"
ANDROID_CLI="${ANDROID_CLI:-}"

LAYOUT_PROVIDER=unavailable
if [ -n "$ANDROID_CLI" ] && [ -x "$ANDROID_CLI" ]; then
  set +e
  with_timeout "$EVIDENCE_TO" evidence "$ANDROID_CLI" layout --device "$SERIAL" \
    --pretty --full --output="$F/layout.json" >/dev/null 2>&1
  rc=$?
  set -e
  if [ "$rc" -eq 0 ] && [ -s "$F/layout.json" ]; then
    LAYOUT_PROVIDER=android_cli
  else
    rm -f "$F/layout.json"
  fi
fi

if [ "$LAYOUT_PROVIDER" = "unavailable" ]; then
  set +e
  adb_timeout "$EVIDENCE_TO" evidence shell uiautomator dump /sdcard/_verify_fail.xml >/dev/null 2>&1
  r1=$?
  adb_timeout "$EVIDENCE_TO" evidence pull /sdcard/_verify_fail.xml "$F/layout.xml" >/dev/null 2>&1
  r2=$?
  set -e
  if [ "$r1" -eq 0 ] && [ "$r2" -eq 0 ] && [ -s "$F/layout.xml" ]; then
    LAYOUT_PROVIDER=uiautomator_xml
  else
    rm -f "$F/layout.xml"
  fi
fi

if [ "$LAYOUT_PROVIDER" = "unavailable" ]; then
  printf 'LAYOUT_UNAVAILABLE_REASON=%s\n' "android_cli and uiautomator providers both unavailable (or no device)"
fi
echo "LAYOUT_PROVIDER=$LAYOUT_PROVIDER"
