# DESIGN — KeepLab M5 = A8 Multi-Device Hardening (UI / visual ground truth)

## Design Source

Existing application (`existing_app`). M5 adds no visual design deliverable and consumes no new
design source: it extends the existing Material 3 / Compose surfaces of the account area
(`ui/settings/`), the credential surface (`ui/auth/`), the navigation graph (`ui/navigation/`) and
the existing A6 conflict surface (`ui/conflict/`). `stitch_used=false`. The visual language is
whatever the app already uses; no new design system is introduced.

## Action Placement

- `ui/settings/` — the account area already shows the active account, the sync-status indicators and
  the conflict entry point. M5 adds, in that same area: the session list, the current-installation
  marker, a per-session revoke affordance for another session, and the account lifecycle
  affordances (request deletion, show DELETION_PENDING with its grace window, cancel inside the
  window). The existing "Retry sync" and "Sign out" affordances keep their place and meaning.
- `ui/auth/` — re-authentication is the in-grace cancellation path; the existing credential surface
  is reused, not duplicated.
- `ui/navigation/` — routes for the session list and the account lifecycle states.
- `ui/conflict/` — the A6 surface is consumed unchanged; its entry point in the account area is
  preserved.
- No destructive affordance is added. "Sign out" stays non-destructive; deletion is a separate,
  deliberate, confirmable action.

## State Indicators

- Session list: each session shows its installation identity; exactly one row is marked as the
  current installation (`m5_session_row_current`).
- Session-invalid state: a revoked or disabled remote session shows a non-destructive
  `AUTH_REQUIRED` indicator (`m5_auth_required_banner`) that explicitly does not imply data loss,
  and local notes remain visible in the note list (`m5_note_list`).
- Account lifecycle: `ACTIVE` (normal), `DELETION_PENDING` (grace window shown, cancellation
  available) and `PURGED` (account data gone) are distinguishable; the pending state must not read
  as "deleted".
- Sync: the existing sync-status/manual-sync affordance (`m5_sync_status`) reflects
  success/failure/`AUTH_REQUIRED` without promising a push-driven refresh.
- Conflicts: a persisted conflict is surfaced through the existing `m5_conflict_banner` path.

## Accessibility

Every new affordance is reachable and operable without sight of colour or position: a title/role and
an accessible name for the session-list rows, the revoke action, the deletion request and the
in-grace cancellation; the current-installation marker must not be conveyed by colour alone; status
text must be readable by a screen reader and must not be the only indication of the
`AUTH_REQUIRED` or `DELETION_PENDING` state; touch targets follow the app's existing Material
sizing. No existing accessibility behaviour may be regressed.

## Reused Visual System

The existing Material 3 theme, typography, spacing, shapes and components under `ui/theme/` and
`ui/common/` are reused as-is. M5 introduces no colour, typography, spacing or component of its own
and changes no theme token; it only composes existing components into the account area. The new
selectors of the selector contract identify states and affordances within that reused system.
