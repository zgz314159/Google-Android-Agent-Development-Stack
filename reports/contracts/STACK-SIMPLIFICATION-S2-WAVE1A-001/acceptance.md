# STACK-SIMPLIFICATION-S2-WAVE1A-001 — Acceptance Criteria

Package: `Google-Android-Agent-Development-Stack/reports/contracts/STACK-SIMPLIFICATION-S2-WAVE1A-001/`
Contract: `STACK-SIMPLIFICATION-S2-WAVE1A-001` (v0.1.0, temporary current-format contract)
Scope: evaluation classification cleanup + shadow observability preparation + proof tooling consolidation
Device: `87296ada` — NOT USED. Zero visual LLM judgment. Deterministic local verification only.

This file carries the DETAIL the lean `implementation-contract.json` delegates. The contract is
normative for scope, boundaries, hashes and stop conditions; this file is normative for the exact
acceptance evidence. Where they differ, the stricter reading wins and the executor must STOP with
`CONTRACT_DEVIATION`.

---

## 1. Measured baseline (evidence, not estimate)

| Metric | M4 value |
|---|---|
| `wait_device_sec` total | 105.567 |
| `wait_device_sec` truly device-attributable | 0.000 (device was NOT used) |
| `unknown_sec` | 508.979 |
| `unknown_share_of_agent_owned` | 0.116 |
| UNKNOWN span count | 7 |
| agent-owned wall | 4393.729 |
| total wait-tag wall | 671.244 |
| logical failures | FAIL-001, FAIL-003, FAIL-004 |
| repairs | REPAIR-002, REPAIR-003 |
| requests / input / output / cache read / cache write | 113 / 673851 / 148391 / 25064448 / 0 |

Fixture: `HERMES-20261006_171926_af865e`
Transcript: `/mnt/AndroidDev/Projects/_evaluation/_hermes_staging/20261006_171926_af865e.jsonl`
Results: `/mnt/AndroidDev/Projects/_evaluation/Google-Android-Agent-Development-Stack/HERMES-20261006_171926_af865e/`
All of the above is READ-ONLY. Nothing in that tree may be written.

---

## 2. Defect A — the T7c WAIT_DEVICE false positive (proven root cause)

`evaluation/commandcode/phase_rules.json` → rule `t7c_evidence_cmd` contains the alternative

```
(layout|ui|window_dump)[^|;&\n]*\.(json|xml)
```

`core.py::PhaseMapper._match` applies `command_regex` to the tool's command string with
`re.search`, case-insensitively. The substring `ui` therefore matches INSIDE the word `build`, and
anything later in the same command that ends in `.xml` closes the match. The result is a build or
manifest inspection classified `T7 / T7c / WAIT_DEVICE`.

Live reproduction performed by the contract-creation phase: applying the current rule to the M4
transcript yields EXACTLY 3 matching shell calls, and those are exactly the 3 T7c spans
(9.175 + 43.578 + 52.814 = 105.567 s):

| Span | Row | Seconds | Matched substring |
|---|---:|---:|---|
| TURN-0018 | h000061 | 9.175 | `uild.gradle.kts gradle/libs.versions.toml app/src/main/AndroidManifest.xml` |
| TURN-0110 | h000351 | 43.578 | `uild/intermediates -name "AndroidManifest.xml` |
| TURN-0111 | h000353 | 52.814 | `uild/intermediates/merged_manifests/debug/processDebugManifest/AndroidManifest.xml` |

None of the three is a device operation. The device was not used in M4 at all.

### 2.1 The three exact false-positive commands (must NOT be T7c after the fix)

1. TURN-0018 / h000061

```
cd /mnt/AndroidDev/Projects/KeepLab-Relay; wc -l app/build.gradle.kts gradle/libs.versions.toml app/src/main/AndroidManifest.xml app/src/test -R 2>/dev/null | tail -5; find app/src/test -name "*.kt" | xargs wc -l | sort -n
```

2. TURN-0110 / h000351

