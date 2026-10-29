"""Institution name resolution for synthetic case imports."""
from __future__ import annotations

import re
from typing import Any

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Institution

ABBREVIATIONS = {
    "inst": "institute",
    "engg": "engineering",
    "tech": "technology",
    "coll": "college",
    "univ": "university",
}
_WORD_RE = re.compile(r"[a-z0-9]+")


def normalize_institution_name(value: str) -> str:
    words = _WORD_RE.findall(value.casefold())
    return " ".join(ABBREVIATIONS.get(word, word) for word in words)


def resolve_institution(
    db: Session,
    *,
    aicte_id: str | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    """Resolve by exact AICTE ID first, otherwise use normalized token-set ratio."""
    if aicte_id:
        exact = db.scalar(
            select(Institution).where(Institution.aicte_permanent_id == aicte_id.strip())
        )
        if exact is not None:
            return {
                "status": "AUTO_MATCH",
                "institution_id": exact.id,
                "institution": exact,
                "score": 1.0,
                "match_type": "exact_aicte_id",
            }

    if not name or not name.strip():
        return {
            "status": "UNRESOLVED",
            "institution_id": None,
            "institution": None,
            "score": 0.0,
            "match_type": None,
        }

    normalized_query = normalize_institution_name(name)
    candidates = db.scalars(select(Institution).order_by(Institution.aicte_permanent_id)).all()
    scored = [
        (
            fuzz.token_set_ratio(normalized_query, normalize_institution_name(candidate.name)) / 100.0,
            candidate,
        )
        for candidate in candidates
    ]
    if not scored:
        return {
            "status": "UNRESOLVED",
            "institution_id": None,
            "institution": None,
            "score": 0.0,
            "match_type": None,
        }

    score, institution = max(scored, key=lambda item: (item[0], item[1].aicte_permanent_id))
    if score >= 0.92:
        status = "AUTO_MATCH"
    elif score >= 0.75:
        status = "NEEDS_REVIEW"
    else:
        status = "UNRESOLVED"
    return {
        "status": status,
        "institution_id": institution.id if status != "UNRESOLVED" else None,
        "institution": institution if status != "UNRESOLVED" else None,
        "score": score,
        "match_type": "fuzzy",
    }