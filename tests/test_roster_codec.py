"""Tests fuer die Serialisierung der Lok-Stammdaten (roster_codec)."""

from __future__ import annotations

import pytest

from modellbahn.domain.roster import Locomotive, Roster
from modellbahn.domain.roster_codec import RosterDecodeError, from_dict, to_dict


def _full_roster() -> Roster:
    """Baut ein Roster mit allen Feldern gesetzt."""
    roster = Roster(version=1)
    loco = Locomotive(
        id="aaa111",
        name="BR 218",
        address=218,
        speed_steps=28,
        function_count=12,
        length_mm=303,
        max_speed_kmh=140,
        notes="Diesellok Epoche IV",
    )
    roster.locomotives[loco.id] = loco
    return roster


def _minimal_roster() -> Roster:
    """Baut ein Roster mit nur Pflichtfeldern und Defaults."""
    roster = Roster(version=1)
    loco = Locomotive(
        id="bbb222",
        name="BR 103",
        address=103,
    )
    roster.locomotives[loco.id] = loco
    return roster


class TestRoundTrip:
    """to_dict -> from_dict Round-Trip."""

    def test_all_fields_set(self) -> None:
        original = _full_roster()
        assert from_dict(to_dict(original)) == original

    def test_only_defaults(self) -> None:
        original = _minimal_roster()
        restored = from_dict(to_dict(original))
        assert restored == original
        loco = list(restored.locomotives.values())[0]
        assert loco.speed_steps == 128
        assert loco.function_count == 28
        assert loco.length_mm is None
        assert loco.max_speed_kmh is None
        assert loco.notes == ""


class TestOptionalFields:
    """Optionale Felder null/fehlend."""

    def test_null_values_produce_none(self) -> None:
        data = {
            "version": 1,
            "locomotives": [
                {
                    "id": "c1",
                    "name": "Test",
                    "address": 1,
                    "speed_steps": 128,
                    "function_count": 28,
                    "length_mm": None,
                    "max_speed_kmh": None,
                    "notes": "",
                }
            ],
        }
        roster = from_dict(data)
        loco = roster.locomotives["c1"]
        assert loco.length_mm is None
        assert loco.max_speed_kmh is None

    def test_missing_optional_fields_use_defaults(self) -> None:
        data = {
            "version": 1,
            "locomotives": [
                {
                    "id": "c2",
                    "name": "Minimal",
                    "address": 42,
                }
            ],
        }
        roster = from_dict(data)
        loco = roster.locomotives["c2"]
        assert loco.speed_steps == 128
        assert loco.function_count == 28
        assert loco.length_mm is None
        assert loco.max_speed_kmh is None
        assert loco.notes == ""


class TestVersionErrors:
    """Schema-Version-Pruefung."""

    def test_wrong_version_raises(self) -> None:
        data = {"version": 999, "locomotives": []}
        with pytest.raises(RosterDecodeError, match="Unbekannte Schema-Version"):
            from_dict(data)

    def test_bool_version_raises(self) -> None:
        data = {"version": True, "locomotives": []}
        with pytest.raises(RosterDecodeError, match="keine ganze Zahl"):
            from_dict(data)

    def test_missing_version_raises(self) -> None:
        data = {"locomotives": []}
        with pytest.raises(RosterDecodeError, match="fehlt"):
            from_dict(data)


class TestBrokenInput:
    """Strukturell kaputter Input."""

    def test_not_a_dict_raises(self) -> None:
        with pytest.raises(RosterDecodeError, match="kein Objekt"):
            from_dict("string")  # type: ignore[arg-type]

    def test_missing_locomotives_raises(self) -> None:
        data: dict[str, object] = {"version": 1}
        with pytest.raises(RosterDecodeError, match="keine Liste"):
            from_dict(data)

    def test_locomotive_not_a_dict_raises(self) -> None:
        data: dict[str, object] = {"version": 1, "locomotives": ["nope"]}
        with pytest.raises(RosterDecodeError, match="kein Objekt"):
            from_dict(data)


class TestInvalidSpeedSteps:
    """Ungueltige speed_steps."""

    def test_invalid_speed_steps_raises(self) -> None:
        data = {
            "version": 1,
            "locomotives": [{"id": "x", "name": "Lok", "address": 1, "speed_steps": 64}],
        }
        with pytest.raises(RosterDecodeError, match="ungueltiger speed_steps"):
            from_dict(data)

    def test_valid_speed_steps_14(self) -> None:
        data = {
            "version": 1,
            "locomotives": [{"id": "x", "name": "Lok", "address": 1, "speed_steps": 14}],
        }
        roster = from_dict(data)
        assert roster.locomotives["x"].speed_steps == 14

    def test_valid_speed_steps_28(self) -> None:
        data = {
            "version": 1,
            "locomotives": [{"id": "x", "name": "Lok", "address": 1, "speed_steps": 28}],
        }
        roster = from_dict(data)
        assert roster.locomotives["x"].speed_steps == 28

    def test_valid_speed_steps_128(self) -> None:
        data = {
            "version": 1,
            "locomotives": [{"id": "x", "name": "Lok", "address": 1, "speed_steps": 128}],
        }
        roster = from_dict(data)
        assert roster.locomotives["x"].speed_steps == 128


class TestToDict:
    """Serialisierungsdetails."""

    def test_optional_null_fields_are_always_present(self) -> None:
        roster = _minimal_roster()
        d = to_dict(roster)
        loco_dict = d["locomotives"][0]  # type: ignore[index]
        assert "length_mm" in loco_dict  # type: ignore[operator]
        assert loco_dict["length_mm"] is None  # type: ignore[index]
        assert "max_speed_kmh" in loco_dict  # type: ignore[operator]
        assert loco_dict["max_speed_kmh"] is None  # type: ignore[index]

    def test_locomotives_as_list(self) -> None:
        roster = _full_roster()
        d = to_dict(roster)
        assert isinstance(d["locomotives"], list)
