# KEEPLAB-AUTH-SYNC-HUMAN-DECISIONS

**Explicit open decisions required before KeepLab account / sync implementation**

- Task: `KEEPLAB-AUTH-SYNC-ARCHITECTURE-SPEC`
- Date: 2026-10-05 (CST) · Status: **CANONICAL_ARCHITECTURE_DRAFT · NON_IMPLEMENTATION_AUTHORIZING**
- Not decided by the architecture task itself: each row started as `HUMAN_DECISION_PENDING` and
  **must not** be silently frozen. A decision is asked once; once answered it belongs in the
  canonical governance record and (if applicable) `.factory/decisions.md` per the project's own
  convention. **As of A0 (2026-10-06) six rows are answered — see §0.**

---

## 0. A0 — human decisions recorded (2026-10-06)

```
D-02: DECIDED  YES_LOCAL_ONLY_BEFORE_SIGNIN
D-03: DECIDED  SINGLE_ACTIVE_ACCOUNT_PHASE1
D-07: DECIDED  KOTLIN_KTOR
D-08: DECIDED  TENCENT_CLOUD + PORTABLE_DOCKER
D-09: DECIDED  POSTGRESQL
D-15: DECIDED  YES_BOUNDED_ACCOUNT_NETWORK_UNLOCK
```

Remaining pending: D-01 · D-04 · D-05 · D-06 · D-10 · D-11 · D-12 · D-13 · D-14 → **9**.

- Source: `HUMAN_PROJECT_OWNER_APPROVAL`, 2026-10-06 conversation/task input.
- Record: `reports/KEEPLAB-A0-HUMAN-ARCHITECTURE-DECISIONS.md`;
  bounded policy + amendment proposal: `reports/KEEPLAB-A0-BOUNDED-ACCOUNT-NETWORK-GOVERNANCE.md`.
- The canonical governance *amendment* (`MISSION.md` / `FACTORY_RULES.md` / `ROADMAP.md`
  `RISK-GOV-001`) is **BLOCKED_BY_CONTRACT_GUARD** and was not applied.

---

## 1. The decision table

| # | Decision | Why it must be human | Options / candidates | Blocks | Spec ref |
| --- | --- | --- | --- | --- | --- |
| D-01 | **Final auth method** | product/security posture | A email+password (+optional passkey) · B passkey-first (+email/recovery bootstrap) · C phone+code | A3 | AUTH-DEC-004 |
| D-02 | **Notes before first sign-in?** | product UX + `LOCAL_ONLY` existence | **DECIDED 2026-10-06 · `YES_LOCAL_ONLY_BEFORE_SIGNIN`** (was: yes (local-first, later linked) · no (account required first)) | A1/A3 | AUTH-DEC-010 |
| D-03 | **Phase-1 single-account vs multi-account** | product scope | **DECIDED 2026-10-06 · `SINGLE_ACTIVE_ACCOUNT_PHASE1`** (multi-account stays `FUTURE_EXTENSION`; no multi-account UI now) | A1/A9 | AUTH-DEC-009 |
| D-04 | **Sign-out local-data policy** | data-safety posture | A keep app-private local cache (non-destructive) · B remove after confirmation · C export then remove | A3 | AUTH-DEC-011 |
| D-05 | **Server-account deletion retention / grace period** | legal/product | **DECIDED 2026-10-07 · `ACCOUNT_DELETE_GRACE_30_DAYS`** (was: none · grace period · retention window) | A3/A8 | AUTH-DEC-012 |
| D-06 | **Trash retention duration** | product | 7 days (reference candidate) · other | A4/A6 | SYNC-DEC-015 |
| D-07 | **Backend technology stack (language)** | infrastructure | **DECIDED 2026-10-06 · `KOTLIN_KTOR`** (Kotlin + Ktor) | A2 | BACKEND-DEC-003 |
| D-08 | **Cloud provider** | infrastructure | **DECIDED 2026-10-06 · `TENCENT_CLOUD + PORTABLE_DOCKER`** (initial target; container-portable packaging; no vendor-exclusive application APIs; no GCP/AWS/Firebase assumption) | A2 | BACKEND-DEC-002 |
| D-09 | **Database vendor** | infrastructure | **DECIDED 2026-10-06 · `POSTGRESQL`** (technology only — hosting/topology/version/HA/backup remain A2 design) | A2 | BACKEND-DEC-004 |
| D-10 | **Token format** | security/implementation | JWT · opaque · PASETO | A3 | AUTH-DEC-005 |
| D-11 | **Push notification provider** | infrastructure (optional) | **DECIDED 2026-10-07 · `NO_PUSH_PROVIDER_IN_A8_CORRECTNESS_PATH`** (was: none now · later provider) | A8 | BACKEND-DEC-005 |
| D-12 | **Collaboration scope** | product | out of scope · future | A9 | spec §6.3 |
| D-13 | **Attachment limits** (size, count, types, quotas) | product/cost | not chosen | A7 | SYNC-DEC-016 |
| D-14 | **Formal spec package location** | governance | open a canonical spec path later · keep under `reports/**` | A0+ | GOV-DEC-003 |
| D-15 | **Account/network governance unlock** | governance | **DECIDED 2026-10-06 · `YES_BOUNDED_ACCOUNT_NETWORK_UNLOCK`** (bounded, phase-gated; canonical `MISSION.md`/`FACTORY_RULES.md`/`ROADMAP.md` amendment **BLOCKED_BY_CONTRACT_GUARD**) | everything | GOV-DEC-001/005 |

