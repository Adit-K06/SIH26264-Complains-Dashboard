"""Reproducible held-out evaluation of the Tier-B scorer and the institution resolver (synthetic data).

Run:  cd backend && python -m app.ai.evaluate     (Docker: docker compose exec api python -m app.ai.evaluate)
Writes docs/evaluation.json and docs/evaluation.md, which GET /api/v1/admin/evaluation serves.
"""
from __future__ import annotations
import hashlib
import json

import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score

from .overlap import OPEN_STATUSES, OVERLAP_THRESHOLD, build_vectorizer, score_pair
from .paths import data_dir, docs_dir

THRESHOLDS = [round(x / 100, 2) for x in range(20, 91, 5)]


def _partition(inst_id) -> str:
    # Stable institution-level split; no random state, no runtime-dependent ordering.
    n = int(hashlib.sha256(str(inst_id).encode()).hexdigest()[:8], 16) % 100
    return "test" if n < 40 else "train"


def _metric(y, pred):
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel().tolist()
    return {"precision": round(precision_score(y, pred, zero_division=0), 4),
            "recall": round(recall_score(y, pred, zero_division=0), 4),
            "f1": round(f1_score(y, pred, zero_division=0), 4),
            "accuracy": round(accuracy_score(y, pred), 4),
            "confusion_matrix": {"true_negative": tn, "false_positive": fp, "false_negative": fn, "true_positive": tp},
            "support": len(y)}


def _eligible(a, b) -> bool:
    """Only pairs the production detector would ever score: same institution, different bureau, both open."""
    return (str(a["institution_id"]) == str(b["institution_id"]) and str(a["bureau"]) != str(b["bureau"])
            and str(a["status"]).upper() in OPEN_STATUSES and str(b["status"]).upper() in OPEN_STATUSES)


def evaluate_resolver():
    """Match messy institution names back to their true institution. Needs rapidfuzz (see requirements)."""
    import os
    if os.getenv("AI_EVAL_SKIP_RESOLVER"):
        return {"status": "not_run", "reason": "skipped via AI_EVAL_SKIP_RESOLVER"}
    try:
        from .institution_resolver import resolve_institution
    except ImportError as exc:
        return {"status": "not_run", "reason": f"dependency missing: {exc}"}
    d = data_dir()
    inst = pd.read_csv(d / "institutions.csv", keep_default_na=False)
    messy = pd.read_csv(d / "messy_institution_names.csv", keep_default_na=False)
    records = [{"id": r["institution_id"], "name": r["institution_name"], "aicte_id": r["aicte_id"]} for r in inst.to_dict("records")]
    counts = {"auto_correct": 0, "auto_wrong": 0, "needs_review": 0, "no_match": 0}
    review_contains_truth = 0
    for r in messy.to_dict("records"):
        # name only: the AICTE-ID shortcut is trivially correct and would hide fuzzy errors
        res = resolve_institution(records, r["messy_name"], None)
        if res.institution_id is not None:
            counts["auto_correct" if res.institution_id == r["institution_id"] else "auto_wrong"] += 1
        elif res.needs_review:
            counts["needs_review"] += 1
            review_contains_truth += any(c["id"] == r["institution_id"] for c in res.candidates)
        else:
            counts["no_match"] += 1
    n = len(messy)
    return {"status": "ok", "names_tested": n, **counts, "review_candidates_contain_truth": review_contains_truth,
            "auto_match_precision": round(counts["auto_correct"] / max(1, counts["auto_correct"] + counts["auto_wrong"]), 4),
            "auto_match_rate": round((counts["auto_correct"] + counts["auto_wrong"]) / max(1, n), 4)}


