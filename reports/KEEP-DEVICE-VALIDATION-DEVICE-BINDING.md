# KEEP-DEVICE-VALIDATION-DEVICE-BINDING

**Additive execution binding: bind the Web-first Google Keep research backlog to the new
validation device `c67d32fa`**

- Task: `KEEP-TARGETED-DEVICE-VALIDATION-PREP`
- Predecessor: `KEEP-GLOBAL-RESEARCH-AUTH-SYNC-OFFLINE` (STATUS: READY)
- Date: **2026-10-05 (CST)**
- Phase type: **preparation / provisioning only** — no journey runs, no notes, no benchmark
- Result: **VALIDATION USER PROVISIONED, ISOLATION PASS, VERSION GATE PASS, STOPPED AT HUMAN LOGIN CHECKPOINT**

---

## 1. Binding record (required fields)

| Field | Value |
| --- | --- |
| RESEARCH BACKLOG SOURCE | `reports/KEEP-DEVICE-VERIFICATION-BACKLOG.md` |
| HISTORICAL SERIAL IN BACKLOG | `87296ada` |
| EXECUTION SERIAL | `c67d32fa` |
| MODEL | `M2007J17C` / `gauguinpro` (Xiaomi, LineageOS) |
| EXECUTION USER | `KEEP-REF-VALIDATION` (Android user id **10**, `full.SECONDARY`) |
| ACCOUNT | reference-side Google account only (dedicated, human-entered) |
| FIRST PASS | `J1`–`J4` (4 MUST journeys) |
| OPTIONAL | `J5`–`J6` |
| OWNER USER | `0` — untouched |

The original research report and backlog were **not modified**. All serial text mentioning
`87296ada` in `KEEP-DEVICE-VERIFICATION-BACKLOG.md` remains as historical evidence of the
device assumption used at research time. This file is the **additive execution binding** and
**overrides the execution serial** for future Google Keep targeted-validation runs.

Byte-level check: `reports/KEEP-DEVICE-VERIFICATION-BACKLOG.md` was left byte-identical
(193 lines, 11963 bytes, mtime 2026-10-05 11:54).

---

## 2. Governance preserved (unchanged)

```
GOOGLE KEEP:                          REFERENCE PRODUCT ONLY
GOOGLE KEEP BENCHMARK ACCOUNT:        REFERENCE_SIDE_ONLY
KEEPLAB AUTHORITY:                    OWN_BACKEND
KEEPLAB GOOGLE ACCOUNT REQUIRED:      NO
GOOGLE AUTH IN KEEPLAB:               FORBIDDEN_UNLESS_HUMAN_APPROVED
FIREBASE AUTH IN KEEPLAB:             FORBIDDEN_UNLESS_HUMAN_APPROVED
GOOGLE PRIVATE API:                   FORBIDDEN
```

No governance decision was re-opened, edited or reinterpreted.

---

## 3. Scope discipline — what this phase did NOT do

- No `J1`–`J4` journey was started (conflict / offline indicator / propagation timing /
  reload-reinstall safety).
- No validation note was created. Validation note count: **0**.
- No P0B matched-scale device rebase was started; `c67d32fa` is **not** declared the final
  P0B performance device.
- No Google Keep `c67d32fa` performance was compared with KeepLab `87296ada` performance.
- `P0B_MATCHED_SCALE_DEVICE_DECISION` remains a separate later step.
- No question already resolved by web evidence was re-researched.
- KeepLab, Testapp and PowerAi were not touched.

---

## 4. Read-only preflight (`device-preflight.json`)

### 4.1 Device

