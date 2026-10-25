"""SLA Monitoring API router.

Endpoints:
  GET /sla/overview – aggregated SLA compliance and status breakdown
  GET /sla/cases    – paginated open-case SLA tracking with computed status

Role and scoping:
  - ADMIN, SENIOR_MGMT: see across all bureaus and regions.
  - BUREAU_OFFICER: restricted to own bureau cases.
  - REGIONAL_OFFICER: restricted to cases for institutions in own region.
"""
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Bureau, Case, Category, Institution, Region, SlaRule, User
from app.models.enums import CaseStatusEnum, OPEN_CASE_STATUSES, PriorityEnum, RoleEnum

router = APIRouter(prefix="/sla", tags=["sla"])

_DEFAULT_SLA_DAYS: dict[PriorityEnum, int] = {
    PriorityEnum.HIGH: 15,
    PriorityEnum.MEDIUM: 30,
    PriorityEnum.LOW: 45,
}


def get_sla_rule_for_case(db: Session, category_id: Optional[int], priority: PriorityEnum) -> Optional[SlaRule]:
    """Find specific or default SlaRule for given category and priority."""
    rule = None
    if category_id:
        rule = db.query(SlaRule).filter(
            SlaRule.category_id == category_id,
            SlaRule.priority == priority,
        ).first()
    if rule is None:
        rule = db.query(SlaRule).filter(
            SlaRule.category_id.is_(None),
            SlaRule.priority == priority,
        ).first()
    return rule


class SlaCaseItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_no: str
    bureau_id: int
    bureau_code: Optional[str] = None
    institution_id: Optional[int] = None
    institution_name: Optional[str] = None
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    status: CaseStatusEnum
    priority: PriorityEnum
    received_on: date
    expected_disposal_on: Optional[date] = None
    days_elapsed: int
    days_remaining: Optional[int] = None
    sla_status: str  # "WITHIN_SLA", "DUE_SOON", "OVERDUE"
    is_beyond_sla: bool


class SlaCasesList(BaseModel):
    items: list[SlaCaseItem]
    total: int
    page: int
    page_size: int


class BureauSlaBreakdown(BaseModel):
    bureau_id: int
    bureau_code: str
    total_open: int
    within_sla: int
    due_soon: int
    overdue: int
    compliance_rate_pct: float


class SlaOverview(BaseModel):
    total_open_cases: int
    within_sla_count: int
    due_soon_count: int
    overdue_count: int
    compliance_rate_pct: float
    by_bureau: list[BureauSlaBreakdown]


def _apply_case_scoping(query, user: User):
    """Enforce RBAC scoping for case queries."""
    if user.role == RoleEnum.BUREAU_OFFICER:
        query = query.filter(Case.bureau_id == user.bureau_id)
    elif user.role == RoleEnum.REGIONAL_OFFICER:
        query = query.join(Institution, Case.institution_id == Institution.id).filter(
            Institution.region_id == user.region_id
        )
    return query


