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
