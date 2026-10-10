# DESIGN — Phase-4 evidence-only termination smoke (UI / visual ground truth)

## Design Source

No visual design source. This change is a single deterministic evidence-only task on a stdlib-only
Python control kernel; it renders no screen, adds no surface and consumes no design deliverable.
`existing_app`, `stitch_used=false`: no Android app is touched at all.

## Action Placement

No interactive affordance is added, moved or removed. The only "action" is one filesystem write of
one marker file inside the single authorized evidence directory.

## State Indicators

The states this change must be able to distinguish are filesystem and termination states, not
visual states:

- `phase4_termination_smoke_dir_present` — the isolated smoke evidence directory exists.
- `phase4_termination_smoke_marker_present` — the single marker file exists inside it.
- PASS -> FINAL RESPONSE -> STOP — the termination state the smoke exists to demonstrate.

The marker file makes the run observable: its presence and content are the deterministic indicator
that the task executed, and the absence of any post-PASS tool call is the indicator that the
hardened termination semantics held.

## Accessibility

Not applicable: no user-visible control, no accessible name, no role, no touch target. No
accessibility surface is created, altered or regressed. The smoke must not change any
accessibility-visible behaviour anywhere in the stack, because it changes no UI at all.

## Reused Visual System

None. No colours, spacing, shapes, typography or components are introduced, referenced or reused,
because no UI is produced. The only shared conventions are the ones already frozen in the stack:
the contract-package gate, the Contract Guard allow-list, and the HERMES_TASK_V1 /
HERMES_RESULT_V1 envelope the bridge already speaks.
