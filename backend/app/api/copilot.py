"""AICTE Copilot / Natural Language Assistant endpoint."""
from __future__ import annotations

import re
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Bureau, Case, Category, Institution, OverlapFlag, Region, User
from app.models.enums import CaseStatus, OverlapTier
from app.security import get_current_user

router = APIRouter()


class CopilotQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)


class CopilotAction(BaseModel):
    label: str
    link: str


class CopilotItem(BaseModel):
    id: str
    title: str
    subtitle: str | None = None
    status: str | None = None
    link: str


class CopilotResponse(BaseModel):
    query: str
    intent: str
    answer: str
    highlight: str | None = None
    items: list[CopilotItem] = Field(default_factory=list)
    action: CopilotAction | None = None
    suggestions: list[str] = Field(default_factory=list)


def _clean(text: str) -> str:
    return text.lower().strip()


@router.post("/copilot/query", response_model=CopilotResponse)
def handle_copilot_query(
    payload: CopilotQueryRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> CopilotResponse:
    q = _clean(payload.query)

    # 1. Overlaps & Coordination
    if any(k in q for k in ["overlap", "coordination", "conflict", "parallel", "tier a", "tier b", "rb and pgrc", "rb vs pgrc"]):
        flags = db.scalars(
            select(OverlapFlag)
            .where(OverlapFlag.state == "OPEN")
            .order_by(OverlapFlag.tier, OverlapFlag.score.desc().nullslast())
            .limit(5)
        ).all()
        tier_a_count = db.scalar(select(func.count()).select_from(OverlapFlag).where(OverlapFlag.tier == "A", OverlapFlag.state == "OPEN")) or 0
        tier_b_count = db.scalar(select(func.count()).select_from(OverlapFlag).where(OverlapFlag.tier == "B", OverlapFlag.state == "OPEN")) or 0
        
        items = []
        for f in flags:
            inst = db.get(Institution, f.institution_id)
            inst_name = inst.name if inst else "Unknown Institution"
            items.append(CopilotItem(
                id=str(f.id),
                title=f"Tier {f.tier}: {inst_name}",
                subtitle=f"Reasons: {', '.join(f.reasons)} · State: {f.state}",
                status=f"Tier {f.tier}",
                link="/overlaps",
            ))

        return CopilotResponse(
            query=payload.query,
            intent="OVERLAPS",
            answer=(
                f"There are currently {tier_a_count} campus-level coordination flags (Tier A) where multiple bureaus "
                f"handle open cases simultaneously, and {tier_b_count} potential case pair overlaps (Tier B) identified by "
                f"the cross-bureau matching engine."
            ),
            highlight=f"{tier_a_count + tier_b_count} Active Overlaps",
            items=items,
            action=CopilotAction(label="Open Overlap Center", link="/overlaps"),
            suggestions=[
                "Which institutions have Tier A overlap?",
                "Show overdue cases",
                "Workload breakdown by bureau",
            ],
        )

    # 2. Overdue / Beyond SLA
    if any(k in q for k in ["overdue", "beyond sla", "sla", "delayed", "late", "timeline", "past due"]):
        overdue_cases = db.scalars(
            select(Case)
            .where(
                Case.status != CaseStatus.DISPOSED.value,
                Case.expected_disposal_on.is_not(None),
                Case.expected_disposal_on < func.current_date(),
            )
            .order_by(Case.expected_disposal_on.asc())
            .limit(5)
        ).all()
        total_overdue = db.scalar(
            select(func.count())
            .select_from(Case)
            .where(
                Case.status != CaseStatus.DISPOSED.value,
                Case.expected_disposal_on.is_not(None),
                Case.expected_disposal_on < func.current_date(),
            )
        ) or 0

        items = []
        for c in overdue_cases:
            bureau = db.get(Bureau, c.bureau_id)
            inst = db.get(Institution, c.institution_id) if c.institution_id else None
            items.append(CopilotItem(
                id=str(c.id),
                title=f"{c.case_no} · {inst.name if inst else 'Unresolved Institution'}",
                subtitle=f"Bureau: {bureau.code if bureau else '—'} | Due: {c.expected_disposal_on.isoformat() if c.expected_disposal_on else '—'}",
                status=c.status,
                link=f"/cases/{c.id}",
            ))

        return CopilotResponse(
            query=payload.query,
            intent="OVERDUE_CASES",
            answer=(
                f"Found {total_overdue} open cases currently exceeding their prescribed SLA resolution timelines. "
                f"Immediate review or escalation is recommended."
            ),
            highlight=f"{total_overdue} Beyond SLA",
            items=items,
            action=CopilotAction(label="View All Overdue Cases", link="/cases?beyond_sla=true"),
            suggestions=[
                "Show escalated cases",
                "Active RB vs PGRC overlaps",
                "Summary of North region",
            ],
        )

    # 3. Status checks: Pending, Under Process, Escalated, Disposed
    status_match = None
    if "pending" in q:
        status_match = CaseStatus.PENDING.value
    elif "under process" in q or "investigation" in q:
        status_match = CaseStatus.UNDER_PROCESS.value
    elif "escalat" in q:
        status_match = CaseStatus.ESCALATED.value
    elif "disposed" in q or "closed" in q or "resolved" in q:
        status_match = CaseStatus.DISPOSED.value
    elif "transfer" in q:
        status_match = CaseStatus.TRANSFERRED.value

    if status_match:
        matched_cases = db.scalars(
            select(Case)
            .where(Case.status == status_match)
            .order_by(Case.received_on.desc())
            .limit(5)
        ).all()
        count = db.scalar(select(func.count()).select_from(Case).where(Case.status == status_match)) or 0
        items = []
        for c in matched_cases:
            bureau = db.get(Bureau, c.bureau_id)
            inst = db.get(Institution, c.institution_id) if c.institution_id else None
            items.append(CopilotItem(
                id=str(c.id),
                title=f"{c.case_no} · {inst.name if inst else 'Unresolved Institution'}",
                subtitle=f"{bureau.code if bureau else '—'} · Received: {c.received_on.isoformat()}",
                status=c.status,
                link=f"/cases/{c.id}",
            ))

        return CopilotResponse(
            query=payload.query,
            intent="STATUS_QUERY",
            answer=f"There are currently {count} cases in '{status_match}' status across all AICTE bureaus.",
            highlight=f"{count} Cases in {status_match}",
            items=items,
            action=CopilotAction(label=f"Filter {status_match} Cases", link=f"/cases?status={status_match}"),
            suggestions=[
                "Show overdue cases",
                "Workload breakdown by bureau",
                "Review open overlaps",
            ],
        )

    # 4. Bureau Specific Workload
    bureau = None
    if "rb" in q or "regulation" in q:
        bureau = db.scalar(select(Bureau).where(Bureau.code == "RB"))
    elif "pgrc" in q or "grievance" in q:
        bureau = db.scalar(select(Bureau).where(Bureau.code == "PGRC"))
    elif "approval" in q:
        bureau = db.scalar(select(Bureau).where(Bureau.code == "APPROVAL"))
    elif "academic" in q:
        bureau = db.scalar(select(Bureau).where(Bureau.code == "ACADEMIC"))
    elif "finance" in q:
        bureau = db.scalar(select(Bureau).where(Bureau.code == "FINANCE"))

    if bureau:
        b_cases = db.scalars(select(Case).where(Case.bureau_id == bureau.id).order_by(Case.received_on.desc()).limit(5)).all()
        b_total = db.scalar(select(func.count()).select_from(Case).where(Case.bureau_id == bureau.id)) or 0
        b_open = db.scalar(select(func.count()).select_from(Case).where(Case.bureau_id == bureau.id, Case.status != "DISPOSED")) or 0
        
        items = []
        for c in b_cases:
            inst = db.get(Institution, c.institution_id) if c.institution_id else None
            items.append(CopilotItem(
                id=str(c.id),
                title=f"{c.case_no} · {inst.name if inst else 'Institution'}",
                subtitle=f"Status: {c.status} · Priority: {c.priority}",
                status=c.status,
                link=f"/cases/{c.id}",
            ))

        return CopilotResponse(
            query=payload.query,
            intent="BUREAU_WORKLOAD",
            answer=(
                f"{bureau.name} ({bureau.code}) currently has {b_total} total recorded cases, of which "
                f"{b_open} are active and pending resolution."
            ),
            highlight=f"{bureau.code}: {b_open} Open / {b_total} Total",
            items=items,
            action=CopilotAction(label=f"View {bureau.code} Cases", link=f"/cases?bureau_id={bureau.id}"),
            suggestions=[
                "Compare with PGRC workload",
                "Show RB vs PGRC overlaps",
                "Check Beyond SLA cases",
            ],
        )

    # 5. Institution Lookup
    inst_match = None
    id_match = re.search(r"syn-\d{5}", q, re.IGNORECASE)
    if id_match:
        inst_match = db.scalar(select(Institution).where(Institution.aicte_permanent_id == id_match.group(0).upper()))
    else:
        # Search institution by name keyword
        for word in q.split():
            if len(word) >= 4 and word not in ["show", "cases", "about", "what", "find", "list", "complaints"]:
                inst_match = db.scalar(select(Institution).where(Institution.name.ilike(f"%{word}%")))
                if inst_match:
                    break

    if inst_match:
        inst_cases = db.scalars(select(Case).where(Case.institution_id == inst_match.id).order_by(Case.received_on.desc()).limit(6)).all()
        c_count = len(inst_cases)
        items = []
        for c in inst_cases:
            bureau = db.get(Bureau, c.bureau_id)
            items.append(CopilotItem(
                id=str(c.id),
                title=f"{c.case_no} ({bureau.code if bureau else '—'})",
                subtitle=c.summary[:90] + "..." if c.summary and len(c.summary) > 90 else c.summary,
                status=c.status,
                link=f"/cases/{c.id}",
            ))

        return CopilotResponse(
            query=payload.query,
            intent="INSTITUTION_PROFILE",
            answer=(
                f"Found profile for '{inst_match.name}' ({inst_match.aicte_permanent_id}) located in {inst_match.state}. "
                f"There are {c_count} complaints recorded across bureaus for this campus."
            ),
            highlight=f"{inst_match.aicte_permanent_id} · {inst_match.name}",
            items=items,
            action=CopilotAction(label="Open Campus Profile", link=f"/institutions/{inst_match.id}"),
            suggestions=[
                "Check overlaps for this campus",
                "Show overdue cases",
                "List all institutions",
            ],
        )

    # 6. Topic or Keyword Search (e.g., Scholarship, Fee, Faculty, Exam)
    topic_keywords = ["scholarship", "fee", "admission", "exam", "faculty", "hostel", "laboratory", "ragging", "harassment"]
    matched_topic = next((t for t in topic_keywords if t in q), None)
    if matched_topic:
        cases = db.scalars(
            select(Case)
            .where(Case.summary.ilike(f"%{matched_topic}%"))
            .order_by(Case.received_on.desc())
            .limit(5)
        ).all()
        count = db.scalar(select(func.count()).select_from(Case).where(Case.summary.ilike(f"%{matched_topic}%"))) or 0
        items = []
        for c in cases:
            bureau = db.get(Bureau, c.bureau_id)
            inst = db.get(Institution, c.institution_id) if c.institution_id else None
            items.append(CopilotItem(
                id=str(c.id),
                title=f"{c.case_no} · {inst.name if inst else 'Campus'}",
                subtitle=f"{bureau.code if bureau else '—'} | {c.summary[:80]}...",
                status=c.status,
                link=f"/cases/{c.id}",
            ))

        return CopilotResponse(
            query=payload.query,
            intent="TOPIC_SEARCH",
            answer=f"Found {count} complaints mentioning '{matched_topic}' across all bureaus and institutions.",
            highlight=f"{count} Cases mentioning '{matched_topic}'",
            items=items,
            action=CopilotAction(label=f"Search '{matched_topic}' Cases", link=f"/cases?q={matched_topic}"),
            suggestions=[
                "Active RB vs PGRC overlaps",
                "Show cases beyond SLA",
                "Open Dashboard summary",
            ],
        )

    # 7. Default Executive Summary / Help Response
    total_cases = db.scalar(select(func.count()).select_from(Case)) or 0
    open_cases = db.scalar(select(func.count()).select_from(Case).where(Case.status != "DISPOSED")) or 0
    open_overlaps = db.scalar(select(func.count()).select_from(OverlapFlag).where(OverlapFlag.state == "OPEN")) or 0
    
    return CopilotResponse(
        query=payload.query,
        intent="GENERAL_ASSISTANT",
        answer=(
            f"The AICTE Complaint Coordination system currently monitors {total_cases} total cases "
            f"({open_cases} active) across 40 technical institutions and 5 bureaus. There are {open_overlaps} "
            f"open overlap alerts requiring inter-bureau coordination."
        ),
        highlight=f"{open_cases} Active Cases · {open_overlaps} Overlap Flags",
        items=[],
        action=CopilotAction(label="Go to Dashboard", link="/dashboard"),
        suggestions=[
            "Show overdue cases beyond SLA",
            "Active RB vs PGRC overlaps",
            "Regulation Bureau workload",
            "Complaints for Synthetic Aster Institute",
            "Find scholarship delay issues",
        ],
    )

