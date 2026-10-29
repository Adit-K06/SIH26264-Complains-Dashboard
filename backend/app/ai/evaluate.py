"""Group-held-out evaluation for synthetic overlap labels."""
from __future__ import annotations

import csv
import json
import math
import random
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.ai.overlaps import score_pair
from app.db import SessionLocal
from app.models import Case

REPO_ROOT = Path(__file__).resolve().parents[3]
LABELS_PATH = REPO_ROOT / "data" / "labels.csv"
JSON_PATH = REPO_ROOT / "docs" / "evaluation.json"
MARKDOWN_PATH = REPO_ROOT / "docs" / "evaluation.md"
SPLIT_SEED = 42
TEST_SIZE = 0.40


def _f1(precision: float, recall: float) -> float:
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def _metrics(labels: list[int], predictions: list[int]) -> dict[str, Any]:
    tp = sum(actual == 1 and predicted == 1 for actual, predicted in zip(labels, predictions))
    tn = sum(actual == 0 and predicted == 0 for actual, predicted in zip(labels, predictions))
    fp = sum(actual == 0 and predicted == 1 for actual, predicted in zip(labels, predictions))
    fn = sum(actual == 1 and predicted == 0 for actual, predicted in zip(labels, predictions))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": _f1(precision, recall),
        "confusion_matrix": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
    }


def _load_labeled_pairs(db) -> list[dict[str, Any]]:
    cases = {str(case.id): case for case in db.scalars(select(Case)).all()}
    rows: list[dict[str, Any]] = []
    with LABELS_PATH.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            case_a = cases.get(row["case_a_id"])
            case_b = cases.get(row["case_b_id"])
            if case_a is None or case_b is None:
                raise ValueError(
                    f"Label references missing case(s): {row['case_a_no']} / {row['case_b_no']}. "
                    "Run python -m app.seed --reset first."
                )
            if case_a.institution_id != case_b.institution_id:
                raise ValueError(
                    f"Label pair crosses institutions: {row['case_a_no']} / {row['case_b_no']}"
                )
            score, reasons = score_pair(case_a, case_b)
            rows.append(
                {
                    "case_a": case_a,
                    "case_b": case_b,
                    "case_a_no": row["case_a_no"],
                    "case_b_no": row["case_b_no"],
                    "label": int(row["label"]),
                    "kind": row.get("kind", ""),
                    "source": row.get("source", ""),
                    "score": score,
                    "reasons": reasons,
                    "group": str(case_a.institution_id),
                }
            )
    if len(rows) < 2 or len({row["group"] for row in rows}) < 2:
        raise ValueError("Evaluation needs labeled pairs from at least two institutions.")
    return rows


def _select_threshold(train_rows: list[dict[str, Any]]) -> tuple[float, dict[str, Any]]:
    labels = [row["label"] for row in train_rows]
    unique_scores = sorted({row["score"] for row in train_rows})
    candidates = {0.5}
    candidates.update(
        (left + right) / 2
        for left, right in zip(unique_scores, unique_scores[1:])
    )
    if unique_scores:
        candidates.add(min(1.0, unique_scores[-1] + 1e-9))
    evaluated = []
    for threshold in sorted(candidates):
        predictions = [int(row["score"] >= threshold) for row in train_rows]
        metrics = _metrics(labels, predictions)
        evaluated.append((metrics["f1"], metrics["precision"], threshold, metrics))
    _, _, threshold, metrics = max(evaluated, key=lambda item: (item[0], item[1], item[2]))
    return threshold, metrics


def _baseline_prediction(row: dict[str, Any]) -> int:
    case_a, case_b = row["case_a"], row["case_b"]
    same_institution = case_a.institution_id == case_b.institution_id
    same_category = case_a.category_id == case_b.category_id
    within_30_days = abs((case_a.received_on - case_b.received_on).days) <= 30
    return int(same_institution and same_category and within_30_days)


def _example(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_a": row["case_a_no"],
        "case_b": row["case_b_no"],
        "label": row["label"],
        "score": round(row["score"], 6),
        "kind": row["kind"],
        "summary_a": (row["case_a"].summary or "")[:240],
        "summary_b": (row["case_b"].summary or "")[:240],
    }


