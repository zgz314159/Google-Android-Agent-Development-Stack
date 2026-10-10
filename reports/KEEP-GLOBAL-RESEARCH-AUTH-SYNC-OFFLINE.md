# KEEP-GLOBAL-RESEARCH-AUTH-SYNC-OFFLINE

**Web-first Google Keep / Android Identity / Offline-Sync research**

- Task ID: `KEEP-GLOBAL-RESEARCH-AUTH-SYNC-OFFLINE`
- Date: **2026-10-05 (CST)**
- Method: **WEB_FIRST · DEVICE_TARGETED · BENCHMARK_DEVICE_FIRST**
- Device usage: **none** (no `adb` input/tap, no Maestro/UiAutomator run, no user creation/switching,
  no account login, no note creation, no APK install/uninstall). Device `c67d32fa`
  (M2007J17C/gauguinpro) was **not used and is not needed** for this phase.
- Product changes: **none.** `KeepLab-Relay/app/src/main/**`, Gradle, Room schema, network code, auth
  code, backend code, Testapp, PowerAi and Hermes core were **not modified**.
- Historical evidence: **not rewritten.** `reports/KEEPLAB-AUTH-BOUNDARY-CORRECTION.md`,
  `reports/P0B-GK-MATCHED-SCALE-A2-ACCOUNT-MODEL.md` and all P0B evidence are preserved as-is.

Companion artifacts:
- `reports/KEEP-RESEARCH-SOURCE-MATRIX.md` (provenance, tiers, classification)
- `reports/KEEP-AUTH-REFERENCE-BLUEPRINT.md` (login/session reference + own-backend identity)
- `reports/KEEP-OFFLINE-SYNC-BLUEPRINT.md` (Keep public behavior matrix + KeepLab sync design)
- `reports/KEEP-DEVICE-VERIFICATION-BACKLOG.md` (minimal device backlog)
- `orchestration/hermes/evidence/keep-global-research-auth-sync-offline/` (compact evidence)

---

## 0. Authoritative governance (preserved verbatim)

```
GOOGLE KEEP:                     REFERENCE PRODUCT ONLY
GOOGLE KEEP BENCHMARK ACCOUNT:   REFERENCE_SIDE_ONLY
KEEPLAB AUTHORITY:               OWN_BACKEND
KEEPLAB GOOGLE ACCOUNT REQUIRED: NO
GOOGLE AUTH IN KEEPLAB:          FORBIDDEN_UNLESS_HUMAN_APPROVED
FIREBASE AUTH IN KEEPLAB:        FORBIDDEN_UNLESS_HUMAN_APPROVED
GOOGLE PRIVATE API:              FORBIDDEN
```

Google Keep **public** behaviour may be studied. Google's private backend/auth/database/protocol was
**not** reverse-engineered and is **not** guessed anywhere in these reports. KeepLab's future
implementation is an **independent** implementation against a **KeepLab-owned** backend.

---

## 1. Research method

`WEB_FIRST` for general technology/architecture, `BENCHMARK_DEVICE_FIRST` reserved for performance,
and `DEVICE_TARGETED` only for the small set of Keep-specific questions public sources cannot answer.
Product research was deliberately **not** conflated with performance benchmarking (§24).

Source hierarchy used (see the source matrix):
**T1** Android/Google/Keep Help/Jetpack/AOSP/standards · **T2** official repos & standards bodies ·
**T3** community/implementation · **T4** weak/anecdotal (recorded, never load-bearing).

---

## 2. No device in this phase

Confirmed: no Android device was mutated. The attached/new device `c67d32fa`
(M2007J17C / gauguinpro) was not needed and was not touched. Historical device records were not
changed. `P0B-GK-DEVICE-REBASE` was not started.

**Device-attachment note (honest):** during this task no check of live device attachment was
required, because no device work was in scope. Nothing in this report depends on a live device.

---

## 3. Source hierarchy & 4. Source provenance

See `reports/KEEP-RESEARCH-SOURCE-MATRIX.md`. Every important claim there carries: source title,
publisher/repo, URL, source tier, access date, the claim it supports, the evidence category
(GOOGLE KEEP / ANDROID PLATFORM / GENERAL ARCHITECTURE / COMMUNITY IMPLEMENTATION), and a
classification (`OFFICIAL_FACT` / `PUBLIC_KEEP_BEHAVIOR` / `COMMUNITY_OBSERVATION` /
`IMPLEMENTATION_EXAMPLE` / `KEEPLAB_DESIGN_INFERENCE` / `DEVICE_VALIDATION_REQUIRED`).

