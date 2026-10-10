# Creation Router

Routes a creation need to the most appropriate official path.
Rationale: CLI / Studio Wizard / Architecture Templates solve *different*
problems, so selection is **horizontal by requirement**, not a vertical
three-tier template stack.

## Routing table

| Requirement | First choice |
|---|---|
| Minimal Compose / smoke / PoC | `android create` |
| Official single-module layered app | `architecture-templates/base` |
| Mid/large multi-feature app | `architecture-templates/multimodule` |
| Existing app, new standard Activity/Component | Android Studio Wizard |
| Login / Maps / Wear / TV specialized component | Android Studio Wizard |
| Large production architecture reference | Now in Android |
| Repository / ViewModel / UDF pattern | Architecture Samples |
| Compose UI patterns | Compose Samples |
| Adaptive / list-detail | Adaptive Apps Samples |
| Platform API usage | Platform Samples |

## Android Studio Wizard status

The Android Studio New Project Wizard / component wizards are **not** currently
exposed as a formal Agent CLI API. Treat them as:

- IDE component scaffolding
- Form-factor / specialized generator
- Official source reference

Do **not** treat Studio Wizard as a directly callable Agent API.

## Explicit non-goals

Do **not** build a Template Bridge. Do **not** wrap or reverse-engineer the
Android Studio internal template engine, NPW, or maintain a template fork.
Wait for an official Google interface.
