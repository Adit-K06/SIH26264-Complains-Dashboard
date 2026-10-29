"""CSV and JSON report endpoints."""
from __future__ import annotations

import csv
import io
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

from app.analytics import report_rows
from app.db import get_db
from app.models import User
from app.security import get_current_user

router = APIRouter()
REPORT_TYPES = {
    "bureau",
    "region",
    "institution",
    "ageing",
    "disposal-rate",
    "status",
    "overlaps",
    "monthly",
}


@router.get("/reports/{report_type}")
def report(
    report_type: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    format: Literal["csv", "json"] = Query(default="json"),
):
    if report_type not in REPORT_TYPES:
        raise HTTPException(
            status_code=404,
            detail={"code": "REPORT_NOT_FOUND", "message": "Unknown report type."},
        )
    rows = report_rows(db, report_type)
    if format == "json":
        return JSONResponse(content={"items": rows, "total": len(rows)})
    output = io.StringIO(newline="")
    fieldnames = list(rows[0]) if rows else ["empty"]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{report_type}.csv"'},
    )