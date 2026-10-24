"""Reports API router.

Endpoints per AGENTS.md:
  GET /reports/{type}?format=csv|json|pdf
  Types: bureau, region, institution, ageing, disposal-rate, status, overlaps, monthly, quarterly

Ownership: P4 Platform/QA.
All endpoints:
  - Enforce authentication and RBAC scoping.
  - Return aggregated database metrics.
  - Never leak complainant references or personal data.
  - Support format=json (default) and format=csv (downloadable).
"""
import csv
from datetime import date, datetime, timedelta, timezone
import io
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Bureau, Case, Category, Institution, OverlapFlag, Region, User
from app.models.enums import CaseStatusEnum, OPEN_CASE_STATUSES, OverlapStateEnum, OverlapTierEnum, RoleEnum

router = APIRouter(prefix="/reports", tags=["reports"])

SUPPORTED_TYPES = {
    "bureau",
    "region",
    "institution",
    "ageing",
    "disposal-rate",
    "status",
    "overlaps",
    "monthly",
    "quarterly",
}


def _apply_report_case_scoping(query, user: User):
    """Enforce RBAC scoping on case queries for reports."""
    if user.role == RoleEnum.BUREAU_OFFICER:
        query = query.filter(Case.bureau_id == user.bureau_id)
    elif user.role == RoleEnum.REGIONAL_OFFICER:
        query = query.join(Institution, Case.institution_id == Institution.id).filter(
            Institution.region_id == user.region_id
        )
    return query


def _generate_csv(headers: list[str], rows: list[list[Any]]) -> str:
    """Safely format data into a CSV string."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    return output.getvalue()


@router.get("/{report_type}")
def get_report(
    report_type: str,
    format: str = Query("json"),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    bureau_id: Optional[int] = Query(None),
    region_id: Optional[int] = Query(None),
    category_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate complaint monitoring and tracking reports."""
    report_type = report_type.lower()
    if report_type not in SUPPORTED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Unsupported report type: '{report_type}'. Supported types: {', '.join(sorted(SUPPORTED_TYPES))}",
                }
            },
        )

    format_lower = format.lower()
    if format_lower == "pdf":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": {
                    "code": "FORMAT_NOT_SUPPORTED",
                    "message": "PDF format is not supported; please use 'json' or 'csv'",
                }
            },
        )
    if format_lower not in {"json", "csv"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": {
                    "code": "INVALID_FORMAT",
                    "message": f"Unsupported format: '{format}'. Use 'json' or 'csv'",
                }
            },
        )

    today = date.today()

    # Base case query
    query = db.query(Case)
    query = _apply_report_case_scoping(query, current_user)

    if from_date:
        query = query.filter(Case.received_on >= from_date)
    if to_date:
        query = query.filter(Case.received_on <= to_date)
    if bureau_id:
        query = query.filter(Case.bureau_id == bureau_id)
    if category_id:
        query = query.filter(Case.category_id == category_id)
    if region_id and current_user.role != RoleEnum.REGIONAL_OFFICER:
        query = query.join(Institution, Case.institution_id == Institution.id).filter(
            Institution.region_id == region_id
        )

    cases = query.all()

    # Dispatch to specific report generator
    if report_type == "bureau":
        result_data, headers, csv_rows = _report_bureau(db, cases, current_user, today)
    elif report_type == "region":
        result_data, headers, csv_rows = _report_region(db, cases, current_user, today)
    elif report_type == "institution":
        result_data, headers, csv_rows = _report_institution(db, cases, today)
    elif report_type == "ageing":
        result_data, headers, csv_rows = _report_ageing(cases, today)
    elif report_type == "disposal-rate":
        result_data, headers, csv_rows = _report_disposal_rate(db, cases, current_user)
    elif report_type == "status":
        result_data, headers, csv_rows = _report_status(cases)
    elif report_type == "overlaps":
        result_data, headers, csv_rows = _report_overlaps(
            db, current_user, bureau_id=bureau_id, region_id=region_id
        )
    elif report_type == "monthly":
        result_data, headers, csv_rows = _report_monthly(cases, from_date, to_date, today)
    elif report_type == "quarterly":
        result_data, headers, csv_rows = _report_quarterly(cases, from_date, to_date, today)

    if format_lower == "csv":
        csv_content = _generate_csv(headers, csv_rows)
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="report_{report_type}.csv"'},
        )

    return {
        "report_type": report_type,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_records": len(cases) if report_type != "overlaps" else result_data.get("total_flags", 0),
        "data": result_data,
    }


