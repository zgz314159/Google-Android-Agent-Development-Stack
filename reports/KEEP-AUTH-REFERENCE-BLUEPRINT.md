# KEEP-AUTH-REFERENCE-BLUEPRINT

**Generic login / session UX reference + KeepLab authentication design inference**

- Task: `KEEP-GLOBAL-RESEARCH-AUTH-SYNC-OFFLINE`
- Date: **2026-10-05 (CST)**
- Status: **RESEARCH + DESIGN INFERENCE ONLY.** No implementation. No dependency added. No KeepLab
  product source modified. No Google/Firebase authentication introduced.
- Governance this file obeys: `reports/KEEPLAB-AUTH-BOUNDARY-CORRECTION.md`
  (`KEEPLAB_AUTHORITY: OWN_BACKEND`, `GOOGLE_AUTH_IN_KEEPLAB: FORBIDDEN_UNLESS_HUMAN_APPROVED`,
  `FIREBASE_AUTH_IN_KEEPLAB: FORBIDDEN_UNLESS_HUMAN_APPROVED`, `GOOGLE_PRIVATE_API: FORBIDDEN`).

> **Label discipline.** Sections marked `OFFICIAL_FACT` restate Android/standard documentation.
> Sections marked `KEEPLAB_DESIGN_INFERENCE` are **our proposal** and are **not** Google Keep's
> behaviour and **not** Google's recommendation for KeepLab.

---

## 0. The question this blueprint answers

The task forbids concluding "KeepLab should use Sign in with Google". The real question is:

> Which **generic** platform/UX concepts remain useful even when KeepLab authenticates against its
> **own** backend, and what does Android *itself* recommend today?

Answer: the **Credential Manager client UX** is separable from **Google identity federation**. The
first is a platform affordance KeepLab can adopt; the second stays forbidden.

---

## 1. Android's current recommended authentication UX/API — `OFFICIAL_FACT`

**Source basis:** S-01, S-02, S-03, S-04, S-05, S-06.

| Question | Official answer |
|----------|-----------------|
| Recommended API | **Credential Manager** (`androidx.credentials`) — the recommended Jetpack API for credential exchange (S-01) |
| What it unifies | passkeys, passwords, Sign in with Google / other federated sign-in, digital credentials (S-01) |
| Preferred method | passkeys are positioned as the default/preferred method; passwords are supported but second-choice (S-04, S-06) |
| Sign-in surface | a **bottom-sheet UI** inline to app content, plus (for federated) a distinct button (S-02) |
| Legacy status | legacy Google Sign-In (`com.google.android.gms:play-services-auth`) is **deprecated** and slated for removal; migrate to Credential Manager (S-03) |
| API level | Credential Manager passwords API 19+; passkeys API 28+ (S-04, S-05) |
| Sign-in vocabulary | *relying party client app* (your app), *relying party server* (your app server), *credential provider* (e.g. Google Password Manager) (S-01) |
| Passkey mechanics | public key stored on the **app server**; private key in the device credential provider; server sends a challenge and verifies the signed assertion (S-05) |
| Restore on new device | **Restore Credentials** can restore app accounts during new-device setup; supports multiple signed-in accounts (S-13) |
| Automatic sign-in | `filterByAuthorizedAccounts=true` + `setAutoSelectEnabled=true` reproduces the old `silentSignIn` behaviour with a brief non-interactive sheet (S-02, S-03) |

**What this changes for us:** the platform's *UX vocabulary* (unified credential sheet, passkey-first,
explicit button fallback, restore-on-new-device, manage-passkeys in settings) is worth adopting.
Nothing here requires Google to be KeepLab's identity provider.

---

## 2. Login UX reference model — `OFFICIAL_FACT` (states) + `KEEPLAB_DESIGN_INFERENCE` (mapping)

### 2.1 Required states

