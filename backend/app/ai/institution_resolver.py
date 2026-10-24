"""Institution identity resolution: exact AICTE ID, then normalized fuzzy name."""
from __future__ import annotations
from dataclasses import asdict
import re
import unicodedata
from typing import Any

from rapidfuzz import fuzz, process
from . import ResolveResult

ALIASES = {
    "inst": "institute", "instt": "institute", "engg": "engineering",
    "tech": "technology", "coll": "college", "clg": "college",
    "univ": "university", "uni": "university", "govt": "government",
}
AUTO_MATCH = 0.92
REVIEW_MATCH = 0.75


def normalize_name(value: Any) -> str:
    if value is None:
        return ""
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode().lower()
    text = re.sub(r"\b(inst|instt|engg|tech|coll|clg|univ|uni|govt)\b", lambda m: ALIASES[m.group()], text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _get(obj: Any, *names, default=None):
    for name in names:
        if isinstance(obj, dict) and name in obj:
            return obj[name]
        if hasattr(obj, name):
            return getattr(obj, name)
    return default


def _model(db, table_name: str):
    """Find a mapped SQLAlchemy model by its exact table name."""
    try:
        from sqlalchemy import inspect
        bind = db.get_bind()
        mapper_registry = getattr(db, "registry", None)
        if mapper_registry:
            for mapper in mapper_registry.mappers:
                if mapper.local_table.name == table_name:
                    return mapper.class_
    except Exception:
        pass
    # Common project model exports.
    try:
        import app.models as models
        for value in vars(models).values():
            if getattr(value, "__tablename__", None) == table_name:
                return value
    except Exception:
        pass
    raise RuntimeError(f"SQLAlchemy model for table '{table_name}' was not found")


def _rows(source):
    if hasattr(source, "to_dict") and hasattr(source, "columns"):
        return source.to_dict(orient="records")
    if isinstance(source, (list, tuple)):
        return list(source)
    return list(source)


def resolve_institution(db, name: str | None = None, aicte_id: str | None = None) -> ResolveResult:
    """Resolve against SQLAlchemy DB session or a list/DataFrame for offline use.

    Return contract: ResolveResult(institution_id, confidence, method, candidates, needs_review).
    Scores are in [0, 1]. Fuzzy >= .92 auto-matches; .75-.92 requires review.
    """
    if not (name and str(name).strip()) and not (aicte_id and str(aicte_id).strip()):
        return ResolveResult()

    # Allow DataFrame/list inputs for reproducible offline evaluation and tests.
    if hasattr(db, "columns") or isinstance(db, (list, tuple)):
        records = _rows(db)
    else:
        model = _model(db, "institutions")
        if aicte_id:
            id_col = getattr(model, "aicte_permanent_id", None)
            if id_col is None:
                id_col = getattr(model, "aicte_id", None)
            if id_col is not None:
                exact = db.query(model).filter(id_col == aicte_id).first()
                if exact:
                    return ResolveResult(_get(exact, "id", "institution_id"), 1.0, "EXACT_ID", [{"id": _get(exact, "id", "institution_id"), "name": _get(exact, "name", "institution_name"), "score": 1.0}], False)
        records = db.query(model).all()

    if aicte_id:
        matches = [r for r in records if str(_get(r, "aicte_permanent_id", "aicte_id", default="") or "").strip().casefold() == str(aicte_id).strip().casefold()]
        if len(matches) == 1:
            r = matches[0]
            return ResolveResult(_get(r, "id", "institution_id"), 1.0, "EXACT_ID", [{"id": _get(r, "id", "institution_id"), "name": _get(r, "name", "institution_name"), "score": 1.0}], False)

    query = normalize_name(name)
    if not query:
        return ResolveResult()
    scored = []
    for row in records:
        row_name = _get(row, "name", "institution_name", default="")
        norm = normalize_name(row_name)
        if not norm:
            continue
        score = max(fuzz.ratio(query, norm), fuzz.token_set_ratio(query, norm)) / 100.0
        scored.append((score, row))
    scored.sort(key=lambda item: item[0], reverse=True)
    candidates = []
    seen_ids = set()
    for score, row in scored:
        rid = _get(row, "id", "institution_id")
        if rid in seen_ids:
            continue
        seen_ids.add(rid)
        if score < REVIEW_MATCH and len(candidates) >= 3:
            break
        candidates.append({"id": rid, "name": _get(row, "name", "institution_name"), "score": round(score, 4)})
        if len(candidates) >= 5:
            break
    if not candidates or candidates[0]["score"] < REVIEW_MATCH:
        return ResolveResult(None, candidates[0]["score"] if candidates else 0.0, "NONE", candidates, bool(candidates))
    best = candidates[0]
    tied = len(candidates) > 1 and abs(best["score"] - candidates[1]["score"]) < 0.015
    if best["score"] >= AUTO_MATCH and not tied:
        return ResolveResult(best["id"], best["score"], "FUZZY", candidates, False)
    return ResolveResult(None, best["score"], "FUZZY", candidates, True)
