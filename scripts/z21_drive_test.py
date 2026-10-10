"""Kontrollierter Fahrtest fuer Lok 3 an der realen Z21.

Faehrt behutsam an (max. Fahrstufe 60 von 128), liest nach jedem Schritt den
Lok-Zustand zurueck und stoppt am Ende GARANTIERT auf Fahrstufe 0 (auch im
Fehlerfall). Bewegt echtes Rollmaterial.

Aufruf:
    PYTHONPATH=src .venv/bin/python scripts/z21_drive_test.py [host] [port]
"""

from __future__ import annotations

import asyncio
import sys

from modellbahn.z21 import messages, protocol

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.0.111"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 21105
ADDRESS = 3
MAX_STEP = 60


class DriveProtocol(asyncio.DatagramProtocol):
    def __init__(self) -> None:
        self.last_loco: messages.LocoInfo | None = None

    def datagram_received(self, data: bytes, addr: object) -> None:
        for header, payload in protocol.parse_datasets(data):
            msg = messages.parse_message(header, payload)
            if isinstance(msg, messages.LocoInfo) and msg.address == ADDRESS:
                self.last_loco = msg


async def main() -> None:
    loop = asyncio.get_running_loop()
    transport, proto = await loop.create_datagram_endpoint(
        DriveProtocol, remote_addr=(HOST, PORT)
    )

    def drive(step: int, forward: bool = True) -> None:
        assert 0 <= step <= MAX_STEP, f"Fahrstufe {step} ueber Limit {MAX_STEP}!"
        transport.sendto(protocol.build_loco_drive(ADDRESS, step, forward))

    async def report(label: str) -> None:
        transport.sendto(protocol.build_get_loco_info(ADDRESS))
        await asyncio.sleep(0.5)
        print(f"  [{label}] -> {proto.last_loco}")

    try:
        # Broadcast-Flags aktivieren, damit Lok-Info-Updates kommen.
        transport.sendto(protocol.build_set_broadcastflags(0x00010101))
        transport.sendto(protocol.build_get_status())
        await asyncio.sleep(0.3)
        await report("Start")

        print("Anfahren auf Fahrstufe 20 (vorwaerts) ...")
        drive(20)
        await asyncio.sleep(2.0)
        await report("Stufe 20")

        print("Beschleunigen auf Fahrstufe 60 ...")
        drive(60)
        await asyncio.sleep(3.0)
        await report("Stufe 60")

        print("Reduzieren auf Fahrstufe 25 ...")
        drive(25)
        await asyncio.sleep(2.0)
        await report("Stufe 25")

        print("Anhalten (Fahrstufe 0) ...")
        drive(0)
        await asyncio.sleep(1.0)
        await report("Stop")
    finally:
        # Sicherheit: unbedingt stoppen und abmelden.
        try:
            transport.sendto(protocol.build_loco_drive(ADDRESS, 0, True))
        finally:
            transport.sendto(protocol.build_logoff())
            transport.close()
        print("Fahrtest beendet, Lok gestoppt.")


if __name__ == "__main__":
    asyncio.run(main())