| State | Meaning | Typical trigger | Generic UI expectation |
|-------|---------|-----------------|------------------------|
| `SIGNED_OUT` | No session, no stored credential | fresh install / after sign-out | primary sign-in entry point |
| `AUTHENTICATING` | Credential exchange in flight | user tapped sign-in / passkey sheet showing | non-blocking progress; sheet owns the interaction (S-01) |
| `SIGNED_IN` | Valid session | success | normal app shell |
| `AUTH_EXPIRED` | Session no longer valid (expired/revoked) | server rejects a refresh | silent re-auth attempt first |
| `REAUTH_REQUIRED` | Re-authentication needed for a sensitive action | session too old for an operation | re-prompt without discarding local data |
| `NETWORK_ERROR` | Credential exchange could not reach the server | offline during sign-in | retry affordance; **must not** destroy local notes |
| `INVALID_CREDENTIAL` | Wrong username/password | login attempt | field-level error; generic wording (no account enumeration) |
| `ACCOUNT_DISABLED` | Account suspended/disabled by operator | login attempt | distinct, actionable message |
| `SERVER_ERROR` | Backend fault (5xx) | login attempt | transient-error message + retry |
| `OFFLINE_WITH_VALID_LOCAL_SESSION` | No network, but local session material is still valid | connectivity lost | **app stays fully usable on local data** (see §5) |
| `OFFLINE_WITHOUT_VALID_SESSION` | No network and no usable session | connectivity lost before first sign-in | local-only mode or a non-blocking sign-in prompt |

### 2.2 Which parts may be *inspired* by Google/Android, and which are KeepLab's own

| Concern | Inspired by Google/Android? | Owned entirely by KeepLab Backend? |
|---------|-----------------------------|------------------------------------|
| Unified credential sheet / bottom-sheet | Yes (S-01, S-02) — platform affordance | No |
| Passkey-first, password fallback, explicit button | Yes (S-02, S-06) | No |
| "Manage passkeys / sign out" in settings | Yes (S-06) | Partially (the account server owns revocation) |
| Credential restore on a new device | Yes, conceptually (S-13) | Yes — KeepLab decides what a restore key means |
| What a *valid session* is, expiry, revocation | No | **Yes** |
| Which credential types are accepted | No | **Yes** |
| Account recovery | UX pattern only | **Yes** (all recovery semantics are ours) |
| Error semantics (disabled account, lockout) | No | **Yes** |

> Explicitly **not** adopted: Google account as identity, Sign in with Google, Google Identity
> Services, Firebase Authentication, Google branding/logo (per the boundary correction).

---

## 3. Can Credential Manager be used with KeepLab's own backend identity? — `OFFICIAL_FACT`

**YES — SUPPORTED.** Verified against S-01, S-04, S-05, S-33, S-36, S-37.

- Credential Manager is a **client-side credential exchange API**. It does not require Google to be
  the identity authority (S-01).
- **Passkeys** are defined by a *relying party* model: **your** server (the relying party server)
  stores public keys, issues challenges, and verifies signed assertions (S-05, S-36, S-37). A
  passkey created for KeepLab is verified by **KeepLab Backend**, not by Google — the credential
  provider merely stores the private key on the device.
- **Passwords** are equally app-owned: `CreatePasswordRequest`/`GetPasswordOption` store/retrieve a
  username+password that belong to the app's account system; Credential Manager is the storage/UX
  layer, the password is validated by the app's own server (S-04).
- The official **Shrine** sample (S-33) demonstrates exactly this: multi-method sign-up/sign-in,
  settings configuration and **session management** using Credential Manager with the app's own
  session — i.e. Credential Manager *with* an app-owned session, not Google-owned identity.
- **Digital Asset Links** are required only to share credentials between the app and a KeepLab
  website (S-04). Optional; not needed for a mobile-only phase.

### 3.1 Architecture (approved direction)

```
Android Credential Manager UI  (bottom sheet: passkey / password)
        |
        v
KeepLab credential  (passkey private key on device / username+password)
        |
        v
KeepLab Backend  (relying party server: challenge, public-key store, verification)
        |
        v
KeepLab account   (KeepLab-owned identity, sessions, tokens)
```

### 3.2 Explicitly separate, and NOT approved

```
Sign in with Google  --->  Google identity federation  --->  FORBIDDEN_UNLESS_HUMAN_APPROVED
```

