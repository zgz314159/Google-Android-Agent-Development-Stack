# Implementation Design — <Feature>

## Architecture
<!-- The real existing architecture this change plugs into. Name the layers and where the
     change lands. State explicitly what is REUSED and must not be rebuilt. -->

## Data Flow
<!-- Step-by-step path from user action to persisted state and back to the UI. -->

## File Structure Plan
<!-- The boundary map. Every path must be verified to exist (brownfield). -->

**MUST TOUCH**
| File | Role | Expected change |
| --- | --- | --- |
| `<path>` | <role> | <change> |

**MAY TOUCH**
| File | Role | Expected change |
| --- | --- | --- |
| `<path>` | <role> | <change> |

**MUST NOT TOUCH**
- `<path>` — <why frozen>

## Selector Contract
<!-- Stable automation identities: name -> Compose testTag -> UiAutomator selector -> state. -->

## Contract Metadata
```json
{
  "decisions": [
    { "id": "DEC-001", "statement": "<decision>", "rationale": "<why it is frozen>" }
  ],
  "assumptions": [
    { "id": "ASM-001", "statement": "<assumption an executor may challenge>" }
  ],
  "data_change": {
    "schema_version_current": 0,
    "schema_version_target": 0,
    "migration_required": false,
    "notes": "<schema/data note>"
  },
  "ui_change": {
    "surfaces": ["<surface>"],
    "selectors_added": ["<selector name>"]
  },
  "selector_contract": [
    {
      "name": "<selector-name>",
      "compose_test_tag": "<selector-name>",
      "uiautomator": "By.res(\"<selector-name>\")",
      "state": "<state this selector identifies>",
      "required": true
    }
  ],
  "stop_conditions": ["<when the executor must STOP and emit CONTRACT_DEVIATION>"]
}
```
