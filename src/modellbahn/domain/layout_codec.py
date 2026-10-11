"""Serialisierung des statischen Anlagenmodells zu/aus JSON-tauglichen Dicts.

Reine `dict`<->`dataclass`-Konvertierung des `Layout`-Modells aus `layout.py`
plus Pruefung der Schema-Version. Es wird nur die Standardbibliothek genutzt;
keine externen Libs, kein Pickle und kein `json.dumps/loads` (das Lesen/Schreiben
der Datei folgt in einer spaeteren Aufgabe). Keine FastAPI-/HTTP-/UDP-Abhaengigkeit.

Zielstruktur (Top-Level EXAKT):

    {"version": 1, "blocks": [...], "elements": [...], "routes": [...]}

Collections werden als Listen in Einfuegereihenfolge ausgegeben und beim Laden
nach `id` in die `dict`-Felder von `Layout` indiziert. Optionale Felder werden
immer als Schluessel mit `null` serialisiert (nie weggelassen).
"""

from __future__ import annotations

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

SCHEMA_VERSION = 1


class LayoutDecodeError(Exception):
    """Fehler beim Dekodieren eines Layout-Dicts (ungueltige Struktur/Version)."""


# ---------------------------------------------------------------------------
# Serialisierung (dataclass -> dict)
# ---------------------------------------------------------------------------


def to_dict(layout: Layout) -> dict[str, object]:
    """Serialisiert ein `Layout` in ein JSON-taugliches `dict`.

    Collections werden als Listen in Einfuegereihenfolge ausgegeben; `ElementType`
    als String-Wert; `detector_ref`-Tupel als 2er-Liste. Optionale Felder sind
    immer als Schluessel mit `null` vorhanden.
    """
    return {
        "version": SCHEMA_VERSION,
        "blocks": [_block_to_dict(b) for b in layout.blocks.values()],
        "elements": [_element_to_dict(e) for e in layout.elements.values()],
        "routes": [_route_to_dict(r) for r in layout.routes.values()],
    }


def _element_to_dict(element: TopologyElement) -> dict[str, object]:
    return {
        "id": element.id,
        "name": element.name,
        "type": element.type.value,
        "address": element.address,
        "address_b": element.address_b,
    }


def _detector_assignment_to_dict(assignment: DetectorAssignment) -> dict[str, object]:
    return {
        "detector_nid": assignment.detector_nid,
        "detector_port": assignment.detector_port,
        "order": assignment.order,
        "length_mm": assignment.length_mm,
    }


def _marker_to_dict(marker: Marker | None) -> dict[str, object] | None:
    if marker is None:
        return None
    detector_ref = None if marker.detector_ref is None else list(marker.detector_ref)
    return {
        "detector_ref": detector_ref,
        "position_mm": marker.position_mm,
    }


def _direction_markers_to_dict(markers: DirectionMarkers) -> dict[str, object]:
    return {
        "stop": _marker_to_dict(markers.stop),
        "brake": _marker_to_dict(markers.brake),
    }


def _block_to_dict(block: Block) -> dict[str, object]:
    return {
        "id": block.id,
        "name": block.name,
        "length_mm": block.length_mm,
        "max_speed_kmh": block.max_speed_kmh,
        "detectors": [_detector_assignment_to_dict(d) for d in block.detectors],
        "markers_forward": _direction_markers_to_dict(block.markers_forward),
        "markers_backward": _direction_markers_to_dict(block.markers_backward),
    }


def _element_setting_to_dict(setting: ElementSetting) -> dict[str, object]:
    return {
        "element_id": setting.element_id,
        "desired_state": setting.desired_state,
    }


def _route_to_dict(route: Route) -> dict[str, object]:
    return {
        "id": route.id,
        "name": route.name,
        "start_block_id": route.start_block_id,
        "transit_block_ids": list(route.transit_block_ids),
        "end_block_id": route.end_block_id,
        "element_settings": [_element_setting_to_dict(s) for s in route.element_settings],
        "claimed_element_ids": list(route.claimed_element_ids),
    }


