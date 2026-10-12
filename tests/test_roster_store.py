"""Tests fuer die Datei-Persistenz der Lok-Stammdaten (roster_store)."""

from __future__ import annotations

from pathlib import Path

import pytest

from modellbahn.domain import roster_store
from modellbahn.domain.roster import Locomotive, Roster
from modellbahn.domain.roster_codec import RosterDecodeError


def _full_roster() -> Roster:
    """Baut ein nicht-triviales Roster mit mehreren Loks und allen Feldern."""
    roster = Roster(version=1)
    loco_a = Locomotive(
        id="a1",
        name="BR 218",
        address=218,
        speed_steps=28,
        function_count=12,
        length_mm=303,
        max_speed_kmh=140,
        notes="Diesellok",
    )
    loco_b = Locomotive(
        id="b1",
        name="BR 103",
        address=103,
    )
    roster.locomotives[loco_a.id] = loco_a
    roster.locomotives[loco_b.id] = loco_b
    return roster


def test_load_missing_file_returns_empty_roster(tmp_path: Path) -> None:
    result = roster_store.load(tmp_path / "fehlt.json")
    assert result == Roster()
    assert result.locomotives == {}
    assert result.version == 1


def test_save_then_load_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "roster.json"
    original = _full_roster()
    roster_store.save(path, original)
    assert roster_store.load(path) == original


def test_load_corrupt_json_raises(tmp_path: Path) -> None:
    path = tmp_path / "roster.json"
    path.write_text("{ kein json", encoding="utf-8")
    with pytest.raises(RosterDecodeError) as excinfo:
        roster_store.load(path)
    assert str(path) in str(excinfo.value)


def test_load_invalid_schema_raises(tmp_path: Path) -> None:
    path = tmp_path / "roster.json"
    path.write_text('{"version": 999, "locomotives": []}', encoding="utf-8")
    with pytest.raises(RosterDecodeError):
        roster_store.load(path)


def test_atomic_write_no_tmp_leftover(tmp_path: Path) -> None:
    path = tmp_path / "roster.json"
    roster_store.save(path, _full_roster())

    assert path.exists()
    leftovers = list(tmp_path.glob("*" + roster_store.TMP_SUFFIX))
    assert leftovers == []
    assert roster_store.load(path) == _full_roster()


def test_save_creates_target_directory(tmp_path: Path) -> None:
    path = tmp_path / "neu" / "tiefer" / "roster.json"
    roster_store.save(path, _full_roster())
    assert path.exists()
    assert roster_store.load(path) == _full_roster()


def test_first_save_without_existing_file_creates_no_backup(tmp_path: Path) -> None:
    path = tmp_path / "roster.json"
    backup_dir = tmp_path / "backups"
    roster_store.save(path, _full_roster(), backup_dir=backup_dir)
    assert not backup_dir.exists() or list(backup_dir.iterdir()) == []


def test_backup_created_on_overwrite_with_previous_content(tmp_path: Path) -> None:
    path = tmp_path / "roster.json"
    backup_dir = tmp_path / "backups"

    first = _full_roster()
    roster_store.save(path, first, backup_dir=backup_dir)

    second = Roster(version=1)
    second.locomotives["x"] = Locomotive(id="x", name="Nur eine Lok", address=5)
    roster_store.save(path, second, backup_dir=backup_dir)

    backups = sorted(backup_dir.glob("roster-*.json"))
    assert len(backups) == 1
    assert roster_store.load(backups[0]) == first
    assert roster_store.load(path) == second


def test_backup_rotation_keeps_n_newest(tmp_path: Path) -> None:
    path = tmp_path / "roster.json"
    backup_dir = tmp_path / "backups"
    count = 3

    for i in range(count + 3):
        roster = Roster(version=1)
        roster.locomotives[f"l{i}"] = Locomotive(id=f"l{i}", name=f"Lok {i}", address=i + 1)
        roster_store.save(path, roster, backup_dir=backup_dir, backup_count=count)

    backups = sorted(backup_dir.glob("roster-*.json"))
    assert len(backups) == count
    assert len({b.name for b in backups}) == count