> **Not a human decision (added by the corrective review):**
> `SYNC_TOMBSTONE_RETENTION_OR_COMPACTION` is a **protocol-correctness** concern, not a product
> setting. It is NOT the same as Trash duration (D-06), and it is NOT automatically 7 days. It is
> recorded as an architecture/implementation concern (`IMPLEMENTATION_DECISION_PENDING`) governed by
> the anti-resurrection invariant, and it does **not** add a row to the human-decision table above.

---

## 2. What is **already decided** (human governance, do not re-ask)

| Fixed key | Value |
| --- | --- |
| `GOOGLE_KEEP_ROLE` | `REFERENCE_PRODUCT_ONLY` |
| `GOOGLE_KEEP_ACCOUNT_SCOPE` | `REFERENCE_APP_ONLY` |
| `BENCHMARK_GOOGLE_ACCOUNT` | `REFERENCE_SIDE_ONLY` |
| `KEEPLAB_AUTHORITY` | `OWN_BACKEND` |
| `KEEPLAB_GOOGLE_ACCOUNT_REQUIRED` | `NO` |
| `GOOGLE_AUTH_IN_KEEPLAB` | `FORBIDDEN_UNLESS_HUMAN_APPROVED` |
| `FIREBASE_AUTH_IN_KEEPLAB` | `FORBIDDEN_UNLESS_HUMAN_APPROVED` |
| `GOOGLE_PRIVATE_API` | `FORBIDDEN` |
| `GOOGLE_PRIVATE_BACKEND_PROTOCOL` | `FORBIDDEN` |

Source: `reports/KEEPLAB-AUTH-BOUNDARY-CORRECTION.md` (canonical governance record).

---

## 3. Recommended safe defaults (advisory — **not** decisions)

Where a safe, reversible default exists, it is stated as advice so a human can accept it quickly:

| Decision | Recommended default | Why safe |
| --- | --- | --- |
| D-02 | notes may exist before sign-in (`LOCAL_ONLY`) | doesn't force an account wall; preserves current local-first behaviour |
| D-03 | Phase-1 single active account | simplest; `account_id` still present for future multi-account |
| D-04 | keep app-private local cache (non-destructive); `APPLICATION_LEVEL_DATABASE_ENCRYPTION` = `SECURITY_IMPLEMENTATION_DECISION` (`HUMAN_DECISION_PENDING` if the project requires it) | non-destructive; matches MISSION.md's irreversible-list rule; does not falsely claim an encrypted database was chosen |
| D-06 | 7 days `REFERENCE_DEFAULT_CANDIDATE` | publicly precedented; reversible product choice |
| D-10 | opaque tokens treated as opaque by the client | avoids locking a format before a threat model exists |

---

## 4. Immediate blocking decisions (must be answered before A1/A2/A3 begin)

```
RESOLVED BY A0 (2026-10-06):
  D-15  account/network governance unlock        (DECIDED — bounded; canonical write BLOCKED)
  D-07  backend language                         (DECIDED — KOTLIN_KTOR)
  D-08  cloud provider                           (DECIDED — TENCENT_CLOUD + PORTABLE_DOCKER)
  D-09  database vendor                          (DECIDED — POSTGRESQL)

STILL BLOCKING:
  D-01  final auth method                        (blocks A3)
  D-04  sign-out local-data policy               (blocks A3)
  D-10  token format                             (blocks A3)
```

D-15 is now answered, so nothing is stopped by an unanswered governance question. A1/A2 no longer
wait on human decisions (D-02/D-03 and D-07/D-08/D-09 are resolved), but their **execution** still
waits on the canonical A0 governance write
(`BLOCKED_BY_CONTRACT_GUARD` → `OPEN_GOVERNANCE_WRITE_CONTRACT`).

---

## 5. Status

```
HUMAN_DECISIONS_PENDING: 9
HUMAN_DECISIONS_APPROVED_BY_A0: 6
IMPLEMENTATION_AUTHORIZATION_MODEL: PHASE_GATED
CURRENT_IMPLEMENTATION_AUTHORIZATION: NOT_GRANTED
AUTH_NETWORK_GOVERNANCE_GATE: HUMAN_APPROVED_BOUNDED · CANONICAL_AMENDMENT_BLOCKED_BY_CONTRACT_GUARD
```

```
CORRECTIVE REVIEW (KEEPLAB-AUTH-SYNC-ARCHITECTURE-SPEC-REVIEW-FIX, 2026-10-05):
  D-01..D-15 answers changed: 0
  D-15 unlocked:              NO
  new HUMAN_DECISION_PENDING added: 0
  implementation-level (non-human) choices are labelled IMPLEMENTATION_DECISION_PENDING instead —
  e.g. SYNC_TOMBSTONE_RETENTION_OR_COMPACTION, the WorkManager ExistingWorkPolicy
  (A4_IMPLEMENTATION_DECISION), and APPLICATION_LEVEL_DATABASE_ENCRYPTION.

A0 (KEEPLAB-HUMAN-ARCHITECTURE-DECISIONS-A0, 2026-10-06):
  D-02/D-03/D-07/D-08/D-09/D-15 decided:            6 (human project owner approval)
  remaining HUMAN_DECISION_PENDING:                 9
  D-01/D-04/D-10 remain unresolved:                 YES (A3 stays blocked)
  canonical governance amendment (MISSION.md /
    FACTORY_RULES.md / ROADMAP.md RISK-GOV-001):    BLOCKED_BY_CONTRACT_GUARD (not applied)
  implementation authorized:                        NO (PHASE_GATED)
```