Counts are given in §34.

---

## 5. Google / Android identity research

*(Full detail: `KEEP-AUTH-REFERENCE-BLUEPRINT.md`.)*

`OFFICIAL_FACT` — Android's current recommendation is **Credential Manager**
(`androidx.credentials`), the recommended Jetpack API for credential exchange. It unifies
**passkeys, passwords, Sign in with Google / federated sign-in, and digital credentials**, provides a
bottom-sheet UI inline to app content, integrates with password managers and autofill, and supports
**Restore Credentials** on a new device. Passkeys are positioned as the **preferred/default** method;
passwords are supported but second-choice. **Legacy Google Sign-In** (part of
`com.google.android.gms:play-services-auth`) is **deprecated** and slated for removal; official
guidance is to migrate to Credential Manager (S-01..S-06, S-13).

Key terminology the platform itself uses: **relying party client app** (your app), **relying party
server** (your app server), **credential provider** (e.g. Google Password Manager) (S-01).

Sub-topics investigated: credential chooser / bottom-sheet UX; explicit sign-in button fallback;
automatic sign-in; reauthentication; sign-out; account switching; session restoration; error states;
cancellation; multiple credential providers; Android version compatibility (passwords API 19+,
passkeys API 28+); legacy Google Sign-In migration status.

**The conclusion we were told NOT to draw** ("KeepLab should use Sign in with Google") is explicitly
not drawn. The separable, useful part is the **platform UX vocabulary**, not Google identity.

---

## 6. Google Keep account model — `PUBLIC_KEEP_BEHAVIOR`

Publicly documented (T1):

- Keep is **Google-account-bound**: the note you can see depends on which account you are signed in
  with; opening a note from a different account than it was shared with yields a **"Request access"**
  flow (S-20).
- Keep is **multi-account capable**: the widget article states "*If you have used multiple accounts on
  your Google Keep app, you can select an account*" (S-22), and Google's Workspace update added
  **side-by-side multi-account** on large-screen devices (S-60, S-61). Each account keeps a
  **separate note library**.
- Keep's sync is exposed as an **Android account sync item**: *Settings → Accounts → Google →
  account → Sync →* **Keep** (S-16); the platform-level sync UI is documented separately (S-15).

Not publicly documented (must remain `UNKNOWN_PRIVATE`): how accounts are cached locally, whether the
sync toggle gates fetch or push, how side-by-side account sessions are isolated internally.

---

## 7. Google Keep sync behaviour — public evidence & state model

Publicly documented (T1) — see the full matrix in `KEEP-OFFLINE-SYNC-BLUEPRINT.md` §1:

| Behaviour | Public statement |
|-----------|------------------|
| Cross-device sync | "Everything syncs across all your devices" (S-27) |
| Per-account sync toggle | Android account sync item `Keep` (S-16) |
| Offline editing + conflicts | "Conflicting edits found" when the same note is edited on different devices with one offline, or on low-bandwidth Wi-Fi; options **Keep selected** / **Keep both** (S-17) |
| Reload / re-download | optional reload prompt; notes are saved then **re-downloaded to the device**; needs a strong connection; may not finish, with an alert to try again (S-18) |
| Delete propagation | deleting a note you own deletes it for everyone shared with; 7-day Trash (S-19, S-21) |
| Archive | archive/unarchive; independent of a note's task (S-21) |
| Version history | previous versions downloadable (web) (S-23) |
| Collaboration | collaborators may label/colour/archive/remind without affecting others (S-19) |
| Account-scoped data | "Request access" when opened from the wrong account (S-20) |

**Public behaviour state model (client-observable, not internal):**

```
[SYNCED] --local edit--> [EDITED_LOCALLY] --(offline)--> stays local
        --(online)--> [SYNCING] --ok--> [SYNCED]
                            \-- two-device divergence --> [CONFLICT: "Conflicting edits found"]
                                                              |-> Keep selected -> one version wins
                                                              \-> Keep both     -> outcome UNKNOWN (J1)
[SYNCING] --cannot finish--> [RELOAD PROMPT] --accept--> [RE-DOWNLOADING] --(may not finish)--> [ALERT: try again]
[delivered note] --delete (owner)--> [TRASH 7d] --> [GONE]
```

