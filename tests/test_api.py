"""API-Tests ueber den FastAPI-TestClient (ohne reale Zentrale)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from modellbahn.api import create_app
from modellbahn.z21 import protocol


class FakeTransport:
    def __init__(self) -> None:
        self.sent: list[bytes] = []

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    def send(self, dataset: bytes) -> None:
        self.sent.append(dataset)


def _client() -> tuple[TestClient, FakeTransport]:
    tx = FakeTransport()
    app = create_app(transport=tx)
    return TestClient(app), tx


def test_health() -> None:
    client, _ = _client()
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_system_status_defaults() -> None:
    client, _ = _client()
    body = client.get("/api/system/status").json()
    assert body["connected"] is False
    assert body["track_power_on"] is False


def test_track_power_endpoint_sends_command() -> None:
    client, tx = _client()
    resp = client.post("/api/system/track-power", json={"on": True})
    assert resp.status_code == 204
    assert tx.sent[-1] == protocol.build_track_power_on()
    assert client.get("/api/system/status").json()["track_power_on"] is True


def test_drive_endpoint_updates_and_sends() -> None:
    client, tx = _client()
    resp = client.put("/api/locos/3/drive", json={"speed": 20, "forward": False})
    assert resp.status_code == 204
    assert tx.sent[-1] == protocol.build_loco_drive(3, 20, forward=False)
    loco = client.get("/api/locos/3").json()
    assert loco["speed"] == 20
    assert loco["forward"] is False


def test_function_endpoint() -> None:
    client, tx = _client()
    resp = client.put("/api/locos/3/function", json={"function": 1, "on": True})
    assert resp.status_code == 204
    assert tx.sent[-1] == protocol.build_loco_function(3, 1, on=True)
    assert client.get("/api/locos/3").json()["functions"]["1"] is True


def test_unknown_loco_returns_404() -> None:
    client, _ = _client()
    assert client.get("/api/locos/999").status_code == 404


def test_subscribe_loco_requests_info_from_central() -> None:
    client, tx = _client()
    resp = client.post("/api/locos/3/subscribe")
    assert resp.status_code == 204
    assert tx.sent[-1] == protocol.build_get_loco_info(3)


def test_drive_validation_rejects_out_of_range_speed() -> None:
    client, _ = _client()
    assert client.put("/api/locos/3/drive", json={"speed": 200}).status_code == 422
