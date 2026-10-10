"""Dekodierung eingehender Z21-Meldungen in strukturierte Objekte.

Diese Schicht bleibt rein (keine Fachlogik): sie uebersetzt empfangene
Datensaetze in neutrale Datenobjekte, die die domain-Schicht auswertet.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from modellbahn.z21.protocol import HEADER_LAN_X

# Z21-LAN-Header
HEADER_SYSTEMSTATE = 0x84  # LAN_SYSTEMSTATE_DATACHANGED

# X-Header empfangener X-Bus-Meldungen
XHEADER_LOCO_INFO = 0xEF
XHEADER_STATUS = 0x62  # LAN_X_STATUS_CHANGED, DB0 0x22
XHEADER_BC = 0x61  # Track-Power-Broadcasts: DB0 0x00=OFF, 0x01=ON

# Bits im CentralState (siehe Z21-Spezifikation)
CS_EMERGENCY_STOP = 0x01
CS_TRACK_VOLTAGE_OFF = 0x02
CS_SHORT_CIRCUIT = 0x04


@dataclass
class LocoInfo:
    """Dekodierte LAN_X_LOCO_INFO-Meldung."""

    address: int
    speed: int
    forward: bool
    functions: dict[int, bool] = field(default_factory=dict)


@dataclass
class TrackPower:
    """Zustand der Gleisspannung aus einem Broadcast/Status."""

    on: bool


@dataclass
class SystemState:
    """Ausschnitt aus LAN_SYSTEMSTATE_DATACHANGED (header 0x84).

    Enthaelt die fuer eine Statusanzeige relevanten Felder: Gleisspannung,
    Kurzschluss, Nothalt sowie einige Messwerte (Temperatur, Spannungen).
    """

    track_power_on: bool
    short_circuit: bool
    emergency_stop: bool
    temperature_c: int = 0
    supply_voltage_mv: int = 0
    track_voltage_mv: int = 0


def _decode_address(adr_msb: int, adr_lsb: int) -> int:
    return ((adr_msb & 0x3F) << 8) + adr_lsb


def _decode_speed_128(db3: int) -> tuple[int, bool]:
    """Dekodiert DB3 (RVVVVVVV) fuer 128 Fahrstufen zu (speed 0..126, forward)."""
    forward = bool(db3 & 0x80)
    raw = db3 & 0x7F
    speed = 0 if raw <= 1 else raw - 1  # 0=Stop, 1=Nothalt
    return speed, forward


def _decode_functions(data: bytes) -> dict[int, bool]:
    """Dekodiert die Funktionsbits aus LAN_X_LOCO_INFO (ab DB4)."""
    functions: dict[int, bool] = {}
    # data ist der X-Bus-Payload ab X-Header: [0xEF, MSB, LSB, DB2, DB3, DB4, DB5, ...]
    if len(data) <= 5:
        return functions
    db4 = data[5]
    # DB4 = 0 D S L F G H J : L=F0, F=F4, G=F3, H=F2, J=F1
    functions[0] = bool(db4 & 0x10)  # L
    functions[1] = bool(db4 & 0x01)  # J
    functions[2] = bool(db4 & 0x02)  # H
    functions[3] = bool(db4 & 0x04)  # G
    functions[4] = bool(db4 & 0x08)  # F
    # DB5: F5-F12, DB6: F13-F20, DB7: F21-F28 (jeweils F.. ist bit0)
    for block_index, base in enumerate((5, 13, 21)):
        byte_index = 6 + block_index
        if byte_index < len(data):
            byte = data[byte_index]
            for bit in range(8):
                functions[base + bit] = bool(byte & (1 << bit))
    return functions


def parse_message(header: int, data: bytes) -> LocoInfo | TrackPower | SystemState | None:
    """Wertet einen empfangenen Datensatz aus; None bei irrelevanten Meldungen."""
    if header == HEADER_SYSTEMSTATE and len(data) >= 13:
        # SystemState-Layout (16 Byte, little endian): CentralState an Offset 12.
        # 0..1 MainCurrent, 2..3 ProgCurrent, 4..5 FilteredMainCurrent,
        # 6..7 Temperature (INT16, °C), 8..9 SupplyVoltage (UINT16, mV),
        # 10..11 VCCVoltage/Gleisspannung (UINT16, mV), 12 CentralState.
        temperature = int.from_bytes(data[6:8], "little", signed=True)
        supply_mv = int.from_bytes(data[8:10], "little", signed=False)
        track_mv = int.from_bytes(data[10:12], "little", signed=False)
        central_state = data[12]
        return SystemState(
            track_power_on=not (central_state & CS_TRACK_VOLTAGE_OFF),
            short_circuit=bool(central_state & CS_SHORT_CIRCUIT),
            emergency_stop=bool(central_state & CS_EMERGENCY_STOP),
            temperature_c=temperature,
            supply_voltage_mv=supply_mv,
            track_voltage_mv=track_mv,
        )

    if header != HEADER_LAN_X or not data:
        return None
    x_header = data[0]

    if x_header == XHEADER_LOCO_INFO and len(data) >= 5:
        address = _decode_address(data[1], data[2])
        speed, forward = _decode_speed_128(data[4])
        functions = _decode_functions(data)
        return LocoInfo(address=address, speed=speed, forward=forward, functions=functions)

    if x_header == XHEADER_BC and len(data) >= 2:
        # DB0: 0x00 = Track Power OFF, 0x01 = Track Power ON
        return TrackPower(on=data[1] == 0x01)

    if x_header == XHEADER_STATUS and len(data) >= 3:
        # DB0 0x22, DB1 = Status-Byte
        status = data[2]
        return TrackPower(on=not (status & CS_TRACK_VOLTAGE_OFF))

    return None