# ---------------------------------------------------------------------------
# Deserialisierung (dict -> dataclass)
# ---------------------------------------------------------------------------


def from_dict(data: dict[str, object]) -> Layout:
    """Rekonstruiert ein `Layout` aus einem JSON-tauglichen `dict`.

    Prueft zuerst die Schema-Version, dann die Grundstruktur. Bei fehlender/
    unbekannter Version oder strukturell kaputtem Input wird `LayoutDecodeError`
    mit deutscher Meldung geworfen (keine stille Falsch-Dekodierung).
    """
    if not isinstance(data, dict):
        raise LayoutDecodeError("Eingabe ist kein Objekt (dict erwartet).")

    _check_version(data.get("version"))

    layout = Layout(version=SCHEMA_VERSION)

    for raw in _require_list(data, "blocks"):
        block = _block_from_dict(raw)
        layout.blocks[block.id] = block

    for raw in _require_list(data, "elements"):
        element = _element_from_dict(raw)
        layout.elements[element.id] = element

    for raw in _require_list(data, "routes"):
        route = _route_from_dict(raw)
        layout.routes[route.id] = route

    return layout


def _check_version(version: object) -> None:
    # bool ist ein int-Subtyp; True/False ist keine gueltige Version.
    if version is None or isinstance(version, bool) or not isinstance(version, int):
        raise LayoutDecodeError(
            f"Feld 'version' fehlt oder ist keine ganze Zahl (gefunden: {version!r})."
        )
    if version != SCHEMA_VERSION:
        raise LayoutDecodeError(
            f"Unbekannte Schema-Version {version} (unterstuetzt: {SCHEMA_VERSION})."
        )


def _require_list(data: dict[str, object], key: str) -> list[object]:
    value = data.get(key)
    if not isinstance(value, list):
        raise LayoutDecodeError(f"Feld '{key}' fehlt oder ist keine Liste.")
    return value


def _require_dict(raw: object, context: str) -> dict[str, object]:
    if not isinstance(raw, dict):
        raise LayoutDecodeError(f"{context}: Eintrag ist kein Objekt (dict erwartet).")
    return raw


def _require_str(raw: dict[str, object], key: str, context: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str):
        raise LayoutDecodeError(f"{context}: Pflichtfeld '{key}' fehlt oder ist kein String.")
    return value


def _opt_int(raw: dict[str, object], key: str, context: str) -> int | None:
    value = raw.get(key)
    if value is None:
        return None
    # bool ist int-Subtyp, aber hier unerwuenscht.
    if isinstance(value, bool) or not isinstance(value, int):
        raise LayoutDecodeError(f"{context}: Feld '{key}' ist keine ganze Zahl oder null.")
    return value


def _require_int(raw: dict[str, object], key: str, context: str) -> int:
    value = raw.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise LayoutDecodeError(f"{context}: Pflichtfeld '{key}' fehlt oder ist keine ganze Zahl.")
    return value


def _element_from_dict(raw: object) -> TopologyElement:
    obj = _require_dict(raw, "Element")
    element_id = _require_str(obj, "id", "Element")
    name = _require_str(obj, "name", "Element")
    type_value = obj.get("type")
    if not isinstance(type_value, str):
        raise LayoutDecodeError(f"Element '{element_id}': Feld 'type' fehlt oder ist kein String.")
    try:
        element_type = ElementType(type_value)
    except ValueError as err:
        raise LayoutDecodeError(f"Element '{element_id}': ungueltiger Typ {type_value!r}.") from err
    return TopologyElement(
        id=element_id,
        name=name,
        type=element_type,
        address=_opt_int(obj, "address", f"Element '{element_id}'"),
        address_b=_opt_int(obj, "address_b", f"Element '{element_id}'"),
    )


def _detector_assignment_from_dict(raw: object) -> DetectorAssignment:
    obj = _require_dict(raw, "Melder-Zuordnung")
    context = "Melder-Zuordnung"
    return DetectorAssignment(
        detector_nid=_require_int(obj, "detector_nid", context),
        detector_port=_require_int(obj, "detector_port", context),
        order=_require_int(obj, "order", context),
        length_mm=_opt_int(obj, "length_mm", context),
    )


