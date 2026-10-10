"""Fachlogik-Controller: verbindet Z21-Transport und zentralen Zustand.

Haelt die Single Source of Truth (LayoutState). Kommandos werden ueber einen
Z21Transport gesendet; eingehende Meldungen aktualisieren den Zustand. Der
Controller haengt nur vom Transport-Protokoll ab, nicht von einer konkreten
UDP-Implementierung -> testbar mit einem Fake-Transport.
"""

from __future__ import annotations

from collections.abc import Callable

from modellbahn.domain.state import LayoutState
from modellbahn.z21 import messages, protocol
from modellbahn.z21.client import Z21Transport


class LocoController:
    """Steuert Loks und Gleisspannung und pflegt den Anlagenzustand."""

    def __init__(
        self,
        transport: Z21Transport | None = None,
        state: LayoutState | None = None,
        on_change: Callable[[], None] | None = None,
    ) -> None:
        self._transport = transport
        self.state = state or LayoutState()
        self._on_change = on_change

    def set_transport(self, transport: Z21Transport) -> None:
        """Setzt den Transport nachtraeglich (fuer die App-Verdrahtung)."""
        self._transport = transport

    @property
    def _tx(self) -> Z21Transport:
        if self._transport is None:
            raise RuntimeError("Kein Z21-Transport gesetzt")
        return self._transport

    def _notify(self) -> None:
        if self._on_change is not None:
            self._on_change()

    # --- eingehende Meldungen ------------------------------------------

    def on_raw(self, header: int, data: bytes) -> None:
        """Callback fuer empfangene Z21-Datensaetze; aktualisiert den Zustand."""
        # Jede empfangene Meldung belegt eine bestehende Verbindung.
        self.state.connected = True
        message = messages.parse_message(header, data)
        if isinstance(message, messages.LocoInfo):
            loco = self.state.loco(message.address)
            loco.speed = message.speed
            loco.forward = message.forward
            loco.functions.update(message.functions)
        elif isinstance(message, messages.TrackPower):
            self.state.track_power_on = message.on
        self._notify()

    # --- ausgehende Kommandos ------------------------------------------

    def set_track_power(self, on: bool) -> None:
        dataset = protocol.build_track_power_on() if on else protocol.build_track_power_off()
        self._tx.send(dataset)
        self.state.track_power_on = on
        self._notify()

    def drive(self, address: int, speed: int, forward: bool) -> None:
        self._tx.send(protocol.build_loco_drive(address, speed, forward))
        loco = self.state.loco(address)
        loco.speed = speed
        loco.forward = forward
        self._notify()

    def set_function(self, address: int, function: int, on: bool) -> None:
        self._tx.send(protocol.build_loco_function(address, function, on))
        self.state.loco(address).functions[function] = on
        self._notify()

    def request_status(self) -> None:
        self._tx.send(protocol.build_get_status())
