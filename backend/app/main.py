"""FastAPI application for the AICTE complaint coordination dashboard."""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.admin import router as admin_router
from app.api.alerts import router as alerts_router
from app.api.auth import router as auth_router
from app.api.cases import router as cases_router
from app.api.copilot import router as copilot_router
from app.api.dashboard import router as dashboard_router
from app.api.institutions import router as institutions_router
from app.api.overlaps import router as overlaps_router
from app.api.reports import router as reports_router
from app.config import settings
from app.db import create_tables


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_tables()
    yield


app = FastAPI(
    title="AICTE Complaint Coordination Dashboard",
    description=(
        "Monitoring and coordination across existing AICTE Bureau/Cell systems. "
        "Demo uses synthetic data. SLA values are placeholders, not official AICTE norms."
    ),
    version="0.2.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict) and "code" in exc.detail and "message" in exc.detail:
        error = exc.detail
    else:
        codes = {
            400: "BAD_REQUEST",
            401: "UNAUTHENTICATED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            409: "CONFLICT",
            422: "VALIDATION_ERROR",
        }
        error = {"code": codes.get(exc.status_code, "HTTP_ERROR"), "message": str(exc.detail)}
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": error},
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    messages = [
        f"{'.'.join(str(part) for part in error.get('loc', ()))}: {error.get('msg', 'invalid value')}"
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "; ".join(messages),
            }
        },
    )


app.include_router(auth_router, prefix="/api")
app.include_router(institutions_router, prefix="/api")
app.include_router(cases_router, prefix="/api")
app.include_router(overlaps_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(alerts_router, prefix="/api")
app.include_router(copilot_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
app.include_router(admin_router, prefix="/api")


@app.get("/api/health", tags=["health"])
def health() -> dict:
    return {
        "status": "ok",
        "service": "aicte-dashboard-api",
        "env": settings.APP_ENV,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {"message": "AICTE Complaint Dashboard API. See /api/docs."}