def _report_bureau(db: Session, cases: list[Case], user: User, today: date):
    bureaus = db.query(Bureau).order_by(Bureau.id.asc()).all()
    if user.role == RoleEnum.BUREAU_OFFICER:
        bureaus = [b for b in bureaus if b.id == user.bureau_id]

    bureau_map = {b.id: {"code": b.code, "name": b.name, "total": 0, "open": 0, "disposed": 0, "beyond_sla": 0} for b in bureaus}

    for c in cases:
        if c.bureau_id in bureau_map:
            entry = bureau_map[c.bureau_id]
            entry["total"] += 1
            if c.status == CaseStatusEnum.DISPOSED:
                entry["disposed"] += 1
            elif c.status in OPEN_CASE_STATUSES:
                entry["open"] += 1
                if c.expected_disposal_on and c.expected_disposal_on < today:
                    entry["beyond_sla"] += 1

    items = []
    headers = ["Bureau Code", "Bureau Name", "Total Cases", "Open Cases", "Disposed Cases", "Beyond SLA", "Disposal Rate (%)"]
    csv_rows = []

    for b_id, entry in bureau_map.items():
        total = entry["total"]
        rate = round(entry["disposed"] / total * 100, 1) if total > 0 else 0.0
        item = {
            "bureau_id": b_id,
            "bureau_code": entry["code"],
            "bureau_name": entry["name"],
            "total_cases": total,
            "open_cases": entry["open"],
            "disposed_cases": entry["disposed"],
            "beyond_sla": entry["beyond_sla"],
            "disposal_rate_pct": rate,
        }
        items.append(item)
        csv_rows.append([entry["code"], entry["name"], total, entry["open"], entry["disposed"], entry["beyond_sla"], rate])

    return {"bureaus": items}, headers, csv_rows


def _report_region(db: Session, cases: list[Case], user: User, today: date):
    regions = db.query(Region).order_by(Region.id.asc()).all()
    if user.role == RoleEnum.REGIONAL_OFFICER:
        regions = [r for r in regions if r.id == user.region_id]

    # Pre-map institution to region
    inst_regions = {i.id: i.region_id for i in db.query(Institution.id, Institution.region_id).all()}

    region_map = {r.id: {"name": r.name, "total": 0, "open": 0, "disposed": 0, "beyond_sla": 0} for r in regions}

    for c in cases:
        r_id = inst_regions.get(c.institution_id)
        if r_id in region_map:
            entry = region_map[r_id]
            entry["total"] += 1
            if c.status == CaseStatusEnum.DISPOSED:
                entry["disposed"] += 1
            elif c.status in OPEN_CASE_STATUSES:
                entry["open"] += 1
                if c.expected_disposal_on and c.expected_disposal_on < today:
                    entry["beyond_sla"] += 1

    items = []
    headers = ["Region Name", "Total Cases", "Open Cases", "Disposed Cases", "Beyond SLA"]
    csv_rows = []

    for r_id, entry in region_map.items():
        item = {
            "region_id": r_id,
            "region_name": entry["name"],
            "total_cases": entry["total"],
            "open_cases": entry["open"],
            "disposed_cases": entry["disposed"],
            "beyond_sla": entry["beyond_sla"],
        }
        items.append(item)
        csv_rows.append([entry["name"], entry["total"], entry["open"], entry["disposed"], entry["beyond_sla"]])

    return {"regions": items}, headers, csv_rows


def _report_institution(db: Session, cases: list[Case], today: date):
    inst_map: dict[int, dict[str, Any]] = {}
    for c in cases:
        if not c.institution_id:
            continue
        if c.institution_id not in inst_map:
            inst = c.institution
            inst_map[c.institution_id] = {
                "institution_id": c.institution_id,
                "aicte_id": inst.aicte_permanent_id if inst else "N/A",
                "institution_name": inst.name if inst else "Unknown",
                "total": 0,
                "open": 0,
                "disposed": 0,
                "beyond_sla": 0,
            }
        entry = inst_map[c.institution_id]
        entry["total"] += 1
        if c.status == CaseStatusEnum.DISPOSED:
            entry["disposed"] += 1
        elif c.status in OPEN_CASE_STATUSES:
            entry["open"] += 1
            if c.expected_disposal_on and c.expected_disposal_on < today:
                entry["beyond_sla"] += 1

    items = sorted(inst_map.values(), key=lambda x: x["total"], reverse=True)
    headers = ["AICTE ID", "Institution Name", "Total Cases", "Open Cases", "Disposed Cases", "Beyond SLA"]
    csv_rows = [
        [i["aicte_id"], i["institution_name"], i["total"], i["open"], i["disposed"], i["beyond_sla"]]
        for i in items
    ]

    return {"institutions": items}, headers, csv_rows


