# Expected FAIL bundle layout (reference)

On FAIL the runner writes `<run-dir>/failure/` and validates it with
`core/evidence_completeness.py`. Required files (or an explicit
`{name, available:false, reason}` entry in `metadata.json`):

```
failure/
├── metadata.json          # {layout_provider, artifacts[{name,file,available,reason?}], ...}
├── executor-output.txt    # am instrument / maestro output
├── failed-assertion.json  # emitted by FailureBundleRule inside the test process
├── logcat.txt             # host-captured, bounded
├── screenshot.png         # host-captured (may be declared unavailable)
├── db-state.json          # project oracle state (may be declared unavailable)
├── layout.json            # android_cli provider (preferred)
│   OR layout.xml          # uiautomator_xml provider — XML is NEVER relabelled .json
├── dumpsys-activity-top.txt
├── dumpsys-window.txt
└── completeness.json      # written by evidence_completeness.py
```

`layout_provider ∈ {android_cli, uiautomator_xml, unavailable}`.

Example `metadata.json`:

```json
{
  "engine": "uiautomator",
  "journey": "J1",
  "run_id": "KEEPLAB-REFERENCE-J1",
  "device_serial": "87296ada",
  "device_available": true,
  "layout_provider": "android_cli",
  "evidence_steps": ["screenshot", "android_cli", "logcat", "dumpsys"],
  "artifacts": [
    {"name": "metadata", "file": "metadata.json", "available": true},
    {"name": "screenshot", "file": "screenshot.png", "available": true},
    {"name": "layout", "file": "layout.json", "available": true},
    {"name": "logcat", "file": "logcat.txt", "available": true},
    {"name": "dumpsys", "file": "dumpsys-activity-top.txt", "available": true},
    {"name": "executor-output", "file": "executor-output.txt", "available": true},
    {"name": "failed-assertion", "file": "failed-assertion.json", "available": true},
    {"name": "db-state", "file": "db-state.json", "available": true}
  ],
  "timestamp": "2026-10-03T16:00:25Z"
}
```
