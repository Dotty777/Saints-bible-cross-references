# 2 Chronicles record recovery

Read ../canon.json, ../progress.json, verses.json and inventory.json first. Fetch current remote main and preserve every completed object and review batch. Never run an initial bootstrap builder over this tracker.

Recover the source from the exact commit and blob in source-checks.json. Preserve all original nested book/chapter metadata, ordered verse objects, references, anchors and words. Tracker status is separate from earlier source-edition status. Use the actual inventory for counts, continuation units and gaps; do not replace supplied names or numbering with another edition.

Recover through Git history in a new commit. Recompute counts and the first unfinished source unit. Inventory/import, duplicates, unresolved evidence and technical checks add no review credit. Run python scripts/render_books.py and then python scripts/validate.py --write-verification from the repository root. WordPress and Saints-Translation are separate from this tracker.

## Pending source review recovery

All 833 actual 2 Chronicles source units in 36 chapters were inventoried before source review. Only the 52 actual units in chapters 1–3 have been read in this review: 52 source units and 52 retained pairs are completed. The remaining 781 inventoried units have not been reviewed. The first unfinished and never-reviewed 2 Chronicles source is **2 Chronicles 4:1**. Preserve all original source objects, numbering, anchors, continuation bodies, inventory evidence and completed review objects.

The next new source review is **2 Chronicles 4:1**. Root progress.json keeps its earliest-pending next at **1 Chronicles 1:24** and its separate next_unreviewed at **2 Chronicles 4:1**. Read those fields separately and recompute both positions from actual ordered source objects after every update. Inventory, unresolved evidence and rereading add no completion credit.
