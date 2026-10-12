"""API-Tests fuer die Lokverwaltung (`/api/roster`).

Nutzt den FastAPI-TestClient ohne reale Zentrale (FakeTransport). Der
`roster_path` zeigt auf eine `tmp_path`-Datei, damit nie nach `conf/`
geschrieben wird.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from modellbahn.api import create_app
from modellbahn.config import Settings
from modellbahn.domain.roster_codec import RosterDecodeError


class FakeTransport:
    def __init__(self) -> None:
        self.sent: list[bytes] = []

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    def send(self, dataset: bytes) -> None:
        self.sent.append(dataset)


def _client(tmp_path: Path) -> TestClient:
    settings = Settings(
        roster_path=tmp_path / "roster.json",
        layout_path=tmp_path / "layout.json",
    )
    app = create_app(settings=settings, transport=FakeTransport())
    return TestClient(app)


def _new_loco(client: TestClient, name: str, address: int = 3, **kwargs: object) -> dict:
    resp = client.post("/api/roster", json={"name": name, "address": address, **kwargs})
    assert resp.status_code == 201, resp.text
    return resp.json()["entity"]


# ---------------------------------------------------------------------------
# GET (leer + nach Anlegen)
# ---------------------------------------------------------------------------
def test_get_roster_empty(tmp_path: Path) -> None:
    client = _client(tmp_path)
    body = client.get("/api/roster").json()
    assert body == {"locomotives": []}


def test_create_and_get_loco(tmp_path: Path) -> None:
    client = _client(tmp_path)
    entity = _new_loco(client, "BR 101", address=3, max_speed_kmh=220)
    assert entity["id"]
    assert entity["name"] == "BR 101"
    assert entity["address"] == 3
    assert entity["max_speed_kmh"] == 220
    assert entity["speed_steps"] == 128  # Default

    # Einzelabruf
    resp = client.get(f"/api/roster/{entity['id']}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "BR 101"

    # In der Gesamtliste
    roster = client.get("/api/roster").json()
    assert len(roster["locomotives"]) == 1


def test_create_persists(tmp_path: Path) -> None:
    client = _client(tmp_path)
    _new_loco(client, "BR 101")
    assert (tmp_path / "roster.json").exists()


# ---------------------------------------------------------------------------
# Validierung (400)
# ---------------------------------------------------------------------------
def test_create_duplicate_name_400(tmp_path: Path) -> None:
    client = _client(tmp_path)
    _new_loco(client, "BR 101")
    resp = client.post("/api/roster", json={"name": "br 101", "address": 5})
    assert resp.status_code == 400


def test_create_invalid_speed_steps_400(tmp_path: Path) -> None:
    client = _client(tmp_path)
    resp = client.post("/api/roster", json={"name": "Lok", "address": 3, "speed_steps": 64})
    assert resp.status_code == 400


def test_create_address_out_of_range_422(tmp_path: Path) -> None:
    """Adresse ausserhalb 1–9999 wird vom Pydantic-Schema abgelehnt (422)."""
    client = _client(tmp_path)
    resp = client.post("/api/roster", json={"name": "Lok", "address": 0})
    assert resp.status_code == 422
    resp2 = client.post("/api/roster", json={"name": "Lok", "address": 10000})
    assert resp2.status_code == 422


# ---------------------------------------------------------------------------
# 404
# ---------------------------------------------------------------------------
def test_get_unknown_404(tmp_path: Path) -> None:
    client = _client(tmp_path)
    assert client.get("/api/roster/nope").status_code == 404


def test_put_unknown_404(tmp_path: Path) -> None:
    client = _client(tmp_path)
    resp = client.put("/api/roster/nope", json={"name": "X", "address": 1})
    assert resp.status_code == 404


def test_delete_unknown_404(tmp_path: Path) -> None:
    client = _client(tmp_path)
    assert client.delete("/api/roster/nope").status_code == 404


# ---------------------------------------------------------------------------
# Update + Delete
# ---------------------------------------------------------------------------
def test_update_loco(tmp_path: Path) -> None:
    client = _client(tmp_path)
    entity = _new_loco(client, "BR 101", address=3)
    resp = client.put(
        f"/api/roster/{entity['id']}",
        json={"name": "BR 101 ICE", "address": 3, "speed_steps": 28},
    )
    assert resp.status_code == 200
    assert resp.json()["entity"]["name"] == "BR 101 ICE"
    assert resp.json()["entity"]["speed_steps"] == 28


def test_delete_loco(tmp_path: Path) -> None:
    client = _client(tmp_path)
    entity = _new_loco(client, "BR 101")
    assert client.delete(f"/api/roster/{entity['id']}").status_code == 204
    assert client.get("/api/roster").json()["locomotives"] == []


# ---------------------------------------------------------------------------
# Adress-Warnung (Duplikat, kein Fehler)
# ---------------------------------------------------------------------------
def test_address_duplicate_warning(tmp_path: Path) -> None:
    client = _client(tmp_path)
    _new_loco(client, "BR 101", address=3)
    resp = client.post("/api/roster", json={"name": "BR 103", "address": 3})
    assert resp.status_code == 201  # Kein Fehler!
    warnings = resp.json()["warnings"]
    assert any(w["code"] == "adresse_doppelt" for w in warnings)


def test_no_warning_on_unique_address(tmp_path: Path) -> None:
    client = _client(tmp_path)
    resp = client.post("/api/roster", json={"name": "BR 101", "address": 3})
    assert resp.status_code == 201
    assert resp.json()["warnings"] == []


# ---------------------------------------------------------------------------
# Start-Abbruch bei kaputter Roster-Datei
# ---------------------------------------------------------------------------
def test_create_app_aborts_on_broken_roster(tmp_path: Path) -> None:
    broken = tmp_path / "roster.json"
    broken.write_text("{ kaputt", encoding="utf-8")
    settings = Settings(
        roster_path=broken,
        layout_path=tmp_path / "layout.json",
    )
    with pytest.raises(RosterDecodeError):
        create_app(settings=settings, transport=FakeTransport())
