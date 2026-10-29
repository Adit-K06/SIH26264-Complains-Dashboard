"""Computed dashboard and report aggregates."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Alert,
    Bureau,
    Case,
    CaseAction,
    Institution,
    OverlapFlag,
    Region,
)
from app.models.enums import CaseStatus, OverlapState


def value(item) -> str:
    return item.value if hasattr(item, "value") else str(item)


def status_counts(cases: list[Case]) -> dict[str, int]:
    counts = {item.value: 0 for item in CaseStatus}
    for case in cases:
        status = value(case.status)
        counts[status] = counts.get(status, 0) + 1
    return counts


def dashboard_summary(db: Session) -> dict:
    cases = db.scalars(select(Case)).all()
    flags = db.scalars(select(OverlapFlag)).all()
    unread_count = len(db.scalars(select(Alert).where(Alert.read_at.is_(None))).all())
    statuses = status_counts(cases)
    open_count = sum(
        count for status, count in statuses.items()
        if status != CaseStatus.DISPOSED.value
    )
    open_flags = sum(value(flag.state) == OverlapState.OPEN.value for flag in flags)
    return {
        "total_cases": len(cases),
        "open_cases": open_count,
        "disposed_cases": statuses.get(CaseStatus.DISPOSED.value, 0),
        "status_counts": statuses,
        "open_overlaps": open_flags,
        "unread_alerts": unread_count,
    }


def workload_rows(db: Session) -> list[dict]:
    bureaus = db.scalars(select(Bureau).order_by(Bureau.code)).all()
    cases = db.scalars(select(Case)).all()
    grouped: dict[object, list[Case]] = defaultdict(list)
    for case in cases:
        grouped[case.bureau_id].append(case)
    rows = []
    for bureau in bureaus:
        items = grouped.get(bureau.id, [])
        by_status = status_counts(items)
        rows.append(
            {
                "bureau_id": str(bureau.id),
                "bureau_code": bureau.code,
                "bureau_name": bureau.name,
                "total_cases": len(items),
                "open_cases": sum(
                    count for status, count in by_status.items()
                    if status != CaseStatus.DISPOSED.value
                ),
                "status_counts": by_status,
            }
        )
    return rows


def ageing_rows(db: Session, today: date | None = None) -> list[dict]:
    as_of = today or date.today()
    bands = [
        ("0-7 days", 0, 7),
        ("8-30 days", 8, 30),
        ("31-60 days", 31, 60),
        ("61+ days", 61, None),
    ]
    counts = Counter()
    for case in db.scalars(select(Case)).all():
        if value(case.status) == CaseStatus.DISPOSED.value:
            continue
        age_days = max(0, (as_of - case.received_on).days)
        for label, lower, upper in bands:
            if age_days >= lower and (upper is None or age_days <= upper):
                counts[label] += 1
                break
    return [
        {"band": label, "cases": counts[label]}
        for label, _, _ in bands
    ]


def _month_starts(today: date, count: int = 12) -> list[date]:
    current_index = today.year * 12 + today.month - 1
    starts = []
    for offset in reversed(range(count)):
        index = current_index - offset
        starts.append(date(index // 12, index % 12 + 1, 1))
    return starts


def monthly_rows(db: Session, today: date | None = None) -> list[dict]:
    as_of = today or date.today()
    months = _month_starts(as_of)
    month_keys = {month.strftime("%Y-%m"): {"month": month.strftime("%Y-%m"), "received": 0, "disposed": 0} for month in months}
    for case in db.scalars(select(Case)).all():
        key = case.received_on.strftime("%Y-%m")
        if key in month_keys:
            month_keys[key]["received"] += 1
    for action in db.scalars(
        select(CaseAction).where(CaseAction.to_status == CaseStatus.DISPOSED.value)
    ).all():
        if action.created_at is None:
            continue
        key = action.created_at.date().strftime("%Y-%m")
        if key in month_keys:
            month_keys[key]["disposed"] += 1
    return list(month_keys.values())


def report_rows(db: Session, report_type: str) -> list[dict]:
    cases = db.scalars(select(Case)).all()
    if report_type == "bureau":
        return workload_rows(db)
    if report_type == "region":
        institutions = db.scalars(select(Institution)).all()
        regions = db.scalars(select(Region)).all()
        region_by_id = {region.id: region.name for region in regions}
        region_for_institution = {
            institution.id: region_by_id.get(institution.region_id, "Unassigned")
            for institution in institutions
        }
        grouped: dict[str, list[Case]] = defaultdict(list)
        for case in cases:
            region_name = region_for_institution.get(case.institution_id, "Unassigned")
            grouped[region_name].append(case)
        return [
            {
                "region": name,
                "total_cases": len(items),
                "open_cases": sum(value(case.status) != CaseStatus.DISPOSED.value for case in items),
                "disposed_cases": sum(value(case.status) == CaseStatus.DISPOSED.value for case in items),
            }
            for name, items in sorted(grouped.items())
        ]
    if report_type == "institution":
        institutions = db.scalars(select(Institution).order_by(Institution.aicte_permanent_id)).all()
        grouped: dict[object, list[Case]] = defaultdict(list)
        for case in cases:
            grouped[case.institution_id].append(case)
        return [
            {
                "institution_id": str(institution.id),
                "aicte_permanent_id": institution.aicte_permanent_id,
                "institution_name": institution.name,
                "total_cases": len(grouped.get(institution.id, [])),
                "open_cases": sum(
                    value(case.status) != CaseStatus.DISPOSED.value
                    for case in grouped.get(institution.id, [])
                ),
            }
            for institution in institutions
        ]
    if report_type == "ageing":
        return ageing_rows(db)
    if report_type == "disposal-rate":
        bureaus = db.scalars(select(Bureau).order_by(Bureau.code)).all()
        grouped: dict[object, list[Case]] = defaultdict(list)
        for case in cases:
            grouped[case.bureau_id].append(case)
        rows = []
        for bureau in bureaus:
            items = grouped.get(bureau.id, [])
            disposed = sum(value(case.status) == CaseStatus.DISPOSED.value for case in items)
            rows.append(
                {
                    "bureau_code": bureau.code,
                    "total_cases": len(items),
                    "disposed_cases": disposed,
                    "disposal_rate": disposed / len(items) if items else None,
                }
            )
        return rows
    if report_type == "status":
        counts = status_counts(cases)
        return [{"status": key, "cases": count} for key, count in counts.items()]
    if report_type == "overlaps":
        flags = db.scalars(select(OverlapFlag)).all()
        grouped = Counter((value(flag.tier), value(flag.state)) for flag in flags)
        return [
            {"tier": tier, "state": state, "flags": grouped[(tier, state)]}
            for tier, state in sorted(grouped)
        ]
    if report_type == "monthly":
        return monthly_rows(db)
    raise ValueError(f"Unknown report type: {report_type}")

