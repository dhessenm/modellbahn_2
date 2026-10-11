"""API-Tests fuer das statische Anlagenmodell (`/api/layout`).

Nutzt den FastAPI-TestClient ohne reale Zentrale (FakeTransport). Der
`layout_path` zeigt auf eine `tmp_path`-Datei, damit nie nach `conf/`
geschrieben wird; so sind Persistenz und Backup real pruefbar.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from modellbahn.api import create_app
from modellbahn.config import Settings
from modellbahn.domain.layout_codec import LayoutDecodeError


class FakeTransport:
    def __init__(self) -> None:
        self.sent: list[bytes] = []

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    def send(self, dataset: bytes) -> None:
        self.sent.append(dataset)


def _client(tmp_path: Path) -> tuple[TestClient, FakeTransport]:
    tx = FakeTransport()
    settings = Settings(layout_path=tmp_path / "layout.json")
    app = create_app(settings=settings, transport=tx)
    return TestClient(app), tx


def _new_block(client: TestClient, name: str, **kwargs: object) -> dict:
    resp = client.post("/api/layout/blocks", json={"name": name, **kwargs})
    assert resp.status_code == 201, resp.text
    return resp.json()["entity"]


# ---------------------------------------------------------------------------
# Lesen / Gesamtmodell
# ---------------------------------------------------------------------------
def test_get_layout_empty(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    body = client.get("/api/layout").json()
    assert body == {"blocks": [], "elements": [], "routes": []}


# ---------------------------------------------------------------------------
# Block-CRUD + Persistenz
# ---------------------------------------------------------------------------
def test_create_block_persists_and_appears(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    resp = client.post("/api/layout/blocks", json={"name": "B1"})
    assert resp.status_code == 201
    entity = resp.json()["entity"]
    assert entity["id"]
    assert entity["name"] == "B1"

    layout = client.get("/api/layout").json()
    assert [b["name"] for b in layout["blocks"]] == ["B1"]
    assert (tmp_path / "layout.json").exists()


def test_create_block_duplicate_name_returns_400(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    _new_block(client, "B1")
    resp = client.post("/api/layout/blocks", json={"name": "b1"})
    assert resp.status_code == 400


def test_set_detectors_duplicate_order_400_and_valid_200(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    block = _new_block(client, "B1")
    bad = client.put(
        f"/api/layout/blocks/{block['id']}/detectors",
        json={
            "detectors": [
                {"detector_nid": 1, "detector_port": 0, "order": 1},
                {"detector_nid": 1, "detector_port": 1, "order": 1},
            ]
        },
    )
    assert bad.status_code == 400

    good = client.put(
        f"/api/layout/blocks/{block['id']}/detectors",
        json={
            "detectors": [
                {"detector_nid": 1, "detector_port": 0, "order": 1},
                {"detector_nid": 1, "detector_port": 1, "order": 2},
            ]
        },
    )
    assert good.status_code == 200
    orders = [d["order"] for d in good.json()["entity"]["detectors"]]
    assert orders == [1, 2]


def test_block_write_passes_through_warnings(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    block = _new_block(client, "B1", length_mm=100)
    resp = client.put(
        f"/api/layout/blocks/{block['id']}/detectors",
        json={
            "detectors": [
                {"detector_nid": 1, "detector_port": 0, "order": 1, "length_mm": 30},
                {"detector_nid": 1, "detector_port": 1, "order": 2, "length_mm": 30},
            ]
        },
    )
    assert resp.status_code == 200
    codes = [w["code"] for w in resp.json()["warnings"]]
    assert "laengensumme" in codes


# ---------------------------------------------------------------------------
# Element-CRUD + Adressregeln
# ---------------------------------------------------------------------------
def test_create_elements_per_type(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    turnout = client.post(
        "/api/layout/elements",
        json={"name": "W1", "type": "turnout", "address": 10},
    )
    assert turnout.status_code == 201
    assert turnout.json()["type"] == "turnout"

    dkw = client.post(
        "/api/layout/elements",
        json={"name": "DKW1", "type": "dkw", "address": 11, "address_b": 12},
    )
    assert dkw.status_code == 201
    assert dkw.json()["address_b"] == 12

    crossing = client.post(
        "/api/layout/elements",
        json={"name": "K1", "type": "crossing"},
    )
    assert crossing.status_code == 201
    assert crossing.json()["address"] is None


def test_create_element_invalid_address_rules_400(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    # Weiche ohne Adresse.
    assert (
        client.post("/api/layout/elements", json={"name": "W1", "type": "turnout"}).status_code
        == 400
    )
    # Kreuzung mit Adresse.
    assert (
        client.post(
            "/api/layout/elements",
            json={"name": "K1", "type": "crossing", "address": 5},
        ).status_code
        == 400
    )


# ---------------------------------------------------------------------------
# Route-CRUD + Referenzen
# ---------------------------------------------------------------------------
def test_create_route_unknown_block_400_valid_201(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    start = _new_block(client, "Start")
    end = _new_block(client, "Ziel")

    bad = client.post(
        "/api/layout/routes",
        json={"name": "F1", "start_block_id": "unbekannt", "end_block_id": end["id"]},
    )
    assert bad.status_code == 400

    good = client.post(
        "/api/layout/routes",
        json={"name": "F1", "start_block_id": start["id"], "end_block_id": end["id"]},
    )
    assert good.status_code == 201
    assert good.json()["start_block_id"] == start["id"]


def test_delete_block_referenced_by_route_409(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    start = _new_block(client, "Start")
    end = _new_block(client, "Ziel")
    route = client.post(
        "/api/layout/routes",
        json={"name": "F1", "start_block_id": start["id"], "end_block_id": end["id"]},
    ).json()

    resp = client.delete(f"/api/layout/blocks/{start['id']}")
    assert resp.status_code == 409
    body = resp.json()["detail"]
    assert len(body["blocked_by"]) == 1
    blocker = body["blocked_by"][0]
    assert blocker["type"] == "route"
    assert blocker["id"] == route["id"]
    assert blocker["name"] == "F1"


# ---------------------------------------------------------------------------
# Runtime (abgeleiteter Blockzustand)
# ---------------------------------------------------------------------------
def test_runtime_occupied_and_unknown(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    with_det = _new_block(client, "Belegt")
    without_det = _new_block(client, "Ohne")

    resp = client.put(
        f"/api/layout/blocks/{with_det['id']}/detectors",
        json={"detectors": [{"detector_nid": 100, "detector_port": 0, "order": 1}]},
    )
    assert resp.status_code == 200

    controller = client.app.state.controller  # type: ignore[attr-defined]
    controller.state.detector(100, 0).occupied = True

    runtimes = {rt["block_id"]: rt for rt in client.get("/api/layout/runtime").json()}
    assert runtimes[with_det["id"]]["occupancy"] == "occupied"
    assert runtimes[without_det["id"]]["occupancy"] == "unknown"


# ---------------------------------------------------------------------------
# 404 fuer unbekannte Pfad-IDs
# ---------------------------------------------------------------------------
def test_mutations_on_unknown_ids_return_404(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    assert client.put("/api/layout/blocks/nope", json={"name": "X"}).status_code == 404
    assert client.delete("/api/layout/blocks/nope").status_code == 404
    assert (
        client.put(
            "/api/layout/elements/nope",
            json={"name": "X", "type": "turnout", "address": 1},
        ).status_code
        == 404
    )
    assert client.delete("/api/layout/elements/nope").status_code == 404
    assert (
        client.put(
            "/api/layout/routes/nope",
            json={"name": "X", "start_block_id": "a", "end_block_id": "b"},
        ).status_code
        == 404
    )
    assert client.delete("/api/layout/routes/nope").status_code == 404


# ---------------------------------------------------------------------------
# Start-Abbruch bei kaputter Modelldatei
# ---------------------------------------------------------------------------
def test_create_app_aborts_on_broken_file(tmp_path: Path) -> None:
    broken = tmp_path / "layout.json"
    broken.write_text("{ kein gueltiges json", encoding="utf-8")
    settings = Settings(layout_path=broken)
    with pytest.raises(LayoutDecodeError):
        create_app(settings=settings, transport=FakeTransport())


# ---------------------------------------------------------------------------
# Update-Happy-Paths (Review-Befund: Testluecken)
# ---------------------------------------------------------------------------
def test_update_element_changes_fields(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    element = client.post(
        "/api/layout/elements",
        json={"name": "W1", "type": "turnout", "address": 10},
    ).json()
    resp = client.put(
        f"/api/layout/elements/{element['id']}",
        json={"name": "W1-neu", "type": "turnout", "address": 20},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "W1-neu"
    assert resp.json()["address"] == 20
    # Persistiert und im Gesamtmodell sichtbar.
    layout = client.get("/api/layout").json()
    assert [e["name"] for e in layout["elements"]] == ["W1-neu"]


def test_update_route_changes_fields(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    start = _new_block(client, "Start")
    end = _new_block(client, "Ziel")
    other = _new_block(client, "Ziel2")
    route = client.post(
        "/api/layout/routes",
        json={"name": "F1", "start_block_id": start["id"], "end_block_id": end["id"]},
    ).json()
    resp = client.put(
        f"/api/layout/routes/{route['id']}",
        json={"name": "F1-neu", "start_block_id": start["id"], "end_block_id": other["id"]},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "F1-neu"
    assert resp.json()["end_block_id"] == other["id"]


# ---------------------------------------------------------------------------
# SSE-Signal bei Mutation (Kopplung an die UI)
# ---------------------------------------------------------------------------
def test_mutation_triggers_sse_publish(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    broker = client.app.state.broker  # type: ignore[attr-defined]
    queue = broker.subscribe()
    try:
        resp = client.post("/api/layout/blocks", json={"name": "B1"})
        assert resp.status_code == 201
        # Eine erfolgreiche Mutation signalisiert "changed" ueber den EventBroker.
        assert not queue.empty()
    finally:
        broker.unsubscribe(queue)


def test_failed_mutation_does_not_publish(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    _new_block(client, "B1")
    broker = client.app.state.broker  # type: ignore[attr-defined]
    queue = broker.subscribe()
    try:
        # Doppelter Name -> 400, keine Mutation, kein SSE-Signal.
        resp = client.post("/api/layout/blocks", json={"name": "b1"})
        assert resp.status_code == 400
        assert queue.empty()
    finally:
        broker.unsubscribe(queue)
