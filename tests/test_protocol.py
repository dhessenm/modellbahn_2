"""Tests der Z21-Protokollschicht (ohne Hardware)."""

from __future__ import annotations

from modellbahn.z21.protocol import (
    build_dataset,
    build_get_status,
    build_loco_drive,
    build_loco_function,
    build_track_power_off,
    build_track_power_on,
    build_xbus,
    encode_loco_address,
    parse_datasets,
    xbus_checksum,
)


def test_xbus_checksum_is_xor_over_payload() -> None:
    assert xbus_checksum(bytes([0x21, 0x24])) == 0x05
    assert xbus_checksum(b"") == 0x00


def test_build_dataset_prefixes_little_endian_len_and_header() -> None:
    ds = build_dataset(0x40, bytes([0x21, 0x24, 0x05]))
    assert ds == bytes([0x07, 0x00, 0x40, 0x00, 0x21, 0x24, 0x05])


def test_build_xbus_appends_checksum() -> None:
    ds = build_xbus(0x21, bytes([0x24]))
    assert ds == bytes([0x07, 0x00, 0x40, 0x00, 0x21, 0x24, 0x05])


def test_get_status_and_track_power() -> None:
    assert build_get_status() == bytes([0x07, 0x00, 0x40, 0x00, 0x21, 0x24, 0x05])
    assert build_track_power_on() == bytes([0x07, 0x00, 0x40, 0x00, 0x21, 0x81, 0xA0])
    assert build_track_power_off() == bytes([0x07, 0x00, 0x40, 0x00, 0x21, 0x80, 0xA1])


def test_encode_loco_address_sets_high_bits_above_128() -> None:
    assert encode_loco_address(3) == (0x00, 0x03)
    msb, lsb = encode_loco_address(1000)
    assert msb == (0xC0 | ((1000 >> 8) & 0x3F))
    assert lsb == (1000 & 0xFF)


def test_build_loco_drive_direction_and_speed() -> None:
    # Adresse 3, Fahrstufe 10 vorwaerts (128 Fahrstufen): Wert = 10+1 = 11, R=1
    ds = build_loco_drive(3, 10, forward=True)
    # DataLen 0x0A, Header 0x40, X-Header 0xE4, DB0 0x13, MSB 0x00, LSB 0x03, DB3 0x8B
    assert ds[:7] == bytes([0x0A, 0x00, 0x40, 0x00, 0xE4, 0x13, 0x00])
    assert ds[7] == 0x03
    assert ds[8] == 0x80 | 11  # forward + speed_value


def test_build_loco_function_toggle_bits() -> None:
    # F0 einschalten an Adresse 3: DB3 = TT(01)<<6 | 0 = 0x40
    ds = build_loco_function(3, 0, on=True)
    assert ds[4] == 0xE4 and ds[5] == 0xF8
    assert ds[8] == 0x40
    # F1 ausschalten: DB3 = 0x01
    ds_off = build_loco_function(3, 1, on=False)
    assert ds_off[8] == 0x01


def test_parse_datasets_splits_combined_payload() -> None:
    combined = build_get_status() + build_track_power_on()
    out = parse_datasets(combined)
    assert len(out) == 2
    assert out[0][0] == 0x40
    assert out[1][0] == 0x40
