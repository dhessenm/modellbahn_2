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
class DetectorInput:
    """Zustand eines CAN-Belegtmelder-Eingangs (Roco Z21 Detector 10808).

    Schluessel ist (nid, port): nid = unveraenderbare CAN-NetworkID des Moduls
    (stabile Melder-Identitaet), port = Eingang 0..7. addr = konfigurierbare
    Moduladresse, nur Anzeigeinfo (kann 0 sein, nicht zum Schluesseln nutzen).

    locos haelt die per RailCom erkannten Loks als (address, direction)-Tupel
    (domain-eigene, JSON-serialisierbare Darstellung; bewusst nicht die
    messages-Dataclass importiert, um die Schichtentrennung zu wahren).
    """

    nid: int
    port: int
    addr: int = 0
    occupied: bool = False
    with_power: bool = False
    overload: bool = False
    overload_level: int = 0
    locos: list[tuple[int, str]] = field(default_factory=list)


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
    detectors: dict[tuple[int, int], DetectorInput] = field(default_factory=dict)

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

    def detector(self, nid: int, port: int, addr: int = 0) -> DetectorInput:
        """Liefert den Belegtmelder-Eingang (nid, port), legt ihn bei Bedarf an.

        addr wird aktualisiert, wenn ein Wert != 0 mitgegeben wird (Anzeigeinfo).
        """
        key = (nid, port)
        if key not in self.detectors:
            self.detectors[key] = DetectorInput(nid=nid, port=port, addr=addr)
        elif addr:
            self.detectors[key].addr = addr
        return self.detectors[key]