def _report_ageing(cases: list[Case], today: date):
    buckets = {"0-7": 0, "8-15": 0, "16-30": 0, "31-60": 0, "60+": 0}
    total_open = 0

    for c in cases:
        if c.status in OPEN_CASE_STATUSES:
            total_open += 1
            age = (today - c.received_on).days
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

    items = []
    headers = ["Age Bucket (Days)", "Count", "Percentage (%)"]
    csv_rows = []

    for b, count in buckets.items():
        pct = round(count / total_open * 100, 1) if total_open > 0 else 0.0
        items.append({"bucket": b, "count": count, "percentage": pct})
        csv_rows.append([b, count, pct])

    return {"total_open_cases": total_open, "buckets": items}, headers, csv_rows


def _report_disposal_rate(db: Session, cases: list[Case], user: User):
    bureaus = db.query(Bureau).order_by(Bureau.id.asc()).all()
    if user.role == RoleEnum.BUREAU_OFFICER:
        bureaus = [b for b in bureaus if b.id == user.bureau_id]

    bureau_stats = {
        b.id: {"code": b.code, "total": 0, "disposed": 0, "durations": []}
        for b in bureaus
    }

    for c in cases:
        if c.bureau_id in bureau_stats:
            bureau_stats[c.bureau_id]["total"] += 1
            if c.status == CaseStatusEnum.DISPOSED:
                bureau_stats[c.bureau_id]["disposed"] += 1
                # calculate days to dispose using last_action_on
                if c.last_action_on:
                    disp_date = c.last_action_on.date() if isinstance(c.last_action_on, datetime) else c.last_action_on
                    dur = max(0, (disp_date - c.received_on).days)
                    bureau_stats[c.bureau_id]["durations"].append(dur)

    items = []
    headers = ["Bureau Code", "Total Cases", "Disposed Cases", "Disposal Rate (%)", "Average Days to Dispose"]
    csv_rows = []

    for b_id, s in bureau_stats.items():
        tot = s["total"]
        disp = s["disposed"]
        rate = round(disp / tot * 100, 1) if tot > 0 else 0.0
        avg_days = round(sum(s["durations"]) / len(s["durations"]), 1) if s["durations"] else 0.0
        item = {
            "bureau_id": b_id,
            "bureau_code": s["code"],
            "total_cases": tot,
            "disposed_cases": disp,
            "disposal_rate_pct": rate,
            "avg_days_to_dispose": avg_days,
        }
        items.append(item)
        csv_rows.append([s["code"], tot, disp, rate, avg_days])

    return {"bureau_disposal_rates": items}, headers, csv_rows


def _report_status(cases: list[Case]):
    status_counts = {s.value: 0 for s in CaseStatusEnum}
    total = len(cases)

    for c in cases:
        status_counts[c.status.value] += 1

    items = []
    headers = ["Status", "Count", "Percentage (%)"]
    csv_rows = []

    for st, count in status_counts.items():
        pct = round(count / total * 100, 1) if total > 0 else 0.0
        items.append({"status": st, "count": count, "percentage": pct})
        csv_rows.append([st, count, pct])

    return {"total_cases": total, "statuses": items}, headers, csv_rows


