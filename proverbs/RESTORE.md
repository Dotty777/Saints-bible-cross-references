# Proverbs record recovery

Read ../canon.json, ../progress.json, verses.json and inventory.json first. Fetch current remote main and preserve every completed object and review batch. Never run an initial bootstrap builder over this tracker.

Recover the source from the exact commit and blob in source-checks.json. Preserve all original nested book/chapter metadata, ordered verse objects, references, anchors and words. Tracker status is separate from earlier source-edition status. Use the actual inventory for counts, continuation units and gaps; do not replace supplied names or numbering with another edition.

Recover through Git history in a new commit. Recompute counts and the first unfinished source unit. Inventory/import, duplicates, unresolved evidence and technical checks add no review credit. Run python scripts/render_books.py and then python scripts/validate.py --write-verification from the repository root. WordPress and Saints-Translation are separate from this tracker.


## Pending source review recovery

939 original units in 31 native chapters and 34 original source sections remain unchanged. 692 units have been read: 646 completed sources and 669 retained pairs; 247 units have never been reviewed. Read source deferrals earn zero completion credit: Proverbs 1:17, Proverbs 6:4, Proverbs 7:6, Proverbs 7:10, Proverbs 7:11, Proverbs 7:12, Proverbs 7:15, Proverbs 7:16, Proverbs 7:20, Proverbs 9:13, Proverbs 9:18b, Proverbs 10:5, Proverbs 11:25, Proverbs 12:24, Proverbs 12:27, Proverbs 14:7, Proverbs 14:9, Proverbs 14:10, Proverbs 14:13, Proverbs 14:19, Proverbs 14:24, Proverbs 14:28, Proverbs 14:30, Proverbs 15:19, Proverbs 15:23, Proverbs 16:21, Proverbs 16:33, Proverbs 17:12, Proverbs 17:14, Proverbs 17:24, Proverbs 18:3, Proverbs 18:9, Proverbs 18:17, Proverbs 19:19, Proverbs 20:4, Proverbs 21:10, Proverbs 21:12, Proverbs 21:17, Proverbs 22:7, Proverbs 22:12, Proverbs 23:2, Proverbs 23:5, Proverbs 23:7, Proverbs 23:8, Proverbs 23:16, Proverbs 23:28. First pending source: **Proverbs 1:17**. Next never-reviewed source: **Proverbs 24:1**. Root earliest pending remains **1 Chronicles 1:24**. Preserve every original section, native field, prior completed object, deferred case, candidate and historical run.