def evaluate() -> dict[str, Any]:
    with SessionLocal() as db:
        rows = _load_labeled_pairs(db)

    labels = [row["label"] for row in rows]
    groups = [row["group"] for row in rows]
    institution_groups = sorted(set(groups))
    random.Random(SPLIT_SEED).shuffle(institution_groups)
    test_group_count = max(1, math.ceil(TEST_SIZE * len(institution_groups)))
    test_groups = set(institution_groups[:test_group_count])
    train_indices = [index for index, group in enumerate(groups) if group not in test_groups]
    test_indices = [index for index, group in enumerate(groups) if group in test_groups]
    train_rows = [rows[index] for index in train_indices]
    test_rows = [rows[index] for index in test_indices]
    if not train_rows or not test_rows:
        raise ValueError("The fixed group split produced an empty train or test partition.")

    selected_threshold, train_metrics = _select_threshold(train_rows)
    test_labels = [row["label"] for row in test_rows]
    predictions = [int(row["score"] >= selected_threshold) for row in test_rows]
    model_metrics = _metrics(test_labels, predictions)
    baseline_predictions = [_baseline_prediction(row) for row in test_rows]
    baseline_metrics = _metrics(test_labels, baseline_predictions)

    false_positives = [
        _example(row)
        for row, prediction in zip(test_rows, predictions)
        if row["label"] == 0 and prediction == 1
    ][:3]
    misses = [
        _example(row)
        for row, prediction in zip(test_rows, predictions)
        if row["label"] == 1 and prediction == 0
    ][:3]
    result = {
        "disclaimer": (
            "All records and labels are synthetic. Results describe this demo dataset only "
            "and are not operational performance claims."
        ),
        "source": "SYNTHETIC",
        "split": {
            "strategy": "fixed-seed institution group holdout",
            "seed": SPLIT_SEED,
            "test_size": TEST_SIZE,
            "train_rows": len(train_rows),
            "test_rows": len(test_rows),
            "train_institutions": len({row["group"] for row in train_rows}),
            "test_institutions": len({row["group"] for row in test_rows}),
        },
        "model": {
            "score": "0.45*text_sim + 0.30*category_match + 0.15*time_proximity + 0.10*ref_overlap",
            "threshold_tuned_on": "train split only",
            "selected_threshold": selected_threshold,
            "train_metrics": train_metrics,
        },
        "held_out": model_metrics,
        "baseline": {
            "rule": "same institution + same category + within 30 days",
            **baseline_metrics,
        },
        "false_positives": false_positives,
        "misses": misses,
    }
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown = [
        "# Synthetic overlap evaluation",
        "",
        result["disclaimer"],
        "",
        f"- Split: {len(train_rows)} train pairs / {len(test_rows)} held-out pairs; "
        f"grouped by institution with seed {SPLIT_SEED}.",
        f"- Threshold selected from the train split: {selected_threshold:.6f}.",
        "",
        "## Held-out overlap model",
        "",
        f"- Precision: {model_metrics['precision']:.4f}",
        f"- Recall: {model_metrics['recall']:.4f}",
        f"- F1: {model_metrics['f1']:.4f}",
        f"- Confusion matrix (TN, FP, FN, TP): "
        f"{model_metrics['confusion_matrix']['tn']}, "
        f"{model_metrics['confusion_matrix']['fp']}, "
        f"{model_metrics['confusion_matrix']['fn']}, "
        f"{model_metrics['confusion_matrix']['tp']}",
        "",
        "## Held-out baseline",
        "",
        f"Rule: same institution + same category + within 30 days.",
        f"- Precision: {baseline_metrics['precision']:.4f}",
        f"- Recall: {baseline_metrics['recall']:.4f}",
        f"- F1: {baseline_metrics['f1']:.4f}",
        f"- Confusion matrix (TN, FP, FN, TP): "
        f"{baseline_metrics['confusion_matrix']['tn']}, "
        f"{baseline_metrics['confusion_matrix']['fp']}, "
        f"{baseline_metrics['confusion_matrix']['fn']}, "
        f"{baseline_metrics['confusion_matrix']['tp']}",
        "",
        "## False positives",
        "",
    ]
    markdown.extend(
        f"- {item['case_a']} / {item['case_b']} (score {item['score']:.4f}): "
        f"{item['summary_a']} | {item['summary_b']}"
        for item in false_positives
    )
    if not false_positives:
        markdown.append("- None in this held-out split.")
    markdown.extend(["", "## Misses", ""])
    markdown.extend(
        f"- {item['case_a']} / {item['case_b']} (score {item['score']:.4f}): "
        f"{item['summary_a']} | {item['summary_b']}"
        for item in misses
    )
    if not misses:
        markdown.append("- None in this held-out split.")
    markdown.append("")
    MARKDOWN_PATH.write_text("\n".join(markdown), encoding="utf-8")
    return result


def main() -> None:
    result = evaluate()
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