Explicitly **not** claimed: Keep's internal sync algorithm. It is not publicly documented and must
not be inferred from the observable behaviour above.

**Tension worth recording:** the official marketing claim ("syncs in real-time", S-27) is
**contradicted** by multiple community reports of Android→web propagation taking 30 s–30 min and by a
report that a note must be re-opened on the device to flush the change (S-54, S-55). This is a
`DEVICE_VALIDATION_REQUIRED` item (J3), not a licence to assume either is universally true.

---

## 8. Offline-first Android architecture — `OFFICIAL_FACT`

*(Full detail: `KEEP-OFFLINE-SYNC-BLUEPRINT.md` §2.)*

Android officially recommends: a **local data source as the canonical source of truth**; repositories
combining a local + a network data source; **reads from local, observed as state**; writes persisted
for later; **pull / push / hybrid** synchronization; and, for conflict, **last-write-wins by
timestamp**. **WorkManager** is the recommended background engine (constraints, `Result.retry()`,
LINEAR/EXPONENTIAL backoff with a 10 s minimum, work persisted across reboot); **sync adapters
exist but are not the default recommendation.** Connectivity is monitored via
`ConnectivityManager`/`NetworkCallback`. (S-07..S-12, S-14.)

---

## 9. KeepLab independent sync blueprint — `KEEPLAB_DESIGN_INFERENCE`

**This section is our design, not Google Keep's internal architecture.**

The candidate architecture (Compose UI → ViewModel → Repository → Room SSOT → Sync metadata →
PendingMutation/Outbox → WorkManager → HTTPS API → KeepLab Backend → KeepLab DB) was **not blindly
accepted**; it was validated and then refined. Verdict: **accepted with four refinements**:

1. an explicit **outbox table** (not only per-entity dirty flags);
2. **client-generated UUIDs** everywhere;
3. **server revision/version** + a monotonic **delta cursor**;
4. **tombstones** (`deleted_at`) instead of hard local deletes.

Reasons, alternatives considered, and the full diagram are in `KEEP-OFFLINE-SYNC-BLUEPRINT.md` §3.

---

## 10. Data / sync state machine — `KEEPLAB_DESIGN_INFERENCE`

Recommended **minimal robust** set: `LOCAL_ONLY` (optional) · `SYNC_PENDING` · `SYNCING` · `SYNCED` ·
`SYNC_FAILED` · `CONFLICT` · `DELETE_PENDING`, plus a **session-level** `AUTH_REQUIRED`.

**Folded away (with reason):** `DIRTY`→`SYNC_PENDING`; `RETRY_WAIT`→`SYNC_PENDING` + attempt
metadata (WorkManager owns timing); `TOMBSTONE`→a *field* (`deleted_at`), not a state.

Entry/exit conditions, persisted fields, UI indication, network requirement and retry policy per
state are tabulated in `KEEP-OFFLINE-SYNC-BLUEPRINT.md` §4.

---

## 11. Mutation outbox — `KEEPLAB_DESIGN_INFERENCE`

Evaluated: operation log vs entity dirty flags vs hybrid. **Recommended: hybrid** — an outbox table
plus per-entity `sync_state`. Outbox rows carry `mutation_id` (idempotency key), `entity_id` (client
UUID), `op_type`, captured `payload`, `base_revision`, `attempt_count`, `last_error`, client
`created_at` (ordering only), and a `coalesce_key`. Rules: entity write + outbox insert in **one
transaction**; coalesce per `(entity, op-class)`; push the **captured payload** (not the live row);
delete the outbox row only on confirmed success; cap attempts and surface a FAILED state.

Full table + rules: `KEEP-OFFLINE-SYNC-BLUEPRINT.md` §5.

---

## 12. Conflict resolution — `KEEPLAB_DESIGN_INFERENCE`

Research basis: Android documents **LWW** (S-08); Google Keep **publicly** documents a user-facing
**"Conflicting edits found"** chooser (S-17) — used as `PUBLIC_KEEP_BEHAVIOR`, **not** as proof of
Keep's internal algorithm.