@router.get("/overview", response_model=SlaOverview)
def get_sla_overview(
    bureau_id: Optional[int] = Query(None),
    region_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get high-level SLA compliance and open case status breakdown."""
    today = date.today()

    query = db.query(Case).filter(Case.status.in_(OPEN_CASE_STATUSES))
    query = _apply_case_scoping(query, current_user)

    if bureau_id is not None:
        if current_user.role == RoleEnum.BUREAU_OFFICER and bureau_id != current_user.bureau_id:
            # scoped query will return 0 if they try to filter on another bureau
            query = query.filter(Case.bureau_id == bureau_id)
        else:
            query = query.filter(Case.bureau_id == bureau_id)

    if region_id is not None:
        if current_user.role != RoleEnum.REGIONAL_OFFICER:
            query = query.join(Institution, Case.institution_id == Institution.id).filter(
                Institution.region_id == region_id
            )

    open_cases = query.all()

    # Pre-load SlaRules for due-soon calculation
    rules = db.query(SlaRule).all()
    rule_map: dict[tuple[Optional[int], PriorityEnum], SlaRule] = {
        (r.category_id, r.priority): r for r in rules
    }

    within_sla = 0
    due_soon = 0
    overdue = 0

    # Group by bureau for breakdown
    bureau_stats: dict[int, dict[str, int]] = {}

    for c in open_cases:
        b_id = c.bureau_id
        if b_id not in bureau_stats:
            bureau_stats[b_id] = {"total": 0, "within": 0, "due_soon": 0, "overdue": 0}
        bureau_stats[b_id]["total"] += 1

        # Check overdue
        if c.expected_disposal_on and c.expected_disposal_on < today:
            overdue += 1
            bureau_stats[b_id]["overdue"] += 1
        else:
            # Check due soon
            rule = rule_map.get((c.category_id, c.priority)) or rule_map.get((None, c.priority))
            warn_pct = rule.warn_at_pct if rule else 80
            total_days = (
                (c.expected_disposal_on - c.received_on).days
                if (c.expected_disposal_on and c.expected_disposal_on > c.received_on)
                else _DEFAULT_SLA_DAYS.get(c.priority, 30)
            )
            elapsed_days = (today - c.received_on).days
            days_remaining = (c.expected_disposal_on - today).days if c.expected_disposal_on else (total_days - elapsed_days)

            is_due_soon = False
            if total_days > 0 and (elapsed_days / total_days * 100 >= warn_pct or days_remaining <= 3):
                is_due_soon = True

            if is_due_soon:
                due_soon += 1
                bureau_stats[b_id]["due_soon"] += 1
            else:
                within_sla += 1
                bureau_stats[b_id]["within"] += 1

    total_open = len(open_cases)
    compliance_rate = round(((total_open - overdue) / total_open * 100), 1) if total_open > 0 else 100.0

    # Fetch bureaus to label breakdown
    bureaus = db.query(Bureau).order_by(Bureau.id.asc()).all()
    bureau_lookup = {b.id: b.code for b in bureaus}

    by_bureau_list: list[BureauSlaBreakdown] = []
    # If user is bureau officer, show their bureau; otherwise show all active bureaus
    allowed_bureau_ids = [current_user.bureau_id] if current_user.role == RoleEnum.BUREAU_OFFICER else list(bureau_lookup.keys())
    for b_id in allowed_bureau_ids:
        if b_id in bureau_lookup:
            stats = bureau_stats.get(b_id, {"total": 0, "within": 0, "due_soon": 0, "overdue": 0})
            b_total = stats["total"]
            b_comp = round(((b_total - stats["overdue"]) / b_total * 100), 1) if b_total > 0 else 100.0
            by_bureau_list.append(
                BureauSlaBreakdown(
                    bureau_id=b_id,
                    bureau_code=bureau_lookup[b_id],
                    total_open=b_total,
                    within_sla=stats["within"],
                    due_soon=stats["due_soon"],
                    overdue=stats["overdue"],
                    compliance_rate_pct=b_comp,
                )
            )

    return SlaOverview(
        total_open_cases=total_open,
        within_sla_count=within_sla,
        due_soon_count=due_soon,
        overdue_count=overdue,
        compliance_rate_pct=compliance_rate,
        by_bureau=by_bureau_list,
    )


@router.get("/cases", response_model=SlaCasesList)
def get_sla_cases(
    status: Optional[CaseStatusEnum] = Query(None),
    bureau_id: Optional[int] = Query(None),
    region_id: Optional[int] = Query(None),
    category_id: Optional[int] = Query(None),
    priority: Optional[PriorityEnum] = Query(None),
    overdue_only: Optional[bool] = Query(None),
    due_soon_only: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve paginated open cases with SLA monitoring status and metrics."""
    today = date.today()

    query = db.query(Case).filter(Case.status.in_(OPEN_CASE_STATUSES))
    query = _apply_case_scoping(query, current_user)

    if status is not None:
        query = query.filter(Case.status == status)
    if bureau_id is not None:
        query = query.filter(Case.bureau_id == bureau_id)
    if category_id is not None:
        query = query.filter(Case.category_id == category_id)
    if priority is not None:
        query = query.filter(Case.priority == priority)
    if region_id is not None and current_user.role != RoleEnum.REGIONAL_OFFICER:
        query = query.join(Institution, Case.institution_id == Institution.id).filter(
            Institution.region_id == region_id
        )

    if overdue_only is True:
        query = query.filter(
            Case.expected_disposal_on.isnot(None),
            Case.expected_disposal_on < today,
        )

    # Order by urgency: expected_disposal_on ascending (nulls last)
    query = query.order_by(Case.expected_disposal_on.asc().nulls_last(), Case.id.asc())

    # Pre-load SlaRules for due-soon calculation
    rules = db.query(SlaRule).all()
    rule_map = {(r.category_id, r.priority): r for r in rules}

    all_matching = query.all()

    # Calculate SLA status for each
    items = []
    for c in all_matching:
        elapsed = (today - c.received_on).days
        is_overdue = bool(c.expected_disposal_on and c.expected_disposal_on < today)
        remaining = (c.expected_disposal_on - today).days if c.expected_disposal_on else None

        rule = rule_map.get((c.category_id, c.priority)) or rule_map.get((None, c.priority))
        warn_pct = rule.warn_at_pct if rule else 80
        total_days = (
            (c.expected_disposal_on - c.received_on).days
            if (c.expected_disposal_on and c.expected_disposal_on > c.received_on)
            else _DEFAULT_SLA_DAYS.get(c.priority, 30)
        )

        is_due_soon = False
        if not is_overdue:
            if total_days > 0 and (elapsed / total_days * 100 >= warn_pct or (remaining is not None and remaining <= 3)):
                is_due_soon = True

        if due_soon_only is True and not is_due_soon:
            continue

        if is_overdue:
            sla_status = "OVERDUE"
        elif is_due_soon:
            sla_status = "DUE_SOON"
        else:
            sla_status = "WITHIN_SLA"

        items.append(
            SlaCaseItem(
                id=c.id,
                case_no=c.case_no,
                bureau_id=c.bureau_id,
                bureau_code=c.bureau.code if c.bureau else None,
                institution_id=c.institution_id,
                institution_name=c.institution.name if c.institution else None,
                category_id=c.category_id,
                category_name=c.category.name if c.category else None,
                status=c.status,
                priority=c.priority,
                received_on=c.received_on,
                expected_disposal_on=c.expected_disposal_on,
                days_elapsed=elapsed,
                days_remaining=remaining,
                sla_status=sla_status,
                is_beyond_sla=is_overdue,
            )
        )

    total_count = len(items)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_items = items[start_idx:end_idx]

    return SlaCasesList(
        items=paginated_items,
        total=total_count,
        page=page,
        page_size=page_size,
    )
