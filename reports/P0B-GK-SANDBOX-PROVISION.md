# P0B-GK-SANDBOX-PROVISION

**Dedicated Google Keep Benchmark Sandbox Provisioning (Governance Option A)**
Phase: provisioning only. **No benchmark notes were generated. P1 was not started.**

- Date: 2026-10-05 (CST)
- Device: `87296ada` (Redmi Note 7 Pro, `violet`), capacity = 1
- Target reference app: `com.google.android.keep`
- Result: **SANDBOX PROVISIONED, ISOLATION PASS, STOPPED AT HUMAN GOOGLE LOGIN CHECKPOINT**

---

## 1. Scope of this phase

Done:

1. read-only preflight of device, multi-user capability and package state
2. creation of one disposable **full secondary** Android user `P0B-BENCH`
3. deterministic foreground switch to that user
4. per-user availability of the frozen Google Keep reference build
5. per-user availability of the KeepLab benchmark target
6. mandatory owner-data isolation test
7. stop at the Google account login boundary (human-only)

Not done (explicitly out of scope): benchmark note generation (0/10/100/500/1000),
P1, product source changes, Keep APK changes, any Google-credential automation.

---

## 2. Safety attestation

| Forbidden action | Performed | Evidence |
| --- | --- | --- |
| delete existing Android users | NO | `pm list users` shows the original user 0 intact |
| remove/alter owner user | NO | user 0 flags unchanged: `ADMIN\|FULL\|INITIALIZED\|MAIN\|PRIMARY\|SYSTEM` |
| `pm clear` Google Keep in owner user | NO | owner Keep state identical before/after (`ceDataInode=92638`) |
| clear Google Play Services owner data | NO | not touched; owner account count still 1 |
| modify Keep private DB | NO | no DB access at all (no root, no `run-as`); `su` not present |
| root-patch / modify Keep APK | NO | same `codePath`, same version, no install of anything new |
| unofficial Keep private APIs | NO | none used |
| automate Google credentials / read passwords / OTP / 2FA | NO | stopped before the checkpoint; no credential screen touched |
| store Google cookies/tokens | NO | none captured |
| factory reset / wipe /data | NO | none |
| guest / work profile / owner user / emulator fallback | NO | none used |
| switch or remove owner Google account | NO | owner account untouched |

---

## 3. Device resource

Every mutating step ran inside one script holding the host device lock
(`verification/core/device_lock.sh`, `flock` on `device:87296ada`, capacity 1):

```
DEVICE_LOCK_ACQUIRED serial=87296ada
```

No other Hermes child, worker, Maestro or ADB mutator touched the device during the
phase; the lock was released when the script exited. Read-only probes ran outside the
lock as permitted by the policy.

---

## 4. Read-only preflight

| Item | Value |
| --- | --- |
| adb serial | `87296ada` |
| model / codename | Redmi Note 7 Pro / `violet` (xiaomi) |
| Android release / API | 16 / 36 |
| build fingerprint | `xiaomi/violet/violet:10/QKQ1.190915.002/V12.5.1.0.QFHINXM:user/release-keys` |
| build flavor / type | `lineage_violet-userdebug` / userdebug |
| current foreground user (before) | `0` |
| `pm list users` (before) | `0` only — `UserInfo{0:朗少天下:4c13} running` |
| max switchable users | **4** (`pm get-max-users`; `dumpsys user`: “Supports switchable users: true; Max switchable users: 4”) |
| multi-user supported | **YES** |
| Google Keep version | `5.26.391.03.90` (versionCode `220677611`, minSdk 32, targetSdk 37) |
| Google Keep installed users (before) | user 0 only |
| Google Keep in user 0 (structural) | `installed=true stopped=false enabled=0 ceDataInode=92638 deDataInode=65560` |
| KeepLab packages present | `com.keeplab.app` (0.1.0 / versionCode 1), `com.keeplab.app.test` (test variant) |
| owner visible card/count metadata | **NOT collected** — deliberately skipped; it would require content-level access |

