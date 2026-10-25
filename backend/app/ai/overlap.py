"""Tier A rules and Tier B cross-bureau complaint similarity scoring."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime, timezone
from itertools import combinations
import os
import re
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .embeddings import embedding_similarity, similarity_mode

OPEN_STATUSES = {"PENDING", "UNDER_PROCESS", "ESCALATED", "TRANSFERRED"}
# Tier-B cut-off. AGENTS.md starts at 0.60 and says to tune on training data; the synthetic
# evaluation (docs/evaluation.md) selects 0.40 (at 0.60 it finds only ~10% of planted overlaps).
# NOTE: at 0.40, same-category + close-in-time (0.30 + ~0.15) already scores 0.45 with no text
# match, so flags are a "please review" signal, not proof. Override with env OVERLAP_THRESHOLD.
OVERLAP_THRESHOLD = float(os.getenv("OVERLAP_THRESHOLD", "0.40"))

@dataclass
class OverlapFlag:
    institution_id: Any
    case_a: Any = None
    case_b: Any = None
    tier: str = "A"
    score: float = 0.0
    reasons: list[str] | None = None
    state: str = "OPEN"


def _get(obj, *names, default=None):
    for name in names:
        if isinstance(obj, dict) and name in obj:
            return obj[name]
        if hasattr(obj, name):
            return getattr(obj, name)
    return default


def _date(value):
    if isinstance(value, datetime): return value.date()
    if isinstance(value, date): return value
    if value is None: return None
    try: return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except (TypeError, ValueError): return None


def _normal_text(value):
    return re.sub(r"\s+", " ", str(value or "").lower()).strip()


def build_vectorizer(texts):
    """Fit one corpus-level word TF-IDF so IDF reflects the whole institution, not just 2 texts.

    Returns None when there is not enough text to fit (callers then fall back to pair-level fit).
    """
    docs = [_normal_text(t) for t in texts if _normal_text(t)]
    if len(docs) < 2:
        return None
    try:
        return TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, strip_accents="unicode").fit(docs)
    except ValueError:
        return None


def _text_similarity(a: str, b: str, vectorizer=None) -> float:
    """Text similarity in 0..1. SIMILARITY_MODE: tfidf (default) | hybrid | embedding.

    hybrid    = max(TF-IDF, calibrated embedding similarity): TF-IDF keeps exact wording/ID matches,
                embeddings recover paraphrases that TF-IDF misses.
    embedding = embedding similarity only.
    If no embedding model can be loaded, every mode silently falls back to TF-IDF.
    """
    a, b = _normal_text(a), _normal_text(b)
    if not a or not b: return 0.0
    if a == b: return 1.0
    mode = similarity_mode()
    if mode == "tfidf":
        return _tfidf_similarity(a, b, vectorizer)
    semantic = embedding_similarity(a, b)
    if semantic is None:
        return _tfidf_similarity(a, b, vectorizer)
    if mode == "embedding":
        return max(0.0, min(1.0, semantic))
    return max(0.0, min(1.0, max(semantic, _tfidf_similarity(a, b, vectorizer))))


def _tfidf_similarity(a: str, b: str, vectorizer=None) -> float:
    """Lexical similarity (word + character TF-IDF). Inputs must already be normalised."""
    try:
        if vectorizer is not None and hasattr(vectorizer, "vocabulary_"):
            word_matrix = vectorizer.transform([a, b])          # already fitted: do not refit/mutate
        else:
            word_matrix = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, strip_accents="unicode").fit_transform([a, b])
        word_score = float(cosine_similarity(word_matrix[0:1], word_matrix[1:2])[0, 0])
    except ValueError:
        word_score = 0.0
    try:
        char = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)
        char_matrix = char.fit_transform([a, b])
        char_score = float(cosine_similarity(char_matrix[0:1], char_matrix[1:2])[0, 0])
    except ValueError:
        char_score = 0.0
    return max(0.0, min(1.0, 0.65 * word_score + 0.35 * char_score))


def score_pair(case_a, case_b, vectorizer=None) -> dict:
    """Score two cases using the frozen weighted formula; return score and reason codes."""
    text_a = _get(case_a, "summary", "complaint_text", "last_action_text", default="")
    text_b = _get(case_b, "summary", "complaint_text", "last_action_text", default="")
    text_sim = _text_similarity(text_a, text_b, vectorizer)
    cat_a = _get(case_a, "category", "category_name", "category_id")
    cat_b = _get(case_b, "category", "category_name", "category_id")
    cat_match = float(cat_a is not None and cat_b is not None and str(cat_a).casefold() == str(cat_b).casefold())
    date_a = _date(_get(case_a, "received_on", "created_at", "date"))
    date_b = _date(_get(case_b, "received_on", "created_at", "date"))
    days = abs((date_a - date_b).days) if date_a and date_b else None
    time_proximity = max(0.0, 1.0 - days / 90.0) if days is not None else 0.0
    ref_a = str(_get(case_a, "case_no", "case_id", default="") or "").strip().casefold()
    ref_b = str(_get(case_b, "case_no", "case_id", default="") or "").strip().casefold()
    summary_a, summary_b = _normal_text(text_a), _normal_text(text_b)
    complainant_a = str(_get(case_a, "complainant_ref", default="") or "").strip().casefold()
    complainant_b = str(_get(case_b, "complainant_ref", default="") or "").strip().casefold()
    ref_overlap = bool((ref_a and ref_a in summary_b) or (ref_b and ref_b in summary_a))
    complainant_overlap = bool(complainant_a and complainant_a == complainant_b)
    reference_score = float(ref_overlap or complainant_overlap)
    bureau_a = _get(case_a, "bureau", "bureau_code")
    bureau_b = _get(case_b, "bureau", "bureau_code")
    different_bureau = bureau_a is not None and bureau_b is not None and str(bureau_a) != str(bureau_b)
    score = 0.45 * text_sim + 0.30 * cat_match + 0.15 * time_proximity + 0.10 * reference_score
    reasons = []
    if text_sim >= 0.70: reasons.append("HIGH_TEXT_SIMILARITY")
    if cat_match: reasons.append("SAME_CATEGORY")
    if days is not None and days <= 30: reasons.append("WITHIN_30_DAYS")
    if ref_overlap: reasons.append("SHARED_REFERENCE")
    if complainant_overlap: reasons.append("SHARED_COMPLAINANT_REF")
    if different_bureau: reasons.append("DIFFERENT_BUREAU")
    return {"score": round(float(score), 4), "reasons": reasons, "text_similarity": round(text_sim, 4), "category_match": bool(cat_match), "days_apart": days}


def _open(case):
    status = _get(case, "status", default="")
    status = getattr(status, "value", status)
    return str(status).upper() in OPEN_STATUSES


def detect_overlaps(cases, threshold: float | None = None) -> list[OverlapFlag]:
    """Pure in-memory detector used by tests, CSV evaluation, and demos."""
    if hasattr(cases, "to_dict"):
        records = cases.to_dict(orient="records")
    else:
        records = list(cases)
    required = {"institution_id", "bureau", "status"}
    if records and not required.issubset(records[0].keys() if isinstance(records[0], dict) else set()):
        raise ValueError("cases must include institution_id, bureau, and status")
    threshold = OVERLAP_THRESHOLD if threshold is None else threshold
    flags = []
    by_inst = {}
    for case in records:
        if _open(case) and _get(case, "institution_id") is not None:
            by_inst.setdefault(_get(case, "institution_id"), []).append(case)
    for institution_id, group in by_inst.items():
        bureaus = {str(_get(c, "bureau")) for c in group}
        if len(bureaus) < 2: continue
        flags.append(OverlapFlag(institution_id=institution_id, tier="A", score=1.0, reasons=["DIFFERENT_BUREAU"]))
        vec = build_vectorizer([_get(c, "summary", "complaint_text", default="") for c in group])
        for a, b in combinations(group, 2):
            if str(_get(a, "bureau")) == str(_get(b, "bureau")): continue
            scored = score_pair(a, b, vec)
            if scored["score"] >= threshold:
                flags.append(OverlapFlag(institution_id=institution_id, case_a=_get(a, "id", "case_id", "case_no"), case_b=_get(b, "id", "case_id", "case_no"), tier="B", score=scored["score"], reasons=scored["reasons"]))
    return flags


def _model(db, table_name):
    """Find the mapped class for a table name among the classes exported by app.models."""
    try:
        import app.models as models
    except Exception as exc:                       # pragma: no cover - import problem is a real error
        raise RuntimeError(f"cannot import app.models: {exc}") from exc
    for value in vars(models).values():
        if getattr(value, "__tablename__", None) == table_name:
            return value
    raise RuntimeError(f"SQLAlchemy model for table '{table_name}' was not found in app.models")


def _open_status_filter():
    try:
        from app.models.enums import OPEN_CASE_STATUSES
        return list(OPEN_CASE_STATUSES)
    except Exception:
        return sorted(OPEN_STATUSES)


def _as_utc(value):
    """Normalise date / naive datetime / aware datetime to an aware UTC datetime (or None)."""
    if value is None: return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    return None


def _case_row(case, bureau_codes: dict, category_names: dict) -> dict:
    """Plain dict for score_pair. Built from columns only so relationship objects never leak in."""
    status = getattr(case.status, "value", case.status)
    return {
        "id": case.id, "case_no": case.case_no, "institution_id": case.institution_id,
        "bureau_id": case.bureau_id, "bureau": bureau_codes.get(case.bureau_id, case.bureau_id),
        "category_id": case.category_id, "category": category_names.get(case.category_id, case.category_id),
        "status": status, "summary": case.summary, "received_on": case.received_on,
        "last_action_on": case.last_action_on, "last_action_text": case.last_action_text,
        "complainant_ref": case.complainant_ref,
    }


def _changed_after(case_rows, decided_at) -> bool:
    """True if either case was acted on / received after the flag was decided."""
    decided = _as_utc(decided_at)
    if decided is None: return True
    stamps = [_as_utc(r.get("last_action_on")) or _as_utc(r.get("received_on")) for r in case_rows]
    return any(s is not None and s > decided for s in stamps)


def scan_overlaps(db, institution_id: int | None = None) -> int:
    """Scan open cases and persist overlap_flags. Returns the number of newly inserted flags.

    Tier A: institution has open cases in >= 2 distinct bureaus (one flag per institution).
    Tier B: cross-bureau pair whose score_pair() >= OVERLAP_THRESHOLD.
    A DISMISSED pair is only re-opened if one of its cases was acted on after decided_at.
    The session is rolled back and the error re-raised if anything fails, so the caller
    never receives a half-written scan.
    """
    Case = _model(db, "cases")
    Flag = _model(db, "overlap_flags")
    try: Bureau = _model(db, "bureaus")
    except RuntimeError: Bureau = None
    try: Category = _model(db, "categories")
    except RuntimeError: Category = None

    bureau_codes = {b.id: b.code for b in db.query(Bureau).all()} if Bureau else {}
    category_names = {c.id: c.name for c in db.query(Category).all()} if Category else {}

    q = db.query(Case).filter(Case.status.in_(_open_status_filter()), Case.institution_id.isnot(None))
    if institution_id is not None:
        q = q.filter(Case.institution_id == institution_id)
    by_inst: dict = {}
    for case in q.all():
        by_inst.setdefault(case.institution_id, []).append(_case_row(case, bureau_codes, category_names))

    new_count = 0
    try:
        for inst_id, group in by_inst.items():
            if len({r["bureau_id"] for r in group}) < 2:
                continue

            tier_a = db.query(Flag).filter(Flag.institution_id == inst_id, Flag.case_a.is_(None), Flag.case_b.is_(None)).first()
            if tier_a is None:
                db.add(Flag(institution_id=inst_id, case_a=None, case_b=None, tier="A", score=1.0,
                            reasons=["DIFFERENT_BUREAU"], state="OPEN"))
                new_count += 1

            vec = build_vectorizer([r["summary"] for r in group])
            for a, b in combinations(group, 2):
                if a["bureau_id"] == b["bureau_id"]:
                    continue
                result = score_pair(a, b, vec)
                if result["score"] < OVERLAP_THRESHOLD:
                    continue
                if a["id"] > b["id"]:
                    a, b = b, a
                existing = db.query(Flag).filter(Flag.case_a == a["id"], Flag.case_b == b["id"]).first()
                if existing is None:
                    db.add(Flag(institution_id=inst_id, case_a=a["id"], case_b=b["id"], tier="B",
                                score=result["score"], reasons=result["reasons"], state="OPEN"))
                    new_count += 1
                    continue
                state = getattr(existing.state, "value", existing.state)
                if state == "DISMISSED" and not _changed_after((a, b), existing.decided_at):
                    continue                                   # stays dismissed
                existing.score = result["score"]
                existing.reasons = result["reasons"]
                if state == "DISMISSED":                       # something changed -> re-raise
                    existing.state = "OPEN"
                    existing.decided_by = None
                    existing.decided_at = None
                    new_count += 1
        db.commit()
    except Exception:
        db.rollback()
        raise
    return new_count
