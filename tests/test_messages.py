"""Tests der Z21-Meldungsdekodierung."""

from __future__ import annotations

from modellbahn.z21.messages import LocoInfo, TrackPower, parse_message


def _loco_info_payload(adr: int, db3: int, db4: int) -> bytes:
    # [0xEF, MSB, LSB, DB2, DB3, DB4]
    msb = (adr >> 8) & 0x3F
    lsb = adr & 0xFF
    return bytes([0xEF, msb, lsb, 0x04, db3, db4])


def test_parse_loco_info_speed_direction_and_f0() -> None:
    # db3: forward (0x80) + speed_value 11 => Fahrstufe 10
    # db4: L-Bit (0x10) gesetzt => F0 ein
    msg = parse_message(0x40, _loco_info_payload(3, 0x80 | 11, 0x10))
    assert isinstance(msg, LocoInfo)
    assert msg.address == 3
    assert msg.speed == 10
    assert msg.forward is True
    assert msg.functions[0] is True
    assert msg.functions[1] is False


def test_parse_track_power_broadcast() -> None:
    on = parse_message(0x40, bytes([0x61, 0x01, 0x60]))
    off = parse_message(0x40, bytes([0x61, 0x00, 0x61]))
    assert isinstance(on, TrackPower) and on.on is True
    assert isinstance(off, TrackPower) and off.on is False


def test_parse_unknown_returns_none() -> None:
    assert parse_message(0x40, bytes([0x99, 0x00])) is None
    assert parse_message(0x40, b"") is None