Owner-user Keep state was recorded only at structural level. No note text or content
was inspected, no note screen was screenshotted, no private DB was touched.

---

## 5. Multi-user capability gate

PASS — no `SECONDARY_USER_UNAVAILABLE`.

- `pm get-max-users` → `Maximum supported switchable users: 4`
- `dumpsys user` → `Supports switchable users: true`, `Is headless-system mode: false`
- `cmd user list -v` → 1 user, user 0 `type=full.SYSTEM`

No guest, work-profile, owner-user or emulator fallback was needed or used.

---

## 6. Existing user safety

`pm list users` captured before creation. No existing user was altered, stopped,
deleted or switched away destructively. No user named `P0B-BENCH` existed
(`NO_COLLISION`), so `P0B_BENCH_NAME_COLLISION` did not apply.

---

## 7. Create secondary user

```
before : Users: UserInfo{0:朗少天下:4c13} running            (1 user)
command: adb -s 87296ada shell pm create-user --for-testing P0B-BENCH
output : Success: created user id 10
after  : Users: UserInfo{0:朗少天下:4c13} running
                UserInfo{10:P0B-BENCH:8410}                  (2 users)
```

- `BENCH_USER_ID = 10` (id taken from the platform's returned value; nothing invented)
- `BENCH_USER_ID != OWNER_USER_ID` (10 != 0) — verified
- type `android.os.usertype.full.SECONDARY`, flags at creation `FOR_TESTING|FULL`
  (later `FOR_TESTING|FULL|INITIALIZED` as the platform's own new-user setup advanced)
- `--for-testing` is a documented option in the platform's own `pm help` create-user
  output; it makes the new user startable without a manual setup-wizard walkthrough

No destructive retry was needed; creation succeeded on the first attempt.

---

## 8. Switch user

```
adb -s 87296ada shell am start-user -w 10    -> Success: user started
adb -s 87296ada shell am switch-user 10      -> rc 0
adb -s 87296ada shell am get-current-user    -> 10        (matches BENCH_USER_ID)
```

`cmd user list -v` confirms user 10 is `running` and `current`.

**Note:** the platform still had its own new-user setup wizard pending in user 10
(`com.google.android.setupwizard/.user.UserWarningActivity`). That screen requires a
human decision, so it was **not** dismissed, bypassed or automated — see §13.

---

## 9. Google Keep availability in the bench user

Not initially visible for user 10, then made available with the supported per-user
package mechanism only:

```
adb -s 87296ada shell pm install-existing --user 10 com.google.android.keep
  -> Package com.google.android.keep installed for user: 10
```

| Property | user 0 (owner) | user 10 (P0B-BENCH) |
| --- | --- | --- |
| version | 5.26.391.03.90 | 5.26.391.03.90 |
| codePath | `…/com.google.android.keep-mOjR-…` | **identical** |
| installed | true | true |
| ceDataInode | 92638 | 98690 |
| deDataInode | 65560 | 98591 |

No APK was downloaded, no downgrade, no replacement, no reference-version change.
The sandbox uses the **same installed Google Keep build** as the device reference —
fairness requirement met, no mismatch to report.

GMS / GSF / Play Store (`com.google.android.gms`, `com.google.android.gsf`,
`com.android.vending`) were already available in user 10, so the later human sign-in
path exists.

---

## 10. KeepLab benchmark target availability

```
adb -s 87296ada shell pm install-existing --user 10 com.keeplab.app       -> ok
adb -s 87296ada shell pm install-existing --user 10 com.keeplab.app.test  -> ok
```

| Package | Version | user 0 | user 10 |
| --- | --- | --- | --- |
| `com.keeplab.app` | 0.1.0 (versionCode 1) | installed | **installed** |
| `com.keeplab.app.test` | test variant (versionCode 0) | installed | **installed** |

The same benchmark APK is therefore available to execute inside the sandbox user.
Product source was not modified and nothing was benchmarked.

---

## 11. Owner data isolation test (mandatory gate)

Method: launched Google Keep inside user 10 and inspected its **non-sensitive initial
UI state** structurally (activity stack + one accessibility hierarchy dump + per-user
package/account state). Owner note text was never read or compared.

Observed task stack in user 10:

```
Task #1000003 U=10 com.google.android.keep
  Hist #0 u10 com.google.android.keep/…activities.SignInActivity
  Hist #1 u10 android/.accounts.ChooseTypeAndAccountActivity
  Hist #2 u10 com.google.android.gms/…addaccount.ErrorActivity
```

Structural findings:

- Keep in user 10 opened directly into its **sign-in / add-account flow** — no note
  list, no note cards, no owner content.
- Per-user account scope: user 0 has **1** Google account, user 10 has **0**.
- Per-user package data is separate: Keep `ceDataInode` 92638 (user 0) vs 98690 (user 10).
- Owner Keep state is unchanged: `ceDataInode` still 92638, `stopped=false`.

```
OWNER KEEP DATA VISIBLE IN BENCH USER: NO
SANDBOX ISOLATION: PASS
```

---

## 12–13. Google account = human only — HUMAN_ACTION_REQUIRED

No credential step of any kind was attempted. The account checkpoint was reached:

- `BENCH_USER_ID = 10` exists
- foreground user == 10
- Google Keep available and launches in user 10
- owner-data isolation = PASS
- Google account login is required

```
HUMAN_ACTION_REQUIRED
```

### What the human must do (on the phone)

1. Keep the phone inside Android user **P0B-BENCH** (currently the foreground user).
   The screen is at a Google add-account flow that the sandbox triggered. Press
   **Back** to dismiss it.
2. Complete the pending **new-user setup** screens of user 10 (non-secret Android /
   Google setup pages only).
3. Open **Google Keep**.
4. Sign in with a **dedicated benchmark-only Google account**.
5. That account must contain **no personal, work, production or important Google Keep
   data**.
6. Do **not** add that account to the owner Android user.
7. Complete password / OTP / 2FA **manually on the phone**.
8. When Keep opens normally under P0B-BENCH, do **not** create benchmark notes yet.
9. Report back: **BENCHMARK ACCOUNT LOGIN COMPLETE**.

Hermes will not continue automatically.

### Environment warning that can block step 4

The device currently **cannot reach Google endpoints** on its own network path:

| Probe (on device) | Result |
| --- | --- |
| `curl https://accounts.google.com/` | HTTP 000, timed out (10 s) |
| `curl http://accounts.google.com/` (port 80) | HTTP 000, timed out |
| `curl -4 https://accounts.google.com/` | HTTP 000, timed out |
| `curl https://www.google.com/` | HTTP 000, timed out |
| `curl https://www.baidu.com/` | HTTP 200 (general internet works) |
| `ping 8.8.8.8` | 0 % loss |

The workstation reaches Google (HTTP 302) only through a local proxy on the host; the
phone has no proxy/VPN configured (`http_proxy=null`, `private_dns=off`, no VPN app in
the owner user). If sign-in fails at step 4, that network condition — not the sandbox —
is the cause, and the human needs a device-side working path to Google (VPN or another
network). No device network setting was changed by this phase.

---

## 14. Clean exit / state record

| Field | Value |
| --- | --- |
| OWNER_USER_ID | 0 |
| BENCH_USER_ID | 10 (`P0B-BENCH`, `full.SECONDARY`) |
| CURRENT_USER_ID | 10 |
| Google Keep package version | 5.26.391.03.90 |
| Google Keep available in BENCH user | YES |
| KeepLab benchmark APK available | YES (`com.keeplab.app` 0.1.0; `com.keeplab.app.test`) |
| Isolation result | PASS |
| Human login still required | YES |
| Benchmark notes created | 0 |

The phone was intentionally **left in user 10** at the human-login checkpoint and was
**not** switched back. Safe command to return to the owner user later:

```
adb -s 87296ada shell am switch-user 0
```

(This only changes the foreground user; it does not modify any user data.)

---

## 15. Evidence index

`orchestration/hermes/evidence/p0b-gk-sandbox-provision/`

| File | Content |
| --- | --- |
| `preflight.json` | read-only preflight facts (device, multi-user, packages) |
| `create-and-switch.json` | device lock, collision check, create command/output, switch + verification |
| `package-availability.json` | Keep / KeepLab per-user availability, identical codePath, per-user inodes |
| `isolation-test.json` | owner-data isolation gate (structural evidence, PASS) |
| `network-probe.json` | device-side Google reachability probes (environment observation) |
| `final-state.json` | state record + switch-back instruction |
| `ai-rule-effectiveness.json` | passive AI-rule observation |
| `bench-user-keep-ui.xml` | the single accessibility hierarchy dump used for the isolation test |
| `step-a-provision.sh`, `step-b-isolation.sh` | the two locked scripts actually executed |
| `terminal.log` | live session transcript of this phase |

Contains no passwords, no OTP/2FA codes, no tokens, no OAuth cookies, no note content
and no account identifiers (account **counts** only).

---

## 16. Contract Guard

Contract Guard **ACTIVE**, unmodified, not bypassed. Two command *shapes* were refused
by the guard during this phase (`flock -c '<inline body>'` and one inline grouped shell
body); both were replaced with simple invocations of literal-path scripts. No frozen
contract decision was reopened and no Hermes core file was touched.

---

## 17. AI rule effectiveness (passive observation)

| Rule | Respected | Note |
| --- | --- | --- |
| device capacity = 1 | YES | whole mutation ran under `flock` on `device:87296ada` |
| no owner-data mutation | YES | owner Keep inode/state and account count unchanged |
| stop on unsupported secondary user | N/A | multi-user supported (max 4); gate evaluated before mutation |
| stop on account-login boundary | YES | stopped before any credential interaction |
| no secret handling | YES | no password/OTP/token/cookie access; no credential screenshots |
| no early note generation | YES | 0 notes created |
| no destructive fallback | YES | no wipe/reset/delete; no guest/owner/emulator fallback |
| no UI-vision loop | YES | one structural hierarchy dump; no `input tap/swipe/text` |
| prefer supported per-user package mechanism | YES | `pm install-existing --user` only |

No synthetic AI-rule tests were added.

---

## 18. Final output

```
P0B-GK-SANDBOX-PROVISION
========================

DEVICE:
87296ada

MULTI-USER SUPPORTED:
YES

OWNER USER ID:
0

P0B-BENCH USER CREATED:
YES

BENCH USER ID:
10

CURRENT FOREGROUND USER:
10

GOOGLE KEEP AVAILABLE IN BENCH USER:
YES

GOOGLE KEEP VERSION:
5.26.391.03.90

KEEPLAB BENCHMARK TARGET AVAILABLE:
YES

OWNER KEEP DATA VISIBLE IN BENCH USER:
NO

SANDBOX ISOLATION:
PASS

GOOGLE ACCOUNT:
HUMAN_LOGIN_REQUIRED

CREDENTIAL AUTOMATION USED:
NO

OWNER USER DATA MODIFIED:
NO

BENCHMARK NOTES CREATED:
0

CONTRACT GUARD:
ACTIVE

STATUS:
WAITING_FOR_HUMAN_LOGIN

NEXT:
HUMAN BENCHMARK GOOGLE ACCOUNT LOGIN

REPORT:
/mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack/reports/P0B-GK-SANDBOX-PROVISION.md

========================
```

Stopped here. No 10/100/500/1000 notes were generated and P1 was not started.
