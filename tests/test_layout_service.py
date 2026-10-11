"""Tests fuer die Fachlogik des Anlagenmodells (`LayoutService`).

Je Fachregel mind. ein Positiv- und ein Negativfall. Harte Verstoesse werfen
`LayoutValidationError`, der Loeschschutz `ReferenceConflictError`.
"""

from __future__ import annotations

import pytest

from modellbahn.domain.layout import (
    DetectorAssignment,
    DirectionMarkers,
    ElementSetting,
    ElementType,
    Layout,
    Marker,
)
from modellbahn.domain.layout_service import (
    LayoutService,
    LayoutValidationError,
    ReferenceConflictError,
)


# ---------------------------------------------------------------------------
# Konstruktor / ID-Vergabe
# ---------------------------------------------------------------------------
def test_init_default_empty_layout() -> None:
    service = LayoutService()
    assert service.layout.blocks == {}
    assert service.layout.elements == {}
    assert service.layout.routes == {}


def test_init_with_existing_layout_is_held() -> None:
    layout = Layout(version=1)
    service = LayoutService(layout)
    assert service.layout is layout


def test_create_block_assigns_unique_uuid_hex() -> None:
    service = LayoutService()
    block_a = service.create_block("A")
    block_b = service.create_block("B")
    assert len(block_a.id) == 32
    int(block_a.id, 16)  # reines Hex
    assert block_a.id != block_b.id
    assert service.get_block(block_a.id) is block_a
    assert {b.id for b in service.list_blocks()} == {block_a.id, block_b.id}


# ---------------------------------------------------------------------------
# Namenseindeutigkeit je Typ (D8)
# ---------------------------------------------------------------------------
def test_block_name_unique_ok() -> None:
    service = LayoutService()
    service.create_block("Block A")
    service.create_block("Block B")
    assert len(service.list_blocks()) == 2


def test_block_name_conflict_case_insensitive_and_strip() -> None:
    service = LayoutService()
    service.create_block("Block")
    with pytest.raises(LayoutValidationError):
        service.create_block("  block ")


def test_block_name_conflict_leaves_model_unchanged() -> None:
    service = LayoutService()
    service.create_block("Block")
    with pytest.raises(LayoutValidationError):
        service.create_block("block")
    assert len(service.list_blocks()) == 1


def test_block_empty_name_rejected() -> None:
    service = LayoutService()
    with pytest.raises(LayoutValidationError):
        service.create_block("   ")


def test_block_rename_to_own_name_ok() -> None:
    service = LayoutService()
    block = service.create_block("A")
    updated = service.update_block(block.id, name="A")
    assert updated.name == "A"


def test_block_rename_to_foreign_name_rejected() -> None:
    service = LayoutService()
    block_a = service.create_block("A")
    service.create_block("B")
    with pytest.raises(LayoutValidationError):
        service.update_block(block_a.id, name="B")


def test_same_name_different_type_ok() -> None:
    service = LayoutService()
    service.create_block("Gleis 1")
    # Gleicher Name als Element ist erlaubt (Eindeutigkeit nur je Typ).
    element = service.create_element("Gleis 1", ElementType.TURNOUT, address=5)
    assert element.name == "Gleis 1"


# ---------------------------------------------------------------------------
# Element-CRUD + Adress-/Typregeln
# ---------------------------------------------------------------------------
def test_create_turnout_ok() -> None:
    service = LayoutService()
    element = service.create_element("W1", ElementType.TURNOUT, address=5)
    assert len(element.id) == 32
    assert service.get_element(element.id) is element
    assert element in service.list_elements()


def test_create_dkw_ok() -> None:
    service = LayoutService()
    element = service.create_element("DKW1", ElementType.CROSSING_SWITCH, address=10, address_b=11)
    assert element.address == 10
    assert element.address_b == 11


def test_create_crossing_ok() -> None:
    service = LayoutService()
    element = service.create_element("K1", ElementType.CROSSING)
    assert element.address is None
    assert element.address_b is None


def test_turnout_without_address_rejected() -> None:
    service = LayoutService()
    with pytest.raises(LayoutValidationError):
        service.create_element("W1", ElementType.TURNOUT)


