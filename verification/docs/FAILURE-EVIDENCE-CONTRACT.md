# Failure Evidence Contract (v1.0.0)

Deterministic verification is **failure-only**: the PASS path stays compact, and a failure
produces a complete, provider-explicit evidence bundle with no human in the loop.

## 1. PASS path

A single compact `verification-result.json` is written. No screenshots or logcat are kept.

## 2. FAIL path — bundle contents

Written to `<run-dir>/failure/` and validated by `core/evidence_completeness.py`
(`EVIDENCE_COMPLETE=true|false`):

| Artifact | Source |
|---|---|
| `metadata.json` | host — layout provider + per-artifact availability |
| `executor-output.txt` | host — `am instrument`/maestro output |
| `failed-assertion.json` | device — `FailureBundleRule` (in-process assertion) |
| `logcat.txt` | host — bounded |
| `screenshot.png` | host — may be declared unavailable with a reason |
| `db-state.json` | device — project oracle state; may be declared unavailable |
| `layout.json` **or** `layout.xml` | host — see provider chain |
| `dumpsys-activity-top.txt`, `dumpsys-window.txt` | host |
| `completeness.json` | `evidence_completeness.py` |

Every artifact that is absent **must** appear in `metadata.json.artifacts` as
`{name, available: false, reason}`. Nothing is silently missing.

## 3. Layout provider chain (never faked)

```
1. android_cli layout   -> layout.json   (layout_provider = android_cli)
2. uiautomator dump     -> layout.xml    (layout_provider = uiautomator_xml)
3. neither              -> layout_provider = unavailable  (+ explicit reason)
```

Format rule: a `.json` artifact must parse as JSON; a `.xml` artifact must be XML. The
uiautomator dump XML is **never** relabelled as `.json`.

## 4. Device-side producer contract

The project's instrumentation must write, into the app's external files `bench/` dir:

- `events-<runId>.jsonl` — `{kind,name,run_id,journey,elapsed_realtime_ns,epoch_ms}` with span
  kinds `ACTION_START/END`, `ASSERT_START/END`, `EVIDENCE_START/END`, `RUN_START/END`.
- `verify-part.json` — `{journey, outcome, database:{checked, checks:[{name,expected,actual,pass}]}}`.
- On assertion failure, into `bench/failure/`: `failed-assertion.json`, `screenshot.png`,
  `db-state.json`, `metadata.json` (the reference `FailureBundleRule` does this).

Reference sources: `android/uiautomator/*.kt`.

## 5. Machine markers (deterministic debugging trail)

`STAGE_FAIL=<stage>` · `TIMEOUT_STAGE=<stage>` · `HARNESS_ERROR=<msg>` ·
`APK_SHA_MISMATCH=…` · `TEST_APK_SHA_MISMATCH=…` · `PREFLIGHT_FAIL` · `IME_UNAVAILABLE` ·
`IME_SET_FAILED=…` · `INPUT_SMOKE_FAIL` · `CLEANUP_INCOMPLETE` ·
`UIAUTOMATION_CONFLICT_SUSPECTED` · `DEVICE_LOCKED_REQUIRES_OWNER_UNLOCK`.