The two paths share a *UI container* (Credential Manager's sheet can host federated providers) but
are **different trust relationships**. KeepLab uses the container; it does **not** enable the Google
provider.

---

## 4. Future KeepLab authentication options — `KEEPLAB_DESIGN_INFERENCE`

**Not frozen.** This is a comparison and a *recommended shortlist*, not a decision.

| Option | Security | Impl. complexity | Backend requirements | Account recovery | Multi-device | Mainland-China usability (publicly supportable) | Vendor lock-in | Offline session |
|--------|----------|------------------|----------------------|------------------|--------------|-----------------------------------------------|----------------|-----------------|
| Email + password | Medium (password) | Low | hash store (Argon2id), reset flow, rate limiting | Email reset link | Good | Email deliverability varies; needs an email sender | None | Good |
| Email verification code | Medium-High (no password to leak) | Medium | code issue/verify, expiry, rate limit, email sender | Same channel | OK | Depends on email provider | None | OK (session after first sign-in) |
| Username + password | Medium | Low | as email+password, no email sender needed | **Weak** (no natural recovery channel) | Good | Email-free | None | Good |
| Phone verification (SMS) | Medium-High | Medium-High | SMS gateway, per-message cost, abuse controls | Phone-based | OK | SMS delivery locally reliable; cost/abuse are the real issues | SMS aggregator | OK |
| Passkey | **High** (phishing-resistant, no shared secret) | Medium-High | RP server: challenges, public keys, WebAuthn verify; recovery still needed | Needs a bootstrap method (e.g. email or recovery codes) | **Good** (synced passkeys) / device-bound otherwise | Works on modern Android; ecosystem caveats | None (WebAuthn is a standard) | **Depends on session design** (see §5) |
| Password + optional passkey | High (progressive) | Medium-High | both stacks above | Email reset + passkey as second factor/upgrade | Good | Good | None | Good |

### 4.1 Recommended shortlist (`KEEPLAB_DESIGN_INFERENCE`)

1. **Email + password with an optional passkey upgrade** *(progressive)* — lowest first cost, a clear
   upgrade path to passkey, and a real recovery channel.
2. **Passkey-first with an email/recovery-code bootstrap** — best security end-state, higher build.
3. **Phone + code** — viable fallback, dominated by SMS cost/abuse concerns.

Not recommended as a primary: **username + password only** (no recovery channel) and **raw
resource-owner-password OAuth grant** (RFC 9700/2.1 is removing it — S-30).

### 4.2 Sign-in-time state machine (`KEEPLAB_DESIGN_INFERENCE`)

```
SIGNED_OUT ──sign in──▶ AUTHENTICATING ──ok──▶ SIGNED_IN
     ▲                        │  │
     │                        │  ├─ bad secret ──▶ INVALID_CREDENTIAL ──▶ AUTHENTICATING
     │                        │  ├─ 5xx ─────────▶ SERVER_ERROR ──▶ retry
     │                        │  ├─ no network ──▶ NETWORK_ERROR ──▶ retry
     │                        │  └─ disabled ────▶ ACCOUNT_DISABLED
     │
     └──── sign out ──── SIGNED_IN
SIGNED_IN ──token rejected──▶ AUTH_EXPIRED ──silent refresh──▶ SIGNED_IN
                                     └─ refresh fails ──▶ REAUTH_REQUIRED ──▶ AUTHENTICATING
Connectivity loss:
   valid local session ──▶ OFFLINE_WITH_VALID_LOCAL_SESSION   (app fully usable)
   no local session    ──▶ OFFLINE_WITHOUT_VALID_SESSION      (local-only mode / non-blocking prompt)
```

---

## 5. Session / token principles — `KEEPLAB_DESIGN_INFERENCE`, anchored in `OFFICIAL_FACT`

**Anchor:** S-29, S-30 (RFC 9700 / OAuth 2.1) and S-13 (Credential Manager secure storage).

Recommended principles (principles only — **no implementation**):

1. **Short-lived access token** + **longer-lived refresh token**. Access token lifetime minutes;
   refresh token days-weeks (S-29, S-30).
2. **Rotate the refresh token on every use**; invalidate the previous one immediately. Reuse of a
   rotated token is the detection signal for theft → revoke the family (S-29).
3. **Revocation** must exist server-side: sign-out, "sign out all devices", and administrative
   disable (S-29).
4. **Device/session list** in account settings: label sessions by device, allow per-session revoke.
5. **Secure Android storage**: keep refresh material in app-private storage protected by the Android
   Keystore. Never log it. Never store it outside the app sandbox. (Consistent with S-13's
   device-bound credential concept.)
6. **Offline sessions are a first-class case**: the app must remain usable with a locally valid
   session while offline; a *pending* mutation queue must not be discarded merely because a refresh
   could not complete. Only an explicit server "session invalid" response moves the app to
   `REAUTH_REQUIRED`.
7. Optional: **sender-constrained tokens (DPoP)** if threat-model justifies it later (S-29).
8. Behaviour on `AUTH_REQUIRED`: pause sync, keep local data, surface a non-destructive re-auth gate.
   **Never delete local notes on auth failure.**

---

## 6. Security principles (auth scope) — `KEEPLAB_DESIGN_INFERENCE`, anchored in `OFFICIAL_FACT`

| Area | Principle | Anchor |
|------|-----------|--------|
| Transport | TLS only; no cleartext; certificate validation on | S-29 |
| Password storage | Server-side adaptive hash (Argon2id preferred; scrypt/bcrypt/PBKDF2 fallback), per-user salt, tuned work factor; never reversible encryption | S-31 |
| Rate limiting | Per-account **and** per-IP throttling on login, code issue, code verify, reset | S-29 |
| Account enumeration | Uniform responses/timings for "unknown user" vs "wrong password"; generic reset messages | S-29 |
| Credential stuffing | Rate limit + lockout/backoff + optional signals; never reveal which factor failed | S-29 |
| Code abuse | Expiring single-use codes, attempt caps, resend cooldowns, device/IP heuristics | S-29 |
| Refresh-token rotation | Rotate on use; revoke family on reuse | S-29 |
| Revocation | Sign-out, all-device sign-out, admin disable | S-29 |
| Device loss | Remote session revocation + short access-token lifetime bounds the exposure window | S-29 |
| Database encryption | Encrypt at rest; treat fields containing PII as sensitive | — |
| Attachment access control | Per-account authorization on every attachment fetch; no guessable public URLs | — |
| Logging hygiene | Never log secrets/tokens/passwords/codes; redact identifiers | S-31 |
| PII minimisation | Collect the minimum identity data the product needs | — |

---

## 7. What this blueprint does **not** do

- It does not implement login/registration/verification/token/password handling.
- It does not add any dependency (no `androidx.credentials`, no OAuth, no Firebase).
- It does not decide the final auth method (shortlist only).
- It does not touch `KeepLab-Relay/app/src/main/**`, Gradle, Room schema, network or backend code.
- It does not adopt Google identity in any form.

## 8. Confidence

| Conclusion | Confidence | Basis |
|------------|------------|-------|
| Credential Manager is Android's recommended credential API | **HIGH** | T1 (S-01..S-06) |
| Legacy Google Sign-In is deprecated | **HIGH** | T1 (S-03) |
| Credential Manager works with an app-owned backend (passwords + passkeys) | **HIGH** | T1 (S-01, S-04, S-05) + T2 official sample (S-33) |
| Passkey verification belongs to the relying-party (KeepLab) server | **HIGH** | T1 (S-05) + T2 (S-36, S-37) |
| KeepLab should use passkey-first | **MEDIUM** | design inference; depends on product decision (unfrozen) |
| Auth-method shortlist ranking | **MEDIUM** | comparative analysis, no product constraints applied |
| Mobile offline session must survive a failed refresh | **MEDIUM** | derived from offline-first requirement (S-07) |
| Mainland-China usability notes | **LOW** | no Tier-1/Tier-2 source consulted in this pass; flagged as a research gap, not a claim |
