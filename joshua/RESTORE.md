# Joshua record recovery

Read ../canon.json, ../progress.json, verses.json and inventory.json first. Fetch current remote main and preserve every completed object and review batch. Never run an initial bootstrap builder over this tracker.

Recover source records from the exact commit/blob in source-checks.json. Preserve every actual nested chapter and ordered verse object, all reference/id/text fields and original source metadata. Chapter tracker status is distinct from earlier source-edition status. Retain continuation units and numbering gaps; do not invent verses or merge the 9:2a–2f ceremony into another edition's chapter 8.

Recover through Git history in a new commit. Recompute counts and first unfinished verse. Inventory/import, duplicates, unresolved evidence and technical checks add no completion credit. Run python scripts/render_books.py then python scripts/validate.py --write-verification from the repository root. No WordPress or Saints-Translation edits are part of recovery.
