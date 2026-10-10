# KEEPLAB-AUTH-BOUNDARY-CORRECTION

**KeepLab Authentication Authority and Google Keep Reference Boundary**

- Date: 2026-10-05 (CST)
- Kind: governance / specification correction. **No product code, no authentication, no notes, no login.**
- Status: canonical decision recorded. Historical P0B evidence untouched.
- Canonical governance record: **this file**.

---

## 0. Human correction — authoritative

A Human Architecture Decision was issued, taking precedence over any earlier wording that
could be read as ambiguous:

- **Google Keep** = **REFERENCE PRODUCT ONLY**.
- **KeepLab** = **OWN PRODUCT + OWN BACKEND ACCOUNT SYSTEM**.

The false implication is explicitly rejected:

```
Google Keep uses Google Account
  => KeepLab should use Google Account        <- FALSE, never infer this
```

There are two independent identity domains that must never be conflated:

| Domain | Identity | Backend |
| --- | --- | --- |
| `A.` Google Keep (reference app) | benchmark-only Google account | Google's own (opaque, reference-side) |
| `B.` KeepLab (product) | KeepLab-owned account | KeepLab-owned backend |

This task freezes **authority / ownership / boundary only**. It does **not** freeze any
login-method UX, and it starts **no** implementation.

---

## 1. Canonical governance decision record (frozen)

**Title:** KeepLab Authentication Authority and Google Keep Reference Boundary
**Path:** `reports/KEEPLAB-AUTH-BOUNDARY-CORRECTION.md` (this file)
**Mechanism used:** this Stack's existing canonical record mechanism — a report under
`reports/` (the same mechanism used for the `P0B-GK-SANDBOX-PROVISION` "Governance Option A"
decision). **No ADR numbering exists in this Stack and none was invented; no parallel
governance framework was created.**

Frozen keys:

```
GOOGLE_KEEP_ACCOUNT_SCOPE: REFERENCE_APP_ONLY
KEEPLAB_AUTHORITY: OWN_BACKEND
GOOGLE_AUTH_IN_KEEPLAB: FORBIDDEN_UNLESS_HUMAN_APPROVED
FIREBASE_AUTH_IN_KEEPLAB: FORBIDDEN_UNLESS_HUMAN_APPROVED
GOOGLE_PRIVATE_API: FORBIDDEN
BENCHMARK_GOOGLE_ACCOUNT: ALLOWED_REFERENCE_SIDE_ONLY
```

### What may be referenced from Google Keep

login / signup layout and interaction concepts; loading / success / failure states; session
persistence UX; account/profile presentation UX; offline / reconnect UX; client-observable
sync behaviour; client-observable conflict / retry / recovery; account-switching UX;
navigation; visual hierarchy; accessibility; performance characteristics; user-visible backend
capabilities.

### What must NOT be copied or reverse-engineered

Google private authentication protocol; Google internal account service; Google Keep private
server APIs; Google private database; Google proprietary backend implementation; Google
credentials / tokens (classification `FORBIDDEN`).

### Forbidden default assumptions (unless a future human-approved Contract explicitly allows)

Google OAuth; Sign in with Google; Google Identity Services; Firebase Authentication; Google
account as mandatory identity; Google Keep private APIs; Google Keep backend protocol; Google
proprietary authentication protocol; Google branding; Google logo; Google account dependency;
a Firebase dependency introduced merely because Google Keep is the reference app.

Classification: `FORBIDDEN_UNLESS_HUMAN_APPROVED`.

### Canonical architecture (future product phase)

```
KeepLab Android App
        |  HTTPS
        v
KeepLab Backend API
        +-- Authentication
        +-- Registration
        +-- Account Verification
        +-- Session Management
        +-- Password Reset
        +-- Notes / Labels / Search / Sync / Attachments
        +-- future subscription / entitlement
        |
        v
KeepLab-owned Database
```

Exact authentication methods (username+password / email+password / email+code /
phone+code / combinations) remain **unfrozen** and are **not** decided by this task.

### Boundary note — current phase stays as-is

