# KEEP-DEVICE-VERIFICATION-BACKLOG

**Targeted Keep-specific device backlog — the minimal set that public evidence cannot resolve**

- Task: `KEEP-GLOBAL-RESEARCH-AUTH-SYNC-OFFLINE`
- Date: **2026-10-05 (CST)**
- Rule: a journey enters this backlog **only** if no Tier-1/Tier-2 public source answers the
  question. Everything that public sources answered is explicitly listed as `NO_DEVICE_NEEDED`
  (§3) so the device budget stays visible.
- **First-pass MUST journeys: 4.** Optional: 2. Hard cap 8. Nothing here was executed.
- Device policy: device is an exclusive capacity-1 resource; every future run must acquire
  `verification/core/device_lock.sh` (`flock device:<serial>`) first. Deterministic state inspection
  by default; **no** `screenshot → LLM → tap` loop.

---

## 1. Classification of all open questions

### 1.1 NO_DEVICE_NEEDED (resolved by public evidence — must NOT enter the backlog)

| # | Question | Resolved by |
|---|----------|-------------|
| N-1 | Credential Manager architecture and whether it works with an app-owned backend | S-01, S-04, S-05, S-33, S-36, S-37 → §3 of AUTH blueprint |
| N-2 | Whether Google Keep is account-bound / multi-account | S-16, S-22 |
| N-3 | Whether Keep's sync appears as an Android account sync item | S-16 |
| N-4 | Conflicting-edits semantics (Keep selected / Keep both) | S-17 |
| N-5 | Reload means a save-then-re-download of notes | S-18 |
| N-6 | Delete propagation to collaborators; 7-day Trash; archive semantics | S-19, S-21 |
| N-7 | Collaborators can label/colour/archive/remind without affecting others | S-19 |
| N-8 | Note version history exists (downloadable from web) | S-23 |
| N-9 | Widget account selection with multiple accounts | S-22 |
| N-10 | Android official offline-first architecture, LWW, WorkManager semantics | S-07..S-12 |
| N-11 | Refresh-token rotation / PKCE / password hashing requirements | S-29, S-30, S-31 |

### 1.2 OPTIONAL_DEVICE_CONFIRMATION (cheap to confirm, not required)

| # | Question | Why optional |
|---|----------|--------------|
| O-1 | Exact current Google Keep account-switcher presentation (sheet vs full-screen; wording) | S-22 already establishes *that* multiple accounts are supported; only the current presentation is undocumented. Only worth confirming if KeepLab parity requires the exact switcher layout. |
| O-2 | First-run gate when **no** Google account is on the device (what exactly is shown) | The account requirement is inferable; only the screen design is unknown. Optional because KeepLab's own account model differs. |

### 1.3 MUST_DEVICE_VALIDATE (public evidence genuinely insufficient)

| # | Question | Why web is insufficient |
|---|----------|-------------------------|
| M-1 | What **"Keep both"** actually produces (a duplicate note? both merged into one? what title/time?) and what the conflict chooser looks like structurally | S-17 documents the *options* but not the outcome. Community reports describe both benign and data-loss outcomes (S-52..S-57) and are contradictory. |
| M-2 | Whether Google Keep shows **any** offline/sync indicator, and its exact wording/behaviour (banner? "syncing" animation? nothing?) | Not documented anywhere in Tier 1. Community reports explicitly disagree (some say "no indicator", some report a transient "syncing…"). |
| M-3 | Android→other-device propagation: is it immediate, delayed, or flush-on-note-open? (community reports 30 s – 30 min and "must reopen the note to flush") | Contradicts the marketing claim "syncs in real-time" (S-27 vs S-54/S-55). Only device observation resolves which is true for the current build. |
| M-4 | Whether **unsynced local edits survive a reload/re-download** and a reinstall (the reload path re-downloads notes — S-18) | S-18 documents the reload but not its data-safety behaviour; S-57 suggests reinstall can break sync. This is a data-loss-risk question that must be answered before KeepLab copies any reload UX. |

