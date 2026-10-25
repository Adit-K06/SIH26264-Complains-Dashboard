"""AI/ML integration contract for SIH26264 backend."""
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class ResolveResult:
    institution_id: Optional[int] = None
    confidence: float = 0.0
    method: str = "NONE"  # EXACT_ID | FUZZY | NONE
    candidates: list = field(default_factory=list)
    needs_review: bool = False

from .institution_resolver import resolve_institution
from .overlap import scan_overlaps, score_pair

__all__ = ["ResolveResult", "resolve_institution", "scan_overlaps", "score_pair"]
