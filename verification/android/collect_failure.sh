#!/usr/bin/env bash
# Failure bundle collector — deterministic, provider-explicit evidence chain.
#
#   collect_failure.sh <run-dir>
#
# The bundle must never single-point-depend on `android layout`. The XML fallback is kept
# as .xml and is NEVER relabelled as .json. Every unavailable artifact is recorded in
# metadata.json as {artifact, available:false, reason} — no silent missing files. Finally
# the bundle is validated by core/evidence_completeness.py.
#
# Environment: ENGINE, JOURNEY, RUN_ID, VERIFICATION_ID (optional), OUT (defaults to arg).
set -euo pipefail
ANDROID_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib_android.sh
source "$ANDROID_DIR/lib_android.sh"

OUT=${1:?usage: collect_failure.sh <run-dir>}
export OUT
F="$OUT/failure"
mkdir -p "$F"

device_ok=0
if resolve_serial 2>/dev/null; then device_ok=1; fi

screenshot_reason=""; logcat_reason=""; dumpsys_reason=""; layout_reason=""; executor_reason=""

# ---- screenshot (always, when a device is available) ----
if [ "$device_ok" = 1 ]; then
  set +e
  adb_timeout "$EVIDENCE_TO" evidence exec-out screencap -p > "$F/screenshot.png" 2>/dev/null
  rc=$?
  set -e
  if [ "$rc" -ne 0 ] || [ ! -s "$F/screenshot.png" ]; then
    rm -f "$F/screenshot.png"; screenshot_reason="screencap failed (rc=$rc)"
  fi
else
  screenshot_reason="no device available"
fi

# ---- layout provider chain (android_cli -> uiautomator_xml -> unavailable) ----
LAYOUT_PROVIDER=unavailable
if [ "$device_ok" = 1 ]; then
  layout_out="$(SERIAL="$SERIAL" OUT="$OUT" bash "$ANDROID_DIR/evidence/layout.sh" "$F" 2>&1 || true)"
  LAYOUT_PROVIDER="$(printf '%s\n' "$layout_out" | sed -n 's/^LAYOUT_PROVIDER=//p' | tail -1)"
  [ -n "$LAYOUT_PROVIDER" ] || LAYOUT_PROVIDER=unavailable
  layout_reason="$(printf '%s\n' "$layout_out" | sed -n 's/^LAYOUT_UNAVAILABLE_REASON=//p' | tail -1)"
fi
if [ "$LAYOUT_PROVIDER" = "unavailable" ] && [ -z "$layout_reason" ]; then
  layout_reason="android_cli and uiautomator providers both unavailable (or no device)"
fi

# ---- logcat + dumpsys (always, bounded) ----
if [ "$device_ok" = 1 ]; then
  set +e
  adb_timeout "$EVIDENCE_TO" evidence logcat -d > "$F/logcat.txt" 2>&1; rc=$?
  set -e
  if [ "$rc" -ne 0 ] || [ ! -s "$F/logcat.txt" ]; then rm -f "$F/logcat.txt"; logcat_reason="logcat failed (rc=$rc)"; fi

  set +e
  adb_timeout "$EVIDENCE_TO" evidence shell dumpsys activity top > "$F/dumpsys-activity-top.txt" 2>&1; rc=$?
  set -e
  if [ "$rc" -ne 0 ] || [ ! -s "$F/dumpsys-activity-top.txt" ]; then
    rm -f "$F/dumpsys-activity-top.txt"; dumpsys_reason="dumpsys activity top failed (rc=$rc)"
  fi

  set +e
  adb_timeout "$EVIDENCE_TO" evidence shell dumpsys window windows > "$F/dumpsys-window.txt" 2>&1; rc=$?
  set -e
  if [ "$rc" -ne 0 ] || [ ! -s "$F/dumpsys-window.txt" ]; then
    rm -f "$F/dumpsys-window.txt"; dumpsys_reason="${dumpsys_reason:-}dumpsys window failed (rc=$rc)"
  fi
else
  logcat_reason="no device available"; dumpsys_reason="no device available"
fi

# ---- merge in-process failure artifacts (assertion/db-state/screenshot) ----
if [ -f "$OUT/executor.txt" ]; then
  cp "$OUT/executor.txt" "$F/executor-output.txt" 2>/dev/null || executor_reason="copy failed"
else
  executor_reason="no executor.txt (run did not reach instrumentation)"
fi
if [ -d "$OUT/bench/failure" ]; then
  cp -f "$OUT/bench/failure/"* "$F/" 2>/dev/null || true
fi

# ---- metadata: layout_provider + per-artifact availability (merge; never fabricate) ----
python3 - "$F" "$LAYOUT_PROVIDER" "$SERIAL" "$ENGINE" "$JOURNEY" "$RUN_ID" "$VERIFICATION_ID" "$device_ok" \
  "$screenshot_reason" "$logcat_reason" "$dumpsys_reason" "$layout_reason" "$executor_reason" <<'PY'
import json, sys, pathlib
from datetime import datetime, timezone
(f, provider, serial, engine, journey, run_id, verification_id, device_ok,
 scr_r, log_r, dmp_r, lay_r, exe_r) = sys.argv[1:14]
f = pathlib.Path(f)
meta_path = f / "metadata.json"
meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
for k, v in (("engine", engine), ("journey", journey), ("run_id", run_id), ("verification_id", verification_id)):
    if v:
        meta.setdefault(k, v)
meta["device_serial"] = serial or meta.get("device_serial")
meta["device_available"] = device_ok == "1"
meta["layout_provider"] = provider
meta["evidence_steps"] = ["screenshot", provider, "logcat", "dumpsys"]
meta["timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def present(name):
    p = f / name
    return p.is_file() and p.stat().st_size > 0

layout_file = None
for cand in ("layout.json", "layout.xml"):
    if present(cand):
        layout_file = cand
        break

spec = [
    ("metadata", "metadata.json", None, False),
    ("screenshot", "screenshot.png", scr_r, True),
    ("layout", layout_file, lay_r, True),
    ("logcat", "logcat.txt", log_r, True),
    ("dumpsys", "dumpsys-activity-top.txt", dmp_r, True),
    ("executor-output", "executor-output.txt", exe_r, True),
    ("failed-assertion", "failed-assertion.json", "not emitted", True),
    ("db-state", "db-state.json", "not emitted", True),
]
artifacts = []
for name, fname, reason, allow_unavail in spec:
    available = present(fname) if fname else True
    entry = {"name": name, "file": fname, "available": available}
    if not available:
        entry["reason"] = reason or "unavailable"
    artifacts.append(entry)
meta["artifacts"] = artifacts
meta_path.write_text(json.dumps(meta, indent=2))
PY

echo "FAILURE_BUNDLE=$F"
echo "LAYOUT_PROVIDER=$LAYOUT_PROVIDER"

set +e
python3 "$VERIFY_CORE/evidence_completeness.py" "$F"
comp_rc=$?
set -e
ls -1 "$F"
exit "$comp_rc"
