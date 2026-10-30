# 1 Chronicles record recovery

Read ../canon.json, ../progress.json, verses.json and inventory.json first. Fetch current remote main and preserve every completed object and review batch. Never run an initial bootstrap builder over this tracker.

Recover the source from the exact commit and blob in source-checks.json. Preserve all original nested book/chapter metadata, ordered verse objects, references, anchors and words. Tracker status is separate from earlier source-edition status. Use the actual inventory for counts, continuation units and gaps; do not replace supplied names or numbering with another edition.

Recover through Git history in a new commit. Recompute counts and the first unfinished source unit. Inventory/import, duplicates, unresolved evidence and technical checks add no review credit. Run python scripts/render_books.py and then python scripts/validate.py --write-verification from the repository root. WordPress and Saints-Translation are separate from this tracker.

## Pending source review recovery

The latest review scope is 1 Chronicles 1:1-14:17; it describes the span read, not an uninterrupted completed range. 516 supported source units and 516 retained pairs are completed. 12 read source units remain pending with zero source and pair completion credit: 1 Chronicles 1:24, 1 Chronicles 1:52, 1 Chronicles 2:47, 1 Chronicles 4:3, 1 Chronicles 4:8, 1 Chronicles 4:16, 1 Chronicles 4:17, 1 Chronicles 4:18, 1 Chronicles 4:19, 1 Chronicles 4:20, 1 Chronicles 7:12, 1 Chronicles 7:19.

The first unfinished source unit in actual inventory order is **1 Chronicles 1:24**. Revisit every deferred unit using its exact pinned source evidence and recorded reason in source-checks.json and the review batch; retain its original pending verse object until a supported review is completed. Never-reviewed source units start at **1 Chronicles 15:1** (402 units). Preserve all supported completed objects while reviewing those later units; do not treat the end of the review scope as proof that earlier deferrals are complete. Recompute the first unfinished unit from ordered pending objects after each update.
