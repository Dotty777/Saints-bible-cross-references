# Recover Titus cross-reference records

The authoritative tracker is [verses.json](verses.json), with the complete original inventory in [inventory.json](inventory.json), decisions in [source-checks.json](source-checks.json), and review history in [../new-testament/review-batches/](../new-testament/review-batches/). Pin identities and full original source/target files are in [../new-testament/source-snapshots/](../new-testament/source-snapshots/).

1. Recover these files and [../new-testament/progress.json](../new-testament/progress.json) from the same repository commit. Preserve the existing Old Testament records.
2. From the repository root run `python scripts/render_new_testament.py`, then `python scripts/validate_new_testament.py --write-verification`.
3. The validator checks the original snapshot bytes against Git blob SHAs, every original source unit and retained target body, ordering, hashes, counts, unique pairs, readable content and both continuation positions. It does not create new review decisions.
4. Resume at the saved first unfinished position and the separate next new source position. Read and assess actual passages before changing status; technical repair earns zero review credit.
5. Commit records, notes, review history, readable files and progress together. Verify the remote main commit and published file identities after uploading.

First unfinished: none. Next new source review in this book: none. All original source units in this book have been read. Overall next new source: none.

Do not reconstruct Greek Psalm numbering or named figures from another edition. Do not silently replace source text. Independent specialist review and live destination checks are pending.

Hourly target: 500 newly completed distinct source verses. Count a source verse once regardless of its number of target passages. Save each run’s actual source-verse count, pair count, target result, shortfall and exact continuation.
