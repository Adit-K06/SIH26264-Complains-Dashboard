"""Seed reference tables and SYNTHETIC institutions/cases into the app database.

    docker compose exec api python -m app.ai.seed [--reset] [--no-scan]

--reset removes ONLY rows this script created (institutions with aicte id SYN-AICTE-*, cases with
case_no SYN-CASE-*, and their flags/actions) and then re-seeds. Users from app.seed are never touched.
Everything is marked source='SYNTHETIC'; these are not real AICTE records.
"""
from __future__ import annotations
import argparse
from datetime import date, datetime, timedelta, timezone

import pandas as pd

from .overlap import _model
from .paths import data_dir

REGIONS = ["Central", "Eastern", "North-Eastern", "Northern", "Southern", "South-Western", "Western"]
BUREAUS = {"RB": "Regional Bureau", "PGRC": "Public Grievance Redressal Cell", "APPROVAL": "Approval Bureau",
           "ACADEMIC": "Academic Bureau", "FINANCE": "Finance Bureau"}
# Demo assumption only (AGENTS.md lists the regions but not their state mapping).
STATE_TO_REGION = {"Karnataka": "South-Western", "Maharashtra": "Western", "Tamil Nadu": "Southern", "Delhi": "Northern"}
# Placeholder SLA days (AGENTS.md rule 4: not official norms); used only when no SlaRule row exists.
FALLBACK_DAYS = {"HIGH": 15, "MEDIUM": 30, "LOW": 45}
SEED_INST_PREFIX, SEED_CASE_PREFIX = "SYN-AICTE-", "SYN-CASE-"


def _get_or_create(db, model, key: dict, **extra):
    row = db.query(model).filter_by(**key).first()
    if row is None:
        row = model(**key, **extra)
        db.add(row)
        db.flush()
    return row


def reset_synthetic(db) -> dict:
    Case, Inst = _model(db, "cases"), _model(db, "institutions")
    cases = db.query(Case).filter(Case.case_no.like(f"{SEED_CASE_PREFIX}%")).all()
    n_cases = len(cases)
    for c in cases:
        db.delete(c)                 # ORM cascade removes actions/links/alerts/attachments/flags
    db.flush()
    insts = db.query(Inst).filter(Inst.aicte_permanent_id.like(f"{SEED_INST_PREFIX}%")).all()
    n_inst = len(insts)
    for i in insts:
        db.delete(i)
    db.commit()
    return {"cases_removed": n_cases, "institutions_removed": n_inst}


def seed_database(db, reset: bool = False, scan: bool = True) -> dict:
    d = data_dir()
    if not all((d / f).exists() for f in ("institutions.csv", "complaints.csv")):
        from .generate_data import main as generate
        generate()
    Institution, Case = _model(db, "institutions"), _model(db, "cases")
    Region, Bureau, Category = _model(db, "regions"), _model(db, "bureaus"), _model(db, "categories")
    try: CaseAction = _model(db, "case_actions")
    except RuntimeError: CaseAction = None
    try: SlaRule = _model(db, "sla_rules")
    except RuntimeError: SlaRule = None

    removed = reset_synthetic(db) if reset else {}

    regions = {n: _get_or_create(db, Region, {"name": n}).id for n in REGIONS}
    bureaus = {c: _get_or_create(db, Bureau, {"code": c}, name=n).id for c, n in BUREAUS.items()}
    cases_df = pd.read_csv(d / "complaints.csv", keep_default_na=False)
    categories = {n: _get_or_create(db, Category, {"name": n}).id for n in sorted(set(cases_df["category"]))}

    inst_df = pd.read_csv(d / "institutions.csv", keep_default_na=False)
    inst_map, inst_created = {}, 0
    for r in inst_df.to_dict("records"):
        row = db.query(Institution).filter_by(aicte_permanent_id=r["aicte_id"]).first()
        if row is None:
            row = Institution(aicte_permanent_id=r["aicte_id"], name=r["institution_name"], state=r["state"],
                              region_id=regions.get(STATE_TO_REGION.get(r["state"], "Southern")),
                              type="SYNTHETIC", status="ACTIVE", address="Synthetic demo address", district="Synthetic")
            db.add(row); db.flush(); inst_created += 1
        inst_map[r["institution_id"]] = row.id

    sla_days = {}
    if SlaRule is not None:
        for s in db.query(SlaRule).all():
            sla_days[(s.category_id, getattr(s.priority, "value", s.priority))] = s.days_to_dispose

    existing = {(c.case_no, c.bureau_id) for c in db.query(Case.case_no, Case.bureau_id).filter(Case.case_no.like(f"{SEED_CASE_PREFIX}%"))}
    created = skipped = 0
    for r in cases_df.to_dict("records"):
        bureau_id = bureaus[r["bureau"]]
        if (r["case_no"], bureau_id) in existing:
            skipped += 1; continue
        received = datetime.fromisoformat(r["created_at"]).date()
        cat_id = categories[r["category"]]
        prio = "MEDIUM"
        days = sla_days.get((cat_id, prio), FALLBACK_DAYS[prio])
        acted_at = datetime.combine(received, datetime.min.time(), tzinfo=timezone.utc)   # DateTime column, not date
        case = Case(case_no=r["case_no"], institution_id=inst_map[r["institution_id"]], bureau_id=bureau_id,
                    category_id=cat_id, status=r["status"], received_on=received, last_action_on=acted_at,
                    last_action_text="Synthetic demo case imported", expected_disposal_on=received + timedelta(days=days),
                    priority=prio, summary=r["summary"], complainant_ref=r["complainant_ref"] or None,
                    source="SYNTHETIC",
                    link_group_id=None,            # ground-truth group_id must NOT leak into the product as "already linked"
                    needs_institution_review=False)
        db.add(case); db.flush()
        if CaseAction is not None:                 # append-only audit trail starts with CREATED (AGENTS.md)
            db.add(CaseAction(case_id=case.id, actor_id=None, bureau_id=bureau_id, action_type="CREATED",
                              from_status=None, to_status="PENDING", remarks="Synthetic demo case imported", created_at=acted_at))
        created += 1
    db.commit()

    result = {"institutions": len(inst_map), "institutions_created": inst_created, "cases_created": created,
              "cases_skipped_existing": skipped, "synthetic": True, **removed}
    if scan:
        from .overlap import scan_overlaps
        result["overlap_flags_created"] = scan_overlaps(db)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--reset", action="store_true", help="delete previously seeded SYNTHETIC rows first")
    p.add_argument("--no-scan", action="store_true", help="skip the overlap scan after seeding")
    args = p.parse_args()
    from app.database import SessionLocal, get_engine
    if SessionLocal.kw.get("bind") is None:
        SessionLocal.configure(bind=get_engine())
    db = SessionLocal()
    try:
        print(seed_database(db, reset=args.reset, scan=not args.no_scan))
    finally:
        db.close()


if __name__ == "__main__":
    main()
