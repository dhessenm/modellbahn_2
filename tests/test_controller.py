"""Tests der Fachlogik gegen einen Fake-Transport (ohne reale Zentrale)."""

from __future__ import annotations

from modellbahn.domain.controller import LocoController
from modellbahn.z21 import protocol


class FakeTransport:
    """Sammelt gesendete Datensaetze; erfuellt den Z21Transport-Vertrag."""

    def __init__(self) -> None:
        self.sent: list[bytes] = []

    async def start(self) -> None:  # pragma: no cover - im Test nicht genutzt
        pass

    async def stop(self) -> None:  # pragma: no cover
        pass

    def send(self, dataset: bytes) -> None:
        self.sent.append(dataset)


def test_drive_sends_command_and_updates_state() -> None:
    tx = FakeTransport()
    changes: list[int] = []
    ctrl = LocoController(transport=tx, on_change=lambda: changes.append(1))

    ctrl.drive(address=3, speed=20, forward=False)

    assert tx.sent == [protocol.build_loco_drive(3, 20, forward=False)]
    assert ctrl.state.loco(3).speed == 20
    assert ctrl.state.loco(3).forward is False
    assert changes  # on_change wurde ausgeloest


def test_set_function_updates_state() -> None:
    tx = FakeTransport()
    ctrl = LocoController(transport=tx)
    ctrl.set_function(address=3, function=1, on=True)
    assert ctrl.state.loco(3).functions[1] is True
    assert tx.sent[-1] == protocol.build_loco_function(3, 1, on=True)


def test_track_power_updates_state() -> None:
    tx = FakeTransport()
    ctrl = LocoController(transport=tx)
    ctrl.set_track_power(True)
    assert ctrl.state.track_power_on is True
    assert tx.sent[-1] == protocol.build_track_power_on()


def test_incoming_loco_info_marks_connected_and_updates_state() -> None:
    tx = FakeTransport()
    ctrl = LocoController(transport=tx)
    # LAN_X_LOCO_INFO fuer Adresse 3, Fahrstufe 10 vorwaerts, F0 ein
    payload = bytes([0xEF, 0x00, 0x03, 0x04, 0x80 | 11, 0x10])
    ctrl.on_raw(0x40, payload)
    assert ctrl.state.connected is True
    assert ctrl.state.loco(3).speed == 10
    assert ctrl.state.loco(3).functions[0] is True


def test_set_turnout_sends_activate_and_updates_state() -> None:
    tx = FakeTransport()
    ctrl = LocoController(transport=tx)
    ctrl.set_turnout(address=5, position=1)
    assert tx.sent[-1] == protocol.build_set_turnout(5, 1, activate=True)
    assert ctrl.state.turnout(5).position == 1


def test_deactivate_turnout_sends_deactivate() -> None:
    tx = FakeTransport()
    ctrl = LocoController(transport=tx)
    ctrl.deactivate_turnout(address=5, position=1)
    assert tx.sent[-1] == protocol.build_set_turnout(5, 1, activate=False)


def test_incoming_turnout_info_updates_state() -> None:
    tx = FakeTransport()
    ctrl = LocoController(transport=tx)
    ctrl.on_raw(0x40, bytes([0x43, 0x00, 0x05, 0b10]))  # Adresse 5, Position 1
    assert ctrl.state.turnout(5).position == 1


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


def test_incoming_detector_occupancy_updates_state_and_connects() -> None:
    tx = FakeTransport()
    ctrl = LocoController(transport=tx)
    # Typ 0x01, Value1 0x1100 = besetzt mit Spannung
    ctrl.on_raw(0xC4, _can_detector_payload(0xD764, 0, 0, 0x01, 0x1100))
    assert ctrl.state.connected is True
    detector = ctrl.state.detector(0xD764, 0)
    assert detector.occupied is True
    assert detector.with_power is True


def test_incoming_detector_locos_first_block_replaces_list() -> None:
    tx = FakeTransport()
    ctrl = LocoController(transport=tx)
    # Erste 0x11-Meldung: zwei Adressen
    ctrl.on_raw(0xC4, _can_detector_payload(0xD764, 0, 0, 0x11, 0x8003, 0xC02A))
    detector = ctrl.state.detector(0xD764, 0)
    assert detector.locos == [(3, "forward"), (42, "backward")]
    # Folgemeldung Typ 0x11 ersetzt (haengt nicht an)
    ctrl.on_raw(0xC4, _can_detector_payload(0xD764, 0, 0, 0x11, 0x8007))
    assert detector.locos == [(7, "forward")]


def test_request_detectors_sends_query() -> None:
    tx = FakeTransport()
    ctrl = LocoController(transport=tx)
    ctrl.request_detectors()
    assert tx.sent == [protocol.build_get_can_detectors()]