Recommended **per-field** policy:

| Field | Policy |
|-------|--------|
| title/body | server revision check; non-auto-mergeable divergence → user resolves (keep local / keep server / **keep both**); single-sided change fast-forwards |
| checklist | **item-level merge by stable item id** (union of adds, deletes by id, per-item text LWW) |
| labels | **set union** |
| archive / pin / colour | **LWW on server revision** |
| attachments | **content-addressed, append-only**, no merge |
| delete vs concurrent edit | **explicit conflict** surfaced to the user |

Explicitly **not** recommended for Phase-1: CRDT for bodies; automatic three-way text merge;
client-wins-everywhere LWW. Server returns a **409 + current version** on a stale mutation rather
than silently applying or rejecting. Full rationale: `KEEP-OFFLINE-SYNC-BLUEPRINT.md` §6.

---

## 13. Keep official help research — `GOOGLE_KEEP_PUBLIC_BEHAVIOR_MATRIX`

Built and maintained in `KEEP-OFFLINE-SYNC-BLUEPRINT.md` §1 with the required columns (capability ·
officially documented · source · observable semantics · unknown internals · KeepLab implication ·
device verification needed), covering: sync troubleshooting, conflicting edits, sharing, archive,
delete, labels, reminders, account behaviour, widgets/account selection, offline/reload behaviour,
collaboration, and version history.

---

## 14. GitHub research

Reviewed (details + assessment in the source matrix): official samples
**`android/identity-samples`** (S-33; includes `Shrine` — recommended Credential Manager UX **with
session management** — `CredentialManager`, `CredentialProvider/MyVault`, `WebView`, `SmsVerification`,
`DigitalCredentials`; Apache-2.0; ~517★; last commit ~2026-08), **`android/nowinandroid`** (S-34;
official offline-first + sync + Macrobenchmark reference), **`android/architecture-samples`** (S-35),
**`android/skills`** (S-36), **`android/sunflower`** (S-39); plus community examples
**FieldNotes-OfflineFirstSystemDesign** (S-40), **OfflineNotesEngine** (S-41),
**OfflineFirstAppMechanism** (S-42), **latchsync** (S-43), **android-room-workmanager-offline-first-lab**
(S-44), **Android-OfflineFirst-Sync-App** (S-45), and the standard **AppAuth-Android** (S-38).

For each: repo, maintainer, activity, architecture, useful ideas, anti-patterns, production maturity,
license, and type (`OFFICIAL_SAMPLE` / `REFERENCE_IMPLEMENTATION` / `COMMUNITY_EXAMPLE`).
**No code was copied into KeepLab. No dependency was installed.**

Notable anti-patterns found: deleting local rows when a sync fails "to keep data consistent"
(OfflineFirstAppMechanism); treating `getWorkInfosByTagFlow()` as an event stream (S-48); generating
an unbounded unique-work name per save (S-46).

---

## 15. Community research

Developer-community and user-community evidence consulted for: Keep offline behaviour, conflicting
edits, multi-account behaviour, sync delays, reconnect behaviour; Credential Manager confusion;
WorkManager sync pitfalls; Room offline-first pitfalls; multi-device note-conflict strategies.

All of it is labelled `COMMUNITY_OBSERVATION` and is used **only** to discover edge cases, failure
modes, and questions for later device verification — never elevated above official documentation.
The strongest community signal is the disagreement about offline indicators and propagation timing
(S-52..S-57), which is precisely what produced backlog journeys J2 and J3.

---

## 16. Login UX reference model

Produced as a generic model (not a Google clone): `SIGNED_OUT`, `AUTHENTICATING`, `SIGNED_IN`,
`AUTH_EXPIRED`, `REAUTH_REQUIRED`, `NETWORK_ERROR`, `INVALID_CREDENTIAL`, `ACCOUNT_DISABLED`,
`SERVER_ERROR`, `OFFLINE_WITH_VALID_LOCAL_SESSION`, `OFFLINE_WITHOUT_VALID_SESSION`, with a
per-state trigger and UI expectation table, an explicit "inspired by Google/Android" vs "owned
entirely by KeepLab Backend" split, and a sign-in-time state machine.
See `KEEP-AUTH-REFERENCE-BLUEPRINT.md` §2.

---

