# 1 Chronicles record recovery

Read ../canon.json, ../progress.json, verses.json and inventory.json first. Fetch current remote main and preserve every completed object and review batch. Never run an initial bootstrap builder over this tracker.

Recover the source from the exact commit and blob in source-checks.json. Preserve all original nested book/chapter metadata, ordered verse objects, references, anchors and words. Tracker status is separate from earlier source-edition status. Use the actual inventory for counts, continuation units and gaps; do not replace supplied names or numbering with another edition.

Recover through Git history in a new commit. Recompute counts and the first unfinished source unit. Inventory/import, duplicates, unresolved evidence and technical checks add no review credit. Run python scripts/render_books.py and then python scripts/validate.py --write-verification from the repository root. WordPress and Saints-Translation are separate from this tracker.

## Pending source review recovery

All 930 original 1 Chronicles source units have now been read in the recorded scopes. 917 source units and 1000 retained pairs are completed; 13 source units remain pending with zero completion credit: 1 Chronicles 1:24, 1 Chronicles 1:52, 1 Chronicles 2:47, 1 Chronicles 4:3, 1 Chronicles 4:8, 1 Chronicles 4:16, 1 Chronicles 4:17, 1 Chronicles 4:18, 1 Chronicles 4:19, 1 Chronicles 4:20, 1 Chronicles 7:12, 1 Chronicles 7:19, 1 Chronicles 27:32.

The first unfinished source is **1 Chronicles 1:24**. Preserve its status and all other uncertain sources until substantive supported evidence is checked. Preserve all earlier completed objects and review batches. There are no never-reviewed 1 Chronicles units remaining. Do not mark 1 Chronicles complete while pending sources remain.

The next new source review is **Nahum 1:1** (inventory required before review). Root progress.json keeps its earliest-pending next at **1 Chronicles 1:24** and its separate next_unreviewed at **Nahum 1:1** (inventory required before review). Read those fields separately and recompute both positions from actual ordered source objects after every update. Inventory, unresolved evidence and rereading add no completion credit.
