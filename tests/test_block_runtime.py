"""Tests fuer die reine Ableitung des Laufzeit-Blockzustands (`block_runtime`).

Konstruiert `Block`/`DetectorAssignment` (statisch) und `LayoutState`/
`DetectorInput` (live) direkt und prueft die abgeleitete Belegung sowie die
aggregierten Lokadressen. Besonderes Augenmerk auf dem sicherheitsrelevanten
Randfall „zugeordnet, aber nie live gesehen" (-> `unknown`, nicht `free`).
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from modellbahn.domain.block_runtime import (
    FREE,
    OCCUPIED,
    UNKNOWN,
    BlockRuntime,
    derive_all_block_runtimes,
    derive_block_runtime,
)
from modellbahn.domain.layout import Block, DetectorAssignment, Layout
from modellbahn.domain.state import DetectorInput, LayoutState


def _assignment(nid: int, port: int, order: int) -> DetectorAssignment:
    return DetectorAssignment(detector_nid=nid, detector_port=port, order=order)


def _block(
    block_id: str = "b1", name: str = "A", detectors: list[DetectorAssignment] | None = None
) -> Block:
    return Block(id=block_id, name=name, detectors=detectors or [])


def _state(*detector_inputs: DetectorInput) -> LayoutState:
    return LayoutState(detectors={(di.nid, di.port): di for di in detector_inputs})


def test_no_detectors_is_unknown() -> None:
    block = _block(detectors=[])
    runtime = derive_block_runtime(block, _state())
    assert runtime.occupancy == UNKNOWN
    assert runtime.loco_addresses == []


def test_all_assigned_detectors_live_and_free_is_free() -> None:
    block = _block(detectors=[_assignment(1, 0, 0), _assignment(1, 1, 1)])
    state = _state(
        DetectorInput(nid=1, port=0, occupied=False),
        DetectorInput(nid=1, port=1, occupied=False),
    )
    runtime = derive_block_runtime(block, state)
    assert runtime.occupancy == FREE
    assert runtime.loco_addresses == []


def test_any_occupied_detector_is_occupied() -> None:
    block = _block(detectors=[_assignment(1, 0, 0), _assignment(1, 1, 1)])
    state = _state(
        DetectorInput(nid=1, port=0, occupied=False),
        DetectorInput(nid=1, port=1, occupied=True),
    )
    runtime = derive_block_runtime(block, state)
    assert runtime.occupancy == OCCUPIED


def test_assigned_but_never_seen_live_is_unknown_not_free() -> None:
    # Sicherheitsrandfall: Melder zugeordnet, aber kein Live-Datensatz vorhanden.
    # Ein nie live gesehener Melder ist KEINE Freimeldung -> unknown (nicht free),
    # damit ein moeglicherweise belegter Block nicht faelschlich als frei gilt.
    block = _block(detectors=[_assignment(1, 0, 0), _assignment(1, 1, 1)])
    runtime = derive_block_runtime(block, _state())
    assert runtime.occupancy == UNKNOWN
    assert runtime.loco_addresses == []


def test_mix_of_live_free_and_unseen_is_free() -> None:
    # Semantik: ein zugeordneter Melder ist live & frei, ein weiterer ist zwar
    # zugeordnet, aber nicht live bekannt. Mindestens ein live-freier Melder
    # rechtfertigt free; der unbekannte Melder verhindert free nicht.
    block = _block(detectors=[_assignment(1, 0, 0), _assignment(1, 1, 1)])
    state = _state(DetectorInput(nid=1, port=0, occupied=False))
    runtime = derive_block_runtime(block, state)
    assert runtime.occupancy == FREE


def test_occupied_without_identity() -> None:
    block = _block(detectors=[_assignment(1, 0, 0)])
    state = _state(DetectorInput(nid=1, port=0, occupied=True, locos=[]))
    runtime = derive_block_runtime(block, state)
    assert runtime.occupancy == OCCUPIED
    assert runtime.loco_addresses == []


def test_loco_addresses_deduplicated_and_sorted() -> None:
    block = _block(detectors=[_assignment(1, 0, 0), _assignment(1, 1, 1)])
    state = _state(
        DetectorInput(nid=1, port=0, occupied=True, locos=[(10, "fwd"), (3, "bwd")]),
        DetectorInput(nid=1, port=1, occupied=False, locos=[(10, "fwd")]),
    )
    runtime = derive_block_runtime(block, state)
    # Lok 10 ueber beide Melder gemeldet -> nur einmal; Richtung ignoriert; sortiert.
    assert runtime.loco_addresses == [3, 10]
    assert runtime.occupancy == OCCUPIED


def test_derive_all_block_runtimes_one_per_block_in_order() -> None:
    block_empty = _block(block_id="b1", name="A", detectors=[])
    block_occupied = _block(block_id="b2", name="B", detectors=[_assignment(2, 0, 0)])
    layout = Layout(blocks={"b1": block_empty, "b2": block_occupied})
    state = _state(DetectorInput(nid=2, port=0, occupied=True))
    result = derive_all_block_runtimes(layout, state)
    assert [r.block_id for r in result] == ["b1", "b2"]
    assert result[0].occupancy == UNKNOWN
    assert result[1].occupancy == OCCUPIED


def test_block_runtime_is_frozen() -> None:
    runtime = BlockRuntime(block_id="b1", occupancy=FREE, loco_addresses=[])
    with pytest.raises(FrozenInstanceError):
        runtime.occupancy = OCCUPIED  # type: ignore[misc]
