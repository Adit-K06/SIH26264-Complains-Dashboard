"""Idempotently seed reference tables and synthetic institutions/cases into the app DB.

The backend owns SQLAlchemy models/session setup. This module discovers those mapped
classes by table name and accepts a Session in seed_database(db); CLI mode looks for
SessionLocal in app.database or app.db.
"""
from __future__ import annotations
import argparse
from datetime import datetime
from pathlib import Path
import pandas as pd
from .overlap import _model

ROOT=Path(__file__).resolve().parents[3]
DATA=ROOT/"data"
REGIONS=["Central","Eastern","North-Eastern","Northern","Southern","South-Western","Western"]
BUREAUS={"RB":"Regional Bureau","PGRC":"Public Grievance Redressal Cell","APPROVAL":"Approval Bureau","ACADEMIC":"Academic Bureau","FINANCE":"Finance Bureau"}

def _value(model, **kwargs):
    allowed=set(model.__table__.columns.keys())
    return model(**{k:v for k,v in kwargs.items() if k in allowed})

def _find(db, model, **criteria):
    q=db.query(model)
    for key,value in criteria.items():
        if hasattr(model,key): q=q.filter(getattr(model,key)==value)
    return q.first()

def seed_database(db, reset=False):
    """Seed data idempotently. reset is intentionally non-destructive and does not drop tables."""
    files=[DATA/"institutions.csv",DATA/"complaints.csv"]
    if not all(p.exists() for p in files):
        from .generate_data import main
        main()
    Institution=_model(db,"institutions"); Case=_model(db,"cases")
    try: Region=_model(db,"regions")
    except RuntimeError: Region=None
    try: Bureau=_model(db,"bureaus")
    except RuntimeError: Bureau=None
    try: Category=_model(db,"categories")
    except RuntimeError: Category=None
    regions={}
    if Region:
        for name in REGIONS:
            row=_find(db,Region,name=name)
            if row is None:
                row=_value(Region,name=name); db.add(row); db.flush()
            regions[name]=row.id
    bureaus={}
    if Bureau:
        for code,name in BUREAUS.items():
            row=_find(db,Bureau,code=code)
            if row is None:
                row=_value(Bureau,code=code,name=name); db.add(row); db.flush()
            bureaus[code]=row.id
    categories={}
    if Category:
        for name in sorted(set(pd.read_csv(DATA/"complaints.csv")["category"])):
            row=_find(db,Category,name=name)
            if row is None:
                row=_value(Category,name=name); db.add(row); db.flush()
            categories[name]=row.id
    inst_df=pd.read_csv(DATA/"institutions.csv",keep_default_na=False)
    inst_map={}
    for r in inst_df.to_dict("records"):
        # Stable mapping via AICTE permanent ID where supported; synthetic IDs are not official IDs.
        key=r.get("aicte_id","")
        row=_find(db,Institution,aicte_permanent_id=key) if hasattr(Institution,"aicte_permanent_id") else _find(db,Institution,name=r["institution_name"])
        if row is None:
            region_id=regions.get("Southern")
            row=_value(Institution,aicte_permanent_id=key,name=r["institution_name"],state=r["state"],region_id=region_id,type="SYNTHETIC",status="ACTIVE",address="Synthetic demo address",district="Synthetic")
            db.add(row); db.flush()
        inst_map[r["institution_id"]]=row.id
    cases_df=pd.read_csv(DATA/"complaints.csv",keep_default_na=False)
    created=0; duplicates=0
    for r in cases_df.to_dict("records"):
        bureau_id=bureaus.get(r["bureau"])
        existing_q=db.query(Case).filter(Case.case_no==r["case_no"])
        if bureau_id is not None and hasattr(Case,"bureau_id"): existing_q=existing_q.filter(Case.bureau_id==bureau_id)
        if existing_q.first() is not None:
            duplicates+=1; continue
        inst_id=inst_map.get(r["institution_id"])
        received=datetime.fromisoformat(r["created_at"]).date()
        kwargs={"case_no":r["case_no"],"institution_id":inst_id,"bureau_id":bureau_id,"category_id":categories.get(r["category"]),"status":r["status"],"received_on":received,"last_action_on":received,"last_action_text":"Synthetic demo case imported","summary":r["summary"],"complainant_ref":r["complainant_ref"] or None,"source":"SYNTHETIC","link_group_id":r["group_id"] or None,"needs_institution_review":False,"priority":"MEDIUM"}
        db.add(_value(Case,**kwargs)); created+=1
    db.commit()
    return {"institutions":len(inst_map),"cases_created":created,"cases_skipped_existing":duplicates,"synthetic":True}

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--reset",action="store_true",help="compatibility flag; does not delete existing data")
    args=parser.parse_args()
    session_factory=None
    for module_name in ("app.database","app.db"):
        try:
            module=__import__(module_name,fromlist=["SessionLocal"]); session_factory=getattr(module,"SessionLocal",None)
            if session_factory: break
        except ImportError: pass
    if session_factory is None:
        raise SystemExit("Could not find SessionLocal in app.database or app.db. Import seed_database(db) from your backend's DB session instead.")
    db=session_factory()
    try: print(seed_database(db,reset=args.reset))
    finally: db.close()
if __name__=="__main__": main()