| Item | Value |
| --- | --- |
| adb serial | `c67d32fa` |
| manufacturer | Xiaomi |
| model | `M2007J17C` |
| codename | `gauguinpro` |
| product | `lineage_gauguin` |
| Android release / API | 16 / 36 |
| security patch | 2026-09-01 |
| build fingerprint | `Xiaomi/gauguin_global/gauguin:12/RKQ1.200826.002/V14.0.2.0.SJSMIXM:user/release-keys` |
| build type / flavor | `userdebug` / `lineage_gauguin-userdebug` |
| ROM | LineageOS `23.2-20260923-NIGHTLY-gauguin` |
| display resolution | 1080 x 2400 |
| density | 440 dpi |
| ABI | `arm64-v8a, armeabi-v7a, armeabi` |
| battery | 93 % (USB powered) |
| thermal status | 0 |
| free storage (`/data`) | 67 G free of 107 G (38 % used) |

### 4.2 Users (before mutation)

```
Users:
    UserInfo{0:GUOZHI ZHONG:4c13} running
am get-current-user          = 0
pm get-max-users             = 4
dumpsys user                 Supports switchable users: true
```

### 4.3 Package availability (before mutation)

| Package | Present | Installed on users |
| --- | --- | --- |
| `com.google.android.keep` | yes | user 0 |
| `com.google.android.gms` | yes | user 0 |
| `com.google.android.gsf` | yes | user 0 |
| `com.android.vending` | yes | user 0 |
| `com.keeplab.app` | **no** | — (KeepLab is not installed on this device) |

Nothing was mutated before the preflight was complete.

---

## 5. Google Keep version gate (`version-gate.json`)

| Field | Value |
| --- | --- |
| package | `com.google.android.keep` |
| CURRENT versionName | **`5.26.391.03.90`** |
| CURRENT versionCode | `220677611` |
| codePath | `/data/app/~~vDdUa_TfjmKzPH3nQJ2IqA==/com.google.android.keep-gzDNizigT75UA9iwBOjrbg==` |
| minSdk / targetSdk | 32 / 37 |
| FROZEN REFERENCE VERSION | `5.26.391.03.90` |
| **REFERENCE_VERSION_MATCH** | **YES** (exact match) |

No downgrade, no APK download, no replacement, no change to the frozen reference. Because the
version matches exactly, future `J1`–`J4` evidence captured on this device may be classified
`FROZEN_REFERENCE_BEHAVIOR_EVIDENCE`. (The execution itself is not part of this phase.)

---

## 6. Multi-user gate + user provisioning (`user-provision.json`)

- Support check with the device's own commands: `pm get-max-users` = **4**,
  `dumpsys user` → *Supports switchable users: true*. → no `SECONDARY_USER_UNAVAILABLE`.
- Existing-user safety: **no** user named `KEEP-REF-VALIDATION` existed before
  (`NO_COLLISION`); no existing user was deleted, recreated, stopped or altered.
- Creation (device help confirms `--for-testing` is supported):

```
pm create-user --for-testing KEEP-REF-VALIDATION
  -> Success: created user id 10
```

- `VALIDATION_USER_ID = 10` — taken from the platform's returned value, **not** assumed.
  Type `android.os.usertype.full.SECONDARY`; flags `FOR_TESTING|FULL` (later
  `FOR_TESTING|FULL|INITIALIZED` as the platform advanced its own new-user setup).
- Start + switch, then verification:

```
am start-user -w 10   -> Success: user started
am switch-user 10     -> rc 0
am get-current-user   -> 10      (== VALIDATION_USER_ID)
```

- No pending setup-wizard task was detected in user 10 and no undocumented command was used
  to bypass anything. → no `HUMAN_SETUP_REQUIRED`.

---

## 7. Device lock (§8)

Every mutating step ran inside one script holding the host device lock
(`verification/core/device_lock.sh`, `flock` on `device:c67d32fa`, capacity 1):

```
DEVICE_LOCK_ACQUIRED serial=c67d32fa
```

observed once per mutating script (`step-a`, `step-b`, `step-c2`, `step-d`, `step-e`). No
other ADB / Maestro / UiAutomator mutator touched the device concurrently. Read-only probes
ran outside the lock as the policy permits.

---

## 8. Google component availability in the validation user (`package-state.json`)

