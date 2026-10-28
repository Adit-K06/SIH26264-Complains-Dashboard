"""P0 — Health endpoint test."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "aicte-dashboard-api"
    assert "timestamp" in data


def test_root_returns_200() -> None:
    response = client.get("/")
    assert response.status_code == 200
