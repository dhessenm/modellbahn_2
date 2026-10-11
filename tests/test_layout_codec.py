"""Tests fuer die Serialisierung des Anlagenmodells (to_dict/from_dict)."""

from __future__ import annotations

import pytest

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
from modellbahn.domain.layout_codec import (
    LayoutDecodeError,
    from_dict,
    to_dict,
)


def _full_layout() -> Layout:
    """Baut ein vollstaendiges Layout mit allen Entitaetstypen und Varianten."""
    layout = Layout(version=1)

    block_a = Block(
        id="b1",
        name="Block A",
        length_mm=1200,
        max_speed_kmh=120,
        detectors=[
            DetectorAssignment(detector_nid=10, detector_port=0, order=0, length_mm=600),
            DetectorAssignment(detector_nid=10, detector_port=1, order=1, length_mm=None),
        ],
        markers_forward=DirectionMarkers(
            stop=Marker(detector_ref=(10, 1)),
            brake=Marker(position_mm=300),
        ),
        markers_backward=DirectionMarkers(
            stop=Marker(position_mm=900),
            brake=None,
        ),
    )
    block_b = Block(id="b2", name="Block B")
    layout.blocks[block_a.id] = block_a
    layout.blocks[block_b.id] = block_b

    weiche = TopologyElement(id="e1", name="W1", type=ElementType.TURNOUT, address=5)
    dkw = TopologyElement(
        id="e2", name="DKW1", type=ElementType.CROSSING_SWITCH, address=10, address_b=11
    )
    kreuzung = TopologyElement(id="e3", name="K1", type=ElementType.CROSSING)
    layout.elements[weiche.id] = weiche
    layout.elements[dkw.id] = dkw
    layout.elements[kreuzung.id] = kreuzung

    route = Route(
        id="r1",
        name="Fahrstrasse 1",
        start_block_id="b1",
        transit_block_ids=["b2"],
        end_block_id="b1",
        element_settings=[
            ElementSetting(element_id="e1", desired_state=1),
            ElementSetting(element_id="e2", desired_state=3),
        ],
        claimed_element_ids=["e3", "e1"],
    )
    layout.routes[route.id] = route

    return layout


def test_round_trip_full_layout() -> None:
    layout = _full_layout()
    assert from_dict(to_dict(layout)) == layout


def test_top_level_structure() -> None:
    d = to_dict(_full_layout())
    assert d["version"] == 1
    assert isinstance(d["blocks"], list)
    assert isinstance(d["elements"], list)
    assert isinstance(d["routes"], list)
    assert [b["id"] for b in d["blocks"]] == ["b1", "b2"]
    assert [e["id"] for e in d["elements"]] == ["e1", "e2", "e3"]
    assert [r["id"] for r in d["routes"]] == ["r1"]


def test_element_type_serialized_as_string() -> None:
    d = to_dict(_full_layout())
    types = [e["type"] for e in d["elements"]]
    assert types == ["turnout", "dkw", "crossing"]
    for value in types:
        assert isinstance(value, str)

    layout = from_dict(d)
    dkw = layout.elements["e2"]
    assert isinstance(dkw.type, ElementType)
    assert dkw.type == ElementType.CROSSING_SWITCH


def test_detector_ref_is_list_in_dict_and_tuple_after_load() -> None:
    d = to_dict(_full_layout())
    block_a = next(b for b in d["blocks"] if b["id"] == "b1")
    stop_ref = block_a["markers_forward"]["stop"]["detector_ref"]
    assert stop_ref == [10, 1]
    assert isinstance(stop_ref, list)

    layout = from_dict(d)
    loaded_ref = layout.blocks["b1"].markers_forward.stop.detector_ref
    assert loaded_ref == (10, 1)
    assert isinstance(loaded_ref, tuple)


def test_optional_fields_present_as_null() -> None:
    d = to_dict(_full_layout())
    block_b = next(b for b in d["blocks"] if b["id"] == "b2")
    assert "length_mm" in block_b and block_b["length_mm"] is None
    assert "max_speed_kmh" in block_b and block_b["max_speed_kmh"] is None

    block_a = next(b for b in d["blocks"] if b["id"] == "b1")
    assert block_a["markers_backward"]["brake"] is None

    weiche = next(e for e in d["elements"] if e["id"] == "e1")
    assert "address_b" in weiche and weiche["address_b"] is None


def test_from_dict_missing_version_raises() -> None:
    with pytest.raises(LayoutDecodeError):
        from_dict({"blocks": [], "elements": [], "routes": []})


def test_from_dict_wrong_version_raises() -> None:
    with pytest.raises(LayoutDecodeError):
        from_dict({"version": 2, "blocks": [], "elements": [], "routes": []})
    with pytest.raises(LayoutDecodeError):
        from_dict({"version": "1", "blocks": [], "elements": [], "routes": []})


def test_from_dict_structurally_broken_raises() -> None:
    with pytest.raises(LayoutDecodeError):
        from_dict({"version": 1, "blocks": {}, "elements": [], "routes": []})

    with pytest.raises(LayoutDecodeError):
        from_dict({"version": 1, "blocks": [{"name": "ohne id"}], "elements": [], "routes": []})

    with pytest.raises(LayoutDecodeError):
        from_dict(
            {
                "version": 1,
                "blocks": [],
                "elements": [{"id": "e1", "name": "W1", "type": "foo"}],
                "routes": [],
            }
        )

    with pytest.raises(LayoutDecodeError):
        from_dict(
            {
                "version": 1,
                "blocks": [
                    {
                        "id": "b1",
                        "name": "Block A",
                        "markers_forward": {
                            "stop": {"detector_ref": [10], "position_mm": None},
                            "brake": None,
                        },
                    }
                ],
                "elements": [],
                "routes": [],
            }
        )


def test_empty_layout_round_trip() -> None:
    assert from_dict(to_dict(Layout())) == Layout()
