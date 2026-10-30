# Judges record recovery

Read ../canon.json, ../progress.json, verses.json and inventory.json first. Fetch current remote main and preserve every completed object and review batch. Never run an initial bootstrap builder over this tracker.

Recover source records from the exact commit/blob in source-checks.json. Preserve every original nested chapter and ordered verse object, all reference/id/text fields, and original source metadata. Chapter tracker status is separate from earlier source-edition status. The pinned inventory has 21 chapters and 618 units without continuation anchors or missing numeric verse numbers; do not alter numbering to match another edition.

Recover through Git history in a new commit. Recompute counts and the first unfinished source unit. Inventory/import, duplicates, unresolved evidence and technical checks add no completion credit. Run python scripts/render_books.py then python scripts/validate.py --write-verification from the repository root. This task does not edit WordPress or Saints-Translation.
