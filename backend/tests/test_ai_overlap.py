"""Pure (no database) tests for the Tier A/B overlap logic in app.ai.overlap."""
import pytest

from app.ai.overlap import OVERLAP_THRESHOLD, build_vectorizer, detect_overlaps, score_pair


def c(cid, inst, bureau, cat, status, text, date="2026-01-01", ref=""):
    return {"id": cid, "case_id": cid, "case_no": f"N{cid}", "institution_id": inst, "bureau": bureau, "category": cat,
            "status": status, "summary": text, "created_at": date, "complainant_ref": ref}


def test_tier_a_for_open_cross_bureau_cases():
    flags = detect_overlaps([c(1, 1, "RB", "fee refund", "PENDING", "refund fees"), c(2, 1, "PGRC", "fee refund", "PENDING", "fee refund")])
    assert any(f.tier == "A" for f in flags)


def test_tier_b_for_similar_cross_bureau_cases():
    cases = [c(1, 1, "RB", "fee refund", "PENDING", "Students report fees have not been returned by the institution.", ref="X"),
             c(2, 1, "PGRC", "fee refund", "UNDER_PROCESS", "A complaint alleges an unresolved delay in refunding student fees.", date="2026-01-12", ref="X")]
    assert any(f.tier == "B" and f.case_a == 1 and f.case_b == 2 for f in detect_overlaps(cases, threshold=.4))


def test_default_threshold_is_the_one_the_evaluation_selected():
    """Guards against code and docs/evaluation.json drifting apart again (was 0.60 vs 0.40)."""
    import json
    from pathlib import Path
    from app.ai.paths import docs_dir
    report = docs_dir() / "evaluation.json"
    if not report.exists():
        pytest.skip("docs/evaluation.json not present")
    assert json.loads(report.read_text())["selected_threshold"] == OVERLAP_THRESHOLD


def test_same_bureau_never_creates_tier_b():
    cases = [c(1, 1, "RB", "fee refund", "PENDING", "fee refund has not been paid"), c(2, 1, "RB", "fee refund", "PENDING", "fees have not been returned")]
    assert not any(f.tier == "B" for f in detect_overlaps(cases))


def test_closed_cases_do_not_create_flags():
    cases = [c(1, 1, "RB", "fee refund", "DISPOSED", "fees not returned"), c(2, 1, "PGRC", "fee refund", "DISPOSED", "refund fees not returned")]
    assert detect_overlaps(cases) == []


def test_score_pair_returns_reason_codes_and_bounded_score():
    a = c(1, 1, "RB", "fee refund", "PENDING", "fee refund pending", ref="X")
    b = c(2, 1, "PGRC", "fee refund", "PENDING", "refund fee pending", ref="X", date="2026-01-10")
    result = score_pair(a, b)
    assert 0 <= result["score"] <= 1
    assert "SAME_CATEGORY" in result["reasons"] and "SHARED_COMPLAINANT_REF" in result["reasons"]


def test_score_pair_does_not_mutate_a_fitted_vectorizer():
    vec = build_vectorizer(["fees not refunded", "salary not paid", "unsafe labs"])
    vocab_before = dict(vec.vocabulary_)
    score_pair(c(1, 1, "RB", "x", "PENDING", "completely new words here"), c(2, 1, "PGRC", "x", "PENDING", "other unseen tokens"), vec)
    assert vec.vocabulary_ == vocab_before


def test_missing_required_columns_raises():
    with pytest.raises(ValueError):
        detect_overlaps([{"id": 1}])
