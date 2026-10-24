"""Dashboard aggregation API router.

Endpoints per AGENTS.md:
  GET /dashboard/summary   – KPI totals, status breakdown, overlap counts, monthly trend
  GET /dashboard/workload  – per-bureau × status case counts
  GET /dashboard/ageing    – open-case age distribution in five buckets

Ownership: P4 Platform/QA.

All endpoints:
  - Require Bearer authentication (any active role).
  - Use SQL aggregation to avoid loading all rows into Python.
  - Return zero / empty collections when no data is present.
  - Never expose complainant_ref or personal case details.
  - Read-only: no mutations.

Metric definitions
------------------
total            : COUNT(*) over all cases, all statuses.
by_status        : COUNT(*) GROUP BY status over all cases.
beyond_sla       : open cases where expected_disposal_on < today (AGENTS.md definition).
open_overlaps    : COUNT(*) from overlap_flags WHERE state = OPEN.
confirmed_groups : COUNT(DISTINCT institution_id) from overlap_flags WHERE state = CONFIRMED.
monthly          : for each of the last 12 calendar months,
                     received  = cases with received_on in that month
                     disposed  = cases whose status is DISPOSED and last_action_on is in that month.
                     (last_action_on is updated on every status change, including DISPOSED.)
workload         : for each bureau (by code), case counts by status.
                   Bureaus with zero cases are included with empty counts.
ageing           : open cases only (PENDING | UNDER_PROCESS | ESCALATED | TRANSFERRED).
                   Age = today – received_on (days).
                   Buckets: 0-7 | 8-15 | 16-30 | 31-60 | 60+.
                   Boundary: bucket 0-7 includes day 0 through day 7 (0 ≤ age ≤ 7);
                   60+ means age > 60 (strictly greater than 60).
"""
from collections import defaultdict
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import and_, case, cast, func, Integer
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Bureau, Case, OverlapFlag, User
from app.models.enums import CaseStatusEnum, OverlapStateEnum

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Five bureaus specified in AGENTS.md – order matches mock/frontend expectation
_BUREAU_CODES = ["RB", "PGRC", "APPROVAL", "ACADEMIC", "FINANCE"]

# Open statuses per AGENTS.md
_OPEN_STATUSES = {
    CaseStatusEnum.PENDING,
    CaseStatusEnum.UNDER_PROCESS,
    CaseStatusEnum.ESCALATED,
    CaseStatusEnum.TRANSFERRED,
}


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class MonthlyPoint(BaseModel):
    month: str          # "YYYY-MM"
    received: int
    disposed: int


class DashboardSummary(BaseModel):
    total: int
    by_status: dict[str, int]
    beyond_sla: int
    open_overlaps: int
    confirmed_groups: int
    monthly: list[MonthlyPoint]


class WorkloadRow(BaseModel):
    bureau: str         # bureau code
    counts: dict[str, int]


class Workload(BaseModel):
    items: list[WorkloadRow]


class AgeingBucket(BaseModel):
    bucket: str         # "0-7" | "8-15" | "16-30" | "31-60" | "60+"
    count: int


class Ageing(BaseModel):
    items: list[AgeingBucket]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _last_12_months(today: date) -> list[str]:
    """Return list of 'YYYY-MM' strings for the last 12 calendar months, oldest first.

    Includes the current month. E.g. if today is 2026-10-24, returns
    ['2025-11', '2025-12', ..., '2026-10'].
    """
    months = []
    year, month = today.year, today.month
    for i in range(11, -1, -1):
        # Go back i months from the current month
        m = month - i
        y = year
        while m <= 0:
            m += 12
            y -= 1
        months.append(f"{y:04d}-{m:02d}")
    return months


# ---------------------------------------------------------------------------
# GET /dashboard/summary
# ---------------------------------------------------------------------------

