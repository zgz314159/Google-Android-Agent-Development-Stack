#!/usr/bin/env bash
# Failure bundle collector — deterministic, provider-explicit evidence chain.
#
#   step 1  Android CLI layout   -> layout.json   (layout_provider=android_cli)
#   step 2  uiautomator dump     -> layout.xml    (layout_provider=uiautomator_xml)
#   step 3  screenshot + logcat + dumpsys/state   (always, best-effort, bounded)
#
# The bundle must never single-point-depend on `android layout`. The XML fallback is kept
# as .xml and is NEVER relabelled as .json. Every unavailable artifact is recorded in
# metadata.json as {artifact, available:false, reason} — no silent missing files. Finally
# the bundle is validated by evidence_completeness.py.
# Usage: collect_failure.sh <run-dir>
set -euo pipefail
HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "$HARNESS_DIR/lib.sh"

OUT=${1:?usage: collect_failure.sh <run-dir>}
F="$OUT/failure"
mkdir -p "$F"

device_ok=0
if resolve_serial 2>/dev/null; then device_ok=1; fi
export SERIAL

screenshot_reason=""; logcat_reason=""; dumpsys_reason=""; layout_reason=""; executor_reason=""

# ---- step 3a: screenshot (always) ----
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

# ---- step 1: Android CLI layout (JSON) ----
LAYOUT_PROVIDER=unavailable
if [ "$device_ok" = 1 ]; then
  if [ -x "$ANDROID_CLI" ]; then
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
  # ---- step 2: uiautomator dump (XML fallback; stays .xml) ----
  if [ "$LAYOUT_PROVIDER" = "unavailable" ]; then
    set +e
    adb_timeout "$EVIDENCE_TO" evidence shell uiautomator dump /sdcard/_vc_fail.xml >/dev/null 2>&1
    r1=$?
    adb_timeout "$EVIDENCE_TO" evidence pull /sdcard/_vc_fail.xml "$F/layout.xml" >/dev/null 2>&1
    r2=$?
    set -e
    if [ "$r1" -eq 0 ] && [ "$r2" -eq 0 ] && [ -s "$F/layout.xml" ]; then
      LAYOUT_PROVIDER=uiautomator_xml
    else
      rm -f "$F/layout.xml"
    fi
  fi
fi
if [ "$LAYOUT_PROVIDER" = "unavailable" ]; then
  layout_reason="android_cli and uiautomator providers both unavailable (or no device)"
fi

# ---- step 3b: logcat + dumpsys/state (always, bounded) ----
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

# merge in-process failure artifacts (assertion/db-state/screenshot) if present
if [ -f "$OUT/executor.txt" ]; then
  cp "$OUT/executor.txt" "$F/executor-output.txt" 2>/dev/null || executor_reason="copy failed"
else
  executor_reason="no executor.txt (run did not reach instrumentation)"
fi
if [ -d "$OUT/bench/failure" ]; then
  cp -f "$OUT/bench/failure/"* "$F/" 2>/dev/null || true
fi

# ---- metadata: record layout_provider + per-artifact availability (merge; never fabricate) ----
python3 - "$F" "$LAYOUT_PROVIDER" "$SERIAL" "$ENGINE" "$JOURNEY" "$RUN_ID" "$device_ok" \
  "$screenshot_reason" "$logcat_reason" "$dumpsys_reason" "$layout_reason" "$executor_reason" <<'PY'
import json, sys, pathlib
from datetime import datetime, timezone
(f, provider, serial, engine, journey, run_id, device_ok, scr_r, log_r, dmp_r, lay_r, exe_r) = sys.argv[1:13]
f = pathlib.Path(f)
meta_path = f / "metadata.json"
meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
if engine:
    meta.setdefault("engine", engine)
if journey:
    meta.setdefault("journey", journey)
if run_id:
    meta.setdefault("run_id", run_id)
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
python3 "$HARNESS_DIR/evidence_completeness.py" "$F"
comp_rc=$?
set -e
ls -1 "$F"
exit "$comp_rc"
