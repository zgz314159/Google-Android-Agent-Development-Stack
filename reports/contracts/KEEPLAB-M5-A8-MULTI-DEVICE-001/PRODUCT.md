# PRODUCT — KeepLab M5 = A8 Multi-Device Hardening

## Product

`KeepLab-Relay` is a brownfield Android + Kotlin/Ktor product repository. Its Android app is an
offline-first notes application whose local store is Room (`SYNC-DEC-001`: Room is the local single
source of truth) and whose background engine is one unique WorkManager `note_sync` pipeline
(`SYNC-DEC-010`). Its backend (`KeepLab-Relay/backend/`) is a Ktor + PostgreSQL service created by
A2 and extended by M2 (auth/session), M3 (offline/conflict) and M4 (attachments).

`Google-Android-Agent-Development-Stack` is the Android AI software-factory system around it: a
change request is compiled by the deterministic Specification Compiler into a frozen Implementation
Contract, then implemented, verified, and evaluated. Every write is gated by the fail-closed
Contract Guard (`pre_tool_call`), which permits a write only when the target path is listed in the
`allowed_paths` of the active compiled contract package.

M2 (A3 auth + A4 single-user sync), M3 (A5 offline hardening + A6 conflict) and M4 (A7 attachments)
are **PASS and CLOSED**. The AUTH/SYNC human-decision layer is partly resolved: A0 approved
D-02/D-03/D-07/D-08/D-09/D-15; D-01/D-04/D-10 were resolved by the A3 implementation. Two further
decisions — **D-05** and **D-11** — were approved by the human project owner on **2026-10-07** and
are frozen by this contract.

## Change Request

Authorize, by one compiler-owned contract package, the single milestone **M5 = A8 multi-device
hardening**: two or more independent device/session identities on ONE KeepLab account, bidirectional
propagation and convergence between them, the existing A6 conflict semantics exercised under real
two-client server concurrency, a server session list, per-session revoke, non-destructive remote
session invalidation, account disable, and the D-05 30-day account-deletion grace state machine with
a deterministic purge boundary — all of it with `PUSH_PROVIDER = NONE` (D-11).

This package freezes the two human decisions and authorizes implementation. It does not implement
M5, does not run a bridge round, and does not start A9.

## Scope

- Freeze D-05 `ACCOUNT_DELETE_GRACE_30_DAYS` and D-11
  `NO_PUSH_PROVIDER_IN_A8_CORRECTNESS_PATH` exactly as approved, without reinterpretation.
- Server session/device/account lifecycle: the session representation distinguishes independent
  installations without device fingerprinting; per-session revoke; account disable;
  `ACTIVE → DELETION_PENDING → ACTIVE | PURGED`.
- Android installation/session identity generation and persistence, session-list and revoke UX, and
  non-destructive `AUTH_REQUIRED` behaviour on a revoked or disabled remote session.
- Two independent Android device/app instances on one KeepLab account for the final M5 journey.
- Real server concurrency between two independent authenticated clients, exercising the existing
  A6 conflict rules.
- One M5 verification pass and one M5 report.

## Non-Goals

- Reopening A0/A1/A2/M2/M3/M4 or any frozen decision (D-01, D-04, D-06, D-07, D-08, D-09, D-10,
  D-13, D-15) — including the A5 retry/outbox policy, the A6 conflict policy, the A7 attachment
  architecture/limits/UI/object storage and the Google Keep reference research.
- A9 multi-account or collaboration (D-12 remains `FUTURE` / A9; D-14 remains `NON_BLOCKING`).
- Any FCM/Firebase/vendor push provider, any Google services dependency, any vendor SDK.
- A production cloud scheduler for the D-05 purge boundary, or any cloud provisioning.
- Trash retention (D-06) and sync-tombstone retention/GC; `TOMBSTONE_GC` stays DISABLED.
- Any new networking stack, CRDT library, or new Gradle dependency.
- Broadening the authorized write surface beyond the enumerated paths.

## Contract Metadata

```json
{
  "experiment": {
    "experiment_id": "KEEPLAB-M5-A8-MULTI-DEVICE",
    "experiment_type": "SPEC_FIRST_BROWNFIELD",
    "matched_control_available": false,
    "contract_id": "KEEPLAB-M5-A8-MULTI-DEVICE-001",
    "mode": "brownfield"
  },
  "feature": {
    "feature_id": "KEEPLAB-M5-A8-MULTI-DEVICE",
    "title": "M5 = A8 multi-device hardening",
    "summary": "One milestone that proves and hardens multi-device correctness on a single KeepLab account: independent device/session identities, bidirectional propagation and convergence, the existing A6 conflict semantics under real two-client concurrency, a server session list, per-session revoke with non-destructive remote invalidation, account disable, and the human-approved D-05 30-day deletion grace state machine with a deterministic purge boundary — all with PUSH_PROVIDER = NONE (D-11) and with Room kept as the local source of truth."
  },
  "scope": [
    "Freeze D-05 ACCOUNT_DELETE_GRACE_30_DAYS and D-11 NO_PUSH_PROVIDER_IN_A8_CORRECTNESS_PATH as approved",
    "Server session/device/account lifecycle: installation-distinguishing session representation, per-session revoke, account disable, ACTIVE -> DELETION_PENDING -> ACTIVE | PURGED",
    "Android installation/session identity, session-list and revoke UX, non-destructive AUTH_REQUIRED",
    "Two independent Android device/app instances on one KeepLab account for the final journey",
    "Real server concurrency between two independent authenticated clients exercising the existing A6 conflict rules",
    "One combined M5 verification pass and one M5 report"
  ],
  "non_goals": [
    "Reopening A0/A1/A2/M2/M3/M4 or any frozen decision",
    "A9 multi-account or collaboration",
    "Any FCM/Firebase/vendor push provider or Google services dependency",
    "A production cloud scheduler or any cloud provisioning",
    "Trash retention (D-06) and sync-tombstone retention/GC",
    "Any new Gradle dependency, networking stack or CRDT library",
    "Broadening the authorized write surface"
  ],
  "unresolved_questions": []
}
```