def main():
    DATA, DOCS = data_dir(), docs_dir()
    cases = pd.read_csv(DATA / "complaints.csv", keep_default_na=False)
    labels = pd.read_csv(DATA / "labels.csv", keep_default_na=False)
    indexed = cases.set_index("case_id", drop=False)

    # Same scoring path as production scan_overlaps: one corpus-level TF-IDF per institution (open cases).
    vec_by_inst = {}
    open_cases = cases[cases.status.str.upper().isin(OPEN_STATUSES)]
    for inst_id, grp in open_cases.groupby("institution_id"):
        vec_by_inst[inst_id] = build_vectorizer(grp.summary.tolist())

    records, excluded = [], 0
    for row in labels.to_dict("records"):
        if row["case_a_ref"] not in indexed.index or row["case_b_ref"] not in indexed.index:
            continue
        a = indexed.loc[row["case_a_ref"]].to_dict(); b = indexed.loc[row["case_b_ref"]].to_dict()
        pa, pb = _partition(a["institution_id"]), _partition(b["institution_id"])
        if pa != pb:
            excluded += 1; continue
        elig = _eligible(a, b)
        score = score_pair(a, b, vec_by_inst.get(a["institution_id"]) if elig else None)["score"]
        records.append({"label": int(row["label"]), "score": score, "partition": pa, "eligible": elig, "reason": row["reason"]})
    frame = pd.DataFrame(records)
    train, test = frame[frame.partition == "train"], frame[frame.partition == "test"]
    train_e, test_e = train[train.eligible], test[test.eligible]
    if train_e.label.nunique() < 2 or test_e.label.nunique() < 2:
        raise RuntimeError("Need positive and negative detector-eligible pairs in both partitions. Regenerate data.")

    # Tune on what the detector actually sees (eligible pairs), not on trivially-separable cross-institution negatives.
    tuned = max(THRESHOLDS, key=lambda t: (f1_score(train_e.label, train_e.score >= t, zero_division=0),
                                           precision_score(train_e.label, train_e.score >= t, zero_division=0), t))
    at_edge = tuned in (THRESHOLDS[0], THRESHOLDS[-1])
    eligible_metrics = _metric(test_e.label, (test_e.score >= tuned).astype(int))
    eligible_baseline = _metric(test_e.label, (test_e.score >= 0.60).astype(int))
    eligible_current = _metric(test_e.label, (test_e.score >= OVERLAP_THRESHOLD).astype(int))
    all_pairs_metrics = _metric(test.label, (test.score >= tuned).astype(int))

    output = {
        "synthetic_only": True, "seed": 42,
        "split": "stable institution hash; cross-partition institution pairs excluded",
        "training_pairs": len(train), "held_out_pairs": len(test), "excluded_cross_partition_pairs": excluded,
        "eligible_train_pairs": len(train_e), "eligible_cross_bureau_open_pairs": len(test_e),
        "threshold_search": THRESHOLDS, "selected_threshold": tuned, "selected_threshold_at_search_edge": at_edge,
        "active_threshold_in_code": OVERLAP_THRESHOLD,
        "eligible_only_metrics": eligible_metrics,
        "eligible_only_baseline_metrics": eligible_baseline,
        "eligible_only_active_threshold_metrics": eligible_current,
        "all_labelled_pairs_metrics_at_selected": all_pairs_metrics,
        "tier_b_weights": {"text_similarity": 0.45, "category_match": 0.30, "time_proximity": 0.15, "reference_overlap": 0.10},
        "resolver": evaluate_resolver(),
        "interpretation": "Synthetic metrics validate code paths only. They are not evidence of performance on real AICTE complaints.",
    }
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "evaluation.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
    md = ["# Synthetic AI/ML evaluation", "",
          "**Warning:** all records are synthetic. These results are not evidence of performance on real AICTE complaints.", "",
          f"- Training pairs: {len(train)} (detector-eligible: {len(train_e)})",
          f"- Held-out pairs: {len(test)} (detector-eligible: {len(test_e)})",
          f"- Excluded cross-partition pairs: {excluded}",
          f"- Selected threshold (tuned on eligible train pairs): {tuned:.2f}" + (" **(at edge of search range - widen it)**" if at_edge else ""),
          f"- Threshold currently active in code (OVERLAP_THRESHOLD): {OVERLAP_THRESHOLD:.2f}", "",
          "## Held-out, detector-eligible pairs at the selected threshold", "", f"`{json.dumps(eligible_metrics)}`", "",
          "## Same pairs at the 0.60 starting threshold", "", f"`{json.dumps(eligible_baseline)}`", "",
          "## Same pairs at the threshold currently active in code", "", f"`{json.dumps(eligible_current)}`", "",
          "## Institution resolver (messy names, name only)", "", f"`{json.dumps(output['resolver'])}`", "",
          "## Interpretation", "",
          "Use these numbers to verify reproducibility and compare algorithm revisions only. The planted positives are far easier than real complaints. "
          "Validate against expert-labelled real cases before operational use."]
    (DOCS / "evaluation.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("Synthetic evaluation completed.")
    print(json.dumps({k: output[k] for k in ["selected_threshold", "active_threshold_in_code", "eligible_only_metrics",
                                              "eligible_only_active_threshold_metrics", "resolver"]}, indent=2))
    print(f"Reports written to: {DOCS}")


if __name__ == "__main__":
    main()
