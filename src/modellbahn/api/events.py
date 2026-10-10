"""Einfacher Event-Broker fuer Server-Sent Events (Push-Kanal).

Der Controller meldet Zustandsaenderungen; der Broker verteilt ein Signal an
alle verbundenen SSE-Clients. Der eigentliche Zustand bleibt die Single Source
of Truth in der domain-Schicht; ueber SSE wird nur signalisiert, dass sich
etwas geaendert hat (der Client holt den aktuellen Zustand per GET).
"""

from __future__ import annotations

import asyncio


class EventBroker:
    """Verteilt 'changed'-Signale an alle Abonnenten."""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[str]] = set()

    def subscribe(self) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue()
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[str]) -> None:
        self._subscribers.discard(queue)

    def publish(self, event: str = "changed") -> None:
        """Nicht-blockierend an alle Abonnenten verteilen."""
        for queue in self._subscribers:
            queue.put_nowait(event)
