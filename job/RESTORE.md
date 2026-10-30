# Job record recovery

Read ../canon.json, ../progress.json, verses.json and inventory.json first. Fetch current remote main and preserve every completed object and review batch. Never run an initial bootstrap builder over this tracker.

Recover the source from the exact commit and blob in source-checks.json. Preserve all original nested book/chapter metadata, ordered verse objects, references, anchors and words. Tracker status is separate from earlier source-edition status. Use the actual inventory for counts, continuation units and gaps; do not replace supplied names or numbering with another edition.

Recover through Git history in a new commit. Recompute counts and the first unfinished source unit. Inventory/import, duplicates, unresolved evidence and technical checks add no review credit. Run python scripts/render_books.py and then python scripts/validate.py --write-verification from the repository root. WordPress and Saints-Translation are separate from this tracker.

## Pending source review recovery

1083 original Job source units in 42 chapters were inventoried before review. 187 units have been read: 143 completed source units and 162 retained pairs; 896 units are never reviewed. Read but deferred sources earn zero completion credit: Job 3:2, Job 3:8, Job 3:18, Job 4:1, Job 4:6, Job 4:9, Job 4:10, Job 4:11, Job 4:14, Job 4:15, Job 4:16, Job 4:18, Job 5:1, Job 5:4, Job 5:5, Job 5:6, Job 5:8, Job 5:19, Job 5:24, Job 6:1, Job 6:7, Job 6:8, Job 6:11, Job 6:13, Job 6:16, Job 6:17, Job 6:19, Job 6:22, Job 6:23, Job 6:25, Job 6:28, Job 6:29, Job 7:3, Job 7:6, Job 7:8, Job 7:13, Job 7:15, Job 7:21, Job 8:1, Job 8:10, Job 8:12, Job 8:16, Job 8:17, Job 8:19. First unfinished source: **Job 3:2**. Next never-reviewed source in this book: **Job 9:1**. Keep this book incomplete while any source unit remains pending.

The next new source review is **Job 9:1**. Root progress.json keeps its earliest-pending next at **1 Chronicles 1:24** and its separate next_unreviewed at **Job 9:1**. Recompute both positions from actual ordered source objects after every update. Preserve earlier completed objects, source fields, anchors, continuation bodies, pending cases and review batches. Inventory, unresolved evidence and rereading add no completion credit.
