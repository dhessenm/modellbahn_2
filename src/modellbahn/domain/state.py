"""Massgeblicher Anlagenzustand (Single Source of Truth).

Dieser Zustand wird aus den Z21-Broadcasts aktualisiert und speist sowohl die
REST-Antworten als auch die Push-Events. Haengt nicht von FastAPI/UDP ab.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LocoState:
    """Zustand einer einzelnen Lok (DCC)."""

    address: int
    speed: int = 0
    forward: bool = True
    functions: dict[int, bool] = field(default_factory=dict)


@dataclass
class SystemInfo:
    """Zentralenstatus (aus LAN_SYSTEMSTATE_DATACHANGED abgeleitet)."""

    short_circuit: bool = False
    emergency_stop: bool = False
    temperature_c: int = 0
    supply_voltage_mv: int = 0
    track_voltage_mv: int = 0


@dataclass
class TurnoutState:
    """Zustand einer Weiche (DCC-Zubehoer)."""

    address: int
    position: int | None = None  # 0, 1 oder None (noch nicht geschaltet)


@dataclass
class LayoutState:
    """Gesamtzustand der Anlage fuer den MVP.

    Erweiterbar um Rueckmelder und Bloecke in spaeteren Versionen.
    """

    connected: bool = False
    track_power_on: bool = False
    system: SystemInfo = field(default_factory=SystemInfo)
    locos: dict[int, LocoState] = field(default_factory=dict)
    turnouts: dict[int, TurnoutState] = field(default_factory=dict)

    def loco(self, address: int) -> LocoState:
        """Liefert den Lok-Zustand, legt ihn bei Bedarf an."""
        if address not in self.locos:
            self.locos[address] = LocoState(address=address)
        return self.locos[address]

    def turnout(self, address: int) -> TurnoutState:
        """Liefert den Weichen-Zustand, legt ihn bei Bedarf an."""
        if address not in self.turnouts:
            self.turnouts[address] = TurnoutState(address=address)
        return self.turnouts[address]
