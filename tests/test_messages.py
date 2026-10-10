"""Tests der Z21-Meldungsdekodierung."""

from __future__ import annotations

from modellbahn.z21.messages import LocoInfo, SystemState, TrackPower, parse_message


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


def test_parse_systemstate_track_power_on() -> None:
    # 16 Byte SystemState; CentralState (Offset 12) = 0x00 => Spannung an
    data = bytes([0x00] * 16)
    msg = parse_message(0x84, data)
    assert isinstance(msg, SystemState)
    assert msg.track_power_on is True
    assert msg.short_circuit is False
    assert msg.emergency_stop is False


def test_parse_systemstate_measurements() -> None:
    # Messwerte: Temperatur (Offset 6, INT16), SupplyVoltage (8, UINT16),
    # VCC/Gleisspannung (10, UINT16) -- jeweils little endian.
    data = bytearray(16)
    data[6:8] = (31).to_bytes(2, "little", signed=True)      # 31 °C
    data[8:10] = (15000).to_bytes(2, "little")                # 15000 mV
    data[10:12] = (18000).to_bytes(2, "little")               # 18000 mV
    msg = parse_message(0x84, bytes(data))
    assert isinstance(msg, SystemState)
    assert msg.temperature_c == 31
    assert msg.supply_voltage_mv == 15000
    assert msg.track_voltage_mv == 18000


def test_parse_systemstate_track_power_off_and_short_circuit() -> None:
    data = bytearray(16)
    data[12] = 0x02 | 0x04  # csTrackVoltageOff | csShortCircuit
    msg = parse_message(0x84, bytes(data))
    assert isinstance(msg, SystemState)
    assert msg.track_power_on is False
    assert msg.short_circuit is True


def test_parse_systemstate_real_sample_from_hardware() -> None:
    # Reale Z21-Antwort (Spannung an): 16 Byte, CentralState an Offset 12 = 0x00
    data = bytes.fromhex("3700030043001f000d4e662e00000000")
    assert len(data) == 16
    msg = parse_message(0x84, data)
    assert isinstance(msg, SystemState)
    assert msg.track_power_on is True
    assert msg.short_circuit is False
    assert msg.emergency_stop is False


def test_parse_unknown_returns_none() -> None:
    assert parse_message(0x40, bytes([0x99, 0x00])) is None
    assert parse_message(0x40, b"") is None