def test_turnout_with_address_b_rejected() -> None:
    service = LayoutService()
    with pytest.raises(LayoutValidationError):
        service.create_element("W1", ElementType.TURNOUT, address=5, address_b=6)


def test_dkw_without_address_b_rejected() -> None:
    service = LayoutService()
    with pytest.raises(LayoutValidationError):
        service.create_element("DKW1", ElementType.CROSSING_SWITCH, address=10)


def test_crossing_with_address_rejected() -> None:
    service = LayoutService()
    with pytest.raises(LayoutValidationError):
        service.create_element("K1", ElementType.CROSSING, address=3)


def test_element_name_conflict_rejected() -> None:
    service = LayoutService()
    service.create_element("W1", ElementType.TURNOUT, address=5)
    with pytest.raises(LayoutValidationError):
        service.create_element("w1", ElementType.TURNOUT, address=6)


def test_update_element_type_change_to_crossing_ok() -> None:
    service = LayoutService()
    element = service.create_element("W1", ElementType.TURNOUT, address=5)
    updated = service.update_element(
        element.id, type=ElementType.CROSSING, address=None, address_b=None
    )
    assert updated.type is ElementType.CROSSING
    assert updated.address is None


def test_update_element_type_change_without_matching_address_rejected() -> None:
    service = LayoutService()
    element = service.create_element("W1", ElementType.TURNOUT, address=5)
    # Typwechsel auf Kreuzung, aber Adresse bleibt gesetzt -> Fehler.
    with pytest.raises(LayoutValidationError):
        service.update_element(element.id, type=ElementType.CROSSING)


# ---------------------------------------------------------------------------
# Melder-Zuordnung / order-Eindeutigkeit
# ---------------------------------------------------------------------------
def test_set_block_detectors_ok_and_replaces() -> None:
    service = LayoutService()
    block = service.create_block("A")
    service.set_block_detectors(
        block.id,
        [
            DetectorAssignment(detector_nid=1, detector_port=0, order=0),
            DetectorAssignment(detector_nid=1, detector_port=1, order=1),
            DetectorAssignment(detector_nid=1, detector_port=2, order=2),
        ],
    )
    assert len(block.detectors) == 3
    # Erneuter Aufruf ersetzt vollstaendig.
    service.set_block_detectors(block.id, [])
    assert block.detectors == []


def test_set_block_detectors_duplicate_order_rejected() -> None:
    service = LayoutService()
    block = service.create_block("A")
    with pytest.raises(LayoutValidationError):
        service.set_block_detectors(
            block.id,
            [
                DetectorAssignment(detector_nid=1, detector_port=0, order=0),
                DetectorAssignment(detector_nid=1, detector_port=1, order=0),
            ],
        )


def test_set_block_detectors_unknown_block_rejected() -> None:
    service = LayoutService()
    with pytest.raises(LayoutValidationError):
        service.set_block_detectors("nope", [])


# ---------------------------------------------------------------------------
# Marker-xor
# ---------------------------------------------------------------------------
def test_markers_xor_ok() -> None:
    service = LayoutService()
    block = service.create_block("A")
    markers = DirectionMarkers(
        stop=Marker(detector_ref=(1, 0)),
        brake=Marker(position_mm=300),
    )
    updated = service.update_block(block.id, markers_forward=markers)
    assert updated.markers_forward is markers


def test_markers_stop_none_ok() -> None:
    service = LayoutService()
    block = service.create_block("A")
    markers = DirectionMarkers(stop=None, brake=Marker(position_mm=100))
    service.update_block(block.id, markers_backward=markers)
    assert block.markers_backward.stop is None


def test_marker_both_fields_rejected() -> None:
    service = LayoutService()
    block = service.create_block("A")
    markers = DirectionMarkers(stop=Marker(detector_ref=(1, 0), position_mm=300))
    with pytest.raises(LayoutValidationError):
        service.update_block(block.id, markers_forward=markers)


def test_marker_no_field_rejected() -> None:
    service = LayoutService()
    block = service.create_block("A")
    markers = DirectionMarkers(stop=Marker())
    with pytest.raises(LayoutValidationError):
        service.update_block(block.id, markers_forward=markers)


