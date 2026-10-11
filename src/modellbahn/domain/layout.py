"""Statisches, persistentes Anlagenmodell (vom Anwender gepflegt).

Dieses Modell beschreibt die Topologie der Anlage: Bloecke, schaltbare
Elemente (Weichen, Doppelkreuzungsweichen, starre Kreuzungen), Melder-
Zuordnungen und Fahrstrassen. Es ist strikt getrennt vom Live-Zustand in
`state.py` (`LayoutState`), der fluechtig aus den Z21-Broadcasts gespeist wird.
Das statische Modell wird dagegen persistiert und nicht von der Zentrale
veraendert.

Reine Dataclasses ohne IO-/FastAPI-/UDP-Abhaengigkeit. Alle Laengen sind `int`
in Millimeter (mm). Serialisierung, Validierung und Service-Logik folgen in
spaeteren Aufgaben.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ElementType(str, Enum):
    """Typ eines schaltbaren bzw. starren Topologie-Elements."""

    TURNOUT = "turnout"  # Weiche: 1 Adresse, Stellung 0/1
    CROSSING_SWITCH = "dkw"  # Doppelkreuzungsweiche: 2 Adressen, 4 Zustaende
    CROSSING = "crossing"  # starre Kreuzung: keine Adresse


@dataclass
class TopologyElement:
    """Schaltbares oder starres Element der Gleis-Topologie.

    `address` ist die Zubehoeradresse A (Weiche bzw. DKW). `address_b` wird nur
    bei der DKW genutzt (zweite Zubehoeradresse), sonst `None`. Die starre
    Kreuzung hat keine Adresse.
    """

    id: str  # UUID4
    name: str  # eindeutig je Typgruppe
    type: ElementType
    address: int | None = None  # Weiche/DKW: Zubehoeradresse A
    address_b: int | None = None  # nur DKW: zweite Zubehoeradresse


@dataclass
class DetectorAssignment:
    """Zuordnung eines Belegtmelder-Eingangs zu einem Block.

    Verweist ueber `(detector_nid, detector_port)` auf dieselbe stabile
    Melderidentitaet wie `state.DetectorInput` (nid, port). `order` legt die
    Anordnung im Block fest; `length_mm` ist die Teillaenge nur innerhalb dieses
    Blocks (mm).
    """

    detector_nid: int
    detector_port: int
    order: int
    length_mm: int | None = None


@dataclass
class Marker:
    """Halt- oder Bremsmarke je Fahrtrichtung.

    Genau EINES von beiden ist gesetzt: entweder `detector_ref` (= (nid, port)
    eines Melders) ODER `position_mm` (virtuelle Position ab Blockanfang, mm).
    Die Validierung dieser xor-Regel erfolgt erst in Aufgabe 3/4; hier nur
    Datenhaltung.
    """

    detector_ref: tuple[int, int] | None = None  # (nid, port)
    position_mm: int | None = None  # ab Blockanfang, mm


@dataclass
class DirectionMarkers:
    """Halt- und Bremsmarke fuer eine Fahrtrichtung."""

    stop: Marker | None = None
    brake: Marker | None = None


@dataclass
class Block:
    """Streckenblock mit Laenge, Vorbildgeschwindigkeit, Melder-Zuordnungen und
    richtungsabhaengigen Markierungen.

    Der Name ist unter Bloecken eindeutig (Eindeutigkeit wird erst im Service
    geprueft). Laengen in mm.
    """

    id: str
    name: str
    length_mm: int | None = None
    max_speed_kmh: int | None = None  # Vorbildgeschwindigkeit (km/h)
    detectors: list[DetectorAssignment] = field(default_factory=list)
    markers_forward: DirectionMarkers = field(default_factory=DirectionMarkers)
    markers_backward: DirectionMarkers = field(default_factory=DirectionMarkers)


@dataclass
class ElementSetting:
    """Soll-Stellung eines schaltbaren Elements in einer Fahrstrasse.

    `desired_state`: Weiche 0/1; DKW 0..3.
    """

    element_id: str
    desired_state: int


@dataclass
class Route:
    """Fahrstrasse: Weg plus Soll-Stellungen und beanspruchte Elemente.

    Der Weg fuehrt vom Start-Block ueber ggf. Zwischenbloecke zum Ziel-Block.
    `element_settings` haelt die zu schaltenden Elemente mit Soll-Stellung;
    `claimed_element_ids` die beanspruchten Elemente inkl. starrer Kreuzungen.
    """

    id: str
    name: str
    start_block_id: str
    transit_block_ids: list[str] = field(default_factory=list)
    end_block_id: str = ""
    element_settings: list[ElementSetting] = field(default_factory=list)
    claimed_element_ids: list[str] = field(default_factory=list)


@dataclass
class Layout:
    """Statisches, persistentes Gesamtmodell der Anlage (nach ID indiziert).

    `version` erlaubt spaetere Migrationen des Persistenzformats.
    """

    version: int = 1
    blocks: dict[str, Block] = field(default_factory=dict)
    elements: dict[str, TopologyElement] = field(default_factory=dict)
    routes: dict[str, Route] = field(default_factory=dict)