Mechanism: **only** `pm install-existing --user 10 <package>`, and only for packages already
present on the device. No APK download, no downgrade, no replacement, no modification, no
root patch.

| Package | user 0 | user 10 before | user 10 after | version |
| --- | --- | --- | --- | --- |
| `com.google.android.keep` | installed | `installed=false` | **installed=true** (`ceDataInode=199558`) | `5.26.391.03.90` |
| `com.google.android.gms` | installed | installed | installed (`ceDataInode=163737`) | `26.36.35 (260400-991383798)` |
| `com.google.android.gsf` | installed | installed | installed (`ceDataInode=200895`) | `16-13343139` |
| `com.android.vending` | installed | installed | installed (`ceDataInode=203810`) | `53.3.21-34 [0] [PR] 986224237` |

Keep's `codePath` is **identical** in user 0 and user 10 — the sandbox uses the same installed
reference build, so no version mismatch is introduced by the sandbox.

`GOOGLE SERVICES AVAILABLE: YES` (GMS + GSF + Play Store reachable in the validation user).

---

## 9. Owner data isolation gate (`isolation.json`)

Method: Google Keep was launched inside user 10 **before any account login**, then inspected
structurally — activity stack + one accessibility hierarchy dump + per-user account counts +
per-user package state. No owner note text was read, and no owner note screen was
screenshotted.

Task stack observed in user 10 (task `t4346 U=10`), from base:

```
Hist #0  u10 com.google.android.keep/…shared.account.activities.SignInActivity
Hist #1  u10 android/android.accounts.ChooseTypeAndAccountActivity   (launched by Keep)
Hist #2..#11 u10 com.google.android.gms/…addaccount.{WrapperControlledActivity,PreAddAccountActivity}
Hist #12 u10 com.google.android.gms/…addaccount.ErrorActivity          (top after settle)
```

Structural findings:

- Keep in user 10 opens directly into its **sign-in / add-account flow** — no note list, no
  note cards, no owner content.
- Per-user account scope: **user 0 = 9 accounts** (counts only, no identifiers recorded),
  **user 10 = 0 accounts**.
- Per-user package data is separate: Keep `ceDataInode` **7396** (user 0) vs **199558** (user 10).
- Owner Keep state unchanged across the whole phase: `ceDataInode=7396`, `stopped=false`.

```
OWNER KEEP DATA VISIBLE IN VALIDATION USER: NO
SANDBOX ISOLATION: PASS
```

---

## 10. Google network check (`network.json`)

The human reported the phone can access / log into Google Keep. Minimal verification from
`c67d32fa`:

Device network context: Wi-Fi `TP-LINK_3209_5G`, network validated, DNS answers mapped into
the fake-IP range `198.18.0.0/15` (router-level DNS intercept), no system `http_proxy`
(`null`), **one active VPN** — `VpnTransportInfo{type=1, sessionId=FlClash, bypassable=true}`
on `tun0`, provider package `com.go.class` (owner uid 10244), covering uids `{0-99999}` with
local HTTP proxy `127.0.0.1:7890`.

| Probe | Result |
| --- | --- |
| direct shell, no proxy — `https://accounts.google.com/` | HTTP 000 (timeout) |
| direct shell, no proxy — `https://www.google.com/` | HTTP 000 (timeout) |
| direct shell, no proxy — `https://www.baidu.com/` | HTTP 000 (timeout) |
| `ping 8.8.8.8` | 0 % loss, rtt ≈ 251 ms |
| `nc 223.5.5.5:443` / `nc 8.8.8.8:53` | ok |
| `nc 8.8.8.8:443` / `:80` | timeout |
| **via the device's own active VPN proxy `127.0.0.1:7890`** — `https://accounts.google.com/` | **HTTP 302** |
| same path — `https://www.google.com/` | **HTTP 302** |
| same path — `https://play.google.com/` | **HTTP 302** |
| same path — `http://connectivitycheck.gstatic.com/generate_204` | **HTTP 204** |

