"""Dekodierung eingehender Z21-Meldungen in strukturierte Objekte.

Diese Schicht bleibt rein (keine Fachlogik): sie uebersetzt empfangene
Datensaetze in neutrale Datenobjekte, die die domain-Schicht auswertet.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from modellbahn.z21.protocol import HEADER_LAN_X

# Z21-LAN-Header
HEADER_SYSTEMSTATE = 0x84  # LAN_SYSTEMSTATE_DATACHANGED
HEADER_CAN_DETECTOR = 0xC4  # LAN_CAN_DETECTOR (Roco Z21 Detector 10808)

# X-Header empfangener X-Bus-Meldungen
XHEADER_LOCO_INFO = 0xEF
XHEADER_TURNOUT_INFO = 0x43  # LAN_X_TURNOUT_INFO
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


@dataclass
class TurnoutInfo:
    """Dekodierte LAN_X_TURNOUT_INFO-Meldung.

    position: 0 oder 1, oder None wenn die Weiche noch nicht geschaltet wurde
    (ZZ=00 = Zustand unbekannt).
    """

    address: int
    position: int | None


@dataclass
class DetectorLoco:
    """Eine am Belegtmelder-Eingang per RailCom erkannte Lok.

    direction: "forward", "backward" oder "unknown" (aus den oberen 2 Bits).
    """

    address: int
    direction: str


@dataclass
class DetectorOccupancy:
    """Belegtstatus eines CAN-Belegtmelder-Eingangs (LAN_CAN_DETECTOR, Typ 0x01).

    Schluessel ist (nid, port): nid = unveraenderbare CAN-NetworkID des Moduls,
    port = Eingang 0..7. addr = konfigurierbare Moduladresse (nur Anzeigeinfo).
    """

    nid: int
    addr: int
    port: int
    occupied: bool
    with_power: bool
    overload: bool
    overload_level: int = 0


@dataclass
class DetectorLocos:
    """RailCom-Lokadressen eines Belegtmelder-Eingangs (Typ 0x11..0x1F).

    first_block = True markiert den ersten Block (Typ 0x11), der eine neue
    Liste beginnt; 0x12..0x1F haengen weitere Paare an.
    """

    nid: int
    addr: int
    port: int
    locos: list[DetectorLoco]
    first_block: bool


def _decode_address(adr_msb: int, adr_lsb: int) -> int:
    return ((adr_msb & 0x3F) << 8) + adr_lsb


def _decode_turnout_address(fadr_msb: int, fadr_lsb: int) -> int:
    return (fadr_msb << 8) + fadr_lsb


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


def _decode_detector_loco(word: int) -> DetectorLoco:
    """Dekodiert einen 16-bit RailCom-Wert in (Adresse, Richtung).

    Bits 15..14 = Richtung (00 unbekannt, 10 vorwaerts, 11 rueckwaerts),
    Bits 13..0 = Lokadresse.
    """
    address = word & 0x3FFF
    direction = {0b00: "unknown", 0b10: "forward", 0b11: "backward"}.get(
        word >> 14, "unknown"
    )
    return DetectorLoco(address=address, direction=direction)


def _parse_can_detector(
    data: bytes,
) -> DetectorOccupancy | DetectorLocos | None:
    """Dekodiert einen LAN_CAN_DETECTOR-Datensatz (Header 0xC4).

    Layout (little endian): NId(16) Addr(16) Port(8) Typ(8) Value1(16) Value2(16).
    """
    if len(data) < 8:
        return None
    nid = int.from_bytes(data[0:2], "little")
    addr = int.from_bytes(data[2:4], "little")
    port = data[4]
    typ = data[5]
    value1 = int.from_bytes(data[6:8], "little")
    value2 = int.from_bytes(data[8:10], "little") if len(data) >= 10 else 0

    if typ == 0x01:
        occupied = value1 >= 0x1000
        overload = (value1 >> 8) == 0x12
        overload_level = (value1 & 0xFF) if overload else 0
        # Bei Ueberlast liegt immer Spannung an; sonst steuert Bit 0x0100.
        with_power = overload or bool(value1 & 0x0100)
        return DetectorOccupancy(
            nid=nid,
            addr=addr,
            port=port,
            occupied=occupied,
            with_power=with_power,
            overload=overload,
            overload_level=overload_level,
        )

    if 0x11 <= typ <= 0x1F:
        locos: list[DetectorLoco] = []
        for word in (value1, value2):
            if word == 0x0000:  # Adresse 0 = Listenende
                break
            locos.append(_decode_detector_loco(word))
        return DetectorLocos(
            nid=nid,
            addr=addr,
            port=port,
            locos=locos,
            first_block=(typ == 0x11),
        )

    return None


def parse_message(
    header: int, data: bytes
) -> LocoInfo | TurnoutInfo | TrackPower | SystemState | DetectorOccupancy | DetectorLocos | None:
    """Wertet einen empfangenen Datensatz aus; None bei irrelevanten Meldungen."""
    if header == HEADER_CAN_DETECTOR:
        return _parse_can_detector(data)

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

    if x_header == XHEADER_TURNOUT_INFO and len(data) >= 4:
        # DB1/DB2 = Adresse, DB3 = 000000ZZ: 00=unbekannt, 01=P0, 10=P1
        address = _decode_turnout_address(data[1], data[2])
        zz = data[3] & 0x03
        position = {0b01: 0, 0b10: 1}.get(zz)  # None bei 00 (unbekannt) / 11 (ungueltig)
        return TurnoutInfo(address=address, position=position)

    if x_header == XHEADER_BC and len(data) >= 2:
        # DB0: 0x00 = Track Power OFF, 0x01 = Track Power ON
        return TrackPower(on=data[1] == 0x01)

    if x_header == XHEADER_STATUS and len(data) >= 3:
        # DB0 0x22, DB1 = Status-Byte
        status = data[2]
        return TrackPower(on=not (status & CS_TRACK_VOLTAGE_OFF))

    return None
