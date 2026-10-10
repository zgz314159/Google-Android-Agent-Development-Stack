# Verification Selector Contract (v1.0.0)

Applies to any Android feature/UI work expected to be verified by the Verification Layer
(production engine `uiautomator`; challenger `maestro`).

Deterministic verification is earned by a small number of **stable automation identities**,
not by coordinates or fragile text. This contract makes that a required part of feature
delivery, not an after-the-fact debugging exercise.

> Automation identity is part of feature implementation, not a Verification afterthought.

## 1. Selector priority (highest first)

1. **Stable `testTag` / resource id** — Compose `Modifier.testTag("editor-title")` with
   `testTagsAsResourceId = true` on the root, surfaced as an accessibility/resource id. The
   preferred identity for every interaction node.
2. **`contentDescription`** — for icon-only controls (Back, Search, New note).
3. **Exact semantic text** — only when the string is immutable by design. Never for user- or
   locale-variable text.
4. **Structured accessibility relation** — parent/child ordering or class scoping when a
   stable identity genuinely cannot exist.
5. **Coordinates** — absolute last resort. A journey must not depend on `x,y` by default; a
   coordinate selector is a defect to fix in the feature, not a harness workaround.

## 2. Rules

- Key interaction nodes (primary actions, editable fields, list rows, navigation) **must ship
  a stable automation identity at implementation time**.
- `testTag`s are behaviour-neutral: adding one must not change product semantics.
- Do not select on dynamic data (timestamps, counts, user content) unless the journey seeds
  that exact value deterministically.
- When a label is localized or user-visible copy, prefer an id/description over `text`.
- Removing or renaming an existing `testTag` is a breaking change for the Verification Layer;
  treat it like an API change.

## 3. Consumption

The Verification Layer **consumes** this contract; it never adds selectors on behalf of a
feature. A plan may carry a `selectors` block (documentation/validation aid) mirroring the
identities a journey depends on. Coordinate-based steps in a journey are flagged and require
explicit justification.
