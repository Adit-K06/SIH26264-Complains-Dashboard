"""Offline (list / DataFrame) tests for app.ai.institution_resolver."""
import pandas as pd

from app.ai.institution_resolver import normalize_name, resolve_institution


def test_exact_aicte_id_wins():
    df = pd.DataFrame([{"institution_id": 7, "institution_name": "ABC College of Engineering", "aicte_id": "ID-7"}])
    r = resolve_institution(df, "wrong name", "ID-7")
    assert r.institution_id == 7 and r.method == "EXACT_ID" and r.confidence == 1.0


def test_messy_name_auto_matches():
    df = pd.DataFrame([{"institution_id": 7, "institution_name": "ABC College of Engineering", "aicte_id": "ID-7"}])
    r = resolve_institution(df, "ABC Coll. of Engg", None)
    assert r.institution_id == 7 and r.method == "FUZZY" and not r.needs_review


def test_ambiguous_names_need_review():
    df = pd.DataFrame([{"institution_id": 1, "institution_name": "ABC College of Engineering"}, {"institution_id": 2, "institution_name": "ABC College of Engineering"}])
    r = resolve_institution(df, "ABC College of Engineering")
    assert r.institution_id is None and r.needs_review and len(r.candidates) >= 2


def test_unknown_name_does_not_match():
    df = pd.DataFrame([{"institution_id": 1, "institution_name": "ABC College of Engineering"}])
    r = resolve_institution(df, "Completely Different University")
    assert r.method == "NONE" and r.institution_id is None and not r.needs_review


def test_different_numbers_are_never_auto_matched():
    rows = [{"id": 1, "name": "Demo College of Engineering 1"}, {"id": 11, "name": "Demo College of Engineering 11"}]
    r = resolve_institution(rows, "Demo College of Engineering 111")
    assert r.institution_id is None            # near-identical text but a different number -> human review


def test_normalization_aliases():
    assert normalize_name("ABC Engg Coll.") == "abc engineering college"
