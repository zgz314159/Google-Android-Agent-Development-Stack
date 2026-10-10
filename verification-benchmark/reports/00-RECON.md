# 00 — Recon

Read-only reconnaissance for the P0 Verification Compression Benchmark. No home-wide or
Testapp/PowerAi scanning was performed.

## Repository state

| Fact | Value |
|---|---|
| KeepLab path | `/mnt/AndroidDev/Projects/KeepLab-Relay` |
| Branch / HEAD | unborn `HEAD` (zero commits; `git log` fails) |
| Working tree | entire tree untracked (`??`) |
| Consequence | `git worktree` from HEAD is impossible → copy isolation used |
| Isolation copy | `/mnt/AndroidDev/Worktrees/KeepLab-Verification-Compression` (16M, excludes `build/`, `.git/`, `.gradle/`, `.kotlin/`) |
| Deviation | `NO_WORKTREE`; `git_commit = NO_GIT` in all artifacts |

## Artifact root

`/mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack/verification-benchmark/`
→ `journeys/ harness/ maestro/ results/ reports/`

## Device

| Fact | Value |
|---|---|
| Serial | `87296ada` |
| Model | Redmi Note 7 Pro (`violet`) |
| ROM | LineageOS 23.2 |
| Android | 16 / API 36 |
| ABI | arm64-v8a |
| Display | 1080x2340, density 440 |
| Rotation | `accelerometer_rotation=1`, `user_rotation=0` |
| `adb devices -l` | `87296ada device usb:1-2 product:lineage_violet model:Redmi_Note_7_Pro device:violet transport_id:5` |

## Toolchain versions

| Tool | Version |
|---|---|
| adb | 1.0.41 (34.0.4-debian), `/usr/lib/android-sdk/platform-tools/adb` |
| Android CLI | 1.0.16486076 (`/home/zhong/.local/bin/android`) |
| Java | OpenJDK 21.0.12.1 (Ubuntu), `JAVA_HOME` unset, `/usr/lib/jvm/java-21-openjdk-amd64` |
| Gradle (wrapper) | 9.5.1 |
| AGP | 9.2.1 |
| Kotlin | 2.3.21 |
| KSP | 2.3.9 |
| Compose BOM | 2026.05.01 |
| Room | 2.8.4 |
| Hilt | 2.59.2 |
| Navigation3 | 1.1.2 |
| androidx.test runner / ext.junit | 1.7.0 / 1.3.0 |
| Maestro | **not installed** (`maestro: not found`, no `~/.maestro`) |

## App under test

| Fact | Value |
|---|---|
| applicationId / namespace | `com.keeplab.app` |
| Launcher activity | `com.keeplab.app.MainActivity` (`@AndroidEntryPoint`, Hilt) |
| Application | `com.keeplab.app.KeepLabApplication` (`@HiltAndroidApp`) |
| Room DB | name `keeplab.db`, version 2 — tables `notes`, `checklist_items`, `labels`, `note_labels` |
| Layout pref | `SharedPreferences("keeplab_prefs").home_layout` |
| UI | Jetpack Compose + Material 3, Nav3 (`Home`, `Archive`, `Trash`, `Labels`, `LabelNotes(labelId)`, `Editor(noteId)`) |
| Selectors | `contentDescription` on icon controls only; **no `testTag`s** |
| Existing androidTest | `NoteDaoRoomTest`, `MigrationTest` (Room/instrumentation) |
| Existing APK | `app/build/outputs/apk/debug/app-debug.apk` (19,406,951 B, Phase B) |

## Existing Evaluation Core

`.../Google-Android-Agent-Development-Stack/evaluation` — observer-only, zero LLM/network.
`commandcode/{core.py, analyze_session.py, phase_rules.json}`, `taxonomy/*.json`,
`tests/test_evaluation_core.py`. Schema `v3` only. Derives T0–T9 and T7a/T7b/T7c from the
**agent's own session tool calls** (adb input → T7b; screencap/dumpsys/layout/logcat → T7c).
It cannot observe time spent *inside* an instrumentation/Maestro process, so B/C internal
timing must come from harness event logs; an isolated adapter will normalize it (§21).

## Gaps / blockers carried into execution

1. `NO_WORKTREE` — repo has no commits.
2. `GAP-ESPRESSO` — Compose UI instrumentation historically failed on API 36 (`HANDOFF.md`:
   Espresso `InputManager.getInstance()` reflection). Engine B spikes Compose UI first,
   falls back to UiAutomator-only.
3. `MAESTRO_ABSENT` — install `2.11.0` only at Engine C stage.
4. `NO_COMPOSE_TEST_DEPS` — `ui-test-junit4` / `ui-test-manifest` undeclared; add test-only.

## Stack gaps (unchanged from Phase A, re-confirmed)

- `GAP-1`: `android run` needs explicit `--apks`.
- `GAP-2`: (resolved) `android layout` now surfaces Compose `contentDescription`.
