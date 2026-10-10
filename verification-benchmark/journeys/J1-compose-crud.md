# J1 — Pure Compose CRUD

Business goal (identical for engines A/B/C — never changed per executor):

1. Launch KeepLab.
2. Create a text note: title `VC-J1-Title`, body `VC-J1-Body`.
3. Return to home.
4. Search `VC-J1-Title`.
5. Open the note.
6. Change body to `VC-J1-Body-Edited`.
7. Return to home.

## Ground truth (terminal oracle)

| Assertion | Source |
|---|---|
| A note with title `VC-J1-Title` exists | Database (`notes.title`) |
| Its `body == VC-J1-Body-Edited` | Database |
| `archived == false` | Database |
| `trashed == false` | Database |
| The note is visible on Home after search | UI (semantics/UiAutomator) |
| No crash / fatal exception | Process (logcat + instrumentation result) |

Visual evidence is **not** used as the oracle for any of these.

## Real-UI mapping (KeepLab)

- Create: Home FAB `contentDescription="New text note"` → `Editor(noteId)`.
- Title field: first `TextField` (placeholder "Title"); body field: `TextField` (placeholder "Take a note...").
- Back: `contentDescription="Back"` → autosave on change (EditorViewModel autosave).
- Search: top-bar `contentDescription="Search"` → `SearchTopBar` field (placeholder "Search notes").
- Open note: tap the `NoteCard` whose text contains the title.
- Edit body: reopen editor, replace body text, back.

## Fixture

`seedJ1` — clean database (delete `keeplab.db`). No notes.

## Why this journey

Minimal end-to-end: exercises create, autosave, search, edit — the cheapest deterministic
path. It is the clearest place to show B/C replace per-step screenshot inspection with one
batched run + one DB oracle.