## 17. Future KeepLab auth options — `RECOMMENDED SHORTLIST` (not frozen)

Compared on security, implementation complexity, backend requirements, recovery, multi-device,
publicly-supportable Mainland-China considerations, vendor lock-in, and offline-session behaviour:
email+password · email code · username+password · phone verification · passkey · password+optional
passkey.

**Recommended shortlist (not a decision):**
1. **Email + password with an optional passkey upgrade** (progressive);
2. **Passkey-first with an email / recovery-code bootstrap**;
3. **Phone + code** (viable fallback; SMS cost/abuse are the real constraints).

Not recommended as primary: username+password only (no recovery channel); raw resource-owner-password
OAuth grant (RFC 9700/OAuth 2.1 is removing it — S-30). No auth method was implemented and none was
frozen. Mainland-China notes are marked **LOW** confidence (no T1/T2 source consulted) and recorded
as a research gap, not a claim.

---

## 18. Credential Manager with an own backend — **SUPPORTED**

**YES.** Credential Manager is a *client-side credential exchange API*; it does not require Google to
be the identity authority (S-01). Passkeys use a **relying-party model**: the app's **own server**
stores the public key, issues the challenge and verifies the assertion (S-05, S-36, S-37). Passwords
stored via `CreatePasswordRequest`/`GetPasswordOption` belong to the app's own account system and are
validated by the app's own server (S-04). The official **Shrine** sample demonstrates Credential
Manager with **app-owned session management** (S-33). Digital Asset Links are needed only to share
credentials with a KeepLab website (optional).

```
Android credential UI  ->  KeepLab credential (passkey/password)  ->  KeepLab Backend (RP server)  ->  KeepLab account
Sign in with Google    ->  Google identity federation               ->  FORBIDDEN_UNLESS_HUMAN_APPROVED
```
The two share a UI *container* but are different trust relationships. KeepLab uses the container, not
the Google provider.

---

## 19. Server-side blueprint (technology-agnostic)

Conceptual services: Auth API · User service · Session/token service · Notes API · Sync API ·
Attachments API · primary database · object storage for attachments · optional later notification/push
layer. Conceptual endpoints (design examples, **not** commitments): `register`, `login`,
`passkey/challenge` + `passkey/verify`, `refresh`, `logout` / `sessions/{id}/revoke`, notes CRUD,
`POST /sync/mutations` (idempotent), `GET /sync/changes?since=<cursor>`, `GET /sync/checkpoint`,
attachment upload/download. Server invariants: idempotent mutations by `mutation_id`; monotonic note
revisions; cursor advanced only on a clean apply; server-side tombstones with a retention window;
per-account authorization on every attachment fetch. **No cloud provider was chosen.**
Full detail: `KEEP-OFFLINE-SYNC-BLUEPRINT.md` §7.

---

## 20. Session / token research — principles only

Short-lived access token + longer-lived refresh token; **rotate the refresh token on every use** and
invalidate the previous one (reuse = theft signal → revoke the family); server-side revocation;
device/session list with per-session revoke; refresh material in app-private storage protected by the
Android Keystore; **offline sessions are first-class** (a failed refresh must not discard local
data); optional sender-constrained tokens (DPoP) if later justified. Anchored in RFC 9700 / OAuth 2.1
(S-29, S-30) and Credential Manager's device-bound credential concept (S-13). **No secrets stored, no
implementation.**

---

## 21. Security research (no implementation)

TLS only; server-side adaptive password hashing (Argon2id preferred, per-user salt, tuned work
factor — S-31); rate limiting on login/code/reset; anti-enumeration (uniform responses/timings);
credential-stuffing defences and lockout; verification-code abuse controls (expiry, single use,
attempt caps, resend cooldowns); refresh-token rotation + revocation; device-loss handling via remote
session revocation + short access-token lifetimes; database encryption at rest; per-account
attachment access control with non-guessable URLs; logging hygiene (never log secrets/tokens/codes/
passwords; redact identifiers); PII minimisation. Detail: `KEEP-AUTH-REFERENCE-BLUEPRINT.md` §6.

---

## 22. What actually needs a device? (critical deliverable)

