# Synthetic overlap evaluation

All records and labels are synthetic. Results describe this demo dataset only and are not operational performance claims.

- Split: 19 train pairs / 13 held-out pairs; grouped by institution with seed 42.
- Threshold selected from the train split: 0.660959.

## Held-out overlap model

- Precision: 0.6667
- Recall: 0.8571
- F1: 0.7500
- Confusion matrix (TN, FP, FN, TP): 3, 3, 1, 6

## Held-out baseline

Rule: same institution + same category + within 30 days.
- Precision: 0.6364
- Recall: 1.0000
- F1: 0.7778
- Confusion matrix (TN, FP, FN, TP): 2, 4, 0, 7

## False positives

- RB-2026-00028 / RB-2026-00029 (score 0.6726): Students requested review of student transcript verification records at the synthetic institution. | Students asked the bureau to check the student transcript verification records at this synthetic institution.
- RB-2026-00030 / RB-2026-00031 (score 0.6733): Students requested review of admission record correction records at the synthetic institution. | Students asked the bureau to check the admission record correction records at this synthetic institution.
- RB-2026-00032 / RB-2026-00033 (score 0.6726): Students requested review of semester result review records at the synthetic institution. | Students asked the bureau to check the semester result review records at this synthetic institution.

## Misses

- RB-2026-00008 / PGRC-2026-00008 (score 0.6490): Applicants reported that submitted scholarship documents were not reviewed. Synthetic reference SYN-REF-0008. | A complaint says scholarship applications remain pending despite document submission. Reference SYN-REF-0008.
