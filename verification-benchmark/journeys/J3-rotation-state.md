# J3 — Rotation / State Restoration

Business goal (identical for engines A/B/C):

1. Launch KeepLab.
2. Enter a deterministic search/state.
3. Establish selected / navigation / search state.
4. Rotate portrait → landscape.
5. Wait for stable.
6. Verify state restoration.
7. Rotate landscape → portrait.
8. Verify again.
9. Toggle Dark Mode using the existing KeepLab (system) behaviour.
10. Verify content/state remains correct.

## Ground truth (terminal oracle)

| Assertion | Source |
|---|---|
| Active search query survives rotation (Home `rememberSaveable` + ViewModel) | UI |
| The list of matching notes is identical before/after rotation | UI + Database |
| Dark mode renders (system `ui_night_mode`) with content intact | UI + visual (theme checkpoint only) |
| No crash / fatal exception across configuration changes | Process |

## Real-UI mapping (KeepLab)

- Deterministic search state: Home `Search` → query `VC-J3-Keep` (matches the seeded note).
- Rotation: driven at the system level — `adb shell settings put system user_rotation <0|1>`
  with `accelerometer_rotation=0` (UiAutomator `setRotation` where available). Compose internal
  state is asserted via Compose semantics; window/visibility via UiAutomator.
- Dark mode: `adb shell cmd uimode night yes` / `no` (system config change). KeepLab follows
  `isSystemInDarkTheme()`.

## Fixture (`seedJ3`)

Clean database + one deterministic note titled `VC-J3-Keep` with body `VC-J3-Keep-Body`, so a
search returns exactly one stable result across rotations.

## Requirements preserved

This does not lower the Phase-B rotation/state-restoration bar: screen, search query and results
are asserted after each configuration change, on a physical device.
