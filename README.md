# Saints Bible cross-reference records

Book-by-book Old Testament cross-references, matching passage evidence and review status. The folder structure follows [Saints-Translation](https://github.com/Dotty777/Saints-Translation).

- [Genesis — 50 chapters](genesis/README.md): initial curated pass complete for chapters 1–19; **496 source verses, 1244 matching cross-reference pairs**. Later chapters remain pending.

[progress.json](progress.json) records the complete book plan, actual completed verses and pairs, each book's status and the exact continuation. **Next: Genesis 20:1.** No complete Old Testament book is claimed yet.

## Coverage

Work begins at Genesis and follows the reference edition's relative Old Testament order. The scope includes all 43 Old Testament books in the Saints-Translation working edition, its Greek Esther/Daniel material and Psalm 151. It also explicitly reserves Tobit, Judith and Baruch, which are absent from that selected edition, for source selection and verse-numbering inventory before review. The resulting plan contains 46 book records. Their absence from the reference repository is not treated as completed coverage.

The deuterocanonical scope includes 1–2 Maccabees, Wisdom of Solomon, Sirach, Tobit, Judith, Baruch and the expanded Esther/Daniel readings. Tobit and Judith are inserted after Nehemiah; Baruch is inserted after Jeremiah. Other books retain their relative order in Saints-Translation.

Each active book receives a complete inventory from its declared source edition before review. Pending books have no invented verse totals. Genesis currently has 1,531 inventoried source units, of which 496 are completed.

## What completed means

Completed means the initial curated cross-reference pass: the source verse and every listed target passage were read in the pinned Saints-Translation English records, and each retained pair has a specific explanation. It does not mean every possible biblical connection has been exhausted, or independent scholarly approval.

A completed entry includes its unchanged source verse, a matching target passage, an explicit relationship category, an individual explanation, pinned target text and evidence hashes. A multi-verse target passage counts as one pair. Duplicate pairs and unreviewed suggestions do not increase completion counts.

The target is **500 newly completed cross-reference pairs per hourly run**. Distinct source verses and pairs are tracked separately. The initial setup batch contains **94 pairs**, so it does not claim to have reached 500. Future runs resume the exact unfinished verse and save actual progress.

## Files and review limits

Each book folder follows the translation repository's pattern: a README, readable HTML and text, `verses.json`, editorial notes, source checks, verification and recovery guidance. Only completed cross-references appear in the readable edition; the JSON also preserves the pending source-verse inventory.

Source and target texts in the completed records are the supplied Saints-Translation English records, pinned to commit `328967336f32958587835c921fea3b96a5bf6494`. Greek-based verse identities and anchors remain intact. For example, Psalms 103 here is the reference edition's Greek Psalm 103, not a silent substitution of Hebrew Psalm 103. The supplied edition's provisional critical-text and specialist-review limitations continue to apply.

These are AI-assisted English passage reviews. Independent specialist review and live destination-anchor/display verification remain pending. The repository is a separate tracker; it does not deploy WordPress content or edit Saints-Translation.

Run `python scripts/validate.py` to check the saved data, counts, unique pair IDs, evidence hashes, HTML source anchors and next unfinished verse before committing further batches.

After updating the structured records and progress, run `python scripts/render_genesis.py` to refresh the Genesis HTML/text views and current README counts, then validate again.

Latest saved review: 2026-10-28, **610 new pairs across 261 source verses**. Hourly target: 500; shortfall: 0. [Review record](genesis/review-batches/2026-10-28T233950Z.json).
