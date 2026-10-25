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


def _db_institution_model(db):
    from .overlap import _model          # single place that maps table name -> class
    return _model(db, "institutions")


def _rows(source):
    if hasattr(source, "to_dict") and hasattr(source, "columns"):
        return source.to_dict(orient="records")
    return list(source)


def _digits(norm: str) -> set[str]:
    return {t for t in norm.split() if t.isdigit()}


def _cand(row, score):
    return {"id": _get(row, "id", "institution_id"), "name": _get(row, "name", "institution_name"), "score": round(score, 4)}


def resolve_institution(db, name: str | None = None, aicte_id: str | None = None) -> ResolveResult:
    """Resolve against a SQLAlchemy session, or a list/DataFrame of dicts for offline use.

    Order: exact AICTE permanent ID -> normalised fuzzy name.
    Fuzzy >= 0.92 (and not tied) auto-matches; 0.75-0.92 or ties need human review; below 0.75 no match.
    Names that differ in a numeric token ("... 1" vs "... 11") are never auto-matched.
    """
    has_name = bool(name and str(name).strip())
    has_id = bool(aicte_id and str(aicte_id).strip())
    if not has_name and not has_id:
        return ResolveResult()

    offline = hasattr(db, "columns") or isinstance(db, (list, tuple))
    model = None
    records = None
    if offline:
        records = _rows(db)
    else:
        model = _db_institution_model(db)
        if has_id:
            exact = db.query(model).filter(model.aicte_permanent_id == str(aicte_id).strip()).first()
            if exact is not None:
                return ResolveResult(exact.id, 1.0, "EXACT_ID", [_cand(exact, 1.0)], False)
        if not has_name:
            return ResolveResult()
        records = db.query(model).all()

    if has_id and offline:
        wanted = str(aicte_id).strip().casefold()
        hits = [r for r in records if str(_get(r, "aicte_permanent_id", "aicte_id", default="") or "").strip().casefold() == wanted]
        if len(hits) == 1:
            return ResolveResult(_get(hits[0], "id", "institution_id"), 1.0, "EXACT_ID", [_cand(hits[0], 1.0)], False)

    query = normalize_name(name) if has_name else ""
    if not query:
        return ResolveResult()
    norm_names = [normalize_name(_get(r, "name", "institution_name", default="")) for r in records]
    best_by_idx: dict[int, float] = {}
    for scorer in (fuzz.ratio, fuzz.token_set_ratio):
        for _choice, score, idx in process.extract(query, norm_names, scorer=scorer, limit=10):
            if norm_names[idx]:
                best_by_idx[idx] = max(best_by_idx.get(idx, 0.0), score / 100.0)
    qdigits = _digits(query)
    ranked = []
    for idx, score in best_by_idx.items():
        cdigits = _digits(norm_names[idx])
        if qdigits and cdigits and qdigits != cdigits:
            score = min(score, AUTO_MATCH - 0.01)          # number mismatch -> human review at best
        ranked.append((score, idx))
    ranked.sort(key=lambda t: (-t[0], t[1]))

    candidates, seen = [], set()
    for score, idx in ranked:
        rid = _get(records[idx], "id", "institution_id")
        if rid in seen:
            continue
        seen.add(rid)
        candidates.append(_cand(records[idx], score))
        if len(candidates) >= 5:
            break
    if not candidates:
        return ResolveResult()
    best = candidates[0]
    if best["score"] < REVIEW_MATCH:
        # nothing close enough to suggest; keep candidates for the UI but do not flag as needing review
        return ResolveResult(None, best["score"], "NONE", candidates[:3], False)
    tied = len(candidates) > 1 and abs(best["score"] - candidates[1]["score"]) < 0.015
    if best["score"] >= AUTO_MATCH and not tied:
        return ResolveResult(best["id"], best["score"], "FUZZY", candidates, False)
    return ResolveResult(None, best["score"], "FUZZY", candidates, True)
