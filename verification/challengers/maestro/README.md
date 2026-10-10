# Maestro challenger

**Production default: the deterministic UiAutomator executor.**
**Challenger / reference only: Maestro.**

Maestro lives here so it can never leak into the production lifecycle. The production runner
`runner/run_verification.sh` only invokes this directory when a plan explicitly declares
`"engine": "maestro"`; a Maestro run is a separate plan and never shares a run with a
UiAutomator journey.

Notes:

- Maestro has no per-command monotonic timestamps, so a Maestro run's `t7b_ms` is `null`
  (never estimated); `t7c_ms` comes from the shared host-timed oracle.
- The DB/domain oracle is reached through a separate project-supplied instrumentation class
  declared as `oracle.class` in the plan.
- The input-capability smoke flow is project-specific and is pointed at with
  `input_smoke.flow`.
