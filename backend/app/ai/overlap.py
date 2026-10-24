"""Tier A rules and Tier B cross-bureau complaint similarity scoring."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime
from itertools import combinations
import re
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

OPEN_STATUSES = {"PENDING", "UNDER_PROCESS", "ESCALATED", "TRANSFERRED"}
OVERLAP_THRESHOLD = 0.40

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


def _text_similarity(a: str, b: str, vectorizer=None) -> float:
    a, b = _normal_text(a), _normal_text(b)
    if not a or not b: return 0.0
    if a == b: return 1.0
    try:
        word = vectorizer or TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, strip_accents="unicode")
        word_matrix = word.fit_transform([a, b])
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


def _enum_value(value):
    """Return a stable string for SQLAlchemy enum members and plain values."""
    return str(getattr(value, "value", value) or "").upper()


def _open(case):
    return _enum_value(_get(case, "status", default="")) in OPEN_STATUSES


def detect_overlaps(cases, threshold: float = OVERLAP_THRESHOLD) -> list[OverlapFlag]:
    """Pure in-memory detector used by tests, CSV evaluation, and demos."""
    if hasattr(cases, "to_dict"):
        records = cases.to_dict(orient="records")
    else:
        records = list(cases)
    required = {"institution_id", "bureau", "status"}
    if records and not required.issubset(records[0].keys() if isinstance(records[0], dict) else set()):
        raise ValueError("cases must include institution_id, bureau, and status")
    flags = []
    by_inst = {}
    for case in records:
        if _open(case) and _get(case, "institution_id") is not None:
            by_inst.setdefault(_get(case, "institution_id"), []).append(case)
    for institution_id, group in by_inst.items():
        bureaus = {str(_get(c, "bureau")) for c in group}
        if len(bureaus) < 2: continue
        flags.append(OverlapFlag(institution_id=institution_id, tier="A", score=1.0, reasons=["DIFFERENT_BUREAU"]))
        for a, b in combinations(group, 2):
            if str(_get(a, "bureau")) == str(_get(b, "bureau")): continue
            scored = score_pair(a, b)
            if scored["score"] >= threshold:
                flags.append(OverlapFlag(institution_id=institution_id, case_a=_get(a, "id", "case_id", "case_no"), case_b=_get(b, "id", "case_id", "case_no"), tier="B", score=scored["score"], reasons=scored["reasons"]))
    return flags


def _model(db, table_name):
    try:
        import app.models as models
        for value in vars(models).values():
            if getattr(value, "__tablename__", None) == table_name:
                return value
            registry = getattr(value, "registry", None)
            if registry is not None:
                for mapper in registry.mappers:
                    if mapper.local_table.name == table_name:
                        return mapper.class_
    except Exception:
        pass
    raise RuntimeError(f"SQLAlchemy model for table '{table_name}' was not found in app.models")


def _resolve_related(db, case, bureau_models, category_models):
    row = dict(case.__dict__)
    row.pop("_sa_instance_state", None)

    # Store scalar bureau/category labels in the scoring row. SQLAlchemy
    # relationship objects are not present in case.__dict__ under these keys.
    bureau = getattr(case, "bureau", None)
    if bureau is not None:
        row["bureau"] = getattr(bureau, "code", getattr(bureau, "name", None))
    elif case.bureau_id is not None and bureau_models is not None:
        b = db.query(bureau_models).filter(bureau_models.id == case.bureau_id).first()
        if b is not None:
            row["bureau"] = getattr(b, "code", getattr(b, "name", None))

    category = getattr(case, "category", None)
    if category is not None:
        row["category"] = getattr(category, "name", getattr(case, "category_id", None))
    elif case.category_id is not None and category_models is not None:
        c = db.query(category_models).filter(category_models.id == case.category_id).first()
        if c is not None:
            row["category"] = getattr(c, "name", case.category_id)
    return row


def scan_overlaps(db, institution_id: int | None = None) -> int:
    """Scan SQLAlchemy cases and persist overlap_flags. Returns count of newly inserted flags.

    Uses mapped tables named institutions, cases, overlap_flags and optionally bureaus/categories.
    Existing dismissed Tier-B pairs stay dismissed unless summary/status changed after decided_at.
    """
    Case = _model(db, "cases")
    Flag = _model(db, "overlap_flags")
    try: Bureau = _model(db, "bureaus")
    except RuntimeError: Bureau = None
    try: Category = _model(db, "categories")
    except RuntimeError: Category = None
    q = db.query(Case).filter(Case.status.in_(OPEN_STATUSES), Case.institution_id.isnot(None))
    if institution_id is not None: q = q.filter(Case.institution_id == institution_id)
    cases = [_resolve_related(db, c, Bureau, Category) for c in q.all()]
    by_inst = {}
    for c in cases: by_inst.setdefault(c.get("institution_id"), []).append(c)
    new_count = 0
    for inst_id, group in by_inst.items():
        bureaus = {str(c.get("bureau") or c.get("bureau_id")) for c in group}
        if len(bureaus) < 2: continue
        existing_a = db.query(Flag).filter(Flag.institution_id == inst_id, Flag.tier == "A", Flag.case_a.is_(None), Flag.case_b.is_(None)).first()
        if existing_a is None:
            db.add(Flag(institution_id=inst_id, case_a=None, case_b=None, tier="A", score=1.0, reasons=["DIFFERENT_BUREAU"], state="OPEN")); new_count += 1
        for a, b in combinations(group, 2):
            if str(a.get("bureau") or a.get("bureau_id")) == str(b.get("bureau") or b.get("bureau_id")): continue
            result = score_pair(a, b)
            if result["score"] < OVERLAP_THRESHOLD: continue
            aid, bid = a.get("id"), b.get("id")
            if aid is None or bid is None: continue
            if aid > bid: aid, bid = bid, aid; a, b = b, a
            existing = db.query(Flag).filter(Flag.case_a == aid, Flag.case_b == bid).first()
            if existing is not None:
                if getattr(existing, "state", "OPEN") == "DISMISSED":
                    decided_at = getattr(existing, "decided_at", None)
                    changed_a = (a.get("updated_at") or a.get("last_action_on") or a.get("received_on")) if isinstance(a, dict) else (getattr(a, "updated_at", None) or getattr(a, "last_action_on", None) or getattr(a, "received_on", None))
                    changed_b = (b.get("updated_at") or b.get("last_action_on") or b.get("received_on")) if isinstance(b, dict) else (getattr(b, "updated_at", None) or getattr(b, "last_action_on", None) or getattr(b, "received_on", None))
                    changed_at = max(changed_a or datetime.min, changed_b or datetime.min)
                    if decided_at and changed_at and changed_at <= decided_at: continue
                existing.score = result["score"]
                existing.reasons = result["reasons"]
                if getattr(existing, "state", "OPEN") != "CONFIRMED": existing.state = "OPEN"
                continue
            db.add(Flag(institution_id=inst_id, case_a=aid, case_b=bid, tier="B", score=result["score"], reasons=result["reasons"], state="OPEN")); new_count += 1
    db.commit()
    return new_count
