"""Persistente Lok-Stammdaten der Lokverwaltung (vom Anwender gepflegt).

Dieses Modell beschreibt die verwalteten Lokomotiven als feste Stammdaten:
Name, DCC-Adresse, Fahrstufenmodus, Funktionsanzahl sowie optionale Angaben
(Laenge, Vorbild-Hoechstgeschwindigkeit, Freitext-Notizen). Es ist strikt
getrennt vom fluechtigen Live-Zustand einer Lok (`LocoState`), der aus den
Z21-Broadcasts gespeist wird; die Stammdaten werden dagegen persistiert und
nicht von der Zentrale veraendert.

Reine Dataclasses ohne IO-/FastAPI-/UDP-Abhaengigkeit. Laengen sind `int` in
Millimeter (mm), Geschwindigkeiten `int` in Kilometer pro Stunde (km/h) und
beziehen sich auf das Vorbild. Serialisierung, Validierung und Service-Logik
folgen in getrennten Modulen (`roster_codec`, `roster_service`).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Locomotive:
    """Stammdaten einer einzelnen verwalteten Lokomotive.

    `id` ist eine vom Service vergebene UUID4 (32-Zeichen-Hex). `name` ist unter
    allen Loks eindeutig (Pruefung im Service). `address` ist die DCC-Adresse
    (1..9999). `speed_steps` ist der Fahrstufenmodus (14, 28 oder 128).
    `function_count` ist die Anzahl der Funktionen F0..Fn (0..28). `length_mm`
    und `max_speed_kmh` sind optionale Angaben (mm bzw. Vorbild-km/h); `notes`
    ist Freitext.
    """

    id: str  # UUID4
    name: str  # eindeutig je Roster
    address: int  # DCC-Adresse 1..9999
    speed_steps: int = 128  # 14, 28 oder 128
    function_count: int = 28  # 0..28 (F0 bis Fn)
    length_mm: int | None = None  # Modell-Laenge in mm
    max_speed_kmh: int | None = None  # Vorbildgeschwindigkeit (km/h)
    notes: str = ""  # Freitext


@dataclass
class Roster:
    """Gesamtbestand der verwalteten Lokomotiven (nach ID indiziert).

    `version` erlaubt spaetere Migrationen des Persistenzformats.
    """

    version: int = 1
    locomotives: dict[str, Locomotive] = field(default_factory=dict)
