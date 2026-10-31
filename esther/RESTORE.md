# Esther record recovery

Read ../canon.json, ../progress.json, verses.json and inventory.json first. Fetch current remote main and preserve every completed object and review batch. Never run an initial bootstrap builder over this tracker.

Recover the source from the exact commit and blob in source-checks.json. Preserve all original nested book/chapter metadata, ordered verse objects, references, anchors and words. Tracker status is separate from earlier source-edition status. Use the actual inventory for counts, continuation units and gaps; do not replace supplied names or numbering with another edition.

Recover through Git history in a new commit. Recompute counts and the first unfinished source unit. Inventory/import, duplicates, unresolved evidence and technical checks add no review credit. Run python scripts/render_books.py and then python scripts/validate.py --write-verification from the repository root. WordPress and Saints-Translation are separate from this tracker.

## Pending source review recovery

246 original Esther source units in 10 chapters were inventoried before review. 246 units have been read: 197 completed source units and 220 retained pairs; 0 units are never reviewed. Read but deferred sources earn zero completion credit: Esther 1:1b, Esther 1:1d, Esther 1:1g, Esther 1:1m, Esther 1:1q, Esther 1:2, Esther 1:3, Esther 1:4, Esther 1:5, Esther 1:6, Esther 1:7, Esther 1:8, Esther 1:9, Esther 1:10, Esther 1:14, Esther 1:15, Esther 1:17, Esther 1:21, Esther 2:11, Esther 2:13, Esther 2:16, Esther 2:19, Esther 4:2, Esther 4:9, Esther 4:10, Esther 4:12, Esther 4:15, Esther 4:17, Esther 4:17a, Esther 4:17p, Esther 4:17t, Esther 5:2b, Esther 5:5, Esther 5:7, Esther 6:5, Esther 6:7, Esther 7:5, Esther 8:12a, Esther 8:12d, Esther 8:12o, Esther 8:12x, Esther 9:7, Esther 9:8, Esther 9:9, Esther 9:11, Esther 9:31, Esther 10:1, Esther 10:2, Esther 10:3l. First unfinished source: **Esther 1:1b**. Next never-reviewed source in this book: **none**. Keep this book incomplete while any source unit remains pending.

The next new source review is **Hosea 1:1** (inventory required before review). Root progress.json keeps its earliest-pending next at **1 Chronicles 1:24** and its separate next_unreviewed at **Hosea 1:1** (inventory required before review). Recompute both positions from actual ordered source objects after every update. Preserve earlier completed objects, source fields, anchors, continuation bodies, pending cases and review batches. Inventory, unresolved evidence and rereading add no completion credit.
