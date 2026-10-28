"""FastAPI application factory — P0: health endpoint only."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AICTE Complaint Coordination Dashboard",
    description=(
        "Integrated Dashboard for Monitoring and Tracking Institution-Related "
        "Complaint Cases Across AICTE Bureaus/Cells — SIH26264. "
        "Demo uses synthetic data. SLA values are placeholders, not official AICTE norms."
    ),
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ---------------------------------------------------------------------------
# CORS — allow frontend dev server and production nginx origin
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev
        "http://localhost:3000",
        "http://localhost",
        "http://web",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health endpoint (P0 requirement)
# ---------------------------------------------------------------------------
@app.get("/api/health", tags=["health"])
def health() -> dict:
    """Liveness check. Returns service status and UTC timestamp."""
    return {
        "status": "ok",
        "service": "aicte-dashboard-api",
        "env": settings.APP_ENV,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Root redirect hint
# ---------------------------------------------------------------------------
@app.get("/", include_in_schema=False)
def root() -> dict:
    return {"message": "AICTE Complaint Dashboard API. See /api/docs."}