Classification of every unresolved question into `NO_DEVICE_NEEDED` ·
`OPTIONAL_DEVICE_CONFIRMATION` · `MUST_DEVICE_VALIDATE` · `MUST_DEVICE_BENCHMARK`:
see `KEEP-DEVICE-VERIFICATION-BACKLOG.md` §1.

Highlights:
- Credential Manager documented architecture → **NO_DEVICE_NEEDED**
- Google Keep public sync setting (Android account sync item) → **NO_DEVICE_NEEDED**
- conflicting-edits *semantics* → **NO_DEVICE_NEEDED**; conflict *dialog structure / "Keep both"
  outcome* → **MUST_DEVICE_VALIDATE**
- exact current Keep account-switch UI → **OPTIONAL_DEVICE_CONFIRMATION**
- offline indicator / snackbar wording → **MUST_DEVICE_VALIDATE** (undocumented, community disagrees)
- cross-device propagation timing → **MUST_DEVICE_VALIDATE**
- data safety across reload/reinstall → **MUST_DEVICE_VALIDATE**
- cold start / warm start / restart / jank / memory / rotation / 10-100-500-1000 scale
  → **MUST_DEVICE_BENCHMARK** (separate concern)

**Nothing was automatically pushed into DEVICE_VALIDATE.**

---

## 23. Device verification budget

Strict targeted backlog: **4 MUST first-pass journeys** (J1 conflicting-edits outcome; J2 offline
indicator; J3 propagation timing; J4 reload/reinstall data safety) + **2 OPTIONAL** (J5 account
switcher presentation; J6 no-account first-run gate). Cap 8 — backed by **6**. Zero journeys need a
visual LLM. Each journey has QUESTION / WHY WEB IS INSUFFICIENT / PRECONDITION / MINIMAL STEPS /
EXPECTED EVIDENCE / CLEANUP / VISUAL-LLM-NEEDED. Full detail:
`KEEP-DEVICE-VERIFICATION-BACKLOG.md` §2.

---

## 24. Performance separation

Preserved: **P0B performance benchmarking is a separate concern.** A valid matched-scale ratio still
requires Google Keep **and** KeepLab on the **same physical device**. This research task did **not**
choose or rebase the benchmark device, and did **not** start `P0B-GK-DEVICE-REBASE` or
`P0B-GK-MATCHED-SCALE-A2`.

---

## 25. Research questions — answers

**Q1. What parts of Google Keep login/account behaviour can be understood without a device?**
The *account model*: account-bound data, multi-account support with separate per-account libraries,
widget account selection, sync as an Android account sync item, the "Request access" cross-account
flow, and the account-required implied behaviour. All T1-documented (S-16, S-20, S-22). The *exact
account-switcher UI and the no-account first-run gate* are not documented (→ J5/J6, optional).

**Q2. What is Android's current recommended authentication UX/API?**
Credential Manager (`androidx.credentials`): unified sheet for passkeys/passwords/federated sign-in;
passkey-first with an explicit button fallback; bottom-sheet inline UI; Restore Credentials on a new
device; legacy Google Sign-In is deprecated (S-01..S-06).

**Q3. Can Credential Manager be used with KeepLab's own backend identity?**
**YES — SUPPORTED.** Passkeys' relying-party model and Credential Manager's password API are both
app-server-owned; the official Shrine sample shows Credential Manager with app-owned sessions
(S-01, S-04, S-05, S-33, S-36, S-37).

**Q4. What publicly documented sync/offline behaviour does Google Keep expose?**
Cross-device sync; per-account Android sync toggle; offline editing; a "Conflicting edits found"
chooser (Keep selected / Keep both); a reload that re-downloads notes and can be incomplete; delete
propagation + 7-day Trash; archive; version history; collaborator metadata independence; shared-note
account dependence (S-16..S-27).

**Q5. What does Android officially recommend for offline-first data architecture?**
Local data source = canonical source of truth; repository with local+network sources; UI reads local
as state; pull/push/hybrid sync; LWW conflict resolution; WorkManager for background sync with
constraints and exponential backoff; `NetworkCallback` for connectivity (S-07..S-12).

**Q6. What synchronization architecture best fits KeepLab?**
Compose + ViewModel + Repository + **Room as SSOT** + explicit **outbox** + **client UUIDs** +
**server revisions** + **tombstones** + **WorkManager** (single unique pipeline, network constraint,
exponential backoff) + cursor-based **delta pull** + HTTPS to a KeepLab backend. Detailed in
`KEEP-OFFLINE-SYNC-BLUEPRINT.md` §3.

