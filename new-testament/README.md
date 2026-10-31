# Saints Holy Bible — separate New Testament cross-reference tracker

2365 completed source verses; 2414 retained pairs; 21 completed chapters; 134 reviewed units deferred.

First unfinished: **Matthew 1:14**. Next new source review: **Luke 17:1**.

This hourly task begins at Matthew and follows the exact Saints Holy Bible 70-book order and divisions in [../canon.json](../canon.json): Salvation (44–47), Discipleship (48–69), Glory (70). Targets may use any of those 70 books when actual pinned passage evidence is available. [Progress](progress.json) and review counts here are separate from the [Old Testament tracker](../README.md). Pending books have no invented verse inventories.

Completed means an initial curated cross-reference pass: the complete supplied English source unit and each retained target passage were read, and each pair has a specific explanation. It does not mean exhaustive coverage or independent specialist approval.

The source texts remain the supplied English edition; this is not new critical-text or original-language verification. Original Greek-based Saints numbering is retained, including OT targets. Each pair stores the complete target passage, rationale, relationship, source pin and evidence hashes. The readable files show retained pairs and disclose deferred units. Full original inputs and their Git blob identities are archived in [source-snapshots/manifest.json](source-snapshots/manifest.json). The hourly target is **500 newly completed distinct source verses with cross-references**. Count a source verse once regardless of how many target passages it has; pair totals remain separate. Deferred, duplicate, imported and previously completed source verses earn no new-source completion credit.

| Order | Division | Book | Status | Completed verses | Pairs |
| ---: | --- | --- | --- | ---: | ---: |
| 44 | Salvation | [Matthew](matthew/README.md) | in_progress | 1022 | 1055 |
| 45 | Salvation | [Mark](mark/README.md) | in_progress | 660 | 668 |
| 46 | Salvation | [Luke](luke/README.md) | in_progress | 683 | 691 |
| 47 | Salvation | John | pending | 0 | 0 |
| 48 | Discipleship | Acts | pending | 0 | 0 |
| 49 | Discipleship | Romans | pending | 0 | 0 |
| 50 | Discipleship | 1 Corinthians | pending | 0 | 0 |
| 51 | Discipleship | 2 Corinthians | pending | 0 | 0 |
| 52 | Discipleship | Galatians | pending | 0 | 0 |
| 53 | Discipleship | Ephesians | pending | 0 | 0 |
| 54 | Discipleship | Philippians | pending | 0 | 0 |
| 55 | Discipleship | Colossians | pending | 0 | 0 |
| 56 | Discipleship | 1 Thessalonians | pending | 0 | 0 |
| 57 | Discipleship | 2 Thessalonians | pending | 0 | 0 |
| 58 | Discipleship | 1 Timothy | pending | 0 | 0 |
| 59 | Discipleship | 2 Timothy | pending | 0 | 0 |
| 60 | Discipleship | Titus | pending | 0 | 0 |
| 61 | Discipleship | Philemon | pending | 0 | 0 |
| 62 | Discipleship | Hebrews | pending | 0 | 0 |
| 63 | Discipleship | James | pending | 0 | 0 |
| 64 | Discipleship | 1 Peter | pending | 0 | 0 |
| 65 | Discipleship | 2 Peter | pending | 0 | 0 |
| 66 | Discipleship | 1 John | pending | 0 | 0 |
| 67 | Discipleship | 2 John | pending | 0 | 0 |
| 68 | Discipleship | 3 John | pending | 0 | 0 |
| 69 | Discipleship | Jude | pending | 0 | 0 |
| 70 | Glory | Revelation | pending | 0 | 0 |

Run `python scripts/render_new_testament.py` and `python scripts/validate_new_testament.py --write-verification` from the repository root after updating records. Follow the book’s recovery guidance. Independent specialist and live destination-anchor/display checks remain pending.

Latest hourly result: **542 / 500 new source verses**; shortfall: 0. [Review record](review-batches/2026-10-31T014513Z.json).

Original source reading completed for: **Matthew, Mark**. Unresolved source deferrals remain separate and earn no completion credit.
