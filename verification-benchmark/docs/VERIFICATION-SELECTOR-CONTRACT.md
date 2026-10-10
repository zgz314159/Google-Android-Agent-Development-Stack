# Verification Selector Contract

Status: v1.0 (hardening). Applies to any Android feature/UI work that is expected to be
verified by the deterministic harness (Engine B = UiAutomator 2.4.0, Engine C = Maestro).

The benchmark earned its stability from a small number of **stable automation identities**
(`testTag` / `contentDescription`), not from coordinates or fragile text. This contract makes
that a required part of feature delivery instead of an after-the-fact debugging exercise.

## 1. Selector priority (highest first)

1. **Stable `testTag` / resource id** — Compose `Modifier.testTag("editor-title")` with
   `testTagsAsResourceId = true` on the root, surfaced as a resource id / accessibility id.
   This is the preferred identity for every interaction node.
2. **`contentDescription`** — for icon-only controls (e.g. Back, Search, New text note).
3. **Exact semantic text** — only when the string is immutable by design (e.g. the "KeepLab"
   screen title, a fixture note title). Never for user- or locale-variable text.
4. **Structured accessibility relation** — parent/child ordering or `By.clazz` scoping when a
   stable identity genuinely cannot exist.
5. **Coordinates** — absolute last resort. A Journey must **not** depend on `x,y` by default;
   a coordinate selector is a defect to be fixed in the feature, not a harness workaround.

## 2. Rules

- Key interaction nodes (primary actions, editable fields, list rows, navigation) **must ship a
  stable automation identity at implementation time** — in the same change that introduces them.
- `testTag`s are behaviour-neutral: adding one must not change product semantics.
- Do not select on dynamic data (timestamps, counts, user content) unless the Journey seeds that
  exact value deterministically.
- When a label is localized or user-visible copy, prefer an id/description over `text`.
- Removing or renaming an existing `testTag` is a breaking change for the verification layer;
  treat it like an API change.

## 3. Current identities in this codebase

Established for the frozen benchmark (reference, not an invitation to add more ad hoc):

| Node | Identity |
|---|---|
| Editor title field | `testTag("editor-title")` |
| Editor body field | `testTag("editor-body")` |
| Search field | `testTag("search-field")` |
| Home title | text `"KeepLab"` (immutable) |
| Back | `contentDescription("Back")` |
| Search | `contentDescription("Search")` |
| New text note | `contentDescription("New text note")` |

## 4. Enforcement path (future)

- Journeys are reviewed against this contract before a feature is considered verifiable.
- The harness never adds selectors on behalf of a feature; it consumes the contract above.
- Coordinate-based steps in a Journey are flagged and require an explicit justification.

This document adds **no new selectors**; it defines the standard future features must meet so the
verification layer stays stable and low-touch.