```
cd /mnt/AndroidDev/Projects/KeepLab-Relay && f=$(find app/build/intermediates -name "AndroidManifest.xml" -path "*merged*" | head -1); echo "MERGED: $f"; grep -o 'android:name="android.permission[^"]*"' "$f" 2>/dev/null | sort -u; echo "--- FileProvider present? ---"; grep -c "provider" "$f" 2>/dev/null
```

3. TURN-0111 / h000353

```
cd /mnt/AndroidDev/Projects/KeepLab-Relay && f=app/build/intermediates/merged_manifests/debug/processDebugManifest/AndroidManifest.xml; grep -o 'android:name="[^"]*provider[^"]*"' "$f" | sort -u; echo "--- fileprovider mentions ---"; grep -ci "fileprovider" "$f"; echo "--- source manifest mtime/unchanged ---"; ls -l app/src/main/AndroidManifest.xml; find app/build/intermediates/merged_manifests -name "*.xml" | wc -l
```

Additional non-device classes that must also stay non-T7c:

- `test-results.xml`, `androidTest-results/**`, `build/intermediates/**` inspection
- any command whose only `ui` occurrence is inside `build`, `buildDir`, `rebuild`, or a path segment
  such as `app/build/...`
- pure `wc`, `find`, `grep`, `ls`, `cat`, `sort` over source or build artifacts

### 2.2 Genuine device/evidence commands (must STILL be T7 / T7c / WAIT_DEVICE)

- `adb shell uiautomator dump /sdcard/window_dump.xml`
- `adb exec-out screencap -p > /tmp/screen.png`
- `adb shell dumpsys window windows`, `adb shell dumpsys activity`
- `adb shell getprop ro.product.model`
- `adb logcat -d > logcat.txt`
- `adb shell input tap X Y`, `adb shell input text ...`, `adb shell input keyevent ...`
- `read_file` of a saved `window_dump*.xml`, `layout*.json`, `final_state*.json`, `logcat*.txt` under an evidence path

### 2.3 Required device signal

Device classification must require a REAL device/evidence semantic — a bounded token or path meaning
(`layout`, `window_dump`, `uiautomator`, `dumpsys`, `screencap`, `logcat`, device-state equivalent)
and/or an actual device command signal (`adb shell …`, `adb exec-out …`, `pm …`, `am start/force-stop`).
A bare substring is not acceptable: `ui` must not match inside `build`, `buildDir` or `rebuild`.

Forbidden "fixes": adding another broad regex; widening the alternative; deleting device-evidence
coverage. An over-correction that loses 2.2 is a FAILED acceptance criterion.

### 2.4 Regression tests (required)

- Location: `evaluation/commandcode/tests/`
- Load `evaluation/commandcode/phase_rules.json` and apply the declared rule conditions DIRECTLY.
- Must NOT import `evaluation/commandcode/core.py`, must NOT touch a device, must run offline.
- Must assert every command in 2.1 does not resolve to `T7` / `T7c` (and specifically not to
  `wait_tag == WAIT_DEVICE`).
- Must assert every command in 2.2 still resolves to `T7` / `T7c` / `WAIT_DEVICE`.
- Must assert the rule table is still valid JSON, still an ordered list, with no duplicate rule ids
  and no id removed other than the deliberate edit.

---

## 3. Defect B — the seven UNKNOWN Hermes-artifact spans

| Span | Seconds | Tool | Category | Intended classification |
|---|---:|---|---|---|
| TURN-0010 | 29.769 | shell_command | hermes_scratch_tooling | T2 / NECESSARY_OVERHEAD |
| TURN-0052 | 96.162 | tool_call | wrapper_tool_call | T2 / NECESSARY_OVERHEAD / WAIT_TOOL |
| TURN-0053 | 52.447 | tool_call | wrapper_tool_call | T2 / NECESSARY_OVERHEAD / WAIT_TOOL |
| TURN-0097 | 47.957 | write_file | hermes_scratch_tooling | T2 / NECESSARY_OVERHEAD |
| TURN-0099 | 30.493 | edit_file | hermes_scratch_tooling | T2 / NECESSARY_OVERHEAD |
| TURN-0101 | 227.339 | write_file | hermes_scratch_tooling | T2 / NECESSARY_OVERHEAD |
| TURN-0106 | 24.812 | write_file | evidence_path_write | T9 / PRODUCTIVE |

