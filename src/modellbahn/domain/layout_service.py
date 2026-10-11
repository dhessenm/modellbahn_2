"""Fachlogik-Service fuer das statische Anlagenmodell (`Layout`).

Der `LayoutService` kapselt genau ein `Layout` aus `layout.py` und ist der
einzige Weg, es zu veraendern. Alle Mutationen (Bloecke, Elemente, Fahrstrassen,
Melder-Zuordnungen) laufen ueber den Service und werden VOR dem Schreiben hart
validiert: schlaegt eine Validierung fehl, bleibt das Modell unveraendert.

Bewusste Abgrenzung: Dieses Modul macht KEINE Datei-IO/Persistenz (Aufgabe 5),
KEINE weichen Konsistenz-WARNUNGEN (Aufgabe 4; hier nur harte Fachregeln), KEINE
API/HTTP-Bindung und leitet KEINEN Live-Blockzustand ab (Aufgabe 6). Reine
Standardbibliothek; keine FastAPI-/HTTP-/UDP-Abhaengigkeit.

Fehler werden als domaeneneigene Exceptions geworfen (kein HTTP-Bezug):
`LayoutValidationError` fuer Fachregelverstoesse und `ReferenceConflictError`
(mit strukturierter `blocked_by`-Liste) fuer den Loeschschutz. IDs vergibt
ausschliesslich der Service (UUID4 als 32-Zeichen-Hex).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum

from modellbahn.domain.layout import (
    Block,
    DetectorAssignment,
    DirectionMarkers,
    ElementSetting,
    ElementType,
    Layout,
    Marker,
    Route,
    TopologyElement,
)


class LayoutValidationError(ValueError):
    """Harte Verletzung einer Modell-Fachregel (deutsche Meldung).

    Domaeneneigen und ohne HTTP-Bezug. Erbt von `ValueError`, damit Aufrufer
    Fachfehler als Wertfehler behandeln koennen; die spaetere API bildet dies
    selbst auf einen passenden Statuscode ab.
    """


@dataclass(frozen=True)
class ReferenceBlocker:
    """Eine blockierende Referenz beim Loeschschutz.

    `type` benennt die Art der referenzierenden Entitaet (aktuell nur "route"),
    `id`/`name` identifizieren sie fuer eine verstaendliche Fehlermeldung.
    """

    type: str
    id: str
    name: str


class ReferenceConflictError(Exception):
    """Loeschen abgelehnt, weil die Entitaet noch referenziert wird.

    Traegt die strukturierte Blocker-Liste in `blocked_by`, damit der Aufrufer
    (bzw. die spaetere API) dem Nutzer die konkreten Referenzen nennen kann.
    """

    def __init__(self, message: str, blocked_by: list[ReferenceBlocker]) -> None:
        super().__init__(message)
        self.blocked_by = blocked_by


class _Unset(Enum):
    """Sentinel-Typ fuer "nicht uebergeben" bei optionalen Adressfeldern.

    `None` ist bei `update_element` ein gueltiger Zielwert (Kreuzung,
    Weichen-`address_b`) und kann daher nicht "unveraendert" bedeuten. Als
    Enum ist der Sentinel fuer mypy sauber typisierbar (`int | None | _Unset`).
    """

    TOKEN = 0


_UNSET = _Unset.TOKEN


class LayoutService:
    """Kapselt ein `Layout` und uebernimmt alle Mutationen samt Validierung."""

    def __init__(self, layout: Layout | None = None) -> None:
        """Haelt das uebergebene `Layout` oder legt ein leeres an."""
        self.layout = layout if layout is not None else Layout()

    # ------------------------------------------------------------------
    # Interne Helfer
    # ------------------------------------------------------------------
    @staticmethod
    def _new_id() -> str:
        """Erzeugt eine neue, kollisionsfreie Entitaets-ID (UUID4-Hex)."""
        return uuid.uuid4().hex

    @staticmethod
    def _norm(name: str) -> str:
        """Normalisiert einen Namen fuer den Eindeutigkeitsvergleich.

        Vergleich case-insensitive nach `strip()`; `casefold()` ist robuster als
        `lower()` (z. B. fuer "ss"/"ss").
        """
        return name.strip().casefold()

    @staticmethod
    def _require_nonempty_name(name: str) -> str:
        """Stellt sicher, dass ein Name nach `strip()` nicht leer ist."""
        if not name.strip():
            raise LayoutValidationError("Name darf nicht leer sein.")
        return name

    def _require_block(self, block_id: str) -> Block:
        block = self.layout.blocks.get(block_id)
        if block is None:
            raise LayoutValidationError(f"Unbekannte Block-ID: {block_id!r}.")
        return block

    def _require_element(self, element_id: str) -> TopologyElement:
        element = self.layout.elements.get(element_id)
        if element is None:
            raise LayoutValidationError(f"Unbekannte Element-ID: {element_id!r}.")
        return element

    def _require_route(self, route_id: str) -> Route:
        route = self.layout.routes.get(route_id)
        if route is None:
            raise LayoutValidationError(f"Unbekannte Fahrstrassen-ID: {route_id!r}.")
        return route

    def _check_name_unique(
        self,
        name: str,
        existing: dict[str, Block] | dict[str, TopologyElement] | dict[str, Route],
        kind: str,
        *,
        exclude_id: str | None = None,
    ) -> None:
        """Prueft die Namenseindeutigkeit innerhalb EINER Typgruppe.

        Vergleicht `_norm(name)` gegen alle vorhandenen Namen derselben Gruppe;
        `exclude_id` schliesst die eigene Entitaet aus (Umbenennen auf den
        eigenen Namen ist erlaubt).
        """
        target = self._norm(name)
        for entity_id, entity in existing.items():
            if entity_id == exclude_id:
                continue
            if self._norm(entity.name) == target:
                raise LayoutValidationError(
                    f"{kind}-Name {name!r} ist bereits vergeben (gegen {entity.name!r})."
                )

    @staticmethod
    def _validate_element_fields(
        element_type: ElementType, address: int | None, address_b: int | None
    ) -> None:
        """Prueft die Adressregeln je Elementtyp.

        Weiche: `address` Pflicht, `address_b` muss `None` sein. DKW: `address`
        UND `address_b` Pflicht. Starre Kreuzung: beide muessen `None` sein.
        """
        if element_type is ElementType.TURNOUT:
            if address is None:
                raise LayoutValidationError("Weiche benoetigt eine Adresse (address).")
            if address_b is not None:
                raise LayoutValidationError("Weiche darf keine zweite Adresse (address_b) haben.")
        elif element_type is ElementType.CROSSING_SWITCH:
            if address is None or address_b is None:
                raise LayoutValidationError("DKW benoetigt beide Adressen (address und address_b).")
        elif element_type is ElementType.CROSSING:
            if address is not None or address_b is not None:
                raise LayoutValidationError("Starre Kreuzung darf keine Adresse haben.")

    @staticmethod
    def _validate_marker(marker: Marker | None, ctx: str) -> None:
        """Prueft die Marker-xor-Regel: genau EINES von detector_ref/position_mm.

        Ein nicht gesetzter Marker (`None`) ist erlaubt (keine Marke).
        """
        if marker is None:
            return
        has_ref = marker.detector_ref is not None
        has_pos = marker.position_mm is not None
        if has_ref == has_pos:
            raise LayoutValidationError(
                f"{ctx}: genau eines von detector_ref/position_mm muss gesetzt sein."
            )

    def _validate_direction_markers(self, markers: DirectionMarkers, ctx: str) -> None:
        """Validiert Halt- und Bremsmarke einer Fahrtrichtung (je optional)."""
        self._validate_marker(markers.stop, f"{ctx}.stop")
        self._validate_marker(markers.brake, f"{ctx}.brake")

    @staticmethod
    def _validate_detectors(assignments: list[DetectorAssignment]) -> None:
        """Prueft, dass die order-Werte innerhalb eines Blocks eindeutig sind."""
        seen: set[int] = set()
        for assignment in assignments:
            if assignment.order in seen:
                raise LayoutValidationError(
                    f"Doppelter order-Wert {assignment.order} in den Melder-Zuordnungen."
                )
            seen.add(assignment.order)

    def _validate_route_refs(self, route: Route) -> None:
        """Prueft alle Referenzen und Fachregeln einer Fahrstrasse.

        - Block-IDs (start/transit/end) muessen existieren.
        - Element-IDs (element_settings, claimed_element_ids) muessen existieren.
        - `desired_state`-Bereich je Elementtyp: Weiche 0/1, DKW 0..3.
        - Starre Kreuzung darf nicht in `element_settings` vorkommen (Req. 4.6);
          in `claimed_element_ids` ist sie erlaubt.
        """
        block_ids = [route.start_block_id, *route.transit_block_ids, route.end_block_id]
        for block_id in block_ids:
            if block_id not in self.layout.blocks:
                raise LayoutValidationError(
                    f"Fahrstrasse verweist auf unbekannten Block: {block_id!r}."
                )

        for setting in route.element_settings:
            element = self.layout.elements.get(setting.element_id)
            if element is None:
                raise LayoutValidationError(
                    f"Fahrstrasse verweist auf unbekanntes Element: {setting.element_id!r}."
                )
            if element.type is ElementType.CROSSING:
                raise LayoutValidationError(
                    "Starre Kreuzung darf nicht in element_settings vorkommen "
                    f"(Element {element.id!r})."
                )
            if element.type is ElementType.TURNOUT:
                allowed = {0, 1}
            else:  # CROSSING_SWITCH (DKW)
                allowed = {0, 1, 2, 3}
            if setting.desired_state not in allowed:
                raise LayoutValidationError(
                    f"Ungueltiger desired_state {setting.desired_state} fuer Element "
                    f"{element.id!r} (erlaubt: {sorted(allowed)})."
                )

        for element_id in route.claimed_element_ids:
            if element_id not in self.layout.elements:
                raise LayoutValidationError(
                    f"Fahrstrasse beansprucht unbekanntes Element: {element_id!r}."
                )

    # ------------------------------------------------------------------
    # Block-CRUD
    # ------------------------------------------------------------------
    def create_block(
        self,
        name: str,
        length_mm: int | None = None,
        max_speed_kmh: int | None = None,
    ) -> Block:
        """Legt einen neuen Block an und gibt ihn mit vergebener ID zurueck."""
        self._require_nonempty_name(name)
        self._check_name_unique(name, self.layout.blocks, "Block")
        block = Block(
            id=self._new_id(),
            name=name,
            length_mm=length_mm,
            max_speed_kmh=max_speed_kmh,
        )
        self.layout.blocks[block.id] = block
        return block

    def update_block(
        self,
        block_id: str,
        *,
        name: str | None = None,
        length_mm: int | None = None,
        max_speed_kmh: int | None = None,
        markers_forward: DirectionMarkers | None = None,
        markers_backward: DirectionMarkers | None = None,
    ) -> Block:
        """Aktualisiert einzelne Felder eines Blocks (None = unveraendert).

        Validiert vollstaendig vor der Mutation; bei Fehler bleibt der Block
        unveraendert.
        """
        block = self._require_block(block_id)
        if name is not None:
            self._require_nonempty_name(name)
            self._check_name_unique(name, self.layout.blocks, "Block", exclude_id=block_id)
        if markers_forward is not None:
            self._validate_direction_markers(markers_forward, "markers_forward")
        if markers_backward is not None:
            self._validate_direction_markers(markers_backward, "markers_backward")

        if name is not None:
            block.name = name
        if length_mm is not None:
            block.length_mm = length_mm
        if max_speed_kmh is not None:
            block.max_speed_kmh = max_speed_kmh
        if markers_forward is not None:
            block.markers_forward = markers_forward
        if markers_backward is not None:
            block.markers_backward = markers_backward
        return block

    def delete_block(self, block_id: str) -> None:
        """Loescht einen Block, sofern keine Fahrstrasse ihn referenziert.

        Melder-Zuordnungen (`DetectorAssignment`) sind Teil des Blocks und
        blockieren das Loeschen NICHT; sie verschwinden mit dem Block.
        """
        self._require_block(block_id)
        blockers: list[ReferenceBlocker] = []
        for route in self.layout.routes.values():
            referenced = (
                block_id == route.start_block_id
                or block_id == route.end_block_id
                or block_id in route.transit_block_ids
            )
            if referenced:
                blockers.append(ReferenceBlocker(type="route", id=route.id, name=route.name))
        if blockers:
            raise ReferenceConflictError(
                f"Block {block_id!r} wird noch von {len(blockers)} Fahrstrasse(n) referenziert.",
                blockers,
            )
        del self.layout.blocks[block_id]

    def get_block(self, block_id: str) -> Block:
        """Liefert den Block zur ID oder wirft `LayoutValidationError`."""
        return self._require_block(block_id)

    def list_blocks(self) -> list[Block]:
        """Liefert alle Bloecke in Einfuegereihenfolge."""
        return list(self.layout.blocks.values())

    def set_block_detectors(self, block_id: str, assignments: list[DetectorAssignment]) -> Block:
        """Ersetzt die Melder-Zuordnungen eines Blocks vollstaendig.

        Prueft die order-Eindeutigkeit vor dem Ersetzen; eine leere Liste
        entfernt alle Zuordnungen.
        """
        block = self._require_block(block_id)
        self._validate_detectors(assignments)
        block.detectors = list(assignments)
        return block

    # ------------------------------------------------------------------
    # TopologyElement-CRUD
    # ------------------------------------------------------------------
    def create_element(
        self,
        name: str,
        type: ElementType,
        address: int | None = None,
        address_b: int | None = None,
    ) -> TopologyElement:
        """Legt ein neues Topologie-Element an (Adressregeln je Typ geprueft)."""
        self._require_nonempty_name(name)
        self._check_name_unique(name, self.layout.elements, "Element")
        self._validate_element_fields(type, address, address_b)
        element = TopologyElement(
            id=self._new_id(),
            name=name,
            type=type,
            address=address,
            address_b=address_b,
        )
        self.layout.elements[element.id] = element
        return element

    def update_element(
        self,
        element_id: str,
        *,
        name: str | None = None,
        type: ElementType | None = None,
        address: int | None | _Unset = _UNSET,
        address_b: int | None | _Unset = _UNSET,
    ) -> TopologyElement:
        """Aktualisiert ein Element (None = unveraendert, ausser bei Adressen).

        Da `None` ein gueltiger Adresswert ist, unterscheidet ein Sentinel
        `_UNSET` zwischen "nicht uebergeben" und "auf None setzen". Die
        Adressregeln werden auf dem resultierenden Zielzustand geprueft (inkl.
        ggf. geaendertem Typ).
        """
        element = self._require_element(element_id)
        if name is not None:
            self._require_nonempty_name(name)
            self._check_name_unique(name, self.layout.elements, "Element", exclude_id=element_id)

        new_type = type if type is not None else element.type
        new_address = element.address if address is _UNSET else address
        new_address_b = element.address_b if address_b is _UNSET else address_b
        self._validate_element_fields(new_type, new_address, new_address_b)

        if name is not None:
            element.name = name
        element.type = new_type
        element.address = new_address
        element.address_b = new_address_b
        return element

    def delete_element(self, element_id: str) -> None:
        """Loescht ein Element, sofern keine Fahrstrasse es referenziert.

        Referenzierend ist eine Route mit dem Element in `element_settings`
        ODER `claimed_element_ids`; steht es in beiden Listen derselben Route,
        entsteht nur EIN Blocker-Eintrag.
        """
        self._require_element(element_id)
        blockers: list[ReferenceBlocker] = []
        for route in self.layout.routes.values():
            in_settings = any(s.element_id == element_id for s in route.element_settings)
            in_claimed = element_id in route.claimed_element_ids
            if in_settings or in_claimed:
                blockers.append(ReferenceBlocker(type="route", id=route.id, name=route.name))
        if blockers:
            raise ReferenceConflictError(
                f"Element {element_id!r} wird noch von {len(blockers)} "
                "Fahrstrasse(n) referenziert.",
                blockers,
            )
        del self.layout.elements[element_id]

    def get_element(self, element_id: str) -> TopologyElement:
        """Liefert das Element zur ID oder wirft `LayoutValidationError`."""
        return self._require_element(element_id)

    def list_elements(self) -> list[TopologyElement]:
        """Liefert alle Elemente in Einfuegereihenfolge."""
        return list(self.layout.elements.values())

    # ------------------------------------------------------------------
    # Route-CRUD
    # ------------------------------------------------------------------
    def create_route(
        self,
        name: str,
        start_block_id: str,
        end_block_id: str,
        transit_block_ids: list[str] | None = None,
        element_settings: list[ElementSetting] | None = None,
        claimed_element_ids: list[str] | None = None,
    ) -> Route:
        """Legt eine neue Fahrstrasse an (Referenzen und Fachregeln geprueft)."""
        self._require_nonempty_name(name)
        self._check_name_unique(name, self.layout.routes, "Fahrstrasse")
        route = Route(
            id=self._new_id(),
            name=name,
            start_block_id=start_block_id,
            transit_block_ids=list(transit_block_ids) if transit_block_ids else [],
            end_block_id=end_block_id,
            element_settings=list(element_settings) if element_settings else [],
            claimed_element_ids=list(claimed_element_ids) if claimed_element_ids else [],
        )
        self._validate_route_refs(route)
        self.layout.routes[route.id] = route
        return route

    def update_route(
        self,
        route_id: str,
        *,
        name: str | None = None,
        start_block_id: str | None = None,
        end_block_id: str | None = None,
        transit_block_ids: list[str] | None = None,
        element_settings: list[ElementSetting] | None = None,
        claimed_element_ids: list[str] | None = None,
    ) -> Route:
        """Aktualisiert eine Fahrstrasse (None = unveraendert).

        Validiert den Zielzustand vollstaendig vor der Mutation; bei Fehler
        bleibt die Fahrstrasse unveraendert.
        """
        route = self._require_route(route_id)
        if name is not None:
            self._require_nonempty_name(name)
            self._check_name_unique(name, self.layout.routes, "Fahrstrasse", exclude_id=route_id)

        candidate = Route(
            id=route.id,
            name=name if name is not None else route.name,
            start_block_id=(start_block_id if start_block_id is not None else route.start_block_id),
            transit_block_ids=(
                list(transit_block_ids)
                if transit_block_ids is not None
                else list(route.transit_block_ids)
            ),
            end_block_id=end_block_id if end_block_id is not None else route.end_block_id,
            element_settings=(
                list(element_settings)
                if element_settings is not None
                else list(route.element_settings)
            ),
            claimed_element_ids=(
                list(claimed_element_ids)
                if claimed_element_ids is not None
                else list(route.claimed_element_ids)
            ),
        )
        self._validate_route_refs(candidate)
        self.layout.routes[route_id] = candidate
        return candidate

    def delete_route(self, route_id: str) -> None:
        """Loescht eine Fahrstrasse.

        Auf Fahrstrassen verweist im Modell nichts zurueck; sie sind daher
        immer loeschbar (nur die Existenz wird geprueft).
        """
        self._require_route(route_id)
        del self.layout.routes[route_id]

    def get_route(self, route_id: str) -> Route:
        """Liefert die Fahrstrasse zur ID oder wirft `LayoutValidationError`."""
        return self._require_route(route_id)

    def list_routes(self) -> list[Route]:
        """Liefert alle Fahrstrassen in Einfuegereihenfolge."""
        return list(self.layout.routes.values())
