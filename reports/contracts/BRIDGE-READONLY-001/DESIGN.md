# DESIGN — Bridge read-only acceptance task

## Design Source

No visual design source. This task performs a filesystem read-only check and writes one
evidence file in a disposable worktree.

## Action Placement

No interactive affordance is added, moved or removed.

## State Indicators

`bridge_readonly_evidence` denotes that `EVIDENCE.txt` exists with the actual read-only values.

## Accessibility

Not applicable: no user-visible control.

## Reused Visual System

None; no UI is rendered.
