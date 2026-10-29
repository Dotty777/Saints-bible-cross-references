# Exodus record recovery

Read `../canon.json`, `../progress.json`, `verses.json` and `inventory.json` before continuing. Fetch fresh remote main and preserve all completed records and review history. Never rerun an initial builder over this tracker.

Recover using Git history; record corrections in a new commit. Preserve exact source references, original anchors and continuation units, including 28:29a and 35:12a. Recompute counts and the first unfinished source verse. Inventory/import and validation do not count as curated reviews.

Run `python scripts/render_books.py` from the repository root, then `python scripts/validate.py --write-verification`. Scripture sources remain separately pinned in Saints-Translation. No WordPress or translation-repository edits are part of recovery.
