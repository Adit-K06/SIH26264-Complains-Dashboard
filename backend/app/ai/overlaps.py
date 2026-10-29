"""Deterministic Tier A and Tier B overlap detection."""
from __future__ import annotations

import hashlib
import json
import math
import re
import uuid
from collections import Counter
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Case, CaseAction, OverlapFlag
from app.models.enums import ActionType, CaseStatus, OverlapState, OverlapTier

REFERENCE_RE = re.compile(
    r"\b(?:ref(?:erence)?|case(?:\s+no)?|complaint(?:\s+no)?)\s*[:#-]?\s*([A-Z0-9][A-Z0-9/-]{3,})",
    re.IGNORECASE,
)
OPEN_STATUSES = {
    CaseStatus.PENDING.value,
    CaseStatus.UNDER_PROCESS.value,
    CaseStatus.TRANSFERRED.value,
    CaseStatus.ESCALATED.value,
}
_TEXT_THRESHOLD_FOR_REASON = 0.70
_SNAPSHOT_PREFIX = "OVERLAP_SNAPSHOT:"


def _case_status(case: Case) -> str:
    value = case.status
    return value.value if hasattr(value, "value") else str(value)


def _term_counts(text: str, analyzer: str, minimum: int, maximum: int) -> Counter[str]:
    if analyzer == "word":
        tokens = re.findall(r"(?u)\b\w\w+\b", text.lower())
        terms = []
        for width in range(minimum, maximum + 1):
            terms.extend(
                " ".join(tokens[start : start + width])
                for start in range(len(tokens) - width + 1)
            )
        return Counter(terms)

    document = text.lower()
    return Counter(
        document[start : start + width]
        for width in range(minimum, maximum + 1)
        for start in range(len(document) - width + 1)
    )


