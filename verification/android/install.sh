#!/usr/bin/env bash
# Idempotent APK install + package verification.
#
#   install.sh <apk> <package>
set -euo pipefail
ANDROID_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib_android.sh
source "$ANDROID_DIR/lib_android.sh"

APK="${1:?usage: install.sh <apk> <package>}"
PACKAGE="${2:?usage: install.sh <apk> <package>}"

resolve_serial || die "no device for install" install
install_idempotent "$APK" "$PACKAGE"
echo "INSTALL_OK=$PACKAGE"
