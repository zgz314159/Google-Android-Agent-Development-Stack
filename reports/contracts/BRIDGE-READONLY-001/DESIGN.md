# DESIGN — Bridge read-only acceptance task

## Design Source

No visual design source. This task performs a filesystem read-only check and writes one
evidence file in a disposable worktree.

## Action Placement

No interactive affordance is added, moved or removed.

## State Indicators

No UI selector is required; `EVIDENCE.txt` in the task worktree (contract path
`project/EVIDENCE.txt`) is the evidence artifact. It must contain exactly four labeled
lines; acceptance compares them with the trusted `PREP-BINDING.json` and records the
evidence SHA-256.

## Accessibility

Not applicable: no user-visible control.

## Reused Visual System

None; no UI is rendered.
