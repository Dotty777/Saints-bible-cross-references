# Psalms record recovery

Read ../canon.json, ../progress.json, verses.json and inventory.json first. Fetch current remote main and preserve every completed object and review batch. Never run an initial bootstrap builder over this tracker.

Recover the source from the exact commit and blob in source-checks.json. Preserve all original nested book/chapter metadata, ordered verse objects, references, anchors and words. Tracker status is separate from earlier source-edition status. Use the actual inventory for counts, continuation units and gaps; do not replace supplied names or numbering with another edition.

Recover through Git history in a new commit. Recompute counts and the first unfinished source unit. Inventory/import, duplicates, unresolved evidence and technical checks add no review credit. Run python scripts/render_books.py and then python scripts/validate.py --write-verification from the repository root. WordPress and Saints-Translation are separate from this tracker.



## Pending source review recovery

2534 original source units in 151 native chapters and 151 native source groups remain unchanged. 2534 read; 2209 supported sources; 2325 pairs; 0 never reviewed. First pending within book: **Psalms 4:1**. Next never-reviewed within book: **none; all original units read**. Deferred sources have zero completion credit. Preserve all prior evidence and native ordering.

Overall continuation: earliest pending source overall is **1 Chronicles 1:24**. Next new source review: **none; all OT source units read**.

**Pending evidence continuation: none; all pending evidence has been considered, awaiting substantive new leads.** Consideration and rereading alone earn no completion credit. Earliest unresolved source: **1 Chronicles 1:24**.
