"""Rein lesendes Z21-Diagnoseskript.

Sendet Status-/Versions-/SystemState-Abfragen und lauscht einige Sekunden auf
eingehende Datensaetze. Schaltet NICHTS (keine Gleisspannung, keine Fahrbefehle).

Aufruf:
    .venv/bin/python scripts/z21_probe.py [host] [port]
"""

from __future__ import annotations

import asyncio
import sys

from modellbahn.z21 import messages, protocol

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.0.111"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 21105


def build_get_firmware() -> bytes:
    """LAN_X_GET_FIRMWARE_VERSION (X-Header 0xF1, DB0 0x0A)."""
    return protocol.build_xbus(0xF1, bytes([0x0A]))


class ProbeProtocol(asyncio.DatagramProtocol):
    def __init__(self) -> None:
        self.count = 0

    def datagram_received(self, data: bytes, addr: object) -> None:
        for header, payload in protocol.parse_datasets(data):
            self.count += 1
            hexs = payload.hex(" ")
            decoded = messages.parse_message(header, payload)
            print(f"  <= header=0x{header:02X} data=[{hexs}] -> {decoded}")


async def main() -> None:
    print(f"Verbinde (UDP) mit Z21 unter {HOST}:{PORT} ... (nur lesend)")
    loop = asyncio.get_running_loop()
    transport, proto = await loop.create_datagram_endpoint(
        ProbeProtocol, remote_addr=(HOST, PORT)
    )
    try:
        print("=> LAN_X_GET_STATUS")
        transport.sendto(protocol.build_get_status())
        print("=> LAN_X_GET_FIRMWARE_VERSION")
        transport.sendto(build_get_firmware())
        print("=> LAN_SYSTEMSTATE_GETDATA")
        transport.sendto(protocol.build_systemstate_getdata())
        print("=> LAN_SET_BROADCASTFLAGS (Status + Lok-Info)")
        flags = (
            protocol.BROADCAST_DRIVE_SWITCH
            | protocol.BROADCAST_SYSTEMSTATE
            | protocol.BROADCAST_LOCO_INFO_ALL
        )
        transport.sendto(protocol.build_set_broadcastflags(flags))

        # Rein lesend: aktuellen Zustand von Lok 3 abfragen (bewegt nichts).
        print("=> LAN_X_GET_LOCO_INFO (Adresse 3)")
        transport.sendto(protocol.build_get_loco_info(3))

        print("Lausche 4 s auf Antworten/Broadcasts ...")
        await asyncio.sleep(4.0)
        print(f"Empfangene Datensaetze: {proto.count}")
    finally:
        # Sauber abmelden
        transport.sendto(protocol.build_logoff())
        transport.close()


if __name__ == "__main__":
    asyncio.run(main())