def _tfidf_cosine(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0
    vocabulary = left.keys() | right.keys()
    left_vector: dict[str, float] = {}
    right_vector: dict[str, float] = {}
    for term in vocabulary:
        document_frequency = int(term in left) + int(term in right)
        inverse_document_frequency = math.log(3.0 / (1.0 + document_frequency)) + 1.0
        if term in left:
            left_vector[term] = left[term] * inverse_document_frequency
        if term in right:
            right_vector[term] = right[term] * inverse_document_frequency
    dot = sum(left_vector[term] * right_vector.get(term, 0.0) for term in left_vector)
    left_norm = math.sqrt(sum(weight * weight for weight in left_vector.values()))
    right_norm = math.sqrt(sum(weight * weight for weight in right_vector.values()))
    return dot / (left_norm * right_norm) if left_norm and right_norm else 0.0


def _text_similarity(left: str, right: str) -> float:
    """Average pairwise TF-IDF cosine for word 1-2 grams and char 3-5 grams."""
    documents = [left, right]
    if not documents[0].strip() or not documents[1].strip():
        return 0.0
    similarities = []
    for analyzer, ngram_range in (("word", (1, 2)), ("char", (3, 5))):
        left_terms = _term_counts(documents[0], analyzer, *ngram_range)
        right_terms = _term_counts(documents[1], analyzer, *ngram_range)
        similarities.append(_tfidf_cosine(left_terms, right_terms))
    return sum(similarities) / len(similarities)

def _references(case: Case) -> set[str]:
    return {match.group(1).casefold() for match in REFERENCE_RE.finditer(case.summary or "")}


def score_pair(case_a: Case, case_b: Case) -> tuple[float, list[str]]:
    """Return the configured weighted score and reason codes for a case pair."""
    text_sim = _text_similarity(case_a.summary or "", case_b.summary or "")
    category_match = float(case_a.category_id == case_b.category_id)
    days_apart = abs((case_a.received_on - case_b.received_on).days)
    time_proximity = max(0.0, 1.0 - days_apart / 90.0)
    shared_reference = bool(_references(case_a) & _references(case_b))
    shared_complainant = bool(
        case_a.complainant_ref
        and case_b.complainant_ref
        and case_a.complainant_ref.strip().casefold()
        == case_b.complainant_ref.strip().casefold()
    )
    ref_overlap = float(shared_reference or shared_complainant)
    score = (
        0.45 * text_sim
        + 0.30 * category_match
        + 0.15 * time_proximity
        + 0.10 * ref_overlap
    )

    reasons: list[str] = []
    if text_sim >= _TEXT_THRESHOLD_FOR_REASON:
        reasons.append("HIGH_TEXT_SIMILARITY")
    if category_match:
        reasons.append("SAME_CATEGORY")
    if days_apart <= 30:
        reasons.append("WITHIN_30_DAYS")
    if shared_reference:
        reasons.append("SHARED_REFERENCE")
    if shared_complainant:
        reasons.append("SHARED_COMPLAINANT_REF")
    if case_a.bureau_id != case_b.bureau_id:
        reasons.append("DIFFERENT_BUREAU")
    return score, reasons


def _snapshot_signature(cases: list[Case]) -> str:
    values = sorted(
        (
            str(case.id),
            _case_status(case),
            case.summary or "",
        )
        for case in cases
    )
    payload = json.dumps(values, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _recorded_snapshot(db: Session, flag_id: uuid.UUID) -> str | None:
    prefix = f"{_SNAPSHOT_PREFIX}{flag_id}:"
    action = db.scalar(
        select(CaseAction)
        .where(CaseAction.remarks.startswith(prefix))
        .order_by(CaseAction.created_at.desc(), CaseAction.id.desc())
        .limit(1)
    )
    if action is None or not action.remarks:
        return None
    return action.remarks.rsplit(":", 1)[-1]


def _changed_since_dismissal(db: Session, flag: OverlapFlag, current_signature: str) -> bool:
    if flag.decided_at is None:
        return True
    recorded = _recorded_snapshot(db, flag.id)
    if recorded is not None:
        return recorded != current_signature

    case_ids = [case_id for case_id in (flag.case_a, flag.case_b) if case_id is not None]
    if not case_ids:
        return False
    changed_action = db.scalar(
        select(CaseAction.id)
        .where(
            CaseAction.case_id.in_(case_ids),
            CaseAction.created_at > flag.decided_at,
            CaseAction.from_status.is_not(None),
            CaseAction.to_status.is_not(None),
            CaseAction.from_status != CaseAction.to_status,
        )
        .limit(1)
    )
    return changed_action is not None


def _threshold() -> float:
    evaluation_path = Path(__file__).resolve().parents[3] / "docs" / "evaluation.json"
    try:
        data = json.loads(evaluation_path.read_text(encoding="utf-8"))
        threshold = float(data["selected_threshold"])
        if 0.0 <= threshold <= 1.0:
            return threshold
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        pass
    return float(settings.OVERLAP_THRESHOLD)


def _pair_key(case_a: Case, case_b: Case) -> tuple[str, str]:
    return tuple(sorted((str(case_a.id), str(case_b.id))))


def scan_overlaps(db: Session, institution_id: uuid.UUID | None = None) -> dict[str, int]:
    """Scan open cases, maintaining one institution flag and pair flag per match."""
    statement = select(Case).where(Case.institution_id.is_not(None))
    if institution_id is not None:
        statement = statement.where(Case.institution_id == institution_id)
    cases = db.scalars(statement.order_by(Case.institution_id, Case.id)).all()
    grouped: dict[uuid.UUID, list[Case]] = {}
    for case in cases:
        if _case_status(case) in OPEN_STATUSES and case.institution_id is not None:
            grouped.setdefault(case.institution_id, []).append(case)

    created_a = created_b = reopened = checked_pairs = 0
    threshold = _threshold()
    for current_institution_id, institution_cases in grouped.items():
        bureau_ids = {case.bureau_id for case in institution_cases}
        tier_a = db.scalar(
            select(OverlapFlag)
            .where(
                OverlapFlag.institution_id == current_institution_id,
                OverlapFlag.tier == OverlapTier.A.value,
            )
            .order_by(OverlapFlag.created_at.desc())
            .limit(1)
        )
        if len(bureau_ids) >= 2:
            signature = _snapshot_signature(institution_cases)
            if tier_a is None:
                db.add(
                    OverlapFlag(
                        id=uuid.uuid4(),
                        institution_id=current_institution_id,
                        case_a=None,
                        case_b=None,
                        tier=OverlapTier.A.value,
                        score=None,
                        reasons=["DIFFERENT_BUREAU"],
                        state=OverlapState.OPEN.value,
                    )
                )
                created_a += 1
            elif tier_a.state == OverlapState.DISMISSED.value:
                if _changed_since_dismissal(db, tier_a, signature):
                    tier_a.state = OverlapState.OPEN.value
                    tier_a.decided_at = None
                    tier_a.decided_by = None
                    tier_a.reasons = ["DIFFERENT_BUREAU"]
                    reopened += 1

        pair_flags = db.scalars(
            select(OverlapFlag).where(
                OverlapFlag.institution_id == current_institution_id,
                OverlapFlag.tier == OverlapTier.B.value,
            )
        ).all()
        flag_by_pair = {
            tuple(sorted((str(flag.case_a), str(flag.case_b)))): flag
            for flag in pair_flags
            if flag.case_a is not None and flag.case_b is not None
        }

        for case_a, case_b in combinations(institution_cases, 2):
            if case_a.bureau_id == case_b.bureau_id:
                continue
            checked_pairs += 1
            score, reasons = score_pair(case_a, case_b)
            key = _pair_key(case_a, case_b)
            flag = flag_by_pair.get(key)
            if score < threshold:
                continue
            if flag is not None and flag.state == OverlapState.CONFIRMED.value:
                continue
            signature = _snapshot_signature([case_a, case_b])
            if flag is not None and flag.state == OverlapState.DISMISSED.value:
                if not _changed_since_dismissal(db, flag, signature):
                    continue
                flag.state = OverlapState.OPEN.value
                flag.decided_at = None
                flag.decided_by = None
                reopened += 1
            if flag is None:
                flag = OverlapFlag(
                    id=uuid.uuid4(),
                    institution_id=current_institution_id,
                    case_a=case_a.id,
                    case_b=case_b.id,
                    tier=OverlapTier.B.value,
                    score=score,
                    reasons=reasons,
                    state=OverlapState.OPEN.value,
                )
                db.add(flag)
                flag_by_pair[key] = flag
                created_b += 1
            else:
                flag.score = score
                flag.reasons = reasons

    db.flush()
    return {
        "tier_a_created": created_a,
        "tier_b_created": created_b,
        "reopened": reopened,
        "pairs_checked": checked_pairs,
    }


def dismiss_flag(db: Session, flag: OverlapFlag, actor: Any) -> None:
    """Dismiss a flag and append a summary/status snapshot for future suppression."""
    if flag.state == OverlapState.DISMISSED.value:
        return
    if flag.tier == OverlapTier.B.value:
        cases = [
            case
            for case_id in (flag.case_a, flag.case_b)
            if case_id is not None
            for case in [db.get(Case, case_id)]
            if case is not None
        ]
    else:
        cases = db.scalars(
            select(Case).where(
                Case.institution_id == flag.institution_id,
                Case.status != CaseStatus.DISPOSED.value,
            )
        ).all()
    if cases:
        representative = sorted(cases, key=lambda case: str(case.id))[0]
        signature = _snapshot_signature(cases)
        now = datetime.now(timezone.utc)
        db.add(
            CaseAction(
                case_id=representative.id,
                actor_id=actor.id,
                bureau_id=representative.bureau_id,
                action_type=ActionType.NOTE.value,
                from_status=_case_status(representative),
                to_status=_case_status(representative),
                remarks=f"{_SNAPSHOT_PREFIX}{flag.id}:{signature}",
                created_at=now,
            )
        )
    flag.state = OverlapState.DISMISSED.value
    flag.decided_by = actor.id
    flag.decided_at = datetime.now(timezone.utc)