Evidence strings (from the frozen fixture):

```
TURN-0010  cmd: cd /home/zhong/.hermes/profiles/android-stack/cache/scratch && python3 m4_verify_frozen.py
TURN-0052  tool_call: {"calls": [{"arguments": {"session_id": "proc_5e7ec6f68cde"}, "name": "process_manage"}]}
TURN-0053  tool_call: {"calls": [{"arguments": {"action": "wait", "session_id": "proc_5e7ec6f68cde", "timeout": 420}, "name": "process_manage"}]}
TURN-0097  write_file: /home/zhong/.hermes/profiles/android-stack/cache/scratch/m4_postrun_proof.py
TURN-0099  edit_file:  /home/zhong/.hermes/profiles/android-stack/cache/scratch/m4_postrun_proof.py
TURN-0101  write_file: /home/zhong/.hermes/profiles/android-stack/cache/scratch/m4_secret_scan.py
TURN-0106  write_file: /mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/keeplab-m4-attachments/post-run-proof.json
```

### 3.1 Rules

- **hermes_scratch_tooling** — extend the existing `t2_scratch_tooling` vocabulary to the real Hermes
  scratch root (`~/.hermes/profiles/<profile>/cache/scratch/`), not only `/scratchpad/`. Match a
  token-bounded `.hermes/` + `cache/scratch` (or `scratch/`) path/command signature. Do not add
  Android semantics.
- **wrapper_tool_call** — a DEDICATED rule for the Hermes wrapper tool name `tool_call` /
  `process_manage`. Do NOT add a `HERMES_TOOL_ALIAS` entry that forces `tool_call` onto a Command
  Code tool name it is not. `wait_tag: WAIT_TOOL` (the existing tool-wait tag) is the intended tag;
  if the executor finds a better justified existing tag it may use it, recording the reason.
- **evidence_path_write** — extend the existing `t9_result_file` / `t9_handoff_artifact` family to
  `orchestration/hermes/evidence/**` result writes (`.json`, `.jsonl`, `.md`, `.csv`, `.txt`).

### 3.2 Preservation

- `HERMES_TOOL_ALIAS` must keep `terminal→shell_command`, `patch→edit_file`, `search_files→grep`.
- No existing rule may be narrowed so that a previously-classified span regresses to UNKNOWN.
- `evaluation/commandcode/core.py` is BYTE-IDENTICAL at the end of the wave.

### 3.3 Honest residue

If a span genuinely cannot be classified without changing `core.py`, record it in the WAVE1A evidence
as `UNCLASSIFIED_JUSTIFIED` with span id, seconds and the exact reason. A recorded residue is an
acceptable outcome. A fabricated classification is a FAIL. Never edit `core.py` to force a PASS.

---

## 4. Acceptance criteria

### AC-W1A-001 — T7c false positive eliminated
`evaluation/commandcode/phase_rules.json` no longer contains an alternative under which the substring
`ui` inside `build` can classify a build/manifest inspection as device evidence.
**Evidence:** the diff of the rule, plus the reproduced match analysis in §2.

### AC-W1A-002 — device coverage preserved (no over-correction)
Every command in §2.2 still resolves to `T7` / `T7c` / `WAIT_DEVICE` under the changed rule table.
**Evidence:** the regression test output for the §2.2 set.

### AC-W1A-003 — regression tests exist and PASS
Tests live in `evaluation/commandcode/tests/`, are deterministic, offline, do not import `core.py`,
and cover §2.1 (negative) and §2.2 (positive), including the three exact M4 commands.
**Evidence:** test file paths + a full PASS run, plus the exact command text asserted.

### AC-W1A-004 — WAIT_DEVICE false-positive wall eliminated
During the WAVE1A replay of the M4 fixture, the seconds attributed to `T7c` / `WAIT_DEVICE` by the
three §2.1 commands is `0.000`. Total `WAIT_DEVICE` must equal the genuinely device-attributable
value (expected `0.000`, since the device was not used).
**Evidence:** the replay's phase/wait table beside the historical table.