def _marker_from_dict(raw: object, context: str) -> Marker | None:
    if raw is None:
        return None
    obj = _require_dict(raw, context)
    detector_ref: tuple[int, int] | None = None
    ref_value = obj.get("detector_ref")
    if ref_value is not None:
        if not isinstance(ref_value, list) or len(ref_value) != 2:
            raise LayoutDecodeError(f"{context}: 'detector_ref' muss eine Liste [nid, port] sein.")
        nid, port = ref_value
        if (
            isinstance(nid, bool)
            or isinstance(port, bool)
            or not isinstance(nid, int)
            or not isinstance(port, int)
        ):
            raise LayoutDecodeError(f"{context}: 'detector_ref' enthaelt keine ganzen Zahlen.")
        detector_ref = (nid, port)
    return Marker(
        detector_ref=detector_ref,
        position_mm=_opt_int(obj, "position_mm", context),
    )


def _direction_markers_from_dict(raw: object, context: str) -> DirectionMarkers:
    obj = _require_dict(raw, context)
    return DirectionMarkers(
        stop=_marker_from_dict(obj.get("stop"), f"{context}.stop"),
        brake=_marker_from_dict(obj.get("brake"), f"{context}.brake"),
    )


def _block_from_dict(raw: object) -> Block:
    obj = _require_dict(raw, "Block")
    block_id = _require_str(obj, "id", "Block")
    name = _require_str(obj, "name", "Block")
    context = f"Block '{block_id}'"
    detectors_raw = obj.get("detectors", [])
    if not isinstance(detectors_raw, list):
        raise LayoutDecodeError(f"{context}: Feld 'detectors' ist keine Liste.")
    return Block(
        id=block_id,
        name=name,
        length_mm=_opt_int(obj, "length_mm", context),
        max_speed_kmh=_opt_int(obj, "max_speed_kmh", context),
        detectors=[_detector_assignment_from_dict(d) for d in detectors_raw],
        markers_forward=_direction_markers_from_dict(
            obj.get("markers_forward", {}), f"{context}.markers_forward"
        ),
        markers_backward=_direction_markers_from_dict(
            obj.get("markers_backward", {}), f"{context}.markers_backward"
        ),
    )


def _element_setting_from_dict(raw: object) -> ElementSetting:
    obj = _require_dict(raw, "Element-Stellung")
    context = "Element-Stellung"
    return ElementSetting(
        element_id=_require_str(obj, "element_id", context),
        desired_state=_require_int(obj, "desired_state", context),
    )


def _require_str_list(raw: dict[str, object], key: str, context: str) -> list[str]:
    value = raw.get(key, [])
    if not isinstance(value, list):
        raise LayoutDecodeError(f"{context}: Feld '{key}' ist keine Liste.")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise LayoutDecodeError(f"{context}: Feld '{key}' enthaelt einen Nicht-String.")
        result.append(item)
    return result


def _route_from_dict(raw: object) -> Route:
    obj = _require_dict(raw, "Fahrstrasse")
    route_id = _require_str(obj, "id", "Fahrstrasse")
    context = f"Fahrstrasse '{route_id}'"
    settings_raw = obj.get("element_settings", [])
    if not isinstance(settings_raw, list):
        raise LayoutDecodeError(f"{context}: Feld 'element_settings' ist keine Liste.")
    end_block_id = obj.get("end_block_id", "")
    if not isinstance(end_block_id, str):
        raise LayoutDecodeError(f"{context}: Feld 'end_block_id' ist kein String.")
    return Route(
        id=route_id,
        name=_require_str(obj, "name", context),
        start_block_id=_require_str(obj, "start_block_id", context),
        transit_block_ids=_require_str_list(obj, "transit_block_ids", context),
        end_block_id=end_block_id,
        element_settings=[_element_setting_from_dict(s) for s in settings_raw],
        claimed_element_ids=_require_str_list(obj, "claimed_element_ids", context),
    )
