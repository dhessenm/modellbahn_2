"""API-Tests ueber den FastAPI-TestClient (ohne reale Zentrale)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from modellbahn.api import create_app


def test_health() -> None:
    client = TestClient(create_app())
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_system_status_defaults() -> None:
    client = TestClient(create_app())
    resp = client.get("/api/system/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is False
    assert body["track_power_on"] is False
