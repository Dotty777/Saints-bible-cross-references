# 2 Chronicles record recovery

Read ../canon.json, ../progress.json, verses.json and inventory.json first. Fetch current remote main and preserve every completed object and review batch. Never run an initial bootstrap builder over this tracker.

Recover the source from the exact commit and blob in source-checks.json. Preserve all original nested book/chapter metadata, ordered verse objects, references, anchors and words. Tracker status is separate from earlier source-edition status. Use the actual inventory for counts, continuation units and gaps; do not replace supplied names or numbering with another edition.

Recover through Git history in a new commit. Recompute counts and the first unfinished source unit. Inventory/import, duplicates, unresolved evidence and technical checks add no review credit. Run python scripts/render_books.py and then python scripts/validate.py --write-verification from the repository root. WordPress and Saints-Translation are separate from this tracker.

## Pending source review recovery

All 833 original 2 Chronicles source units in 36 chapters have now been read in the recorded scopes. 813 source units and 922 retained pairs are completed; 20 source units remain pending with zero completion credit: 2 Chronicles 8:3, 2 Chronicles 20:13, 2 Chronicles 20:16, 2 Chronicles 24:3, 2 Chronicles 26:10, 2 Chronicles 26:11, 2 Chronicles 26:12, 2 Chronicles 26:13, 2 Chronicles 26:14, 2 Chronicles 27:5, 2 Chronicles 28:7, 2 Chronicles 29:20, 2 Chronicles 29:33, 2 Chronicles 31:7, 2 Chronicles 31:13, 2 Chronicles 31:16, 2 Chronicles 32:23, 2 Chronicles 32:28, 2 Chronicles 33:14, 2 Chronicles 35:26.

The first unfinished source is **2 Chronicles 8:3**. Preserve its status and all other uncertain sources until substantive supported evidence is checked. There are no never-reviewed 2 Chronicles units remaining. Do not mark 2 Chronicles complete while pending sources remain.

The next new source review is **Hosea 1:1** (inventory required before review). Root progress.json keeps its earliest-pending next at **1 Chronicles 1:24** and its separate next_unreviewed at **Hosea 1:1** (inventory required before review). Read those fields separately and recompute both positions from actual ordered source objects after every update. Preserve every earlier completed object, original source field, anchor, continuation body, pending case and review batch. Inventory, unresolved evidence and rereading add no completion credit.
