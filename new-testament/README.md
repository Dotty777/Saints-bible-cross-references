# Saints Holy Bible — separate New Testament cross-reference tracker

7407 completed source verses; 7533 retained pairs; 228 completed chapters; 12 reviewed units deferred.

First unfinished: **Matthew 1:14**. Next new source review: **1 John 3:1**.

This hourly task begins at Matthew and follows the exact Saints Holy Bible 70-book order and divisions in [../canon.json](../canon.json): Salvation (44–47), Discipleship (48–69), Glory (70). Targets may use any of those 70 books when actual pinned passage evidence is available. [Progress](progress.json) and review counts here are separate from the [Old Testament tracker](../README.md). Pending books have no invented verse inventories.

Completed means an initial curated cross-reference pass: the complete supplied English source unit and each retained target passage were read, and each pair has a specific explanation. It does not mean exhaustive coverage or independent specialist approval.

The source texts remain the supplied English edition; this is not new critical-text or original-language verification. Original Greek-based Saints numbering is retained, including OT targets. Each pair stores the complete target passage, rationale, relationship, source pin and evidence hashes. The readable files show retained pairs and disclose deferred units. Full original inputs and their Git blob identities are archived in [source-snapshots/manifest.json](source-snapshots/manifest.json). The hourly target is **500 newly completed distinct source verses with cross-references**. Count a source verse once regardless of how many target passages it has; pair totals remain separate. Deferred, duplicate, imported and previously completed source verses earn no new-source completion credit.

| Order | Division | Book | Status | Completed verses | Pairs |
| ---: | --- | --- | --- | ---: | ---: |
| 44 | Salvation | [Matthew](matthew/README.md) | in_progress | 1066 | 1099 |
| 45 | Salvation | [Mark](mark/README.md) | complete_initial_curated_pass | 673 | 681 |
| 46 | Salvation | [Luke](luke/README.md) | in_progress | 1143 | 1154 |
| 47 | Salvation | [John](john/README.md) | complete_initial_curated_pass | 878 | 889 |
| 48 | Discipleship | [Acts](acts/README.md) | in_progress | 1002 | 1018 |
| 49 | Discipleship | [Romans](romans/README.md) | in_progress | 430 | 443 |
| 50 | Discipleship | [1 Corinthians](1-corinthians/README.md) | complete_initial_curated_pass | 437 | 440 |
| 51 | Discipleship | [2 Corinthians](2-corinthians/README.md) | complete_initial_curated_pass | 256 | 257 |
| 52 | Discipleship | [Galatians](galatians/README.md) | complete_initial_curated_pass | 149 | 153 |
| 53 | Discipleship | [Ephesians](ephesians/README.md) | complete_initial_curated_pass | 155 | 157 |
| 54 | Discipleship | [Philippians](philippians/README.md) | complete_initial_curated_pass | 104 | 106 |
| 55 | Discipleship | [Colossians](colossians/README.md) | complete_initial_curated_pass | 95 | 95 |
| 56 | Discipleship | [1 Thessalonians](1-thessalonians/README.md) | complete_initial_curated_pass | 89 | 90 |
| 57 | Discipleship | [2 Thessalonians](2-thessalonians/README.md) | complete_initial_curated_pass | 47 | 47 |
| 58 | Discipleship | [1 Timothy](1-timothy/README.md) | complete_initial_curated_pass | 113 | 116 |
| 59 | Discipleship | [2 Timothy](2-timothy/README.md) | complete_initial_curated_pass | 83 | 85 |
| 60 | Discipleship | [Titus](titus/README.md) | complete_initial_curated_pass | 46 | 46 |
| 61 | Discipleship | [Philemon](philemon/README.md) | complete_initial_curated_pass | 25 | 25 |
| 62 | Discipleship | [Hebrews](hebrews/README.md) | complete_initial_curated_pass | 303 | 319 |
| 63 | Discipleship | [James](james/README.md) | complete_initial_curated_pass | 108 | 108 |
| 64 | Discipleship | [1 Peter](1-peter/README.md) | complete_initial_curated_pass | 105 | 105 |
| 65 | Discipleship | [2 Peter](2-peter/README.md) | complete_initial_curated_pass | 61 | 61 |
| 66 | Discipleship | [1 John](1-john/README.md) | in_progress | 39 | 39 |
| 67 | Discipleship | 2 John | pending | 0 | 0 |
| 68 | Discipleship | 3 John | pending | 0 | 0 |
| 69 | Discipleship | Jude | pending | 0 | 0 |
| 70 | Glory | Revelation | pending | 0 | 0 |

Run `python scripts/render_new_testament.py` and `python scripts/validate_new_testament.py --write-verification` from the repository root after updating records. Follow the book’s recovery guidance. Independent specialist and live destination-anchor/display checks remain pending.

Latest hourly result: **516 / 500 new source verses**; shortfall: 0. [Review record](review-batches/2026-10-31T145128Z.json).

Original source reading completed for: **Matthew, Mark, Luke, John, Acts, Romans, 1 Corinthians, 2 Corinthians, Galatians, Ephesians, Philippians, Colossians, 1 Thessalonians, 2 Thessalonians, 1 Timothy, 2 Timothy, Titus, Philemon, Hebrews, James, 1 Peter, 2 Peter**. Unresolved source deferrals remain separate and earn no completion credit.