@router.get("/summary", response_model=DashboardSummary)
def get_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Aggregate KPI metrics: total, by_status, beyond_sla, overlaps, monthly trend."""
    today = date.today()

    # ── Total and by-status in one query ──────────────────────────────────
    status_rows = (
        db.query(Case.status, func.count(Case.id).label("cnt"))
        .group_by(Case.status)
        .all()
    )
    by_status: dict[str, int] = {}
    total = 0
    for row in status_rows:
        by_status[row.status.value] = row.cnt
        total += row.cnt

    # ── Beyond SLA: open AND expected_disposal_on < today ─────────────────
    beyond_sla = (
        db.query(func.count(Case.id))
        .filter(
            Case.status.in_(_OPEN_STATUSES),
            Case.expected_disposal_on.isnot(None),
            Case.expected_disposal_on < today,
        )
        .scalar()
    ) or 0

    # ── Overlap counts ─────────────────────────────────────────────────────
    open_overlaps = (
        db.query(func.count(OverlapFlag.id))
        .filter(OverlapFlag.state == OverlapStateEnum.OPEN)
        .scalar()
    ) or 0

    confirmed_groups = (
        db.query(func.count(func.distinct(OverlapFlag.institution_id)))
        .filter(OverlapFlag.state == OverlapStateEnum.CONFIRMED)
        .scalar()
    ) or 0

    # ── Monthly trend: last 12 months ──────────────────────────────────────
    month_labels = _last_12_months(today)

    # Received: cases with received_on in each month
    # SQLite: strftime('%Y-%m', received_on)
    # PostgreSQL: to_char(received_on, 'YYYY-MM')
    # We use func.strftime for SQLite compatibility in tests; PostgreSQL uses
    # a different function but SQLAlchemy's func.strftime is ignored on PG.
    # For portability we do the aggregation in Python by fetching each month's
    # start/end date range — avoids dialect-specific string functions.

    # Compute first/last day of each label
    def _month_bounds(label: str):
        y, m = int(label[:4]), int(label[5:])
        first = date(y, m, 1)
        # last day = first day of next month minus 1 day
        if m == 12:
            last = date(y + 1, 1, 1) - timedelta(days=1)
        else:
            last = date(y, m + 1, 1) - timedelta(days=1)
        return first, last

    # Bulk fetch received counts for all 12 months in one query using CASE
    # Build one query: SELECT month_label, COUNT(*) FROM cases WHERE received_on in range
    # Efficient: single GROUP BY query using truncation-to-month approach via ranges
    twelve_months_start = _month_bounds(month_labels[0])[0]
    twelve_months_end = _month_bounds(month_labels[-1])[1]

    received_rows = (
        db.query(Case.received_on, func.count(Case.id).label("cnt"))
        .filter(Case.received_on >= twelve_months_start, Case.received_on <= twelve_months_end)
        .group_by(Case.received_on)
        .all()
    )

    # Map each date to its YYYY-MM label
    received_by_month: dict[str, int] = defaultdict(int)
    for row in received_rows:
        if row.received_on:
            label = f"{row.received_on.year:04d}-{row.received_on.month:02d}"
            received_by_month[label] += row.cnt

    # Disposed: cases currently DISPOSED AND last_action_on in the month window
    # last_action_on is a timezone-aware datetime; we compare date portion
    disposed_rows = (
        db.query(Case.last_action_on, func.count(Case.id).label("cnt"))
        .filter(
            Case.status == CaseStatusEnum.DISPOSED,
            Case.last_action_on.isnot(None),
            func.date(Case.last_action_on) >= twelve_months_start,
            func.date(Case.last_action_on) <= twelve_months_end,
        )
        .group_by(func.date(Case.last_action_on))
        .all()
    )

    disposed_by_month: dict[str, int] = defaultdict(int)
    for row in disposed_rows:
        if row.last_action_on:
            dt = row.last_action_on
            # dt may be a datetime or a date depending on the DB
            if hasattr(dt, "date"):
                d = dt.date()
            else:
                d = dt
            label = f"{d.year:04d}-{d.month:02d}"
            disposed_by_month[label] += row.cnt

    monthly = [
        MonthlyPoint(
            month=label,
            received=received_by_month.get(label, 0),
            disposed=disposed_by_month.get(label, 0),
        )
        for label in month_labels
    ]

    return DashboardSummary(
        total=total,
        by_status=by_status,
        beyond_sla=beyond_sla,
        open_overlaps=open_overlaps,
        confirmed_groups=confirmed_groups,
        monthly=monthly,
    )


# ---------------------------------------------------------------------------
# GET /dashboard/workload
# ---------------------------------------------------------------------------

@router.get("/workload", response_model=Workload)
def get_workload(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return case counts grouped by bureau code × status.

    All five AGENTS.md bureaus are always present in the response even if they
    have zero cases. A bureau not in the database (not yet seeded) is omitted.
    """
    # Fetch all bureaus that match the five configured codes (actual DB rows)
    bureaus = (
        db.query(Bureau)
        .filter(Bureau.code.in_(_BUREAU_CODES))
        .all()
    )
    bureau_by_id = {b.id: b.code for b in bureaus}
    bureau_by_code = {b.code: b.id for b in bureaus}

    # Single aggregation query: bureau_id × status → count
    rows = (
        db.query(Case.bureau_id, Case.status, func.count(Case.id).label("cnt"))
        .filter(Case.bureau_id.in_(list(bureau_by_id.keys())))
        .group_by(Case.bureau_id, Case.status)
        .all()
    )

    # Build counts dict keyed by bureau_code → {status: count}
    counts_map: dict[str, dict[str, int]] = {code: {} for code in _BUREAU_CODES if code in bureau_by_code}
    for row in rows:
        code = bureau_by_id.get(row.bureau_id)
        if code:
            counts_map.setdefault(code, {})[row.status.value] = row.cnt

    # Return in the specified bureau order; include only bureaus present in DB
    items = [
        WorkloadRow(bureau=code, counts=counts_map.get(code, {}))
        for code in _BUREAU_CODES
        if code in bureau_by_code
    ]

    return Workload(items=items)


# ---------------------------------------------------------------------------
# GET /dashboard/ageing
# ---------------------------------------------------------------------------

@router.get("/ageing", response_model=Ageing)
def get_ageing(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return age distribution of open cases (PENDING | UNDER_PROCESS | ESCALATED | TRANSFERRED).

    Age = today – received_on (in days).
    Buckets: 0-7 | 8-15 | 16-30 | 31-60 | 60+
    Boundary rule: 0-7 means 0 ≤ age ≤ 7; 8-15 means 8 ≤ age ≤ 15;
                   16-30 means 16 ≤ age ≤ 30; 31-60 means 31 ≤ age ≤ 60;
                   60+ means age > 60.
    """
    today = date.today()

    # Fetch open cases with their received_on date
    # Compute age in Python to stay dialect-agnostic (SQLite lacks robust date diff)
    open_cases = (
        db.query(Case.received_on)
        .filter(
            Case.status.in_(_OPEN_STATUSES),
            Case.received_on.isnot(None),
        )
        .all()
    )

    buckets = {"0-7": 0, "8-15": 0, "16-30": 0, "31-60": 0, "60+": 0}
    for (received_on,) in open_cases:
        age = (today - received_on).days
        if age <= 7:
            buckets["0-7"] += 1
        elif age <= 15:
            buckets["8-15"] += 1
        elif age <= 30:
            buckets["16-30"] += 1
        elif age <= 60:
            buckets["31-60"] += 1
        else:
            buckets["60+"] += 1

    items = [AgeingBucket(bucket=k, count=v) for k, v in buckets.items()]
    return Ageing(items=items)