### 1.4 MUST_DEVICE_BENCHMARK (separate concern — NOT in this backlog)

Cold start, warm start, restart, frame/jank, memory, rotation/state restoration, and the
10/100/500/1000-note dataset performance and same-device parity ratios all require a **matched-scale
same-device** Google Keep ↔ KeepLab comparison. That is P0B territory and is explicitly **not**
part of this research phase.

---

## 2. First-pass device journeys (4 MUST + 2 OPTIONAL)

Common preconditions for every journey (not repeated below):
- hold the host device lock (`verification/core/device_lock.sh`, `flock device:87296ada`, capacity 1);
- operate only inside the isolated benchmark Android user; **no account is added, switched or
  removed**; no APK is installed/uninstalled; no user data is created outside a benchmark-prefixed,
  reversible dataset;
- every observation is captured as **deterministic evidence** (UI hierarchy dump, `dumpsys`,
  `logcat` scoped to the package, file timestamps) — **not** visual judgement.

---

### J1 (M-1) — Conflicting edits: chooser structure and the outcome of "Keep both"

- **QUESTION:** When two devices edit one note with one offline, what exactly does the conflict
  surface show, and what does "Keep both" produce (duplicate note? merged note? what title/time)?
- **WHY WEB IS INSUFFICIENT:** S-17 documents only the two option labels. The post-choice state is
  undocumented and community accounts contradict each other.
- **PRECONDITION:** two clients available (the device + the Keep web client) on the same benchmark
  account; one note with known content; network toggling available on the device.
- **MINIMAL STEPS:** create note N on device → toggle device offline → edit N on device → edit N
  differently on web → restore device network → wait for the conflict surface → dump the hierarchy
  → choose **Keep both** → dump the resulting note list and both notes' metadata.
- **EXPECTED EVIDENCE:** hierarchy dump of the conflict surface (node names/labels, no image
  judgement); the resulting note count and the title/body/timestamps of each resulting note.
- **CLEANUP:** delete every created note (owner delete inside the benchmark dataset); verify the
  benchmark account returns to its pre-run note count.
- **VISUAL LLM NEEDED:** **No** — deterministic hierarchy + metadata inspection suffices.
- **Priority:** MUST (first-pass candidate).

### J2 (M-2) — Offline / sync indicator presence and wording

- **QUESTION:** Does Keep surface an offline state or a "syncing" state at all, and with what exact
  wording and trigger?
- **WHY WEB IS INSUFFICIENT:** no Tier-1 source documents it; community reports disagree.
- **PRECONDITION:** note list populated; ability to toggle connectivity.
- **MINIMAL STEPS:** with the app in the foreground, disable connectivity → dump hierarchy (look for
  any offline/banner/snackbar node) → perform a local edit → re-enable connectivity → sample the
  hierarchy repeatedly for a bounded window (e.g. 60 s) recording any transient sync node.
- **EXPECTED EVIDENCE:** presence/absence of indicator nodes with their exact text and the sampling
  timeline.
- **CLEANUP:** delete the created/edited note; confirm pre-existing content untouched.
- **VISUAL LLM NEEDED:** **No** — hierarchy text nodes are the evidence.
- **Priority:** MUST.

### J3 (M-3) — Cross-device propagation timing / flush-on-open

- **QUESTION:** After a device edit, how long until another client sees it, and does re-opening the
  note on the device flush the change?
- **WHY WEB IS INSUFFICIENT:** contradicts the official "real-time" claim (S-27 vs S-54/S-55).
- **PRECONDITION:** device + web client on one benchmark account; a note that already exists on both.
- **MINIMAL STEPS:** open the note on both clients and let them settle → edit on device, then
  immediately background the device app → poll the web client for the change with a timestamped
  bound (e.g. up to 5 min) → if not seen, re-open the note on the device → poll again.
- **EXPECTED EVIDENCE:** timestamped sequence of "change visible on other client: yes/no" and whether
  note-open was required.
