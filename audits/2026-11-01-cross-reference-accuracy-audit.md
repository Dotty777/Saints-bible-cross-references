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
