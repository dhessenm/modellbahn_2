"""Tests fuer die Fachlogik der Lok-Stammdaten (roster_service)."""

from __future__ import annotations

import pytest

from modellbahn.domain.roster_service import (
    WARN_ADDRESS_DUPLICATE,
    RosterService,
    RosterValidationError,
)


class TestCreateLocomotive:
    """Lok anlegen."""

    def test_create_with_all_fields(self) -> None:
        svc = RosterService()
        loco = svc.create_locomotive(
            name="BR 218",
            address=218,
            speed_steps=28,
            function_count=12,
            length_mm=303,
            max_speed_kmh=140,
            notes="Diesellok",
        )
        assert loco.name == "BR 218"
        assert loco.address == 218
        assert loco.speed_steps == 28
        assert loco.function_count == 12
        assert loco.length_mm == 303
        assert loco.max_speed_kmh == 140
        assert loco.notes == "Diesellok"
        assert len(loco.id) == 32  # UUID4 hex

    def test_create_with_defaults(self) -> None:
        svc = RosterService()
        loco = svc.create_locomotive(name="BR 103", address=103)
        assert loco.speed_steps == 128
        assert loco.function_count == 28
        assert loco.length_mm is None
        assert loco.max_speed_kmh is None
        assert loco.notes == ""

    def test_name_empty_raises(self) -> None:
        svc = RosterService()
        with pytest.raises(RosterValidationError, match="nicht leer"):
            svc.create_locomotive(name="   ", address=1)

    def test_name_duplicate_casefold_raises(self) -> None:
        svc = RosterService()
        svc.create_locomotive(name="BR 218", address=218)
        with pytest.raises(RosterValidationError, match="bereits vergeben"):
            svc.create_locomotive(name="  br 218  ", address=219)

    def test_address_zero_raises(self) -> None:
        svc = RosterService()
        with pytest.raises(RosterValidationError, match="Adresse"):
            svc.create_locomotive(name="Lok", address=0)

    def test_address_10000_raises(self) -> None:
        svc = RosterService()
        with pytest.raises(RosterValidationError, match="Adresse"):
            svc.create_locomotive(name="Lok", address=10000)

    def test_address_1_ok(self) -> None:
        svc = RosterService()
        loco = svc.create_locomotive(name="Lok1", address=1)
        assert loco.address == 1

    def test_address_9999_ok(self) -> None:
        svc = RosterService()
        loco = svc.create_locomotive(name="Lok2", address=9999)
        assert loco.address == 9999

    def test_speed_steps_64_raises(self) -> None:
        svc = RosterService()
        with pytest.raises(RosterValidationError, match="speed_steps"):
            svc.create_locomotive(name="Lok", address=1, speed_steps=64)

    def test_speed_steps_14_ok(self) -> None:
        svc = RosterService()
        assert svc.create_locomotive(name="L1", address=1, speed_steps=14).speed_steps == 14

    def test_speed_steps_28_ok(self) -> None:
        svc = RosterService()
        assert svc.create_locomotive(name="L2", address=2, speed_steps=28).speed_steps == 28

    def test_speed_steps_128_ok(self) -> None:
        svc = RosterService()
        assert svc.create_locomotive(name="L3", address=3, speed_steps=128).speed_steps == 128

    def test_function_count_negative_raises(self) -> None:
        svc = RosterService()
        with pytest.raises(RosterValidationError, match="function_count"):
            svc.create_locomotive(name="Lok", address=1, function_count=-1)

    def test_function_count_29_raises(self) -> None:
        svc = RosterService()
        with pytest.raises(RosterValidationError, match="function_count"):
            svc.create_locomotive(name="Lok", address=1, function_count=29)

    def test_function_count_0_ok(self) -> None:
        svc = RosterService()
        assert svc.create_locomotive(name="L1", address=1, function_count=0).function_count == 0

    def test_function_count_28_ok(self) -> None:
        svc = RosterService()
        assert svc.create_locomotive(name="L2", address=2, function_count=28).function_count == 28

    def test_length_mm_negative_raises(self) -> None:
        svc = RosterService()
        with pytest.raises(RosterValidationError, match="Laenge"):
            svc.create_locomotive(name="Lok", address=1, length_mm=-1)

    def test_length_mm_zero_ok(self) -> None:
        svc = RosterService()
        assert svc.create_locomotive(name="L1", address=1, length_mm=0).length_mm == 0

    def test_length_mm_none_ok(self) -> None:
        svc = RosterService()
        assert svc.create_locomotive(name="L2", address=2, length_mm=None).length_mm is None

    def test_max_speed_kmh_negative_raises(self) -> None:
        svc = RosterService()
        with pytest.raises(RosterValidationError, match="Hoechstgeschwindigkeit"):
            svc.create_locomotive(name="Lok", address=1, max_speed_kmh=-1)

    def test_max_speed_kmh_zero_ok(self) -> None:
        svc = RosterService()
        assert svc.create_locomotive(name="L1", address=1, max_speed_kmh=0).max_speed_kmh == 0

    def test_max_speed_kmh_none_ok(self) -> None:
        svc = RosterService()
        assert svc.create_locomotive(name="L2", address=2, max_speed_kmh=None).max_speed_kmh is None


