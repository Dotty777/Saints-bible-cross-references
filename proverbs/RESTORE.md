# Proverbs record recovery

Read ../canon.json, ../progress.json, verses.json and inventory.json first. Fetch current remote main and preserve every completed object and review batch. Never run an initial bootstrap builder over this tracker.

Recover the source from the exact commit and blob in source-checks.json. Preserve all original nested book/chapter metadata, ordered verse objects, references, anchors and words. Tracker status is separate from earlier source-edition status. Use the actual inventory for counts, continuation units and gaps; do not replace supplied names or numbering with another edition.

Recover through Git history in a new commit. Recompute counts and the first unfinished source unit. Inventory/import, duplicates, unresolved evidence and technical checks add no review credit. Run python scripts/render_books.py and then python scripts/validate.py --write-verification from the repository root. WordPress and Saints-Translation are separate from this tracker.

## Pending source review recovery

939 original Proverbs source units in 31 native chapters and 34 original source sections were inventoried before review. 120 units have been read: 119 completed source units and 133 retained pairs; 819 units are never reviewed. Read but deferred sources earn zero completion credit: Proverbs 1:17. First unfinished source: **Proverbs 1:17**. Next never-reviewed source in this book: **Proverbs 5:1**. Keep this book incomplete while any source unit remains pending. Earlier source deferrals and unresolved candidates remain unchanged; this run reviews only the next never-reviewed source units.

The next new source review is **Proverbs 5:1**. Root progress.json keeps its earliest-pending next at **1 Chronicles 1:24** and its separate next_unreviewed at **Proverbs 5:1**. Recompute both positions from actual ordered source objects after every update. Preserve earlier completed objects, source fields, anchors, continuation bodies, pending cases and review batches. Inventory, unresolved evidence and rereading add no completion credit. The complete Psalms inventory remains unchanged at 2534 original units in 151 chapters. The new Proverbs inventory preserves 939 original units in 31 native chapters and 34 source sections; a native chapter completes only after all of its source sections complete.
