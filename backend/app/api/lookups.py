"""Lookup / reference-data API router.

Endpoints:
  GET /bureaus    – all bureaus (id, code, name)
  GET /regions    – all regions (id, name)
  GET /categories – all categories (id, name)

These endpoints return the complete static reference tables that the frontend
uses to populate filter dropdowns (bureau_id, region_id, category_id). They
replace the hard-coded arrays in frontend/src/lib/lookups.ts when live mode
is enabled.

All endpoints:
  - Require authentication (any active role, any bureau/region scope).
  - Return the full list without pagination — these tables are small and static.
  - Are read-only. No write operations are exposed.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Bureau, Category, Region, User

router = APIRouter(tags=["lookups"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class BureauOut(BaseModel):
    id: int
    code: str
    name: str

    model_config = {"from_attributes": True}


class RegionOut(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class CategoryOut(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# GET /bureaus
# ---------------------------------------------------------------------------

@router.get("/bureaus", response_model=list[BureauOut])
def list_bureaus(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return all bureaus ordered by code. Used to populate filter dropdowns."""
    return db.query(Bureau).order_by(Bureau.code.asc()).all()


# ---------------------------------------------------------------------------
# GET /regions
# ---------------------------------------------------------------------------

@router.get("/regions", response_model=list[RegionOut])
def list_regions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return all regions ordered by name. Used to populate filter dropdowns."""
    return db.query(Region).order_by(Region.name.asc()).all()


# ---------------------------------------------------------------------------
# GET /categories
# ---------------------------------------------------------------------------

@router.get("/categories", response_model=list[CategoryOut])
def list_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return all categories ordered by name. Used to populate filter dropdowns."""
    return db.query(Category).order_by(Category.name.asc()).all()
