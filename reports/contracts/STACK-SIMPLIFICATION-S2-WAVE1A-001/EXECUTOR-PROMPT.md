# EXECUTOR-PROMPT — STACK-SIMPLIFICATION-S2-WAVE1A-001

This is the handoff card. The full executor prompt is the sibling file
`STACK-SIMPLIFICATION-S2-WAVE1A-EXECUTE.md`; the acceptance detail is `acceptance.md`.

Package (READ-ONLY INPUT):
`Google-Android-Agent-Development-Stack/reports/contracts/STACK-SIMPLIFICATION-S2-WAVE1A-001/`

Handoff artifacts: `implementation-contract.json`, `READY.json`, `manifest.json`, `EXECUTOR-PROMPT.md`.

---

## Do this

```
PLAN ONCE
  -> FIX CLASSIFICATION RULES
  -> ADD SHADOW OBSERVER
  -> ADD/REUSE DETERMINISTIC SCOPE PROOF TOOL IF NEEDED
  -> UPDATE ONE .hermes.md RULE IF ALLOWED
  -> RUN TARGETED TESTS
  -> REPLAY M4 EVALUATION FIXTURE ONCE
  -> VERIFY SCOPE ONCE
  -> PASS = STOP
```

FAIL: read the failure once, fix the failed part only, re-run the failed step only.
No second audit. No full repository scan. No review of the review.

## Before the first write (mandatory)

1. Verify this package's `manifest.json` sha256 entries.
2. Re-hash the 8 frozen inputs; on drift STOP with `STALE_WAVE1A_INPUT`.
3. Export `HERMES_CONTRACT_PACKAGE=<this package directory>` so the Contract Guard reads THIS
   contract instead of the live `KEEPLAB-P0B-CLOSE-001` package, which blocks `phase_rules.json`
   and `.hermes.md`. Do NOT touch `config.yaml`.

## Allowed write surface

```
Google-Android-Agent-Development-Stack/evaluation/commandcode/phase_rules.json
Google-Android-Agent-Development-Stack/evaluation/commandcode/tests/
Google-Android-Agent-Development-Stack/orchestration/hermes/evaluation_adapter/hermes_session_source.py
Google-Android-Agent-Development-Stack/orchestration/hermes/evaluation_adapter/tests/
Google-Android-Agent-Development-Stack/orchestration/hermes/evaluation_adapter/hooks/hermes-transient-observer.py
Google-Android-Agent-Development-Stack/orchestration/hermes/tools/
Google-Android-Agent-Development-Stack/.hermes.md
Google-Android-Agent-Development-Stack/reports/stack-simplification/
Google-Android-Agent-Development-Stack/orchestration/hermes/evidence/stack-simplification-s2-wave1a/
```

Anything else inside the project is BLOCKED (unclassified fails closed).

## Hard blocks

`evaluation/commandcode/core.py` · `contract_guard.py` · `/home/zhong/.hermes/profiles/android-stack/config.yaml`
· `/home/zhong/.hermes/hermes-agent/**` · `verification/**` · `specification/compiler/**` ·
`reports/contracts/**` (all completed packages) · `orchestration/hermes/evidence/**` (all historical evidence)
· `KeepLab-Relay/**` · `Testapp/**` · `PowerAi/**` · no git initialization · no deletions of scratch or historical artifacts.

## Exit criteria (one pass)

WAIT_DEVICE false positives `105.567 s -> 0` · UNKNOWN `11.6% -> <2%` or all seven spans justified ·
core.py / contract_guard.py / config.yaml / pinned Hermes source / historical M4 evidence byte-identical ·
observer hook tested SHADOW_ONLY and NOT registered · no new custom secret scanner · no new per-phase proof script beyond ONE reusable utility.

`PASS = STOP`.