def _report_overlaps(
    db: Session,
    user: User,
    bureau_id: Optional[int] = None,
    region_id: Optional[int] = None,
):
    query = db.query(OverlapFlag)

    # Enforce bureau scoping: BUREAU_OFFICER is locked to own bureau
    target_bureau_id = user.bureau_id if user.role == RoleEnum.BUREAU_OFFICER else bureau_id

    # Enforce regional scoping: REGIONAL_OFFICER is locked to own region
    target_region_id = user.region_id if user.role == RoleEnum.REGIONAL_OFFICER else region_id

    if target_bureau_id is not None:
        inst_subquery = (
            db.query(Case.institution_id)
            .filter(
                Case.bureau_id == target_bureau_id,
                Case.institution_id.isnot(None),
                Case.status.in_(OPEN_CASE_STATUSES),
            )
        )
        case_subquery = (
            db.query(Case.id)
            .filter(Case.bureau_id == target_bureau_id)
        )
        query = query.filter(
            or_(
                OverlapFlag.case_a.in_(case_subquery),
                OverlapFlag.case_b.in_(case_subquery),
                and_(
                    OverlapFlag.institution_id.isnot(None),
                    OverlapFlag.institution_id.in_(inst_subquery),
                ),
            )
        )

    if target_region_id is not None:
        reg_inst_subquery = (
            db.query(Institution.id)
            .filter(Institution.region_id == target_region_id)
        )
        reg_case_subquery = (
            db.query(Case.id)
            .join(Institution, Case.institution_id == Institution.id)
            .filter(Institution.region_id == target_region_id)
        )
        query = query.filter(
            or_(
                and_(
                    OverlapFlag.institution_id.isnot(None),
                    OverlapFlag.institution_id.in_(reg_inst_subquery),
                ),
                OverlapFlag.case_a.in_(reg_case_subquery),
                OverlapFlag.case_b.in_(reg_case_subquery),
            )
        )

    flags = query.all()

    total_flags = len(flags)
    tier_a = sum(1 for f in flags if f.tier == OverlapTierEnum.A)
    tier_b = sum(1 for f in flags if f.tier == OverlapTierEnum.B)
    open_state = sum(1 for f in flags if f.state == OverlapStateEnum.OPEN)
    confirmed = sum(1 for f in flags if f.state == OverlapStateEnum.CONFIRMED)
    dismissed = sum(1 for f in flags if f.state == OverlapStateEnum.DISMISSED)

    confirmed_insts = len({f.institution_id for f in flags if f.state == OverlapStateEnum.CONFIRMED and f.institution_id})

    data = {
        "total_flags": total_flags,
        "tier_a_count": tier_a,
        "tier_b_count": tier_b,
        "open_count": open_state,
        "confirmed_count": confirmed,
        "dismissed_count": dismissed,
        "confirmed_institutions": confirmed_insts,
    }

    headers = ["Metric", "Count"]
    csv_rows = [
        ["Total Overlap Flags", total_flags],
        ["Tier A Flags", tier_a],
        ["Tier B Flags", tier_b],
        ["Open State", open_state],
        ["Confirmed State", confirmed],
        ["Dismissed State", dismissed],
        ["Confirmed Institutions", confirmed_insts],
    ]

    return data, headers, csv_rows


def _report_monthly(cases: list[Case], from_date: Optional[date], to_date: Optional[date], today: date):
    monthly_data: dict[str, dict[str, int]] = {}

    for c in cases:
        m_rec = c.received_on.strftime("%Y-%m")
        if m_rec not in monthly_data:
            monthly_data[m_rec] = {"month": m_rec, "received": 0, "disposed": 0}
        monthly_data[m_rec]["received"] += 1

        if c.status == CaseStatusEnum.DISPOSED and c.last_action_on:
            disp_date = c.last_action_on.date() if isinstance(c.last_action_on, datetime) else c.last_action_on
            m_disp = disp_date.strftime("%Y-%m")
            if m_disp not in monthly_data:
                monthly_data[m_disp] = {"month": m_disp, "received": 0, "disposed": 0}
            monthly_data[m_disp]["disposed"] += 1

    sorted_months = sorted(monthly_data.keys())
    items = [monthly_data[m] for m in sorted_months]
    headers = ["Month", "Cases Received", "Cases Disposed"]
    csv_rows = [[i["month"], i["received"], i["disposed"]] for i in items]

    return {"monthly_trend": items}, headers, csv_rows


def _report_quarterly(cases: list[Case], from_date: Optional[date], to_date: Optional[date], today: date):
    quarterly_data: dict[str, dict[str, int]] = {}

    for c in cases:
        q_num = (c.received_on.month - 1) // 3 + 1
        q_rec = f"{c.received_on.year}-Q{q_num}"
        if q_rec not in quarterly_data:
            quarterly_data[q_rec] = {"quarter": q_rec, "received": 0, "disposed": 0}
        quarterly_data[q_rec]["received"] += 1

        if c.status == CaseStatusEnum.DISPOSED and c.last_action_on:
            disp_date = c.last_action_on.date() if isinstance(c.last_action_on, datetime) else c.last_action_on
            disp_q_num = (disp_date.month - 1) // 3 + 1
            q_disp = f"{disp_date.year}-Q{disp_q_num}"
            if q_disp not in quarterly_data:
                quarterly_data[q_disp] = {"quarter": q_disp, "received": 0, "disposed": 0}
            quarterly_data[q_disp]["disposed"] += 1

    sorted_quarters = sorted(quarterly_data.keys())
    items = [quarterly_data[q] for q in sorted_quarters]
    headers = ["Quarter", "Cases Received", "Cases Disposed"]
    csv_rows = [[i["quarter"], i["received"], i["disposed"]] for i in items]

    return {"quarterly_trend": items}, headers, csv_rows