### AC-W1A-005 — UNKNOWN below 2% or fully justified
`unknown_share_of_agent_owned < 0.02` in the replay, **or** all seven spans in §3 carry a
deterministic classification **or** an explicit `UNCLASSIFIED_JUSTIFIED` record with its reason.
**Evidence:** the replay's UNKNOWN table (before/after) plus the per-span classification or
justification list.

### AC-W1A-006 — wrapper tool classified by a dedicated rule
`tool_call` / `process_manage` is classified by a rule of its own; it is not forced into a Command
Code tool name through `HERMES_TOOL_ALIAS`; existing aliases and session normalisation are unchanged
and an adapter test proves the normalisation still round-trips.
**Evidence:** the new rule, the unchanged alias map, the adapter test run.

### AC-W1A-007 — frozen core untouched
`evaluation/commandcode/core.py` sha256 equals the frozen baseline
`f076fddd092fbbcb2a119d7a33bf6fd3d37b3f677c95eccbe0411e7ee7fa8b07`.
**Evidence:** pre/post hash output.

### AC-W1A-008 — shadow observer hook exists and behaves
`orchestration/hermes/evaluation_adapter/hooks/hermes-transient-observer.py` exists and, driven by
synthetic local fixtures for `post_tool_call`, `pre_api_request`, `post_api_request`, produces valid
append-only JSONL with one parseable JSON object per line, metadata only, and a second invocation
appends rather than truncates.
**Evidence:** the fixture inputs, the emitted JSONL, and the preserved earlier lines.

### AC-W1A-009 — observer fails safe and leaks nothing
A malformed / empty / non-object payload writes nothing to the JSONL and exits `0`. No line ever
contains a prompt body, message body, tool-result body, attachment data, raw request/response object,
or a secret-looking value. The hook returns no block/allow/modify directive and writes only its JSONL
target.
**Evidence:** the malformed-payload case, plus a scan of every emitted line and its key set.

### AC-W1A-010 — observer NOT enabled live
`/home/zhong/.hermes/profiles/android-stack/config.yaml` sha256 equals the frozen baseline
`7ac5c4cbce7bad53147e45e35bd03d5d14accaced7929ab8a3adc5c669b74a5a`; the hook path appears in no live
registration; the hook header declares SHADOW_ONLY.
**Evidence:** pre/post hash of config.yaml and the absence of the path from it.

### AC-W1A-011 — one reusable utility, no secret scanner
At most ONE new artifact exists under `orchestration/hermes/tools/`; it is deterministic (repeated
runs produce byte-identical output); it imports the specification compiler hashing rather than
reimplementing SHA; it performs no secret/credential detection and does not duplicate Contract Guard
behaviour. No `secret_scan.py` / `credential_regex.py` / `security_grep.py` or equivalent exists
anywhere new.
**Evidence:** the file list, two identical runs, the import list, and the absence check.

### AC-W1A-012 — replay parity + one .hermes.md rule + zero collateral change
In the replay, logical failures (FAIL-001, FAIL-003, FAIL-004 — same ids, types, phases), repair
linkage (REPAIR-002, REPAIR-003 — same triggers, fixes, reruns, results), task completion detection
and token totals (requests 113, input 673851, output 148391, cache read 25064448, cache write 0) are
UNCHANGED. `.hermes.md` gained exactly one compact rule against per-phase ad-hoc scratch
proof/hash/report scripts and nothing else. Every frozen input outside `allowed_paths` is
byte-identical; no historical evidence and no completed contract package changed; no file inside a
forbidden path was created, modified or deleted.
**Evidence:** the comparison table, the `.hermes.md` diff, the pre/post hash table, and the changed
scope summary.

---

## 5. Verification discipline

- PLAN ONCE → EXECUTE → VERIFY ONCE → PASS = STOP.
- FAIL: read the failure once, fix the failed part only, re-run the failed step only.
- No review of the review. No verification of the verification. No post-PASS audit.
- No full-repository scan without a stated cause. No re-checking M4. No reopening A0/A1/A2/M2/M3/M4.
- The mandatory gates are: phase-rule regression tests, observer hook unit test, M4 replay comparison,
  scope/hash verification, and Contract Guard validation of this package.
- A gate that already PASSED is never re-run to "confirm" it.
