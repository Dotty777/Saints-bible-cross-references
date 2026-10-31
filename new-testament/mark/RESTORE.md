# Recover Mark cross-reference records

The authoritative tracker is [verses.json](verses.json), with the complete original inventory in [inventory.json](inventory.json), decisions in [source-checks.json](source-checks.json), and review history in [../review-batches/](../review-batches/). Pin identities and full original source/target files are in [../source-snapshots/](../source-snapshots/).

1. Recover these files and [../progress.json](../progress.json) from the same repository commit. Preserve the existing Old Testament records.
2. From the repository root run `python scripts/render_new_testament.py`, then `python scripts/validate_new_testament.py --write-verification`.
3. The validator checks the original snapshot bytes against Git blob SHAs, every original source unit and retained target body, ordering, hashes, counts, unique pairs, readable content and both continuation positions. It does not create new review decisions.
4. Resume at the saved first unfinished position and the separate next new source position. Read and assess actual passages before changing status; technical repair earns zero review credit.
5. Commit records, notes, review history, readable files and progress together. Verify the remote main commit and published file identities after uploading.

First unfinished: Mark 1:33. Next new source review in this book: Mark 7:1.

Do not reconstruct Greek Psalm numbering or named figures from another edition. Do not silently replace source text. Independent specialist review and live destination checks are pending.

Hourly target: 500 newly completed distinct source verses. Count a source verse once regardless of its number of target passages. Save each run’s actual source-verse count, pair count, target result, shortfall and exact continuation.