# ---------------------------------------------------------------------------
# Route-CRUD + Referenz-Existenz
# ---------------------------------------------------------------------------
def _service_with_route_prereqs() -> tuple[LayoutService, str, str, str, str]:
    """Baut einen Service mit zwei Bloecken, einer Weiche und einer Kreuzung."""
    service = LayoutService()
    start = service.create_block("Start")
    end = service.create_block("Ziel")
    weiche = service.create_element("W1", ElementType.TURNOUT, address=5)
    kreuzung = service.create_element("K1", ElementType.CROSSING)
    return service, start.id, end.id, weiche.id, kreuzung.id


def test_create_route_ok() -> None:
    service, start_id, end_id, weiche_id, kreuzung_id = _service_with_route_prereqs()
    route = service.create_route(
        "Fahrstrasse 1",
        start_block_id=start_id,
        end_block_id=end_id,
        element_settings=[ElementSetting(element_id=weiche_id, desired_state=1)],
        claimed_element_ids=[kreuzung_id, weiche_id],
    )
    assert len(route.id) == 32
    assert service.get_route(route.id) is route
    assert route in service.list_routes()


def test_create_route_unknown_start_block_rejected() -> None:
    service, _start_id, end_id, _weiche_id, _kreuzung_id = _service_with_route_prereqs()
    with pytest.raises(LayoutValidationError):
        service.create_route("R", start_block_id="nope", end_block_id=end_id)


def test_create_route_unknown_transit_block_rejected() -> None:
    service, start_id, end_id, _weiche_id, _kreuzung_id = _service_with_route_prereqs()
    with pytest.raises(LayoutValidationError):
        service.create_route(
            "R", start_block_id=start_id, end_block_id=end_id, transit_block_ids=["nope"]
        )


def test_create_route_unknown_element_setting_rejected() -> None:
    service, start_id, end_id, _weiche_id, _kreuzung_id = _service_with_route_prereqs()
    with pytest.raises(LayoutValidationError):
        service.create_route(
            "R",
            start_block_id=start_id,
            end_block_id=end_id,
            element_settings=[ElementSetting(element_id="nope", desired_state=0)],
        )


def test_create_route_unknown_claimed_element_rejected() -> None:
    service, start_id, end_id, _weiche_id, _kreuzung_id = _service_with_route_prereqs()
    with pytest.raises(LayoutValidationError):
        service.create_route(
            "R", start_block_id=start_id, end_block_id=end_id, claimed_element_ids=["nope"]
        )


# ---------------------------------------------------------------------------
# desired_state-Bereich
# ---------------------------------------------------------------------------
def test_turnout_desired_state_valid() -> None:
    service, start_id, end_id, weiche_id, _kreuzung_id = _service_with_route_prereqs()
    for state in (0, 1):
        route = service.create_route(
            f"R{state}",
            start_block_id=start_id,
            end_block_id=end_id,
            element_settings=[ElementSetting(element_id=weiche_id, desired_state=state)],
        )
        assert route.element_settings[0].desired_state == state


def test_dkw_desired_state_valid() -> None:
    service = LayoutService()
    start = service.create_block("Start")
    end = service.create_block("Ziel")
    dkw = service.create_element("DKW1", ElementType.CROSSING_SWITCH, address=10, address_b=11)
    for state in (0, 1, 2, 3):
        route = service.create_route(
            f"R{state}",
            start_block_id=start.id,
            end_block_id=end.id,
            element_settings=[ElementSetting(element_id=dkw.id, desired_state=state)],
        )
        assert route.element_settings[0].desired_state == state


def test_turnout_desired_state_out_of_range_rejected() -> None:
    service, start_id, end_id, weiche_id, _kreuzung_id = _service_with_route_prereqs()
    with pytest.raises(LayoutValidationError):
        service.create_route(
            "R",
            start_block_id=start_id,
            end_block_id=end_id,
            element_settings=[ElementSetting(element_id=weiche_id, desired_state=2)],
        )


def test_dkw_desired_state_out_of_range_rejected() -> None:
    service = LayoutService()
    start = service.create_block("Start")
    end = service.create_block("Ziel")
    dkw = service.create_element("DKW1", ElementType.CROSSING_SWITCH, address=10, address_b=11)
    with pytest.raises(LayoutValidationError):
        service.create_route(
            "R",
            start_block_id=start.id,
            end_block_id=end.id,
            element_settings=[ElementSetting(element_id=dkw.id, desired_state=4)],
        )


