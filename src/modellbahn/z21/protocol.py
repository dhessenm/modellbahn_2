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


def build_systemstate_getdata() -> bytes:
    """LAN_SYSTEMSTATE_GETDATA (Header 0x85): fordert den Systemzustand an."""
    return build_dataset(0x85, b"")


def build_track_power_on() -> bytes:
    """LAN_X_SET_TRACK_POWER_ON (X-Header 0x21, DB0 0x81)."""
    return build_xbus(0x21, bytes([0x81]))


def build_track_power_off() -> bytes:
    """LAN_X_SET_TRACK_POWER_OFF (X-Header 0x21, DB0 0x80)."""
    return build_xbus(0x21, bytes([0x80]))


def build_logoff() -> bytes:
    """LAN_LOGOFF (Header 0x30) zum sauberen Abmelden des Clients."""
    return build_dataset(0x30, b"")


# Broadcast-Flags (LAN_SET_BROADCASTFLAGS):
#   0x00000001 = Fahren/Schalten-Broadcasts (u. a. LAN_X_LOCO_INFO, Track-Power)
#   0x00000100 = Aenderungen des Z21-Systemzustands (LAN_SYSTEMSTATE_DATACHANGED)
#   0x00010000 = LAN_X_LOCO_INFO auch ohne vorheriges Abo pro Lok (ab FW 1.20)
#   0x00080000 = asynchrone CAN-Belegtmeldungen (LAN_CAN_DETECTOR, Roco 10808)
BROADCAST_DRIVE_SWITCH = 0x00000001
BROADCAST_SYSTEMSTATE = 0x00000100
BROADCAST_LOCO_INFO_ALL = 0x00010000
BROADCAST_CAN_DETECTOR = 0x00080000


def build_set_broadcastflags(flags: int) -> bytes:
    """LAN_SET_BROADCASTFLAGS (Header 0x50), 4 Byte little endian."""
    return build_dataset(0x50, flags.to_bytes(4, "little"))


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


def build_get_loco_info(address: int) -> bytes:
    """LAN_X_GET_LOCO_INFO (X-Header 0xE3, DB0 0xF0, dann Adresse).

    Rein lesend: fordert den aktuellen Lok-Zustand an und abonniert zugleich
    kuenftige LAN_X_LOCO_INFO-Updates fuer diese Lok.
    """
    msb, lsb = encode_loco_address(address)
    return build_xbus(0xE3, bytes([0xF0, msb, lsb]))


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


# --- Weichen / Zubehör (DCC) -----------------------------------------------

def encode_turnout_address(address: int) -> tuple[int, int]:
    """Kodiert eine Weichen-/Funktionsdecoder-Adresse in (FAdr_MSB, FAdr_LSB).

    Die Z21 adressiert Weichen ab 0; in Apps/multiMaus werden sie ab 1 gezaehlt.
    Diese Funktion erwartet die LAN-Adresse (ab 0), wie sie im Protokoll steht.
    """
    if not 0 <= address <= 0x7FF:
        raise ValueError(f"Weichen-Adresse ausserhalb 0..2047: {address}")
    return (address >> 8) & 0xFF, address & 0xFF


def build_set_turnout(address: int, position: int, activate: bool = True) -> bytes:
    """LAN_X_SET_TURNOUT (X-Header 0x53).

    DB3 = 1 0 Q 0 A 0 0 P:
      P = Ausgang/Position (0 oder 1)
      A = Ausgang aktivieren (1) / deaktivieren (0)
      Q = 0 (sofort ausfuehren)
    Ein vollstaendiger Schaltvorgang besteht aus activate=True (Ausgang ein) und
    kurz danach activate=False (Ausgang aus). Die eigentliche Antriebsansteuerung
    uebernimmt der Weichendecoder (z. B. ESU SwitchPilot Servo).
    """
    if position not in (0, 1):
        raise ValueError(f"Position muss 0 oder 1 sein: {position}")
    msb, lsb = encode_turnout_address(address)
    db3 = 0x80 | (0x08 if activate else 0x00) | (position & 0x01)
    return build_xbus(0x53, bytes([msb, lsb, db3]))


def build_get_turnout_info(address: int) -> bytes:
    """LAN_X_GET_TURNOUT_INFO (X-Header 0x43, dann Adresse). Rein lesend."""
    msb, lsb = encode_turnout_address(address)
    return build_xbus(0x43, bytes([msb, lsb]))


# --- CAN-Belegtmelder (Roco Z21 Detector 10808) ----------------------------

def build_get_can_detectors(network_id: int = 0xD000) -> bytes:
    """LAN_CAN_DETECTOR Request (Header 0xC4): fragt den Belegtstatus ab.

    Data = Typ(8)=0x00 | CAN-NetworkID(16, little endian). Die NetworkID
    0xD000 adressiert *alle* CAN-Belegtmelder. Dies ist KEIN X-Bus-Befehl
    (kein Header 0x40, kein XOR-Pruefbyte), sondern ein eigener Z21-LAN-Header
    analog zu LAN_SYSTEMSTATE_GETDATA.

    Voller Datensatz (NetworkID 0xD000): 07 00 C4 00 00 00 D0.
    """
    return build_dataset(0xC4, bytes([0x00]) + network_id.to_bytes(2, "little"))


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

