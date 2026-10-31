# Ezra record recovery

Read ../canon.json, ../progress.json, verses.json and inventory.json first. Fetch current remote main and preserve every completed object and review batch. Never run an initial bootstrap builder over this tracker.

Recover the source from the exact commit and blob in source-checks.json. Preserve all original nested book/chapter metadata, ordered verse objects, references, anchors and words. Tracker status is separate from earlier source-edition status. Use the actual inventory for counts, continuation units and gaps; do not replace supplied names or numbering with another edition.

Recover through Git history in a new commit. Recompute counts and the first unfinished source unit. Inventory/import, duplicates, unresolved evidence and technical checks add no review credit. Run python scripts/render_books.py and then python scripts/validate.py --write-verification from the repository root. WordPress and Saints-Translation are separate from this tracker.

## Pending source review recovery

280 original Ezra source units in 10 chapters were inventoried before review. 280 units have been read: 230 completed source units and 245 retained pairs; 0 units are never reviewed. Read but deferred sources earn zero completion credit: Ezra 1:9, Ezra 1:10, Ezra 2:17, Ezra 2:18, Ezra 2:19, Ezra 2:20, Ezra 2:30, Ezra 3:6, Ezra 3:9, Ezra 3:13, Ezra 4:1, Ezra 4:6, Ezra 4:7, Ezra 4:8, Ezra 4:9, Ezra 4:11, Ezra 4:14, Ezra 4:16, Ezra 4:17, Ezra 4:18, Ezra 4:22, Ezra 5:7, Ezra 6:11, Ezra 7:3, Ezra 7:4, Ezra 7:12, Ezra 7:14, Ezra 7:18, Ezra 7:24, Ezra 8:5, Ezra 8:7, Ezra 8:9, Ezra 8:10, Ezra 8:14, Ezra 10:15, Ezra 10:21, Ezra 10:23, Ezra 10:24, Ezra 10:26, Ezra 10:32, Ezra 10:33, Ezra 10:34, Ezra 10:35, Ezra 10:36, Ezra 10:37, Ezra 10:38, Ezra 10:39, Ezra 10:40, Ezra 10:41, Ezra 10:42. First unfinished source: **Ezra 1:9**. Next never-reviewed source in this book: **none**. Keep this book incomplete while any source unit remains pending.

The next new source review is **Isaiah 56:1**. Root progress.json keeps its earliest-pending next at **1 Chronicles 1:24** and its separate next_unreviewed at **Isaiah 56:1**. Recompute both positions from actual ordered source objects after every update. Preserve earlier completed objects, source fields, anchors, continuation bodies, pending cases and review batches. Inventory, unresolved evidence and rereading add no completion credit.
