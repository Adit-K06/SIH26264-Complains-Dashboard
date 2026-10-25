"""Locate the data/ and docs/ folders in both layouts this project runs in.

Local checkout:  <repo>/backend/app/ai/paths.py  -> data lives in <repo>/data
Docker (compose): ./backend is mounted at /app, ./data at /app/data, ./docs at /app/docs

The old code used ``parents[3]``, which is the repo root locally but ``/`` inside the
container, so seed/evaluate looked in ``/data`` (the uploads volume) instead of ``/app/data``.
Override with the AI_DATA_DIR / AI_DOCS_DIR environment variables if needed.
"""
from __future__ import annotations

import os
from pathlib import Path

_HERE = Path(__file__).resolve()
BACKEND_DIR = _HERE.parents[2]          # <repo>/backend  or  /app
REPO_DIR = _HERE.parents[3]             # <repo>          or  /


def _resolve(env_name: str, folder: str) -> Path:
    override = os.getenv(env_name)
    if override:
        return Path(override)
    inside_backend = BACKEND_DIR / folder
    if inside_backend.is_dir():         # Docker bind mount, or a copy placed in backend/
        return inside_backend
    if REPO_DIR != Path(REPO_DIR.anchor):   # real repo root (not the filesystem root)
        return REPO_DIR / folder
    return inside_backend


def data_dir() -> Path:
    return _resolve("AI_DATA_DIR", "data")


def docs_dir() -> Path:
    return _resolve("AI_DOCS_DIR", "docs")
