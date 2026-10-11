"""Tests fuer die reine Konsistenz-Warnungslogik (`block_consistency_warnings`).

Konstruiert `Block`/`DetectorAssignment`/`Marker`/`DirectionMarkers` direkt
(ohne Service) und prueft die gemeldeten Warnungs-codes.
"""

from __future__ import annotations

from modellbahn.domain.layout import (
    Block,
    DetectorAssignment,
    DirectionMarkers,
    Marker,
)
from modellbahn.domain.layout_consistency import (
    WARN_LENGTH_SUM,
    WARN_MARKER_OUT_OF_RANGE,
    WARN_ORDER_GAP,
    WARN_PARTIAL_LENGTH_MISSING,
    block_consistency_warnings,
)


def _codes(block: Block) -> set[str]:
    return {w.code for w in block_consistency_warnings(block)}


def _detector(order: int, length_mm: int | None = None) -> DetectorAssignment:
    return DetectorAssignment(detector_nid=1, detector_port=order, order=order, length_mm=length_mm)


# ---------------------------------------------------------------------------
# Laengensumme / Teillaenge fehlt
# ---------------------------------------------------------------------------
def test_length_sum_matches_no_warning() -> None:
    block = Block(
        id="b", name="A", length_mm=1000, detectors=[_detector(0, 400), _detector(1, 600)]
    )
    assert WARN_LENGTH_SUM not in _codes(block)


def test_length_sum_mismatch_warning() -> None:
    block = Block(
        id="b", name="A", length_mm=1000, detectors=[_detector(0, 400), _detector(1, 500)]
    )
    codes = [w.code for w in block_consistency_warnings(block)]
    assert codes.count(WARN_LENGTH_SUM) == 1


def test_length_sum_block_length_unset_no_warning() -> None:
    block = Block(
        id="b", name="A", length_mm=None, detectors=[_detector(0, 400), _detector(1, 600)]
    )
    codes = _codes(block)
    assert WARN_LENGTH_SUM not in codes
    assert WARN_PARTIAL_LENGTH_MISSING not in codes


def test_partial_length_missing_hint() -> None:
    block = Block(
        id="b", name="A", length_mm=1000, detectors=[_detector(0, 1000), _detector(1, None)]
    )
    codes = _codes(block)
    assert WARN_PARTIAL_LENGTH_MISSING in codes
    # fehlende Teillaenge wird nicht als 0 gewertet -> keine faelschliche Summenwarnung
    assert WARN_LENGTH_SUM not in codes


# ---------------------------------------------------------------------------
# Marke ausserhalb
# ---------------------------------------------------------------------------
def test_marker_position_within_ok() -> None:
    block = Block(
        id="b",
        name="A",
        length_mm=1000,
        markers_forward=DirectionMarkers(stop=Marker(position_mm=500)),
    )
    assert WARN_MARKER_OUT_OF_RANGE not in _codes(block)


def test_marker_stop_forward_out_of_range() -> None:
    block = Block(
        id="b",
        name="A",
        length_mm=1000,
        markers_forward=DirectionMarkers(stop=Marker(position_mm=1200)),
    )
    assert WARN_MARKER_OUT_OF_RANGE in _codes(block)


def test_marker_brake_forward_out_of_range() -> None:
    block = Block(
        id="b",
        name="A",
        length_mm=1000,
        markers_forward=DirectionMarkers(brake=Marker(position_mm=1500)),
    )
    assert WARN_MARKER_OUT_OF_RANGE in _codes(block)


def test_marker_stop_backward_out_of_range() -> None:
    block = Block(
        id="b",
        name="A",
        length_mm=1000,
        markers_backward=DirectionMarkers(stop=Marker(position_mm=1200)),
    )
    assert WARN_MARKER_OUT_OF_RANGE in _codes(block)


def test_marker_brake_backward_out_of_range() -> None:
    block = Block(
        id="b",
        name="A",
        length_mm=1000,
        markers_backward=DirectionMarkers(brake=Marker(position_mm=1200)),
    )
    assert WARN_MARKER_OUT_OF_RANGE in _codes(block)


def test_marker_detector_ref_ignored() -> None:
    block = Block(
        id="b",
        name="A",
        length_mm=1000,
        markers_forward=DirectionMarkers(stop=Marker(detector_ref=(1, 2))),
    )
    assert WARN_MARKER_OUT_OF_RANGE not in _codes(block)


def test_marker_out_of_range_block_length_unset() -> None:
    block = Block(
        id="b",
        name="A",
        length_mm=None,
        markers_forward=DirectionMarkers(stop=Marker(position_mm=500)),
    )
    assert WARN_MARKER_OUT_OF_RANGE not in _codes(block)


# ---------------------------------------------------------------------------
# order-Luecke
# ---------------------------------------------------------------------------
def test_order_contiguous_no_warning() -> None:
    block = Block(id="b", name="A", detectors=[_detector(0), _detector(1), _detector(2)])
    assert WARN_ORDER_GAP not in _codes(block)


def test_order_contiguous_nonzero_start_no_warning() -> None:
    block = Block(id="b", name="A", detectors=[_detector(1), _detector(2), _detector(3)])
    assert WARN_ORDER_GAP not in _codes(block)


def test_order_gap_warning() -> None:
    block = Block(id="b", name="A", detectors=[_detector(0), _detector(2)])
    assert WARN_ORDER_GAP in _codes(block)


def test_order_single_detector_no_warning() -> None:
    block = Block(id="b", name="A", detectors=[_detector(0)])
    assert WARN_ORDER_GAP not in _codes(block)


# ---------------------------------------------------------------------------
# Sauber konfigurierter Block
# ---------------------------------------------------------------------------
def test_clean_block_no_warnings() -> None:
    block = Block(
        id="b",
        name="A",
        length_mm=1000,
        detectors=[_detector(0, 400), _detector(1, 600)],
        markers_forward=DirectionMarkers(
            stop=Marker(position_mm=900), brake=Marker(detector_ref=(1, 2))
        ),
        markers_backward=DirectionMarkers(stop=Marker(position_mm=100)),
    )
    assert block_consistency_warnings(block) == []
