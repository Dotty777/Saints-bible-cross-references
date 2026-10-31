# Proverbs record recovery

Read ../canon.json, ../progress.json, verses.json and inventory.json first. Fetch current remote main and preserve every completed object and review batch. Never run an initial bootstrap builder over this tracker.

Recover the source from the exact commit and blob in source-checks.json. Preserve all original nested book/chapter metadata, ordered verse objects, references, anchors and words. Tracker status is separate from earlier source-edition status. Use the actual inventory for counts, continuation units and gaps; do not replace supplied names or numbering with another edition.

Recover through Git history in a new commit. Recompute counts and the first unfinished source unit. Inventory/import, duplicates, unresolved evidence and technical checks add no review credit. Run python scripts/render_books.py and then python scripts/validate.py --write-verification from the repository root. WordPress and Saints-Translation are separate from this tracker.



## Pending source review recovery

939 original source units in 31 native chapters and 34 source sections remain unchanged. 939 read; 840 supported sources; 863 pairs; 0 never reviewed. First pending within book: **Proverbs 1:17**. Next never-reviewed within book: **none; all original units read**. Deferred sources have zero completion credit. Preserve all prior evidence and native ordering.

Overall continuation: earliest pending source overall is **1 Chronicles 1:24**. Next new source review: **Hosea 1:1** (inventory required before review).
