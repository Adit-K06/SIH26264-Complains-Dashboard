"""Administration-only demo controls and evaluation report."""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db import get_db
from app.models import User
from app.security import get_current_user
from app.sla import run_sla_check

router = APIRouter()
REPO_ROOT = Path(__file__).resolve().parents[3]


@router.post("/admin/demo/forward")
def forward_demo_clock(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    days: int = Query(ge=0, le=3650),
):
    require_admin(user)
    as_of = date.today() + timedelta(days=days)
    result = run_sla_check(db, as_of)
    db.commit()
    return {"days_forwarded": days, "as_of": as_of.isoformat(), **result}


@router.get("/admin/evaluation")
def evaluation(
    user: Annotated[User, Depends(get_current_user)],
):
    require_admin(user)
    path = REPO_ROOT / "docs" / "evaluation.json"
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail={"code": "EVALUATION_NOT_FOUND", "message": "Run python -m app.ai.evaluate first."},
        )
    return json.loads(path.read_text(encoding="utf-8"))