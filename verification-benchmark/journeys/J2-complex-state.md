# J2 — Complex State / Navigation

Business goal (identical for engines A/B/C):

1. Launch KeepLab.
2. Enter the `Work` label scoped state.
3. Verify notes `VC-J2-A` and `VC-J2-B` are shown.
4. Search `VC-J2`.
5. Multi-select `VC-J2-A` and `VC-J2-B`.
6. Batch archive.
7. Enter Archive; verify A and B.
8. Move A to Trash.
9. Enter Trash; locate A.
10. Restore A.
11. Navigate to its expected destination.

## Ground truth (terminal oracle)

| Assertion | Source |
|---|---|
| A is restored (not trashed), and reachable at its app-design destination | Database + UI |
| B remains archived (`archived == true`) | Database |
| C unchanged (`archived == false`, `trashed == false`, no label) | Database |
| The `Work` label relationship for A and B remains correct | Database (`note_labels`) |
| No crash / fatal exception | Process |

## Real-UI mapping (KeepLab) — recorded, not invented

KeepLab's actual UX differs from a generic "Archive list with per-row delete", so the
business semantics are preserved while the steps map to the real UI:

| Step | Real UI |
|---|---|
| 2. Enter Work scoped state | Home overflow (`More`) → `Labels` → tap `Work` row → `LabelNotes(workId)` |
| 4. Search `VC-J2` | Label screen top-bar `Search label` → query `VC-J2` |
| 5. Multi-select A+B | Long-press `VC-J2-A` card → tap `VC-J2-B` card (`HomeViewModel.toggleSelection`) |
| 6. Batch archive | Selection top bar `Archive selected` |
| 7. Enter Archive | Home overflow (`More`) → `Archive` (ArchiveScreen lists archived, `recentFirst`) |
| 8. Move A to Trash | Tap `VC-J2-A` in Archive → `Editor(noteId)` → action `Move to trash` |
| 9. Enter Trash | back to Home → overflow (`More`) → `Trash` |
| 10. Restore A | TrashScreen row footer `Restore` |
| 11. Expected destination | A returns to Home (active, `trashed=false`); Archive long-press **unarchives**, so deletion intentionally goes through the editor, not the Archive row |

**Note:** `ArchiveScreen.onNoteLongClick = unarchive` (long-press unarchives). The journey
therefore moves A to Trash via the Editor's `Move to trash`, which is the only real path
that reaches Trash. Business semantics (archive B, trash A, restore A, leave C) are unchanged.

## Fixture (`seedJ2`)

| Note | Title | Label |
|---|---|---|
| A | `VC-J2-A` | Work |
| B | `VC-J2-B` | Work |
| C | `VC-J2-C` | (none) |

`Work` label seeded; A and B linked to it; C unlabeled. All `archived=false`, `trashed=false`.

## Why this journey

It stresses navigation depth, selection state, batch mutations, archive/trash lifecycle and
a relationship table — the states an agentic loop would otherwise inspect screenshot by screenshot.
