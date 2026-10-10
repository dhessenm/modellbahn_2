"""Asynchroner UDP-Client fuer die Z21-Zentrale.

Verantwortlich fuer Transport und Keep-Alive, nicht fuer Fachlogik. Eingehende
Datensaetze werden roh an einen Callback uebergeben; die Dekodierung uebernimmt
die aufrufende Schicht (domain) ueber z21.messages.

Das Protokoll `Z21Transport` erlaubt es der domain-Schicht, gegen einen Fake
zu testen (ohne reale Zentrale).
"""

from __future__ import annotations

import asyncio
import logging
import socket
from collections.abc import Callable
from typing import Protocol

from modellbahn.z21 import protocol

RawCallback = Callable[[int, bytes], None]

logger = logging.getLogger("modellbahn.z21")


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
        logger.debug("RECV %d B von %s: %s", len(data), addr, data.hex(" "))
        self._on_any_received()
        for header, payload in protocol.parse_datasets(data):
            self._on_raw(header, payload)

    def error_received(self, exc: Exception) -> None:
        logger.warning("UDP error_received: %r", exc)

    def connection_lost(self, exc: Exception | None) -> None:
        logger.warning("UDP connection_lost: %r", exc)


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
        keepalive_interval_s: float = 5.0,
        broadcast_flags: int | None = None,
        local_port: int = 0,
        local_host: str = "",
    ) -> None:
        self._host = host
        self._port = port
        self._on_raw = on_raw
        self._keepalive_interval_s = keepalive_interval_s
        self._local_port = local_port
        self._local_host = local_host
        self._broadcast_flags = (
            self.DEFAULT_BROADCAST_FLAGS if broadcast_flags is None else broadcast_flags
        )
        self._transport: asyncio.DatagramTransport | None = None
        self._keepalive_task: asyncio.Task[None] | None = None
        self._handshake_task: asyncio.Task[None] | None = None
        self._received_any = False

    def _mark_received(self) -> None:
        self._received_any = True

    def _resolve_local_host(self) -> str:
        """Ermittelt die lokale Adresse, ueber die die Z21 erreichbar ist.

        Wichtig bei aktivem VPN/mehreren Interfaces: An diese Adresse zu binden
        (statt 0.0.0.0) stellt sicher, dass das OS beim Senden das richtige
        Interface (das zur Z21) waehlt. Der 'connect'-Trick auf ein temporaeres
        UDP-Socket sendet nichts, waehlt aber die Quelladresse gemaess Routing.
        """
        if self._local_host:
            return self._local_host
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect((self._host, self._port))
            addr: str = probe.getsockname()[0]
            return addr
        except OSError:
            return "0.0.0.0"
        finally:
            probe.close()

    async def start(self) -> None:
        loop = asyncio.get_running_loop()
        # UNVERBUNDENES Socket (kein remote_addr), aber explizit an das lokale
        # Interface gebunden, das die Z21 erreicht. Beides zusammen vermeidet
        # BrokenPipe (verbundenes Socket) UND "No route to host" (falsches
        # Interface bei aktivem VPN).
        bind_host = self._resolve_local_host()
        local_addr = (bind_host, self._local_port)
        transport, _ = await loop.create_datagram_endpoint(
            lambda: _Z21DatagramProtocol(self._on_raw, self._mark_received),
            local_addr=local_addr,
        )
        self._transport = transport
        self._received_any = False
        sockname = transport.get_extra_info("sockname")
        logger.info(
            "Z21-UDP-Socket geoeffnet: lokal=%s ziel=%s:%s (local_port=%s, unverbunden)",
            sockname,
            self._host,
            self._port,
            self._local_port,
        )
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
        logger.debug("SEND %d B: %s", len(dataset), dataset.hex(" "))
        # Explizites Ziel (unverbundenes Socket). OSError defensiv abfangen,
        # damit ein einmaliger Sendefehler nicht den Keep-Alive-Task beendet.
        try:
            self._transport.sendto(dataset, (self._host, self._port))
        except OSError as exc:
            logger.warning("SEND fehlgeschlagen: %r", exc)

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
