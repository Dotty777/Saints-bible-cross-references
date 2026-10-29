# Deuteronomy record recovery

Read ../canon.json, ../progress.json, verses.json and inventory.json before continuing. Fetch current remote main and preserve every completed object and review batch. Never run an initial bootstrap builder over this tracker.

The declared source is an ordered flat array at the pinned commit/blob in source-checks.json. Preserve each original chapter, ref, id and complete text. Grouping into chapters and adding a full reference do not revise the source. Keep every actual source numbering division and continuation unit.

Recover through Git history and make corrections in a new commit. Recompute source and pair counts and the first unfinished verse. Inventory/import, duplicate pairs and technical checks add no review credit.

Run python scripts/render_books.py and python scripts/validate.py --write-verification from the repository root. No WordPress or Saints-Translation edits are part of recovery.