- **CLEANUP:** delete the edited note from inside the benchmark dataset.
- **VISUAL LLM NEEDED:** **No** — presence of specific text in the other client's DOM/hierarchy.
- **Priority:** MUST.

### J4 (M-4) — Data safety across reload and reinstall

- **QUESTION:** Do **unsynced local edits** survive (a) the reload/re-download path and (b) a
  reinstall?
- **WHY WEB IS INSUFFICIENT:** S-18 documents the reload but not its data-loss behaviour; S-57
  suggests reinstall breaks sync.
- **PRECONDITION:** a benchmark note created **while offline** and not yet synced; the benchmark
  account's pre-run state recorded.
- **MINIMAL STEPS:** go offline → edit a benchmark note → (a) trigger/accept the reload prompt
  (or force-stop + relaunch to obtain the same code path) and inspect whether the offline edit is
  still present; (b) separately, clear app data / reinstall and observe whether the note list
  re-downloads and whether the offline edit is lost.
- **EXPECTED EVIDENCE:** before/after note content for each sub-case + the prompt text observed.
- **CLEANUP:** delete all benchmark notes; confirm the account's pre-run note count is restored.
  **Note:** sub-case (b) may require clearing app data — permitted only inside the isolated
  benchmark user, and only after confirming the dataset is disposable.
- **VISUAL LLM NEEDED:** **No** — note content presence/absence in the hierarchy.
- **Priority:** MUST. *(This is the highest-value journey: it is the only one that tests whether a
  re-download path can destroy local work — the exact failure mode KeepLab must not reproduce.)*

### J5 (O-1) — Account switcher presentation

- **QUESTION:** In the current build, what does the account switcher look like (side sheet vs
  full-screen) and what wording does it use?
- **WHY WEB IS INSUFFICIENT:** only the *existence* of multi-account is documented (S-22, S-60).
- **PRECONDITION:** ≥2 accounts already signed in on the device (**no** account added/switched by us).
- **MINIMAL STEPS:** open Keep → tap the account avatar → dump the hierarchy.
- **EXPECTED EVIDENCE:** node structure and labels of the switcher.
- **CLEANUP:** none (read-only navigation).
- **VISUAL LLM NEEDED:** **No**.
- **Priority:** OPTIONAL (only if exact switcher parity is required).

### J6 (O-2) — No-account first-run gate

- **QUESTION:** What does Keep show on first run when **no** Google account exists on the device?
- **WHY WEB IS INSUFFICIENT:** the account requirement is inferable but the gate is undocumented.
- **PRECONDITION:** the isolated benchmark user has **no** Google account. *(No account may be added
  or removed for this journey — it is observed only in the account-less state.)*
- **MINIMAL STEPS:** launch Keep in the account-less user → dump hierarchy → attempt nothing further.
- **EXPECTED EVIDENCE:** the gate screen's node structure/labels.
- **CLEANUP:** none (read-only).
- **VISUAL LLM NEEDED:** **No**.
- **Priority:** OPTIONAL.

---

## 3. Device budget verdict

| Metric | Value |
|--------|-------|
| MUST first-pass journeys | **4** (J1–J4) |
| OPTIONAL journeys | **2** (J5, J6) |
| Total backlog | **6** (cap 8) |
| Visual-LLM-required journeys | **0** |
| Journeys eliminated by web research | **11** (N-1 … N-11) |
| Performance questions in this backlog | **0** (separated, see §1.4) |

**Device work reduced: YES.** Eleven of the questions a device-first approach would have probed are
answered by public documentation, and every remaining journey is a deterministic-inspection journey
with no visual LLM in the loop.

---

## 4. Not started

```
DEVICE JOURNEYS EXECUTED: 0
DEVICE MUTATED: NO
ACCOUNT ADDED/SWITCHED/REMOVED: NO
APK INSTALLED/UNINSTALLED: NO
HISTORICAL DEVICE RECORDS CHANGED: NO
P0B-GK-DEVICE-REBASE STARTED: NO
P0B-GK-MATCHED-SCALE-A2 STARTED: NO
```
