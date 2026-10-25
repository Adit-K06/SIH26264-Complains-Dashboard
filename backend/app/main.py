"""FastAPI entrypoint. Routers are auto-discovered: any module in app/api/ that defines
`router` is mounted under /api/v1. This avoids merge conflicts between P1 and P4."""
import importlib
import os
import pkgutil

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.api as api_pkg

app = FastAPI(title="SIH26264 Complaint Dashboard (synthetic demo data)")
cors_origins_raw = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:8000,http://localhost:3000")
origins = [o.strip() for o in cors_origins_raw.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"^https://.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

root = APIRouter(prefix="/api/v1")


@root.get("/health")
def health():
    return {"status": "ok"}


for m in pkgutil.iter_modules(api_pkg.__path__):
    mod = importlib.import_module(f"app.api.{m.name}")
    r = getattr(mod, "router", None)
    if r is not None:
        root.include_router(r)

app.include_router(root)