**Q7. What conflict policy best fits notes/checklists?**
Per-field: **user-resolved revision conflict for title/body** (with a "keep both" option),
**item-level merge for checklists**, **set union for labels**, **LWW for archive/pin/colour**,
**append-only for attachments**, **explicit conflict for delete-vs-edit**. No CRDT in Phase-1.

**Q8. What should be local source of truth?**
**Room.** All reads flow from Room Flows; the network only updates Room.

**Q9. What belongs in an outbox / mutation queue?**
Create/update/delete/archive/unarchive/pin/unpin/set-colour/label add-remove/checklist put/attachment
add — each with `mutation_id`, `entity_id`, `op_type`, captured payload, `base_revision`,
`attempt_count`, `last_error`, and a coalesce key; written atomically with the entity change.

**Q10. Which behaviours truly require Google Keep device verification?**
Only four material ones the web cannot settle: the conflict surface's structure and **"Keep both"
outcome**; whether/how an **offline indicator** is shown; **cross-device propagation timing /
flush-on-open**; and **data safety across reload/reinstall**. Backlog: `KEEP-DEVICE-VERIFICATION-BACKLOG.md`.

**Q11. Which behaviours truly require same-device benchmarking?**
The P0B performance set: cold start, warm start, restart, frame/jank, memory, rotation/state
restoration, and the 10/100/500/1000-note dataset performance and same-device parity ratios (§24).

**Q12. What must remain unknown because Google's private implementation is not public?**
Keep's sync protocol; conflict algorithm and granularity; local store schema; retry/backoff; the
notification/transport mechanism; the token model; the internal meaning of the account sync toggle;
the precise mechanics of "Keep both"; version-history retention; and what the reload path does with
unsynced local edits.

---

## 26. Required outputs

| Output | Path | Status |
|--------|------|--------|
| Main research report | `reports/KEEP-GLOBAL-RESEARCH-AUTH-SYNC-OFFLINE.md` | this file |
| Auth reference blueprint | `reports/KEEP-AUTH-REFERENCE-BLUEPRINT.md` | written |
| Offline-sync blueprint | `reports/KEEP-OFFLINE-SYNC-BLUEPRINT.md` | written |
| Device verification backlog | `reports/KEEP-DEVICE-VERIFICATION-BACKLOG.md` | written |
| Research source matrix | `reports/KEEP-RESEARCH-SOURCE-MATRIX.md` | written |
| Supporting evidence | `orchestration/hermes/evidence/keep-global-research-auth-sync-offline/` | written |

---

## 27–28. Source matrix & claim confidence

The matrix (ID · claim · source title · publisher · URL · date/access date · tier · classification ·
supports/contradicts · notes) is `reports/KEEP-RESEARCH-SOURCE-MATRIX.md`.

Every major conclusion carries a confidence and its basis. Highest-confidence conclusions rest on
T1 official documentation; medium on multiple consistent community observations; low on a single
anecdotal report. Per-report confidence tables appear at the end of each companion blueprint.

---

## 29. Public vs private boundary

```
KNOWN_PUBLICLY
  - Android: Credential Manager is the recommended credential API; legacy Google Sign-In deprecated;
    passkey relying-party model; offline-first SSOT + LWW + WorkManager guidance  (S-01..S-12)
  - Google Keep: account-bound, multi-account, Android-account sync item, offline editing,
    "Conflicting edits found" chooser, reload/re-download, delete propagation + 7-day Trash,
    archive, version history, collaborator metadata independence  (S-16..S-27)

DESIGN_INFERENCE   (ours — never present as Google Keep fact)
  - the KeepLab sync architecture, state machine, outbox, conflict policy, server blueprint,
    auth UX model and auth shortlist

UNKNOWN_PRIVATE
  - Keep's sync protocol, conflict algorithm, local schema, retry/backoff, transport, token model,
    "Keep both" mechanics, version retention, reload data-safety behaviour

DEVICE_CHECK_REQUIRED
  - J1 conflict-surface structure + "Keep both" outcome
  - J2 offline/sync indicator presence and wording
  - J3 cross-device propagation timing / flush-on-open
  - J4 data safety across reload and reinstall
  - (optional) J5 account switcher presentation; J6 no-account first-run gate
```

