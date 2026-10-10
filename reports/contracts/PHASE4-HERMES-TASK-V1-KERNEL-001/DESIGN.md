# DESIGN — Phase-4 Hermes Task V1 control kernel install (UI / visual ground truth)

## Design Source

No visual design source. This change is a filesystem install of an existing Python package; it
renders no screen, adds no surface and consumes no design deliverable. `existing_app`,
`stitch_used=false`: no Android app is touched at all.

## Action Placement

No interactive affordance is added, moved or removed. The only "actions" are filesystem writes
performed by the install session inside `orchestration/hermes/bridge/` and, for the parity record,
inside the Phase-4 evidence directory.

## State Indicators

The two states this change must be able to distinguish are filesystem states, not visual states:

- `phase4_staged_kernel_source` — the staged kernel is present under the evidence directory.
- `phase4_bridge_kernel_installed` — the kernel is present under `orchestration/hermes/bridge/`.

The install-parity record makes the transition between them observable: each module carries a
sha256 in both trees, and equality is the indicator.

## Accessibility

Not applicable: no user-visible control, no accessible name, no role, no touch target. No
accessibility surface is created, altered or regressed. The install must not change any
accessibility-visible behaviour anywhere in the stack.

## Reused Visual System

None. No colours, spacing, shapes, typography or components are introduced, referenced or reused,
because no UI is produced. The kernel modules are stdlib-only Python; their only shared conventions
are the ones already frozen in the staged tree.