# ---------------------------------------------------------------------------
# Starre Kreuzung (Req. 4.6)
# ---------------------------------------------------------------------------
def test_crossing_in_claimed_ok() -> None:
    service, start_id, end_id, _weiche_id, kreuzung_id = _service_with_route_prereqs()
    route = service.create_route(
        "R",
        start_block_id=start_id,
        end_block_id=end_id,
        claimed_element_ids=[kreuzung_id],
    )
    assert kreuzung_id in route.claimed_element_ids


def test_crossing_in_element_settings_rejected() -> None:
    service, start_id, end_id, _weiche_id, kreuzung_id = _service_with_route_prereqs()
    with pytest.raises(LayoutValidationError):
        service.create_route(
            "R",
            start_block_id=start_id,
            end_block_id=end_id,
            element_settings=[ElementSetting(element_id=kreuzung_id, desired_state=0)],
        )


# ---------------------------------------------------------------------------
# Loeschschutz (D12)
# ---------------------------------------------------------------------------
def test_delete_unreferenced_block_ok() -> None:
    service = LayoutService()
    block = service.create_block("A")
    service.delete_block(block.id)
    assert service.list_blocks() == []


def test_delete_block_with_detectors_ok() -> None:
    service = LayoutService()
    block = service.create_block("A")
    service.set_block_detectors(
        block.id, [DetectorAssignment(detector_nid=1, detector_port=0, order=0)]
    )
    service.delete_block(block.id)
    assert service.list_blocks() == []


def test_delete_referenced_block_rejected_with_blockers() -> None:
    service, start_id, end_id, _weiche_id, _kreuzung_id = _service_with_route_prereqs()
    route = service.create_route("Fahrstrasse 1", start_block_id=start_id, end_block_id=end_id)
    with pytest.raises(ReferenceConflictError) as excinfo:
        service.delete_block(start_id)
    blocked_by = excinfo.value.blocked_by
    assert len(blocked_by) == 1
    assert blocked_by[0].type == "route"
    assert blocked_by[0].id == route.id
    assert blocked_by[0].name == route.name
    # Block ist nach abgelehntem Loeschen noch vorhanden.
    assert service.get_block(start_id).id == start_id


def test_delete_referenced_element_rejected() -> None:
    service, start_id, end_id, weiche_id, _kreuzung_id = _service_with_route_prereqs()
    service.create_route(
        "R",
        start_block_id=start_id,
        end_block_id=end_id,
        element_settings=[ElementSetting(element_id=weiche_id, desired_state=1)],
    )
    with pytest.raises(ReferenceConflictError):
        service.delete_element(weiche_id)


def test_delete_element_in_both_lists_dedup_single_blocker() -> None:
    service, start_id, end_id, weiche_id, _kreuzung_id = _service_with_route_prereqs()
    service.create_route(
        "R",
        start_block_id=start_id,
        end_block_id=end_id,
        element_settings=[ElementSetting(element_id=weiche_id, desired_state=1)],
        claimed_element_ids=[weiche_id],
    )
    with pytest.raises(ReferenceConflictError) as excinfo:
        service.delete_element(weiche_id)
    assert len(excinfo.value.blocked_by) == 1


def test_delete_unreferenced_element_ok() -> None:
    service = LayoutService()
    element = service.create_element("W1", ElementType.TURNOUT, address=5)
    service.delete_element(element.id)
    assert service.list_elements() == []


def test_delete_route_always_ok() -> None:
    service, start_id, end_id, _weiche_id, _kreuzung_id = _service_with_route_prereqs()
    route = service.create_route("R", start_block_id=start_id, end_block_id=end_id)
    service.delete_route(route.id)
    assert service.list_routes() == []


def test_delete_unknown_raises() -> None:
    service = LayoutService()
    with pytest.raises(LayoutValidationError):
        service.delete_block("nope")
    with pytest.raises(LayoutValidationError):
        service.delete_element("nope")
    with pytest.raises(LayoutValidationError):
        service.delete_route("nope")
