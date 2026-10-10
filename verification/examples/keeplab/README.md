# KeepLab reference example

Minimal reference for onboarding a project to the Verification Layer. KeepLab is a
**fixture / compatibility proof** here — the layer itself carries no KeepLab knowledge.

| File | Purpose |
|---|---|
| `verification-plan.json` | Production path: `engine: uiautomator`, journey J1, diagnostic + excluded from baseline. |
| `verification-plan.maestro.json` | Challenger path: `engine: maestro` + a separate oracle class. |
| `journey/J1JourneyTest.kt` | Journey migrated to `JourneyBase` / `UiDriver` / `TimingLogger`. |
| `fixture/FixtureSeeder.kt` | Deterministic Room fixture (no UI taps). |
| `oracle/Verifier.kt`, `oracle/DbProbe.kt` | Terminal DB oracle + separate probe for Maestro. |
| `selectors/selectors.json` | Identity inventory per the selector contract. |
| `maestro/*.yaml` | Challenger flow + input smoke. |
| `expected/pass-result.json` | Shape of a compact PASS result. |
| `expected/failure-bundle/LAYOUT.md` | Shape of a FAIL evidence bundle. |

The reference plan points at the already-built KeepLab instrumentation classes (which satisfy
the host artifact contract) and the frozen benchmark APK. The `journey/`, `fixture/` and
`oracle/` sources show the migrated form using `android/uiautomator` support sources.

Run it (one diagnostic smoke, never the benchmark):

```bash
verification/runner/run_verification.sh verification/examples/keeplab/verification-plan.json
```
