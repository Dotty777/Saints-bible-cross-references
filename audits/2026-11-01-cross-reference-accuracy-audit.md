# Cross-reference accuracy audit — 1 November 2026

Scope: every saved pair in this repository, and every cross-reference entry on the Saints.Bible staging site (`staging-8e0d-waywardnightjars.wpcomstaging.com`).

Reference text: [Saints-Translation](https://github.com/Dotty777/Saints-Translation) at the pinned commit `328967336f32958587835c921fea3b96a5bf6494`, which is still that repository's `main`. The staging site's own `/wp-json/saints/v1/text` output is identical to it for all 30,870 verses the two share.

## Summary

| Area | Checked | Result |
| --- | ---: | --- |
| Repository: source and target wording against the pinned source | 37,396 pairs | **0 differences** |
| Repository: references resolve to a staging chapter and anchor with the same wording | 100,653 verse references | **0 failures** |
| Repository: rationale matches the cited passage (screened, then read) | 37,396 screened; 578 read in full | **1 imprecise rationale, corrected** |
| Staging: quoted readings equal the Saints text at the linked anchor | 348,409 entries | **0 differences** |
| Staging: evidence quotes match the source and target readings | 348,409 entries | **0 differences** |
| Staging: English (OpenBible) label mapped to the right Greek-numbered verse | 66,460 distinct labels | **6 wrong mappings (21 entries)** |
| Staging: readings reported as "unavailable in this edition" that the edition has | 373 blank labels | **59 labels (223 entries) wrongly blank** |
| Staging: Saints verses with no cross-reference section | 34,534 units | **53 Proverbs verses missing** |

## Repository

### Text fidelity

[`scripts/audit_against_source.py`](../scripts/audit_against_source.py) compares every completed pair with a Saints-Translation checkout, covering:

- source text;
- every target reference, anchor ID, text and continuation paragraph;
- the pinned Git blob identity.

All 29,741 Old Testament and 7,655 New Testament pairs pass. The existing validators do not cover this check: they compare target text with the original only when an archived snapshot is present.

Every source and target verse also resolves to a staging chapter URL and anchor whose live text is identical. Live HTML was spot-checked on 31 chapter pages, including Greek Psalms 113 and 151, Esther 5, Susanna, Bel and the Dragon, and Leviticus 1. All expected `id` anchors were present.

### Rationale accuracy

Each rationale was scored against its target text and against every other verse of the target book. The screen looked for wrong-verse errors, such as off-by-one verse numbers or Hebrew/English numbering used where the Saints edition uses Greek numbering. The 278 pairs with the weakest rationale–target–source overlap, plus a random sample of 300, were then read in full. Every flagged numbering case used Greek numbering correctly, for example Exodus 15:18 → Psalms 145:10 (English 146:10).

One correction was made, recorded in [`review-batches/2026-11-01T120000Z-accuracy-audit.json`](../review-batches/2026-11-01T120000Z-accuracy-audit.json):

- `wisdom-of-solomon-14-4__psalms-106-28-30`: the rationale cited "when sailors' wisdom has failed". That detail is Psalms 106:27, outside the cited range 106:28–30. The rationale now describes only the cited verses. The target, hashes and counts are unchanged.

## Staging site

Every chapter page under `/study-guides/cross-references/` was crawled: 1,291 pages and 348,409 entries, matching the total the site states. Each displayed reading, quote and source verse was compared with the Saints text. Each English-numbered OpenBible label was compared with the World English Bible text at that reference and with the surrounding Saints verses. This exposed mappings where a better Greek equivalent sits nearby or elsewhere in the book. Every outlier was then read by hand.

The mapping is consistent across the site: each label always resolves to the same reading. Almost all differences from English versification are correct Greek equivalents. Examples include Psalm superscriptions counted as verse 1, Jeremiah 46–51 → 26–31, Exodus 36–38 → 37–38, Job 41:1–2 → 40:25–26, and the shorter Old Greek of Daniel 4–6.

Full entry-level detail and the correct target for each defect: [`2026-11-01-staging-cross-reference-defects.json`](2026-11-01-staging-cross-reference-defects.json).

### 1. Wrong readings (6 labels, 21 entries)

The Greek inventory list in Exodus 39:13–23 is in a different order from the English 39:33–43. Staging maps the two lists position by position, so four items show the wrong furnishing:

| English label | Shown now | Correct Saints reading |
| --- | --- | --- |
| Exodus 39:34 (coverings) | nothing ("unavailable") | Exodus 39:20 |
| Exodus 39:36 (table, showbread) | Exodus 39:15 (altar, oil, incense) | Exodus 39:17 |
| Exodus 39:38 (golden altar, oil, incense) | Exodus 39:17 (table) | Exodus 39:15 |
| Exodus 39:39 (bronze altar) | Exodus 39:18 (Aaron's robes) | Exodus 39:15 |
| Exodus 39:41 (Aaron's garments) | Exodus 39:21 (pegs) | Exodus 39:18 |
| Joshua 19:47 (Dan takes Leshem) | Joshua 19:47 (inheritance formula = English 19:48) | Joshua 19:47a–48 |

Several of these entries carry published "supported" reviews of the wrongly displayed text. They should be re-reviewed after the mapping is corrected.

### 2. Proverbs readings wrongly marked unavailable (59 labels, 223 entries)

The Greek Proverbs places 24:23–34, 30:15–33 and 31:10–31 later in the book. They are published on `chapter-24-source-block-2`, `chapter-30-source-block-2` and `chapter-31-source-block-2`. The reference resolver searches only the main chapter page, so these entries say "Passage unavailable in this edition" even though the edition contains them. Example: Proverbs 12:4 → Proverbs 31:10, two sayings about the courageous woman. 36 of these entries carry published reviews written as if the text were missing.

### 3. Proverbs source verses without a cross-reference section (53 verses)

The same gap means the Proverbs 24, 30 and 31 cross-reference pages stop at 24:22e, 30:14 and 31:9. Proverbs 24:23–34, 30:15–33 and 31:10–31 have no cross-references on staging.

### Not defects, but still open

These are disclosed on the site:

- 9 entries headed "Imported source N", whose OpenBible source verse could not be identified. The site says no connection is asserted.
- 904 entries marked partial.
- 57 reviewed entries marked unavailable where the Greek has no equivalent, e.g. Jeremiah 33:14–26 and 1 Samuel 17:12–31.
- 39,930 entries still awaiting review.

Susanna, Bel and the Dragon and the Sirach prologue have no cross-reference pages. OpenBible does not cover them.

## What was not changed

The staging site was not edited. The defects come from the site's reference-resolution plugin, whose code is not in this repository or in Saints-Translation. Correcting individual entries by hand would not fix the resolver and would probably be overwritten on the next import. The JSON file above lists the exact corrections for whoever maintains that importer.

This audit checks wording, numbering and passage identity. Like the existing records, it is AI-assisted and does not replace independent specialist review of interpretation.

## Completion pass (same day)

Every book is now finished in this repository.

| Area | Result |
| --- | --- |
| Revelation | 405 source verses, 1,040 pairs. Each drafted pair was read again by a separate reader: 936 accepted, 104 revised, 1 rejected. |
| Old Testament units left without links (2,009) | 689 linked with 954 new pairs (peer review: 811 accepted, 143 revised, 21 rejected); 1,320 closed with a stated reason. |
| New Testament deferrals (12) | All closed with a stated reason: genealogy names and greetings with no identifiable counterpart, and Syracuse in Acts 28:12. |
| Books finished | 43 of 43 Old Testament, 27 of 27 New Testament. |
| Source fidelity | All 39,390 pairs match the pinned Saints-Translation text (`scripts/audit_against_source.py`). |

**Closed** is a new final status. The unit was read and has no supportable cross-reference in this edition: it holds only a bare name, a speech introducer, or similar. Closed units carry their reason, have no pairs, earn no completion credit, and are listed in each book's `source-checks.json` and readable files. "Completed source verses" still counts only verses with retained pairs.

### Revelation source

The Saints-Translation repository had no Revelation record, so Revelation was blocked. With the owner's approval, the Revelation text published on staging was added to Saints-Translation as `revelation/verses.json`. It was added on branch `claude/add-revelation-snapshot`, commit `bf920386f6355064d4b7a5fd2f1ac4e99d8e5110`, and is marked as a staging text snapshot. All 405 verses were checked against the live chapter pages; the only difference is footnote markers. The Bespoke editorial revision of Revelation is still pending. When it is done, the Revelation records here must be re-pinned.

**Merged:** on 1 November 2026 Saints-Translation `main` was fast-forwarded to this commit, so the pin is on the default branch.

### Staging import

The drafted reviews are published to staging as `saints_xref_review` posts. Staging accepts a review only with the `batch` and `source_hash` of a waiting review-queue item. The site adds queue items about once an hour, a few chapters at a time, and marks an item done once every link in it has a review.

So far: **926 posts carrying 28,571 reviews across 606 chapters** (12,249 supported, 11,417 weak, 4,909 unsupported):

- The first import matched 507 posts (1,979 reviews) to the queue items that were already waiting.
- Then 36 posts carried 45 corrected reviews for queued links whose reading staging maps wrongly. Each note gives the correct Saints reading.
- Since then, 379 posts in 31 hourly queue rounds have carried 26,547 reviews.

Each post ID and the links it carries are listed in [`2026-11-01-staging-import-log.json`](2026-11-01-staging-import-log.json). After every round, each imported link was fetched again from its public chapter page. Each shows the Claude 2026-11-01 attribution and the drafted verdict, summary, why and note text. Copying slips found this way are republished correctly as one-review posts, and the newer entry is the one shown: post 39179 corrects 2 Kings 22:13 → Ezekiel 14:3–4 (why-text), post 39319 corrects 1 Chronicles 13:6 → Psalm 99:1 (summary), post 40114 corrects 2 Chronicles 33:9 → Ezekiel 16:45–47 (why-text). Post 40567 repeats the Nehemiah 11:36 → Joshua 21:1–45 review unchanged, after a false alarm in the page check.

Import continues hourly. **11,413 drafted reviews** are waiting for their chapters to be queued.

Some drafts still cannot be imported, whatever the queue does:

- **Missing source sections.** Proverbs 24:23–34, 30:15–33 and 31:10–31, Susanna, Bel and the Dragon, and the Sirach prologue have no staging pages for a review to attach to.
- **Already-reviewed entries.** Some of the 244 corrected reviews are for entries whose reading staging maps wrongly and that already carry a review. They can only be applied after the resolver is fixed.
