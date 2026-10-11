"""Tests der Z21-Meldungsdekodierung."""

from __future__ import annotations

from modellbahn.z21.messages import (
    DetectorLocos,
    DetectorOccupancy,
    LocoInfo,
    SystemState,
    TrackPower,
    TurnoutInfo,
    parse_message,
)


def _can_detector_payload(
    nid: int, addr: int, port: int, typ: int, value1: int, value2: int = 0
) -> bytes:
    """Baut den Data-Teil eines LAN_CAN_DETECTOR-Datensatzes (little endian)."""
    return (
        nid.to_bytes(2, "little")
        + addr.to_bytes(2, "little")
        + bytes([port, typ])
        + value1.to_bytes(2, "little")
        + value2.to_bytes(2, "little")
    )


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


def test_parse_turnout_info_positions() -> None:
    # X-Header 0x43, Adresse 5, DB3 000000ZZ
    p0 = parse_message(0x40, bytes([0x43, 0x00, 0x05, 0b01]))
    p1 = parse_message(0x40, bytes([0x43, 0x00, 0x05, 0b10]))
    unknown = parse_message(0x40, bytes([0x43, 0x00, 0x05, 0b00]))
    assert isinstance(p0, TurnoutInfo) and p0.address == 5 and p0.position == 0
    assert isinstance(p1, TurnoutInfo) and p1.position == 1
    assert isinstance(unknown, TurnoutInfo) and unknown.position is None


def test_parse_unknown_returns_none() -> None:
    assert parse_message(0x40, bytes([0x99, 0x00])) is None
    assert parse_message(0x40, b"") is None


# --- CAN-Belegtmelder (LAN_CAN_DETECTOR, Header 0xC4) -----------------------


def test_parse_can_detector_occupancy_all_value1_cases() -> None:
    cases = {
        0x0000: (False, False, False, 0),  # frei / ohne Spannung
        0x0100: (False, True, False, 0),   # frei / mit Spannung
        0x1000: (True, False, False, 0),   # besetzt / ohne Spannung
        0x1100: (True, True, False, 0),    # besetzt / mit Spannung
        0x1201: (True, True, True, 1),     # besetzt / Ueberlast 1
        0x1202: (True, True, True, 2),     # besetzt / Ueberlast 2
        0x1203: (True, True, True, 3),     # besetzt / Ueberlast 3
    }
    for value1, (occupied, with_power, overload, level) in cases.items():
        data = _can_detector_payload(0xD764, 0, 0, 0x01, value1)
        msg = parse_message(0xC4, data)
        assert isinstance(msg, DetectorOccupancy), hex(value1)
        assert msg.occupied is occupied, hex(value1)
        assert msg.with_power is with_power, hex(value1)
        assert msg.overload is overload, hex(value1)
        assert msg.overload_level == level, hex(value1)


def test_parse_can_detector_occupancy_header_fields() -> None:
    data = _can_detector_payload(0xD764, 1, 3, 0x01, 0x1100)
    msg = parse_message(0xC4, data)
    assert isinstance(msg, DetectorOccupancy)
    assert msg.nid == 0xD764
    assert msg.addr == 1
    assert msg.port == 3


def test_parse_can_detector_locos_two_addresses_with_direction() -> None:
    # Value1 = vorwaerts Adresse 3 = (0b10<<14)|3 = 0x8003
    # Value2 = rueckwaerts Adresse 42 = (0b11<<14)|42 = 0xC02A
    data = _can_detector_payload(0xD764, 0, 0, 0x11, 0x8003, 0xC02A)
    msg = parse_message(0xC4, data)
    assert isinstance(msg, DetectorLocos)
    assert msg.first_block is True
    assert len(msg.locos) == 2
    assert msg.locos[0].address == 3 and msg.locos[0].direction == "forward"
    assert msg.locos[1].address == 42 and msg.locos[1].direction == "backward"


def test_parse_can_detector_locos_zero_ends_list() -> None:
    # Value2 = 0 beendet die Liste nach der ersten Adresse.
    data = _can_detector_payload(0xD764, 0, 0, 0x11, 0x8003, 0x0000)
    msg = parse_message(0xC4, data)
    assert isinstance(msg, DetectorLocos)
    assert len(msg.locos) == 1
    assert msg.locos[0].address == 3


def test_parse_can_detector_locos_first_block_flag() -> None:
    first = parse_message(0xC4, _can_detector_payload(0xD764, 0, 0, 0x11, 0x8003))
    further = parse_message(0xC4, _can_detector_payload(0xD764, 0, 0, 0x12, 0x8004))
    assert isinstance(first, DetectorLocos) and first.first_block is True
    assert isinstance(further, DetectorLocos) and further.first_block is False


# --- Verifizierte echte Bytes aus einem Live-Test (echte Z21 + 10808) -------
# Nutzer: Moduladresse auf 1 gestellt, Eingang 1 belegt. Addr kommt als 0
# (bestaetigt (nid, port) als Schluessel); Port 0 = physischer Eingang 1.


def test_parse_can_detector_real_occupied_input1() -> None:
    data = bytes.fromhex("64 d7 00 00 00 01 00 11 00 00".replace(" ", ""))
    msg = parse_message(0xC4, data)
    assert isinstance(msg, DetectorOccupancy)
    assert msg.nid == 0xD764
    assert msg.addr == 0
    assert msg.port == 0
    assert msg.occupied is True
    assert msg.with_power is True
    assert msg.overload is False


def test_parse_can_detector_real_free_input2() -> None:
    data = bytes.fromhex("64 d7 00 00 01 01 00 01 00 00".replace(" ", ""))
    msg = parse_message(0xC4, data)
    assert isinstance(msg, DetectorOccupancy)
    assert msg.port == 1
    assert msg.occupied is False
    assert msg.with_power is True


def test_parse_can_detector_real_loco_address_backward() -> None:
    data = bytes.fromhex("64 d7 00 00 00 11 03 c0 00 00".replace(" ", ""))
    msg = parse_message(0xC4, data)
    assert isinstance(msg, DetectorLocos)
    assert msg.port == 0
    assert len(msg.locos) == 1
    assert msg.locos[0].address == 3
    assert msg.locos[0].direction == "backward"
