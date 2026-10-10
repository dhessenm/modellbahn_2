"""Z21-LAN-Protokoll: Kodierung von Datensaetzen.

Aufbau eines Z21-Datensatzes (siehe .kiro/steering/z21-protokoll.md):

    DataLen (2 B, little endian) | Header (2 B, little endian) | Data (n B)

- DataLen ist die Gesamtlaenge inkl. DataLen, Header und Data.
- X-Bus-Befehle laufen unter Header 0x40 und enden mit einem XOR-Pruefbyte
  ueber die X-Bus-Nutzdaten (X-Header + Datenbytes).

Diese Funktionen bilden das Fundament; konkrete Befehle (Fahren, Weichen,
Track-Power, Status) werden darauf aufgebaut.
"""

from __future__ import annotations

import struct

# Z21-LAN-Header
HEADER_LAN_X = 0x40


def xbus_checksum(payload: bytes) -> int:
    """XOR-Pruefsumme ueber die X-Bus-Nutzdaten (X-Header + Datenbytes)."""
    checksum = 0
    for byte in payload:
        checksum ^= byte
    return checksum


def build_dataset(header: int, data: bytes) -> bytes:
    """Rahmt einen Z21-Datensatz: DataLen (LE) + Header (LE) + Data."""
    data_len = 4 + len(data)
    return struct.pack("<HH", data_len, header) + data


def build_xbus(x_header: int, data: bytes = b"") -> bytes:
    """Baut einen vollstaendigen X-Bus-Datensatz (Header 0x40) inkl. XOR-Byte."""
    payload = bytes([x_header]) + data
    checksum = xbus_checksum(payload)
    return build_dataset(HEADER_LAN_X, payload + bytes([checksum]))


# --- Adress-Kodierung ------------------------------------------------------

def encode_loco_address(address: int) -> tuple[int, int]:
    """Kodiert eine Lok-Adresse in (Adr_MSB, Adr_LSB).

    Bei Adressen >= 128 muessen die beiden hoechsten Bits im MSB gesetzt sein
    (DB1 = 0xC0 | Adr_MSB), siehe Z21-Spezifikation.
    """
    if not 0 <= address <= 9999:
        raise ValueError(f"Lok-Adresse ausserhalb des gueltigen Bereichs: {address}")
    msb = (address >> 8) & 0x3F
    lsb = address & 0xFF
    if address >= 128:
        msb |= 0xC0
    return msb, lsb


# --- System / Track Power --------------------------------------------------

def build_get_status() -> bytes:
    """LAN_X_GET_STATUS (X-Header 0x21, DB0 0x24). Dient auch als Keep-Alive."""
    return build_xbus(0x21, bytes([0x24]))


def build_track_power_on() -> bytes:
    """LAN_X_SET_TRACK_POWER_ON (X-Header 0x21, DB0 0x81)."""
    return build_xbus(0x21, bytes([0x81]))


def build_track_power_off() -> bytes:
    """LAN_X_SET_TRACK_POWER_OFF (X-Header 0x21, DB0 0x80)."""
    return build_xbus(0x21, bytes([0x80]))


def build_logoff() -> bytes:
    """LAN_LOGOFF (Header 0x30) zum sauberen Abmelden des Clients."""
    return build_dataset(0x30, b"")


# --- Fahren (DCC 128 Fahrstufen) -------------------------------------------

def build_loco_drive(address: int, speed: int, forward: bool) -> bytes:
    """LAN_X_SET_LOCO_DRIVE fuer DCC mit 128 Fahrstufen.

    speed: 0..126 (0 = Stop). DB0 = 0x13 (S=3 => 128 Fahrstufen).
    DB3 = RVVVVVVV: R = Richtung (1=vorwaerts), VVVVVVV = Fahrstufenwert.
    Bei 128 Fahrstufen gilt: 0=Stop, 1=Nothalt, Fahrstufe n -> Wert n+1.
    """
    if not 0 <= speed <= 126:
        raise ValueError(f"Fahrstufe ausserhalb 0..126: {speed}")
    msb, lsb = encode_loco_address(address)
    speed_value = 0 if speed == 0 else speed + 1  # 1 ist fuer Nothalt reserviert
    db3 = (0x80 if forward else 0x00) | (speed_value & 0x7F)
    return build_xbus(0xE4, bytes([0x13, msb, lsb, db3]))


def build_loco_function(address: int, function: int, on: bool) -> bytes:
    """LAN_X_SET_LOCO_FUNCTION: Einzelfunktion schalten.

    DB0 = 0xF8, DB3 = TTNNNNNN mit TT = 00 (aus) / 01 (ein), NNNNNN = Index.
    """
    if not 0 <= function <= 31:
        raise ValueError(f"Funktionsindex ausserhalb 0..31: {function}")
    msb, lsb = encode_loco_address(address)
    tt = 0b01 if on else 0b00
    db3 = (tt << 6) | (function & 0x3F)
    return build_xbus(0xE4, bytes([0xF8, msb, lsb, db3]))


# --- Dekodierung von Empfangsdaten -----------------------------------------

def parse_datasets(buffer: bytes) -> list[tuple[int, bytes]]:
    """Zerlegt ein (ggf. kombiniertes) UDP-Nutzlast-Buffer in Datensaetze.

    Liefert eine Liste von (header, data) ohne das DataLen/Header-Praefix.
    Unvollstaendige/kaputte Reste am Ende werden ignoriert.
    """
    out: list[tuple[int, bytes]] = []
    offset = 0
    while offset + 4 <= len(buffer):
        data_len, header = struct.unpack_from("<HH", buffer, offset)
        if data_len < 4 or offset + data_len > len(buffer):
            break
        data = buffer[offset + 4 : offset + data_len]
        out.append((header, data))
        offset += data_len
    return out

