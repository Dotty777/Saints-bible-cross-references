# Saints Bible cross-reference records

Book-by-book Old Testament cross-references, matching passage evidence and review status. The folder structure follows [Saints-Translation](https://github.com/Dotty777/Saints-Translation).

- [Genesis — 50 chapters](genesis/README.md): initial curated pass complete for all chapters; **1531 source verses, 3341 matching cross-reference pairs**.
- [Exodus — 40 chapters](exodus/README.md): initial curated pass complete for all chapters; **1165 source verses, 2259 matching cross-reference pairs**.
- [Leviticus — 27 chapters](leviticus/README.md): initial curated pass complete for all chapters; **859 source verses, 1361 matching cross-reference pairs**.
- [Numbers — 36 chapters](numbers/README.md): initial curated pass complete for all chapters; **1287 source verses, 1853 matching cross-reference pairs**.
- [Deuteronomy — 34 chapters](deuteronomy/README.md): initial curated pass complete for all chapters; **959 source verses, 1090 matching cross-reference pairs**.
- [Joshua — 24 chapters](joshua/README.md): initial curated pass complete for all chapters; **659 source verses, 677 matching cross-reference pairs**.
- [Judges — 21 chapters](judges/README.md): initial curated pass complete for all chapters; **618 source verses, 634 matching cross-reference pairs**.
- [Ruth — 4 chapters](ruth/README.md): source inventory complete; initial curated pass pending; **0 source verses, 0 matching cross-reference pairs**.

[progress.json](progress.json) records the complete book plan, actual completed verses and pairs, each book's status and the exact continuation. **Next: Ruth 1:1.** 7 Old Testament books have complete initial curated passes.

## Coverage

Use exclusively the **Saints Holy Bible 70-book edition**, with its exact book order and divisions recorded in [canon.json](canon.json). The current task reviews its **43 Old Testament source books** in order; matching passages may come from any of the 70 books when the actual text is available.

| Testament | Division | Book orders | Books |
| --- | --- | --- | ---: |
| Old Testament | Law | 1–5 | 5 |
| Old Testament | Judgement | 6–20 | 15 |
| Old Testament | Wisdom | 21–27 | 7 |
| Old Testament | Providence | 28–43 | 16 |
| New Testament | Salvation | 44–47 | 4 |
| New Testament | Discipleship | 48–69 | 22 |
| New Testament | Glory | 70 | 1 |

The book plan follows the Saints edition directly. Its 1–2 Maccabees, Wisdom of Solomon, Sirach, expanded Esther/Daniel material and Psalm 151 remain within that edition. Tobit, Judith and Baruch are excluded because they are outside its 70-book list. The New Testament canon listing defines eligible target books; it does not add New Testament source-review work to this Old Testament task.

Each active book receives a complete inventory from its declared source edition before review. Pending books have no invented verse totals. Genesis has 1,531 inventoried source units, of which 1,531 are completed. Exodus has 1,165 inventoried source units, of which 1,165 are completed. Leviticus has 859 inventoried source units, of which 859 are completed. Numbers has 1,287 inventoried source units, of which 1,287 are completed. Deuteronomy has 959 inventoried source units, of which 959 are completed. Joshua has 659 inventoried source units, of which 659 are completed. Judges has 618 inventoried source units, of which 618 are completed. Ruth has 85 inventoried source units, of which 0 are completed.

## What completed means

Completed means the initial curated cross-reference pass: the source verse and every listed target passage were read in the pinned Saints-Translation English records, and each retained pair has a specific explanation. It does not mean every possible biblical connection has been exhausted, or independent scholarly approval.

A completed entry includes its unchanged source verse, a matching target passage, an explicit relationship category, an individual explanation, pinned target text and evidence hashes. A multi-verse target passage counts as one pair. Duplicate pairs and unreviewed suggestions do not increase completion counts.

The target is **500 newly completed cross-reference pairs per hourly run**. Distinct source verses and pairs are tracked separately. The initial setup batch contains **94 pairs**, so it does not claim to have reached 500. Future runs resume the exact unfinished verse and save actual progress.

## Files and review limits

Each book folder follows the translation repository's pattern: a README, readable HTML and text, `verses.json`, editorial notes, source checks, verification and recovery guidance. Only completed cross-references appear in the readable edition; the JSON also preserves the pending source-verse inventory.

Source and target texts in the completed records are the supplied Saints-Translation English records, pinned to commit `328967336f32958587835c921fea3b96a5bf6494`. Greek-based verse identities and anchors remain intact. For example, Psalms 103 here is the reference edition's Greek Psalm 103, not a silent substitution of Hebrew Psalm 103. The supplied edition's provisional critical-text and specialist-review limitations continue to apply.

These are AI-assisted English passage reviews. Independent specialist review and live destination-anchor/display verification remain pending. The repository is a separate tracker; it does not deploy WordPress content or edit Saints-Translation.

Run `python scripts/validate.py` to check the saved data, counts, unique pair IDs, evidence hashes, HTML source anchors and next unfinished verse before committing further batches.

After updating structured records and progress, run `python scripts/render_books.py` to refresh all inventoried books and README counts, then `python scripts/validate.py --write-verification`. The existing `render_genesis.py` entry point runs the same multi-book renderer.

Latest saved review: 2026-10-29, **634 new pairs across 618 source verses**. Hourly target: 500; shortfall: 0. [Review record](review-batches/2026-10-30T011055Z.json).
