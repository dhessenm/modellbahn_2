"""Asynchroner UDP-Client fuer die Z21-Zentrale.

Verantwortlich fuer Transport und Keep-Alive, nicht fuer Fachlogik. Eingehende
Datensaetze werden roh an einen Callback uebergeben; die Dekodierung uebernimmt
die aufrufende Schicht (domain) ueber z21.messages.

Das Protokoll `Z21Transport` erlaubt es der domain-Schicht, gegen einen Fake
zu testen (ohne reale Zentrale).
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Protocol

from modellbahn.z21 import protocol

RawCallback = Callable[[int, bytes], None]


class Z21Transport(Protocol):
    """Minimaler Transport-Vertrag, den die domain-Schicht nutzt."""

    async def start(self) -> None: ...

    async def stop(self) -> None: ...

    def send(self, dataset: bytes) -> None: ...


class _Z21DatagramProtocol(asyncio.DatagramProtocol):
    def __init__(self, on_raw: RawCallback, on_any_received: Callable[[], None]) -> None:
        self._on_raw = on_raw
        self._on_any_received = on_any_received

    def datagram_received(self, data: bytes, addr: object) -> None:
        self._on_any_received()
        for header, payload in protocol.parse_datasets(data):
            self._on_raw(header, payload)


class Z21UdpClient:
    """UDP-Anbindung an die Z21 inkl. Keep-Alive.

    on_raw(header, data) wird fuer jeden empfangenen Datensatz aufgerufen.
    """

    #: Standard-Broadcast-Flags: Fahren/Schalten + Systemzustand + Lok-Info ohne Abo.
    DEFAULT_BROADCAST_FLAGS = (
        protocol.BROADCAST_DRIVE_SWITCH
        | protocol.BROADCAST_SYSTEMSTATE
        | protocol.BROADCAST_LOCO_INFO_ALL
    )

    def __init__(
        self,
        host: str,
        port: int,
        on_raw: RawCallback,
        keepalive_interval_s: float = 20.0,
        broadcast_flags: int | None = None,
    ) -> None:
        self._host = host
        self._port = port
        self._on_raw = on_raw
        self._keepalive_interval_s = keepalive_interval_s
        self._broadcast_flags = (
            self.DEFAULT_BROADCAST_FLAGS if broadcast_flags is None else broadcast_flags
        )
        self._transport: asyncio.DatagramTransport | None = None
        self._keepalive_task: asyncio.Task[None] | None = None
        self._handshake_task: asyncio.Task[None] | None = None
        self._received_any = False

    def _mark_received(self) -> None:
        self._received_any = True

    async def start(self) -> None:
        loop = asyncio.get_running_loop()
        transport, _ = await loop.create_datagram_endpoint(
            lambda: _Z21DatagramProtocol(self._on_raw, self._mark_received),
            remote_addr=(self._host, self._port),
        )
        self._transport = transport
        self._received_any = False
        self._send_init()
        # Start-Handshake: bei UDP-Paketverlust die Init-Pakete kurzzeitig
        # wiederholen, bis die Zentrale antwortet (statt bis zum ersten
        # Keep-Alive nach ~20 s stumm zu bleiben).
        self._handshake_task = asyncio.create_task(self._handshake_loop())
        self._keepalive_task = asyncio.create_task(self._keepalive_loop())

    def _send_init(self) -> None:
        """Broadcast-Flags setzen und initiale Abfragen senden."""
        self.send(protocol.build_set_broadcastflags(self._broadcast_flags))
        self.send(protocol.build_get_status())
        self.send(protocol.build_systemstate_getdata())

    async def _handshake_loop(self) -> None:
        """Wiederholt die Init-Pakete, bis eine Antwort kommt (max. ~5 s)."""
        for _ in range(10):
            await asyncio.sleep(0.5)
            if self._received_any:
                return
            try:
                self._send_init()
            except RuntimeError:
                return

    async def stop(self) -> None:
        for task_attr in ("_handshake_task", "_keepalive_task"):
            task: asyncio.Task[None] | None = getattr(self, task_attr)
            if task is not None:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                setattr(self, task_attr, None)
        if self._transport is not None:
            # Sauberes Abmelden an der Zentrale.
            self.send(protocol.build_logoff())
            self._transport.close()
            self._transport = None

    def send(self, dataset: bytes) -> None:
        if self._transport is None:
            raise RuntimeError("Z21UdpClient ist nicht gestartet")
        self._transport.sendto(dataset)

    async def _keepalive_loop(self) -> None:
        """Haelt die Registrierung aktiv und macht die Verbindung selbstheilend.

        Sendet periodisch (Intervall < 60 s Z21-Timeout) nicht nur eine
        Statusabfrage, sondern erneuert auch die Broadcast-Flags und fragt den
        SystemState ab. Falls das initiale Flags-Paket verloren ging oder die
        Zentrale den Client zwischenzeitlich verworfen hat (z. B. nach einem
        nicht sauberen Beenden), erholt sich die Verbindung so beim naechsten
        Zyklus automatisch, statt dauerhaft stumm zu bleiben.
        """
        while True:
            await asyncio.sleep(self._keepalive_interval_s)
            try:
                self.send(protocol.build_set_broadcastflags(self._broadcast_flags))
                self.send(protocol.build_get_status())
                self.send(protocol.build_systemstate_getdata())
            except RuntimeError:
                return
