# Synthetic AI/ML evaluation

**Warning:** all records are synthetic. These results are not evidence of performance on real AICTE complaints.

- Training pairs: 193
- Held-out pairs: 162
- Excluded cross-partition pairs: 65
- Selected threshold: 0.40

## Held-out metrics

- **precision:** `0.7768`
- **recall:** `1.0`
- **f1:** `0.8744`
- **accuracy:** `0.8457`
- **confusion_matrix:** `{"true_negative": 50, "false_positive": 25, "false_negative": 0, "true_positive": 87}`
- **support:** `162`

## Detector-eligible held-out pairs

- Eligible pairs: 105
- Metrics: `{"precision": 0.9355, "recall": 1.0, "f1": 0.9667, "accuracy": 0.9429, "confusion_matrix": {"true_negative": 12, "false_positive": 6, "false_negative": 0, "true_positive": 87}, "support": 105}`
- Baseline (0.60): `{"precision": 0.75, "recall": 0.1034, "f1": 0.1818, "accuracy": 0.2286, "confusion_matrix": {"true_negative": 15, "false_positive": 3, "false_negative": 78, "true_positive": 9}, "support": 105}`

## Interpretation

Use these metrics to verify reproducibility and compare algorithm revisions only. Review false positives/negatives and validate against expert-labeled real cases before operational use.
