#!/usr/bin/env bash
# Deterministic device-state lifecycle.
#
#   lifecycle.sh snapshot      capture current device state
#   lifecycle.sh apply         apply the deterministic baseline (portrait, light, stay-awake)
#   lifecycle.sh restore       restore the snapshot captured by `snapshot`
#
# Snapshot/restore are best-effort and bounded; `restore` never masks a primary outcome
# failure (callers decide how to treat a non-zero return).
set -euo pipefail
ANDROID_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib_android.sh
source "$ANDROID_DIR/lib_android.sh"

ACTION="${1:?usage: lifecycle.sh snapshot|apply|restore}"
resolve_serial || die "no device for lifecycle $ACTION" lifecycle

case "$ACTION" in
  snapshot)
    state_snapshot
    echo "LIFECYCLE_SNAPSHOT=OK state=$STATE_FILE"
    ;;
  apply)
    set +e
    adb_ shell settings put system accelerometer_rotation 0 >/dev/null 2>&1
    adb_ shell settings put system user_rotation 0 >/dev/null 2>&1
    adb_ shell cmd uimode night no >/dev/null 2>&1
    adb_ shell svc power stayon true >/dev/null 2>&1
    set -e
    echo "LIFECYCLE_APPLY=OK"
    ;;
  restore)
    if state_restore; then
      echo "LIFECYCLE_RESTORE=OK"
    else
      echo "LIFECYCLE_RESTORE=PARTIAL" >&2
      exit 1
    fi
    ;;
  *)
    echo "usage: lifecycle.sh snapshot|apply|restore" >&2
    exit 2
    ;;
esac
