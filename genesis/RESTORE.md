# Genesis record recovery

The versioned JSON records are the authoritative tracker for this repository. Read `../progress.json` and `verses.json` together before continuing. `Genesis.html` and `Genesis.txt` are readable views of completed records.

Use Git history to recover an earlier revision. Make corrections in a new commit and record the reason. Preserve source verse identities, pinned source files, stable pair IDs and earlier review history. Recalculate counts and the first unfinished verse after a correction; do not overwrite completed work from a stale local snapshot.

A book with a complete initial curated pass has `next_reference: null`; the next book's unfinished source verse remains in the overall `progress.json`. Preserve pending target-evidence candidates separately from completed pairs. Run `python scripts/render_books.py` from the repository root, then `python scripts/validate.py --write-verification` to synchronize and check the reading views and counts. The existing `render_genesis.py` entry point runs the same renderer.

Source records remain separately versioned in Saints-Translation at the commit listed in `source-checks.json`. These files do not modify or restore WordPress pages or the translation repository. No staging or production deployment is part of this tracker.
