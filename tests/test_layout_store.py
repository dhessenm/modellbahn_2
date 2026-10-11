"""Tests fuer die Datei-Persistenz des Anlagenmodells (layout_store)."""

from __future__ import annotations

from pathlib import Path

import pytest

from modellbahn.domain import layout_store
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
from modellbahn.domain.layout_codec import LayoutDecodeError


def _full_layout() -> Layout:
    """Baut ein nicht-triviales Layout mit allen Entitaetstypen und Varianten."""
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
    layout.elements[weiche.id] = weiche
    layout.elements[dkw.id] = dkw

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
        claimed_element_ids=["e2", "e1"],
    )
    layout.routes[route.id] = route

    return layout


def test_load_missing_file_returns_empty_layout(tmp_path: Path) -> None:
    result = layout_store.load(tmp_path / "fehlt.json")
    assert result == Layout()
    assert result.blocks == {}
    assert result.elements == {}
    assert result.routes == {}
    assert result.version == 1


def test_save_then_load_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "layout.json"
    original = _full_layout()
    layout_store.save(path, original)
    assert layout_store.load(path) == original


def test_load_corrupt_json_raises(tmp_path: Path) -> None:
    path = tmp_path / "layout.json"
    path.write_text("{ kein json", encoding="utf-8")
    with pytest.raises(LayoutDecodeError) as excinfo:
        layout_store.load(path)
    # Die Meldung nennt den Pfad; es gibt KEINEN stillen leeren Fallback.
    assert str(path) in str(excinfo.value)


def test_load_invalid_schema_raises(tmp_path: Path) -> None:
    path = tmp_path / "layout.json"
    path.write_text(
        '{"version": 999, "blocks": [], "elements": [], "routes": []}',
        encoding="utf-8",
    )
    with pytest.raises(LayoutDecodeError):
        layout_store.load(path)


def test_atomic_write_no_tmp_leftover(tmp_path: Path) -> None:
    path = tmp_path / "layout.json"
    layout_store.save(path, _full_layout())

    assert path.exists()
    # Keine Temp-Datei bleibt liegen.
    leftovers = list(tmp_path.glob("*" + layout_store.TMP_SUFFIX))
    assert leftovers == []
    # Inhalt ist wieder ladbar.
    assert layout_store.load(path) == _full_layout()


def test_save_creates_target_directory(tmp_path: Path) -> None:
    path = tmp_path / "neu" / "tiefer" / "layout.json"
    layout_store.save(path, _full_layout())
    assert path.exists()
    assert layout_store.load(path) == _full_layout()


def test_first_save_without_existing_file_creates_no_backup(tmp_path: Path) -> None:
    path = tmp_path / "layout.json"
    backup_dir = tmp_path / "backups"
    layout_store.save(path, _full_layout(), backup_dir=backup_dir)
    # Kein Backup, weil vorher keine Zieldatei existierte.
    assert not backup_dir.exists() or list(backup_dir.iterdir()) == []


def test_backup_created_on_overwrite_with_previous_content(tmp_path: Path) -> None:
    path = tmp_path / "layout.json"
    backup_dir = tmp_path / "backups"

    first = _full_layout()
    layout_store.save(path, first, backup_dir=backup_dir)

    second = Layout(version=1)
    second.blocks["x"] = Block(id="x", name="Nur ein Block")
    layout_store.save(path, second, backup_dir=backup_dir)

    backups = sorted(backup_dir.glob("layout-*.json"))
    assert len(backups) == 1
    # Das Backup enthaelt den VORHERIGEN Stand.
    assert layout_store.load(backups[0]) == first
    # Die Zieldatei enthaelt den neuen Stand.
    assert layout_store.load(path) == second


def test_backup_rotation_keeps_n_newest(tmp_path: Path) -> None:
    path = tmp_path / "layout.json"
    backup_dir = tmp_path / "backups"
    count = 3

    # Mehr als count+1 Speichervorgaenge mit wechselndem Inhalt.
    for i in range(count + 3):
        layout = Layout(version=1)
        layout.blocks[f"b{i}"] = Block(id=f"b{i}", name=f"Block {i}")
        layout_store.save(path, layout, backup_dir=backup_dir, backup_count=count)

    backups = sorted(backup_dir.glob("layout-*.json"))
    assert len(backups) == count
    # Eindeutige Namen trotz schneller Speichervorgaenge.
    assert len({b.name for b in backups}) == count


def test_unique_backup_path_disambiguates_same_timestamp(tmp_path: Path) -> None:
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    ts = "20240521T081503123456"

    paths = []
    for _ in range(3):
        candidate = layout_store._unique_backup_path(backup_dir, ts)
        candidate.write_text("x", encoding="utf-8")
        paths.append(candidate.name)

    # Eindeutige Namen trotz identischer Mikrosekunde.
    assert len(set(paths)) == 3
    assert paths[0] == f"layout-{ts}.json"
    assert paths[1] == f"layout-{ts}-01.json"
    assert paths[2] == f"layout-{ts}-02.json"
    # Die zweistelligen Suffixe wachsen in fester Breite -> ihre relative
    # lexikografische Ordnung bleibt chronologisch (-01 < -02 < ...).
    suffixed = paths[1:]
    assert suffixed == sorted(suffixed)


def test_rotation_ignores_foreign_files(tmp_path: Path) -> None:
    path = tmp_path / "layout.json"
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    foreign = backup_dir / "README.txt"
    foreign.write_text("nicht anfassen", encoding="utf-8")

    for i in range(5):
        layout = Layout(version=1)
        layout.blocks[f"b{i}"] = Block(id=f"b{i}", name=f"Block {i}")
        layout_store.save(path, layout, backup_dir=backup_dir, backup_count=2)

    assert foreign.exists()
    assert len(sorted(backup_dir.glob("layout-*.json"))) == 2