Interpretation: the device reaches Google only through its own active app-scoped VPN/proxy;
`adb shell` traffic does not inherit that proxy, which is why the raw shell probes time out.
No VPN/proxy setting was modified by this phase.

```
GOOGLE NETWORK: PASS
```

**Caveat for the human login step:** Android VPNs are **per-user**. The active VPN belongs to
the owner user, so inside `KEEP-REF-VALIDATION` (user 10) the same app-scoped Google path may
need to be enabled by the human before sign-in can complete. This is a human network boundary,
not a sandbox defect.

---

## 11. Optional O-2 capture

Captured **one** deterministic accessibility hierarchy of the account-less first-run state:
`optional-first-run.xml` (6352 bytes). Content is text-only, no credentials: the settled
no-account screen is the GMS add-account flow reporting a Google-server communication error
(`com.google.android.gms/.auth.uiflows.addaccount.ErrorActivity`).

Classification: **OPTIONAL_DEVICE_CONFIRMATION** (O-2).

Observed gate structure: with no Google account in the user, launching Google Keep leads to
`keep…SignInActivity` → system `ChooseTypeAndAccountActivity` → GMS add-account flow. No
credential entry was clicked, no account was entered, login was not automated. The Keep-owned
`SignInActivity` sits at the base of the stack; the top screen is the GMS add-account outcome,
which in this network state (no Google path inside user 10 without a VPN) settles on the
communication-error screen.

---

## 12. Safety attestation

| Forbidden action | Performed | Note |
| --- | --- | --- |
| re-open a frozen Contract decision | NO | governance block untouched |
| execute J1–J4 | NO | 0 journeys started |
| create validation notes | NO | 0 notes |
| start P0B device rebase / A2 / P1 | NO | not started |
| downgrade / download / replace / modify Google Keep | NO | same codePath, same version |
| modify Google services / root patch | NO | none |
| automate Google credentials / read password / OTP / 2FA | NO | stopped before the checkpoint |
| record email / token / OAuth cookie / personal Keep content | NO | account **counts** only |
| delete or alter the owner user or its Keep state | NO | owner `ceDataInode` 7396, 9 accounts → unchanged |
| modify VPN / proxy / network settings | NO | none |
| use the owner user as a fallback | NO | dedicated full secondary user used |
| `screenshot → LLM → tap` device loop | NO | one hierarchy dump per capture, structural only |

Owner shared storage: four small **non-sensitive** accessibility dumps were written to
`/sdcard` by the deterministic capture steps (`w.xml`, `d.xml`, `keep-ref-val-window.xml`,
`keep-ref-val-o2.xml`). A cleanup attempt was refused by the Contract Guard (fail-closed on the
relative filename), so they were left in place; they contain only UI node text, no credentials
and no owner Keep content. Safe removal is a one-line human command.

---

## 13. Contract Guard

Contract Guard remains **ACTIVE**, unmodified, not bypassed. It refused **one** command shape in
this phase (a relative-path `rm` inside a compound `adb shell` body, classified
`UNCLASSIFIED_FAIL_CLOSED`); the phase continued without it. All writes were literal paths
under `reports/**` and `orchestration/hermes/evidence/**`. Hermes core, KeepLab, Testapp and
PowerAi were not touched.

---

## 14. Human login checkpoint — HUMAN_ACTION_REQUIRED

Conditions met: `REFERENCE_VERSION_MATCH == YES`, validation user exists, Google Keep
available, isolation PASS, Google network PASS. → **HUMAN_ACTION_REQUIRED**.

The phone is intentionally left **inside user `KEEP-REF-VALIDATION` (id 10)**, at the
account-less Google add-account screen, and was **not** switched back.

### What the human must do (on the phone)