KeepLab's current governance (`KeepLab-Relay/MISSION.md`) still carries the hard invariant
*local-first, no network, no account*. The `KEEPLAB_AUTHORITY: OWN_BACKEND` decision fixes the
**future direction of authority** (KeepLab-owned, never Google). It does **not** lift the
current no-account invariant for the present phase, and it does not authorise any backend
work now. When the product/backend phase arrives, that invariant must be amended by a human
(via the project's own governance route, e.g. the `RISK-GOV-001` family) before implementation.
This is recorded as a boundary clarification, not a reopening of any frozen contract.

---

## 2. Recon — files inspected

Targeted search of active/canonical Stack and KeepLab documentation only. No full scan of
unrelated repositories. **Testapp and PowerAi were not touched.**

### Stack (`Google-Android-Agent-Development-Stack`)

| File | Why |
| --- | --- |
| `.hermes.md` | Stack project-context / governance invariants (protected) |
| `reports/P0B-GK-SANDBOX-PROVISION.md` | current Google Keep benchmark sandbox checkpoint |
| `reports/P0B-CLOSE-BENCHMARKABILITY.md` | benchmark contract semantics |
| `reports/P0B-PERFORMANCE-RELIABILITY.md` | P0B measurement records |
| `reports/REFERENCE-MAP.md` | reference-repo router |
| `specification/README.md`, `specification/docs/ARCHITECTURE.md`, `specification/docs/BROWNFIELD-INTEGRATION.md` | the Stack's decision mechanism (per-package contract metadata) |
| `specification/templates/design.md`, `specification/tests/fixtures/valid_package/design.md` | `decisions` (DEC-*) block shape |
| `orchestration/hermes/README.md`, `INTEGRATION.md`, `DEVICE-EXECUTION-POLICY.md` | orchestration policy surface |
| `orchestration/hermes/evidence/p0b-close/P0B-CLOSE-ANDROID-BENCHMARK-AUDIT.md` | benchmark/seeder boundaries, protected paths |
| `orchestration/hermes/evidence/p0b-gk-sandbox-provision/*.json` | sandbox state record |

### KeepLab (`KeepLab-Relay`)

| File | Why |
| --- | --- |
| `MISSION.md` | hard invariants ("no account, no sync, no network") |
| `FACTORY_RULES.md`, `FACTORY.md`, `HANDOFF.md` | governance / factory boundaries |
| `specs/google-keep-parity/PARITY-PROGRAM.md` | program charter + non-goals |
| `specs/google-keep-parity/GOOGLE-KEEP-REFERENCE.md` | frozen Google Keep reference |
| `specs/google-keep-parity/README.md` | baseline index |
| `specs/google-keep-parity/ROADMAP.md` | `RISK-GOV-001` governance gate; P7 ecosystem |
| `specs/p0b-close-benchmarkability/PRODUCT.md`, `design.md`, `requirements.md` | approved benchmark-only seeder mechanism |

---

## 3. Ambiguities found (classified)

No document was found that claims *"KeepLab should use a Google account"*. The ambiguity is
softer: several canonical documents enumerate Google-ecosystem **sync / collaboration /
ecosystem** parity as `FULL_KEEP_COVERAGE` gaps without stating that KeepLab's own identity
provider is *not* Google. A reader could infer a Google-account dependency from a "sync
parity" gap. Classification of every occurrence:

| # | Location | Text (gist) | Class |
| --- | --- | --- | --- |
| 1 | `KeepLab-Relay/MISSION.md` §Out-of-scope | "Any account, sign-in, cloud sync…" | `KEEPLAB_AUTH` (current-phase invariant) |
| 2 | `KeepLab-Relay/MISSION.md` §Hard invariants | local-first, no network | `KEEPLAB_AUTH` |
| 3 | `KeepLab-Relay/ROADMAP.md` L169-171 | P7 sync/sharing "no-account… blocked on RISK-GOV-001" | `KEEPLAB_AUTH` |
| 4 | `KeepLab-Relay/specs/google-keep-parity/PARITY-PROGRAM.md` L20 | non-goal: "Google account identity UI" | `REFERENCE_GOOGLE_KEEP_ONLY` |
| 5 | `.../GOOGLE-KEEP-REFERENCE.md` §4.10/4.11 | sharing/sync as `GOOGLE_ECOSYSTEM` / `CROSS_PLATFORM` | `REFERENCE_GOOGLE_KEEP_ONLY` (mild `AMBIGUOUS`) |
| 6 | `.../FUNCTION-PARITY.md` L128 | ecosystem in conflict with MISSION invariants | `AMBIGUOUS` |
| 7 | `reports/P0B-GK-SANDBOX-PROVISION.md` §12-13 | "sign in with a dedicated benchmark-only Google account" | `REFERENCE_GOOGLE_KEEP_ONLY` |
| 8 | `specs/p0b-close-benchmarkability/requirements.md` L81 | "no Google account is switched" | `REFERENCE_GOOGLE_KEEP_ONLY` (reference-side safety) |
| 9 | `specs/p0b-close-benchmarkability/design.md` DEC-004..006 | benchmark-only seeder; Google Keep reversible-only | `REFERENCE_GOOGLE_KEEP_ONLY` + KeepLab benchmark data |
| 10 | `KeepLab-Relay/benchmark/results/P0B-CANONICAL/a11y/a11y.json` L619 | reference-side account string in Google Keep a11y dump | `HISTORICAL_EVIDENCE` |
| 11 | Stack `reports/*`, `orchestration/hermes/evidence/**`, `terminal.log`, `finalization.json` | past P0B / P0B-CLOSE / sandbox records | `HISTORICAL_EVIDENCE` |

**Resolution:** occurrences #5 and #6 are the only reader-facing ambiguity. They are **not
rewritten** because they are inside the hash-frozen KeepLab parity baseline
(`BASELINE-MANIFEST.json`); editing them would break a freeze. Instead the boundary is frozen
canonically here (§1) and restated in the A2 guidance artifact (§5). Their wording is not
wrong — it describes Google Keep's own ecosystem — so no correction is required; the
clarification is additive.

---

## 4. Machine-readable policy status

```
MACHINE_READABLE_POLICY: NOT_APPLICABLE
```

Reasoning (observed, not assumed):

- This Stack's **only** machine-readable decision mechanism is the Specification Compiler's
  per-change-package `design.md` `## Contract Metadata` `decisions` block (`DEC-*`), embedded in
  a frozen `implementation-contract.json`. It is change-scoped, not a global policy registry;
  there is no ongoing spec package for this correction, and creating one to hold a governance
  rule would be heavier than the correction and would invent scope.
- `specification/**`, `orchestration/hermes/HERMES-LOCK.json`, `evaluation/commandcode/*` and
  `evaluation/taxonomy/**` are classified **MUST NOT TOUCH / protected** by the frozen P0B-CLOSE
  contract path classes — a rule cannot be added there.
- No global machine-readable policy/rules JSON exists (searched; those found are verification
  result schemas / flow manifests, not governance policy).
- The Hermes Contract Guard is **driven by a frozen contract's path classes**, not by a global
  editable rule table; it is therefore not a policy home either.

Creating a new global policy JSON would be a **new, parallel governance framework** — forbidden
by the task. The sanctioned fallback (document-only canonical record) therefore applies.

---

## 5. Future A2 account model

Compact guidance artifact for the upcoming `P0B-GK-MATCHED-SCALE-A2`:

**`reports/P0B-GK-MATCHED-SCALE-A2-ACCOUNT-MODEL.md`**

Frozen model:

```
GOOGLE KEEP SIDE (reference)  : benchmark-only Google account, inside P0B-BENCH user 10
KEEPLAB SIDE (product)        : does NOT log into that Google account
KEEPLAB SIDE (data mechanism) : P0B-CLOSE-approved benchmark-only deterministic
                                seeder / benchmark-test identity (dataset-scoped,
                                benchmark-prefix, 10 / 100 / 500 / 1000)
SHARED ACCOUNT REQUIRED       : NO
```

The two sides only need matched **dataset scale / data shape / device conditions /
measurement conditions** — never a shared account, backend, provider, database or credential.

**A2 was not started. No notes were generated. No account was logged into.**

---

## 6. Historical artifacts intentionally unchanged

Per the immutability rule, none of the following was rewritten, even where the wording mentions
a Google account (the wording is correct for the Google Keep reference side):

- `reports/P0B-GK-SANDBOX-PROVISION.md` — `sha256 e5296ff1fdff6c7f1b6a4775d2caef1cd7e9df3523ade2466ed02907b5460839`
- `orchestration/hermes/evidence/p0b-gk-sandbox-provision/**` — tree `sha256 d114fb44c156eb13a06619f6cf3051555c9774ca701d914ae14945dea94c9889`
- all `orchestration/hermes/evidence/**` terminal logs, past Evaluation outputs, past
  `finalization.json`, past P0B / P0B-CLOSE evidence
- `KeepLab-Relay/benchmark/results/P0B-CANONICAL/**` (incl. `a11y/a11y.json`)
- the frozen KeepLab parity baseline (`specs/google-keep-parity/*`)

The P0B-GK-SANDBOX-PROVISION requirement for a *benchmark-only Google account* remains
**correct**, because that report is about the Google Keep reference app. It is not a KeepLab
account and is not reinterpreted as one.

---

## 7. Product-safety statement

- This was a **governance correction only**. No login screen, registration screen, backend API,
  server, database auth schema, OAuth dependency, Firebase dependency, token storage, password
  handling or network auth code was added.
- **KeepLab product source was not modified.** `KeepLab-Relay/app/src/main/**` (45 files) tree
  `sha256 c359b86d10fab9ee748712e403250a6fc0c15613e289fe1f72d35b36f921fe5e` — unchanged.
- `KeepLab-Relay` git working tree is untouched by this task (`master` still has no commits;
  no new tracked change made here).
- No `KeepLab-Relay/app/src/main/**` or Hermes-core file was modified. `MISSION.md`,
  `FACTORY_RULES.md`, `.hermes.md` and `specification/**` were **read only**.
- The benchmark-only Google account remains reference-side only and was not reinterpreted.
- P0B keeps using its already-approved benchmark/test data mechanism; no production auth server
  was built to create benchmark data.

---

## 8. Verification

| # | Check | Result |
| --- | --- | --- |
| 1 | Historical P0B sandbox evidence unchanged | **PASS** — sandbox report + evidence hashes recorded above, not modified |
| 2 | P0B-BENCH remains valid | **PASS (from frozen evidence)** — device `87296ada` was **not attached** at verification time (only `c67d32fa` present), so user 10 could not be re-probed live; validity rests on the unchanged `final-state.json` (`BENCH_USER_ID=10`, isolation PASS) |
| 3 | No product source changed | **PASS** — `app/src/main/**` tree hash unchanged |
| 4 | No auth dependency added | **PASS** — no dependency, no OAuth/Firebase, no network auth code |
| 5 | Canonical governance separates reference identity vs product identity | **PASS** — §1 |
| 6 | Upcoming A2 guidance contains corrected account model | **PASS** — §5 + guidance artifact |
| 7 | Google Keep benchmark login checkpoint remains valid | **PASS** — human login still required, reference-side only |

Honest limitation: check 2 is asserted from immutable historical evidence, not a live device
probe, because the reference device was absent during this task.

---

## 9. Final output

```
KEEPLAB-AUTH-BOUNDARY-CORRECTION
================================

GOOGLE KEEP ROLE:
REFERENCE PRODUCT

GOOGLE KEEP BENCHMARK ACCOUNT:
REFERENCE_SIDE_ONLY

KEEPLAB AUTHORITY:
OWN_BACKEND

KEEPLAB GOOGLE ACCOUNT REQUIRED:
NO

GOOGLE OAUTH IN KEEPLAB:
FORBIDDEN_UNLESS_HUMAN_APPROVED

FIREBASE AUTH IN KEEPLAB:
FORBIDDEN_UNLESS_HUMAN_APPROVED

GOOGLE PRIVATE API:
FORBIDDEN

P0B-BENCH SANDBOX STILL VALID:
YES

HISTORICAL P0B EVIDENCE MODIFIED:
NO

KEEPLAB PRODUCT SOURCE MODIFIED:
NO

AUTH IMPLEMENTATION STARTED:
NO

CANONICAL GOVERNANCE RECORD:
/mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack/reports/KEEPLAB-AUTH-BOUNDARY-CORRECTION.md

MACHINE_READABLE_POLICY:
NOT_APPLICABLE

A2 ACCOUNT MODEL
----------------

GOOGLE KEEP:
BENCHMARK GOOGLE ACCOUNT

KEEPLAB:
BENCHMARK/TEST DATA MECHANISM

SHARED ACCOUNT REQUIRED:
NO

STATUS:
READY

NEXT:
HUMAN GOOGLE KEEP BENCHMARK ACCOUNT LOGIN

REPORT:
/mnt/AndroidDev/Projects/Google-Android-Agent-Development-Stack/reports/KEEPLAB-AUTH-BOUNDARY-CORRECTION.md

================================
```

Stopped here. A2 not started, P1 not started, KeepLab authentication not implemented.