class TestUpdateLocomotive:
    """Lok aendern."""

    def test_update_fields(self) -> None:
        svc = RosterService()
        loco = svc.create_locomotive(name="Alt", address=1)
        updated = svc.update_locomotive(loco.id, name="Neu", address=2, speed_steps=14)
        assert updated.name == "Neu"
        assert updated.address == 2
        assert updated.speed_steps == 14

    def test_rename_to_own_name_ok(self) -> None:
        svc = RosterService()
        loco = svc.create_locomotive(name="BR 218", address=218)
        updated = svc.update_locomotive(loco.id, name="BR 218")
        assert updated.name == "BR 218"

    def test_rename_to_other_name_raises(self) -> None:
        svc = RosterService()
        svc.create_locomotive(name="BR 218", address=218)
        loco2 = svc.create_locomotive(name="BR 103", address=103)
        with pytest.raises(RosterValidationError, match="bereits vergeben"):
            svc.update_locomotive(loco2.id, name="br 218")

    def test_set_length_mm_to_none(self) -> None:
        svc = RosterService()
        loco = svc.create_locomotive(name="Lok", address=1, length_mm=200)
        updated = svc.update_locomotive(loco.id, length_mm=None)
        assert updated.length_mm is None

    def test_set_max_speed_kmh_to_none(self) -> None:
        svc = RosterService()
        loco = svc.create_locomotive(name="Lok", address=1, max_speed_kmh=120)
        updated = svc.update_locomotive(loco.id, max_speed_kmh=None)
        assert updated.max_speed_kmh is None

    def test_unknown_id_raises(self) -> None:
        svc = RosterService()
        with pytest.raises(RosterValidationError, match="Unbekannte"):
            svc.update_locomotive("nope", name="X")


class TestDeleteLocomotive:
    """Lok loeschen."""

    def test_delete_success(self) -> None:
        svc = RosterService()
        loco = svc.create_locomotive(name="Lok", address=1)
        svc.delete_locomotive(loco.id)
        assert svc.list_locomotives() == []

    def test_delete_unknown_id_raises(self) -> None:
        svc = RosterService()
        with pytest.raises(RosterValidationError, match="Unbekannte"):
            svc.delete_locomotive("nope")


class TestGetLocomotive:
    """Lok abrufen."""

    def test_get_success(self) -> None:
        svc = RosterService()
        loco = svc.create_locomotive(name="Lok", address=1)
        assert svc.get_locomotive(loco.id) is loco

    def test_get_unknown_id_raises(self) -> None:
        svc = RosterService()
        with pytest.raises(RosterValidationError, match="Unbekannte"):
            svc.get_locomotive("nope")


class TestListLocomotives:
    """Lokliste."""

    def test_insertion_order(self) -> None:
        svc = RosterService()
        first = svc.create_locomotive(name="A", address=1)
        second = svc.create_locomotive(name="B", address=2)
        third = svc.create_locomotive(name="C", address=3)
        result = svc.list_locomotives()
        assert [loco.id for loco in result] == [first.id, second.id, third.id]


class TestAddressWarnings:
    """Adress-Doppelbelegungs-Warnungen."""

    def test_duplicate_address_warning(self) -> None:
        svc = RosterService()
        loco1 = svc.create_locomotive(name="Lok1", address=42)
        loco2 = svc.create_locomotive(name="Lok2", address=42)
        warnings1 = svc.address_warnings(loco1.id)
        assert len(warnings1) == 1
        assert warnings1[0].code == WARN_ADDRESS_DUPLICATE
        assert "Lok2" in warnings1[0].message
        warnings2 = svc.address_warnings(loco2.id)
        assert len(warnings2) == 1
        assert "Lok1" in warnings2[0].message

    def test_no_duplicate_no_warning(self) -> None:
        svc = RosterService()
        loco = svc.create_locomotive(name="Lok", address=1)
        assert svc.address_warnings(loco.id) == []