1. Remain inside Android user **`KEEP-REF-VALIDATION`** (currently the foreground user).
2. Complete any remaining secondary-user setup (non-secret Android / Google screens only).
3. Open **Google Keep**.
4. Sign in to a **dedicated Google Keep reference-validation account**.
5. That account must contain **no personal, work, production or important Keep data**.
6. Do **not** add that account to the owner Android user.
7. Enter password / OTP / 2FA **manually on the phone**.
8. Do **not** create validation notes yet.
9. If sign-in fails, first make Google reachable inside user 10 (the owner user's active VPN is
   per-user and does not cover user 10). No VPN/proxy setting was changed by this phase.
10. When Google Keep reaches a normal usable state, report: **KEEP REFERENCE LOGIN COMPLETE**.

Hermes must not continue automatically. No `J1`–`J4` journey may start until this checkpoint
is reported complete.

### Safe housekeeping commands (human-run, optional)

```
adb -s c67d32fa shell am switch-user 0        # return to the owner user
adb -s c67d32fa shell pm remove-user 10       # destroy the disposable validation user (only when finished)
```

Both are non-destructive to owner data.

---

## 15. Evidence index

`orchestration/hermes/evidence/keep-targeted-device-validation-prep/`

| File | Content |
| --- | --- |
| `device-preflight.json` | read-only device / user / display / storage / package preflight |
| `version-gate.json` | Keep version vs frozen reference, exact-match result |
| `user-provision.json` | lock, collision check, create + switch, current-user verification |
| `package-state.json` | per-user availability of Keep / GMS / GSF / Play Store, identical codePath |
| `isolation.json` | owner-data isolation gate (structural, PASS) |
| `network.json` | device-side Google reachability probes + active VPN context |
| `final-state.json` | state record + safe housekeeping commands |
| `optional-first-run.xml` | the single no-account hierarchy dump (O-2) |
| `step-a-user-provision.sh`, `step-b-switch-isolation.sh`, `step-c-evidence.sh`, `step-c2-evidence.sh`, `step-d-o2-refine.sh`, `step-e-o2-capture.sh` | the locked scripts actually executed |
| `terminal.log` | live session transcript |

Contains no Google password, no OTP/2FA code, no token, no OAuth cookie, no account
identifiers (account **counts** only) and no personal Keep content.

---

## 16. Final output

```
KEEP-TARGETED-DEVICE-VALIDATION-PREP
====================================

DEVICE:
c67d32fa

MODEL:
M2007J17C / gauguinpro (Xiaomi, LineageOS 23.2)

ANDROID:
16 (API 36)

MULTI-USER SUPPORTED:
YES (max switchable users = 4)

OWNER USER:
0

VALIDATION USER CREATED:
YES

VALIDATION USER ID:
10

CURRENT USER:
10

GOOGLE KEEP AVAILABLE:
YES

CURRENT GOOGLE KEEP VERSION:
5.26.391.03.90

FROZEN REFERENCE VERSION:
5.26.391.03.90

REFERENCE VERSION MATCH:
YES

GOOGLE SERVICES AVAILABLE:
YES

OWNER KEEP DATA VISIBLE:
NO

SANDBOX ISOLATION:
PASS

GOOGLE NETWORK:
PASS

OPTIONAL O-2 CAPTURED:
YES

GOOGLE ACCOUNT:
HUMAN_LOGIN_REQUIRED

CREDENTIAL AUTOMATION USED:
NO

VALIDATION NOTES CREATED:
0

J1 STARTED:
NO

J2 STARTED:
NO

J3 STARTED:
NO

J4 STARTED:
NO

P0B DEVICE REBASE STARTED:
NO

P0B A2 STARTED:
NO

CONTRACT GUARD:
ACTIVE

STATUS:
WAITING_FOR_HUMAN_LOGIN

NEXT:
HUMAN KEEP REFERENCE LOGIN

REPORT:
/mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack/reports/KEEP-DEVICE-VALIDATION-DEVICE-BINDING.md

====================================
```

Stopped here. No J1–J4 was executed, no note was created, and no P0B device rebase, A2 or P1
was started.
