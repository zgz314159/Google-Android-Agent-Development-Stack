# DESIGN — Phase-45 thin bounded Campaign Supervisor contract (UI / visual ground truth)

## Design Source

No visual design source. This change is a stdlib-only Python scheduling layer around an existing
stdlib-only control kernel; it renders no screen, adds no surface and consumes no design
deliverable. `existing_app`, `stitch_used=false`: no Android app is touched at all.

## Action Placement

No interactive affordance is added, moved or removed. The only "actions" are CLI subcommands
(`status`, `run`) and the campaign lifecycle they drive. There is no on-device control, so action
placement on a screen is not applicable.

## State Indicators

The states this change must be able to distinguish are scheduling and filesystem states, not
visual states:

- `campaign_supervisor_package_present` — the Supervisor package exists under
  `orchestration/hermes/supervisor/`.
- `campaign_state_file_present` — a per-campaign `state.json` exists under the private state root.
- `campaign_lock_present` — a per-campaign `campaign.lock` exists under the private state root.
- `campaign_evidence_dir_present` — the campaign evidence directory exists under
  `orchestration/hermes/evidence/campaign-supervisor/`.
- Campaign status: `RUNNING` -> `WAITING_FOR_GPT` -> (`CLOSED` | `PAUSED`), and the compact
  progress lines `CAMPAIGN_WAITING_FOR_GPT`, `CAMPAIGN_DISPATCH`, `CAMPAIGN_ROUND_COMPLETE`,
  `CAMPAIGN_CLOSED`.

These observable markers are the deterministic indicators that a campaign ran, dispatched and
terminated within its bounds.

## Accessibility

Not applicable: no user-visible control, no accessible name, no role, no touch target. No
accessibility surface is created, altered or regressed. The change must not alter any
accessibility-visible behaviour anywhere in the stack, because it changes no UI at all.

## Reused Visual System

None. No colours, spacing, shapes, typography or components are introduced, referenced or reused,
because no UI is produced. The only shared conventions are the ones already frozen in the stack:
the compiler-owned contract-package gate, the Contract Guard allow-list, the `HERMES_TASK_V1` /
`HERMES_RESULT_V1` bridge envelope the Supervisor reuses read-only, and the deterministic ChatGPT
adapter READ seam it wraps for the latest completed assistant response.
