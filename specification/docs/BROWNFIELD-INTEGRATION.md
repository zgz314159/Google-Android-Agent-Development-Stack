# BROWNFIELD-INTEGRATION — producing a package for an existing Android app

A brownfield change is compiled the same way, but the contract has *more* obligations: it
must prove it is grounded in the real source, reuse what exists, and fence off what is
frozen.

## 1. Reuse before you build

The first question is never "what shall we build?" but "does this already exist?".

- If the data field, query, or ordering already exists, the contract **uses it** and records
  it as reused. It must not add a duplicate column or a parallel mechanism.
- If the whole capability already exists, the change request is scoped to the **delta**
  (missing affordance, missing automation identity, missing verification), not a rebuild.
- Record what is reused explicitly in `design.md` (Architecture / Data Flow) so the executor
  does not "helpfully" re-implement it.

## 2. Ground every path

`File Structure Plan` in `design.md` is a boundary map, and every path must be verified to
exist against the actual tree before the contract is frozen:

- **MUST TOUCH** — the minimal set of files the change edits.
- **MAY TOUCH** — tests/fixtures the change may add to.
- **MUST NOT TOUCH** — everything frozen: the data model, DI, theme, unrelated screens,
  governance and harness files.

The same intent appears machine-readably in `project-context.json`
(`allowed_paths` / `forbidden_paths`) and `tasks.md` (`Allowed Paths`), where the validator
enforces non-overlap and project-relative safety.

## 3. Recon discipline (the point of the layer)

`project-context.json.read_first` lists the **12 or fewer** files an executor actually needs.
The executor reads the contract plus those files and starts implementing. A broad repo scan
is forbidden; any extension must be justified with an `EXTRA_RECON_REASON`.

## 4. Data changes

- State the room schema version explicitly: `data_change.schema_version_current` and
  `schema_version_target`, plus `migration_required`.
- If a field already exists, `current == target` and `migration_required = false`
  (brownfield change with no schema delta). If a migration is required, specify it as
  additive, data-preserving, and non-destructive.

## 5. Stable automation identity

If the project has no `testTag` convention, the contract introduces one and names the
selectors. Compose `testTag`s are visible to UiAutomator as resource-ids only when a root
node sets `Modifier.semantics { testTagsAsResourceId = true }`; the contract must include
that enablement as an explicit task, and the selector contract records both the Compose tag
and the UiAutomator selector form.

## 6. Verification & Evaluation integration

- `verification-intent.json` is the bridge: `journey_id`, `engine`, `required_selectors`,
  and the persistence / rotation / search checks the downstream Verification Plan must cover.
  It is **not** a runnable plan and must not carry an APK hash that does not exist yet.
- The executor builds the runnable Verification Plan from this intent, runs the Verification
  Layer, and lets the Auto-Finalizer record the Evaluation. The compiler does not run either.

## 7. Optional visual layer

Brownfield visual ground truth is the **existing app**:

```json
"design_source": "existing_app",
"stitch_used": false,
"reference_apk": null
```

- **Stitch** and **AI Studio reference APK** are declared with an explicit value — an empty
  list and `null`, or `not_required`. They are never left absent for an agent to guess.
- Stitch integration is **deferred**; AI Studio reference app is **deferred for greenfield**.

## 8. When the contract is wrong

The contract is authoritative but not infallible. A downstream executor that finds a fact
contradicting the source, a missing required file, a wrong migration assumption, an
impossible acceptance, or an unsafe boundary must **STOP and emit `CONTRACT_DEVIATION` with
evidence** — never silently redesign. This is written into the contract's `stop_conditions`
and the generated `EXECUTOR-PROMPT.md`.