---

## 30. No product changes

No KeepLab `app/src/main/**`, Gradle, Room schema, network code, auth code or backend code was
modified. Testapp, PowerAi and Hermes core were not modified. This was research/report only.

---

## 31. Existing governance preserved

`reports/KEEPLAB-AUTH-BOUNDARY-CORRECTION.md` and `reports/P0B-GK-MATCHED-SCALE-A2-ACCOUNT-MODEL.md`
were **read only**. No frozen P0B evidence was rewritten. `MISSION.md`, `FACTORY_RULES.md`,
`.hermes.md`, `specification/**` were **read only**.

---

## 32. Contract guard

**ACTIVE.** This task wrote **only** to `reports/**` and
`orchestration/hermes/evidence/keep-global-research-auth-sync-offline/**` — both inside the frozen
contract's `allowed_paths`. No forbidden path was targeted; the guard was not bypassed.
Web access was available throughout; `WEB_RESEARCH_UNAVAILABLE` does not apply, and no research was
fabricated.

---

## 33. Research completion gate

| Gate | Result |
|------|--------|
| Official sources actually consulted | **PASS** (Android/Google/Keep Help/Jetpack/standards) |
| Keep Help actually consulted | **PASS** (8 Keep Help articles) |
| GitHub examples actually inspected | **PASS** (official + community, ≥ 10) |
| Community evidence separated from official facts | **PASS** (T3/T4 labelled; no T4 load-bearing) |
| All sources have provenance | **PASS** (source matrix) |
| Private Google implementation not guessed | **PASS** (no internals claimed) |
| KeepLab design inference explicitly labelled | **PASS** (all blueprints §) |
| Device verification backlog exists | **PASS** |
| Device backlog minimal | **PASS** (4 MUST + 2 OPTIONAL ≤ 8) |
| Performance separated from UX research | **PASS** (§24) |
| Product source unchanged | **PASS** |

---

## 34. Final output

```
KEEP-GLOBAL-RESEARCH-AUTH-SYNC-OFFLINE
======================================

OFFICIAL GOOGLE/ANDROID SOURCES: 27        (S-01..S-27; incl. 14 Android Developers docs,
                                           1 Android Help, 11 Keep Help, 1 Workspace announcement)
GOOGLE KEEP HELP SOURCES:        11        (S-16..S-26) + 1 official Workspace announcement (S-27)
GITHUB REPOS REVIEWED:           12        (S-33..S-45 incl. S-38, S-39)
COMMUNITY SOURCES REVIEWED:      21        (T3 16: S-46..S-61 · T4 5 recorded-and-rejected: S-62..S-66)

GOOGLE KEEP PUBLIC BEHAVIOR MODEL: READY
ANDROID IDENTITY RESEARCH:         READY
CREDENTIAL MANAGER + OWN BACKEND:  SUPPORTED
OFFLINE-FIRST BLUEPRINT:           READY
SYNC STATE MODEL:                  READY
CONFLICT STRATEGY:                 RECOMMENDED

PRIVATE GOOGLE IMPLEMENTATION GUESSED: NO

DEVICE QUESTIONS BEFORE RESEARCH:  N/A
DEVICE QUESTIONS AFTER RESEARCH:   6   (4 MUST + 2 OPTIONAL)
FIRST-PASS DEVICE JOURNEYS:        4
DEVICE WORK REDUCED:               YES
PERFORMANCE DEVICE BENCHMARK STILL REQUIRED: YES

KEEPLAB PRODUCT SOURCE MODIFIED:   NO
GOOGLE AUTH ADDED TO KEEPLAB:      NO
BACKEND IMPLEMENTED:               NO

CONTRACT GUARD:                    ACTIVE

STATUS:                            READY

NEXT:                              TARGETED_KEEP_DEVICE_VALIDATION
                                   (then, separately: P0B_MATCHED_SCALE_DEVICE_DECISION)

REPORT:
/mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack/reports/KEEP-GLOBAL-RESEARCH-AUTH-SYNC-OFFLINE.md

======================================
```

Stopped here. The device backlog was **not** executed. `P0B-GK-DEVICE-REBASE` was **not** started.
A2 was **not** started. P1 was **not** started.
