"""Tests der Z21-Protokollschicht (ohne Hardware)."""

from __future__ import annotations

from modellbahn.z21.protocol import build_dataset, build_xbus, xbus_checksum


def test_xbus_checksum_is_xor_over_payload() -> None:
    assert xbus_checksum(bytes([0x21, 0x24])) == 0x05
    assert xbus_checksum(b"") == 0x00


def test_build_dataset_prefixes_little_endian_len_and_header() -> None:
    ds = build_dataset(0x40, bytes([0x21, 0x24, 0x05]))
    # DataLen = 4 + 3 = 7 -> 0x07 0x00, Header 0x40 -> 0x40 0x00
    assert ds == bytes([0x07, 0x00, 0x40, 0x00, 0x21, 0x24, 0x05])


def test_build_xbus_appends_checksum() -> None:
    # LAN_X_GET_STATUS: X-Header 0x21, DB0 0x24, XOR 0x05
    ds = build_xbus(0x21, bytes([0x24]))
    assert ds == bytes([0x07, 0x00, 0x40, 0x00, 0x21, 0x24, 0x05])
