# Reference Map

Router map for the local Google/Android reference repositories.
This is an index, not a full database. Agents should read only the exact
files a task needs — never recursively scan these repositories by default.

Reference root: `Google-Android-Agent-Development-Stack/references/`

## architecture-templates
Repo: https://github.com/android/architecture-templates
- Official Android **architecture starter** for new projects.
- Two flavors: `base` (single-module layered) and `multimodule` (multi-feature).
- Compose, Material 3, Hilt, Room, ViewModel, Navigation, Coroutines/Flow,
  version catalog, unit/UI test scaffolding.
- Use: new official single-module app (`base`) or clearly mid/large modular app (`multimodule`).
- Local layout: both flavors are materialized as git worktrees —
  `architecture-templates/base/` and `architecture-templates/multimodule/`.

## nowinandroid
Repo: https://github.com/android/nowinandroid
- Large, **production-grade** Android architecture reference.
- Reference for modularization, data/domain/ui layering, offline-first, DI, testing at scale.
- Use: architecture reading for large apps. Do **not** bulk scan; read targeted modules only.

## architecture-samples
Repo: https://github.com/android/architecture-samples
- Canonical **Repository / ViewModel / UDF** and testing pattern reference.
- Use: unidirectional data flow, repository pattern, ViewModel testing patterns.

## compose-samples
Repo: https://github.com/android/compose-samples
- Official **Compose UI / state / animation** pattern reference.
- Use: Compose UI, state hoisting, animation, theming patterns.

## adaptive-apps-samples
Repo: https://github.com/android/adaptive-apps-samples
- Official **adaptive UI** reference: tablet / foldable / list-detail / responsive layouts.
- Use: adaptive layouts, NavigationSuiteScaffold, window size classes.

## platform-samples
Repo: https://github.com/android/platform-samples
- Official **platform API** reference (per-API demo snippets).
- Use: platform API usage examples. **Not** a production architecture template.

## Notes
- Android SDK, Android CLI, and installed Agent skills remain in their official
  locations and are intentionally NOT copied here.
- `studio-template-notes/` (planned) is reserved for Studio Wizard template notes only,
  not the Android Studio source tree.
