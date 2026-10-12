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


def test_set_turnout_sends_activate_and_updates_state() -> None:
    client, tx = _client()
    resp = client.put("/api/turnouts/5", json={"position": 1})
    assert resp.status_code == 204
    # Mindestens das Aktivieren muss gesendet worden sein.
    assert protocol.build_set_turnout(5, 1, activate=True) in tx.sent
    state = client.get("/api/turnouts/5").json()
    assert state["position"] == 1


def test_get_turnout_unknown_returns_null_position() -> None:
    client, _ = _client()
    body = client.get("/api/turnouts/99").json()
    assert body["address"] == 99
    assert body["position"] is None


def test_turnout_position_validation() -> None:
    client, _ = _client()
    assert client.put("/api/turnouts/5", json={"position": 2}).status_code == 422


def test_drive_validation_rejects_out_of_range_speed() -> None:
    # Die modusabhaengige Range-Pruefung liegt jetzt in build_loco_drive
    # (nicht mehr im Pydantic-Schema), daher 400 statt 422.
    client, _ = _client()
    assert client.put("/api/locos/3/drive", json={"speed": 200}).status_code == 400


def _can_detector_payload(
    nid: int, addr: int, port: int, typ: int, value1: int, value2: int = 0
) -> bytes:
    return (
        nid.to_bytes(2, "little")
        + addr.to_bytes(2, "little")
        + bytes([port, typ])
        + value1.to_bytes(2, "little")
        + value2.to_bytes(2, "little")
    )


def test_get_detectors_status_text_and_locos() -> None:
    client, _ = _client()
    controller = client.app.state.controller  # type: ignore[attr-defined]
    # Eingang (nid 0xD764, port 0): besetzt mit Spannung + zwei Lokadressen.
    controller.on_raw(0xC4, _can_detector_payload(0xD764, 0, 0, 0x01, 0x1100))
    controller.on_raw(0xC4, _can_detector_payload(0xD764, 0, 0, 0x11, 0x8003, 0xC02A))
    # Zweiter Eingang (port 1): frei mit Spannung.
    controller.on_raw(0xC4, _can_detector_payload(0xD764, 0, 1, 0x01, 0x0100))

    body = client.get("/api/detectors").json()
    detectors = body["detectors"]
    assert len(detectors) == 2
    # Sortierung nach (addr, nid, port): port 0 vor port 1.
    first = detectors[0]
    assert first["port"] == 0
    assert first["occupied"] is True
    assert first["status_text"] == "besetzt (mit Spannung)"
    assert first["locos"] == [
        {"address": 3, "direction": "forward"},
        {"address": 42, "direction": "backward"},
    ]
    assert detectors[1]["port"] == 1
    assert detectors[1]["status_text"] == "frei (mit Spannung)"


def test_get_detectors_overload_status_text() -> None:
    client, _ = _client()
    controller = client.app.state.controller  # type: ignore[attr-defined]
    controller.on_raw(0xC4, _can_detector_payload(0xD764, 0, 0, 0x01, 0x1202))
    body = client.get("/api/detectors").json()
    assert body["detectors"][0]["status_text"] == "besetzt (Ueberlast 2)"


def test_refresh_detectors_sends_query() -> None:
    client, tx = _client()
    resp = client.post("/api/detectors/refresh")
    assert resp.status_code == 204
    assert protocol.build_get_can_detectors() in tx.sent
