# 2 Chronicles record recovery

Read ../canon.json, ../progress.json, verses.json and inventory.json first. Fetch current remote main and preserve every completed object and review batch. Never run an initial bootstrap builder over this tracker.

Recover the source from the exact commit and blob in source-checks.json. Preserve all original nested book/chapter metadata, ordered verse objects, references, anchors and words. Tracker status is separate from earlier source-edition status. Use the actual inventory for counts, continuation units and gaps; do not replace supplied names or numbering with another edition.

Recover through Git history in a new commit. Recompute counts and the first unfinished source unit. Inventory/import, duplicates, unresolved evidence and technical checks add no review credit. Run python scripts/render_books.py and then python scripts/validate.py --write-verification from the repository root. WordPress and Saints-Translation are separate from this tracker.

## Pending source review recovery

All 833 actual 2 Chronicles source units in 36 chapters were inventoried before review. The 561 actual units in chapters 1–26 have been read; 552 source units and 596 retained pairs are completed. 9 read source units remain pending with zero completion credit: 2 Chronicles 8:3, 2 Chronicles 20:13, 2 Chronicles 20:16, 2 Chronicles 24:3, 2 Chronicles 26:10, 2 Chronicles 26:11, 2 Chronicles 26:12, 2 Chronicles 26:13, 2 Chronicles 26:14. The remaining 272 source units have not been reviewed.

The first unfinished source in this book is **2 Chronicles 8:3**. The next never-reviewed source is **2 Chronicles 27:1**. Root progress.json retains its earliest-pending next at **1 Chronicles 1:24** and its separate next_unreviewed at **2 Chronicles 27:1**. Preserve every earlier completed object, original source field, anchor, continuation body, pending case and review batch. Do not mark a book complete while pending source units remain. Inventory, unresolved evidence and rereading add no completion credit.
