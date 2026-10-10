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
class LayoutState:
    """Gesamtzustand der Anlage fuer den MVP.

    Erweiterbar um Weichen, Rueckmelder und Bloecke in spaeteren Versionen.
    """

    connected: bool = False
    track_power_on: bool = False
    locos: dict[int, LocoState] = field(default_factory=dict)

    def loco(self, address: int) -> LocoState:
        """Liefert den Lok-Zustand, legt ihn bei Bedarf an."""
        if address not in self.locos:
            self.locos[address] = LocoState(address=address)
        return self.locos[address]
