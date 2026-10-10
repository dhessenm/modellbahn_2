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
