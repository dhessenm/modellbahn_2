"""Tests des Z21UdpClient (ohne reale Zentrale, mit gemocktem Datagram-Endpoint)."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from modellbahn.z21 import protocol
from modellbahn.z21.client import Z21UdpClient


class FakeDatagramTransport(asyncio.DatagramTransport):
    """Minimaler Fake, der gesendete Datagramme sammelt."""

    def __init__(self) -> None:
        self.sent: list[bytes] = []
        self.closed = False

    def sendto(self, data: bytes, addr: object = None) -> None:
        self.sent.append(bytes(data))

    def get_extra_info(self, name: str, default: object = None) -> object:
        return {"sockname": ("0.0.0.0", 21105), "peername": ("192.0.2.1", 21105)}.get(name, default)

    def close(self) -> None:
        self.closed = True


async def test_start_sends_broadcastflags_status_and_systemstate(
    monkeypatch: Any,
) -> None:
    fake = FakeDatagramTransport()

    async def fake_create_endpoint(
        protocol_factory: Callable[[], asyncio.DatagramProtocol],
        local_addr: tuple[str, int] | None = None,
        remote_addr: tuple[str, int] | None = None,
    ) -> tuple[asyncio.DatagramTransport, asyncio.DatagramProtocol]:
        proto = protocol_factory()
        return fake, proto

    loop = asyncio.get_running_loop()
    monkeypatch.setattr(loop, "create_datagram_endpoint", fake_create_endpoint)

    client = Z21UdpClient("192.0.2.1", 21105, on_raw=lambda h, d: None)
    await client.start()

    # Erwartet: Broadcast-Flags, dann Status, dann SystemState-Getdata.
    assert fake.sent[0] == protocol.build_set_broadcastflags(client.DEFAULT_BROADCAST_FLAGS)
    assert fake.sent[1] == protocol.build_get_status()
    assert fake.sent[2] == protocol.build_systemstate_getdata()

    await client.stop()
    # Beim Stop wird LAN_LOGOFF gesendet und der Transport geschlossen.
    assert fake.sent[-1] == protocol.build_logoff()
    assert fake.closed is True


async def test_handshake_retries_until_response(monkeypatch: Any) -> None:
    """Ohne Antwort werden die Init-Pakete wiederholt gesendet (Start-Handshake)."""
    fake = FakeDatagramTransport()
    captured: dict[str, asyncio.DatagramProtocol] = {}

    async def fake_create_endpoint(
        protocol_factory: Callable[[], asyncio.DatagramProtocol],
        local_addr: tuple[str, int] | None = None,
        remote_addr: tuple[str, int] | None = None,
    ) -> tuple[asyncio.DatagramTransport, asyncio.DatagramProtocol]:
        proto = protocol_factory()
        captured["proto"] = proto
        return fake, proto

    loop = asyncio.get_running_loop()
    monkeypatch.setattr(loop, "create_datagram_endpoint", fake_create_endpoint)

    client = Z21UdpClient("192.0.2.1", 21105, on_raw=lambda h, d: None, keepalive_interval_s=100.0)
    await client.start()

    # Nach dem Start zunaechst 3 Init-Pakete. Ohne Antwort folgen Wiederholungen.
    initial = len(fake.sent)
    await asyncio.sleep(1.3)  # ~2 Handshake-Wiederholungen (alle 0.5 s)
    assert len(fake.sent) > initial, "Handshake sollte Init-Pakete wiederholen"

    # Sobald etwas empfangen wird, stoppt der Handshake die Wiederholungen.
    # Gemessen an den SET_BROADCASTFLAGS-Paketen (Teil des Init-Handshakes);
    # die davon unabhaengige Belegtmelder-Initialabfrage (_initial_detectors_loop,
    # eigener Task) sendet bewusst auch nach dem ersten Empfang weiter und wird
    # hier daher nicht mitgezaehlt.
    flags_packet = protocol.build_set_broadcastflags(client.DEFAULT_BROADCAST_FLAGS)
    captured["proto"].datagram_received(protocol.build_get_status(), ("192.0.2.1", 21105))
    await asyncio.sleep(0.1)
    stable_handshakes = fake.sent.count(flags_packet)
    await asyncio.sleep(1.2)
    assert (
        fake.sent.count(flags_packet) == stable_handshakes
    ), "Nach Empfang keine weiteren Handshake-Wiederholungen"

    await client.stop()


async def test_initial_detectors_query_repeated_after_start(monkeypatch: Any) -> None:
    """Die CAN-Belegtabfrage wird nach dem Start mehrfach wiederholt.

    Die Z21 beantwortet die Belegtabfrage direkt nach dem Verbindungsaufbau oft
    noch nicht; daher muss der Client sie einige Male erneut senden, damit der
    Belegtstatus zuverlaessig einmal erfasst wird (auch wenn bereits andere
    Antworten eingegangen sind, der Handshake also laengst gestoppt hat).
    """
    fake = FakeDatagramTransport()

    async def fake_create_endpoint(
        protocol_factory: Callable[[], asyncio.DatagramProtocol],
        local_addr: tuple[str, int] | None = None,
        remote_addr: tuple[str, int] | None = None,
    ) -> tuple[asyncio.DatagramTransport, asyncio.DatagramProtocol]:
        proto = protocol_factory()
        return fake, proto

    loop = asyncio.get_running_loop()
    monkeypatch.setattr(loop, "create_datagram_endpoint", fake_create_endpoint)

    client = Z21UdpClient("192.0.2.1", 21105, on_raw=lambda h, d: None, keepalive_interval_s=100.0)
    await client.start()

    can_query = protocol.build_get_can_detectors()
    initial_queries = fake.sent.count(can_query)  # 1x aus _send_init

    # Nach dem Start folgen weitere Belegtabfragen aus dem Initial-Task,
    # unabhaengig davon, dass bereits Pakete gesendet/empfangen wurden.
    await asyncio.sleep(1.8)
    assert (
        fake.sent.count(can_query) > initial_queries
    ), "Belegtabfrage sollte nach dem Start wiederholt werden"

    await client.stop()
