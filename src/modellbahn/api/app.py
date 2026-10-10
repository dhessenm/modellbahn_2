"""FastAPI-App-Factory, Lifespan-Verdrahtung, REST-Endpunkte und SSE-Push.

Verdrahtung (Single Source of Truth im Backend):

    Z21UdpClient --(on_raw)--> LocoController --(on_change)--> EventBroker --> SSE
                                     |
                               LayoutState (massgeblicher Zustand)

REST liefert immer den aktuellen LayoutState; SSE signalisiert nur Aenderungen.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import StreamingResponse

from modellbahn.api.events import EventBroker
from modellbahn.api.schemas import (
    DriveRequest,
    FunctionRequest,
    LocoStateResponse,
    SystemStatusResponse,
    TrackPowerRequest,
)
from modellbahn.config import Settings, get_settings
from modellbahn.domain.controller import LocoController
from modellbahn.domain.state import LayoutState
from modellbahn.logging_setup import configure_logging
from modellbahn.z21.client import Z21Transport, Z21UdpClient


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startet/stoppt den UDP-Client, falls einer gesetzt ist."""
    client: Z21UdpClient | None = getattr(app.state, "z21_client", None)
    if client is not None:
        await client.start()
    try:
        yield
    finally:
        if client is not None:
            await client.stop()


def create_app(
    settings: Settings | None = None,
    transport: Z21Transport | None = None,
) -> FastAPI:
    """Erzeugt die FastAPI-App.

    transport: optional einspeisbar (z. B. ein Fake fuer Tests). Ohne Transport
    wird ein echter Z21UdpClient erzeugt und ueber den Lifespan verwaltet.
    """
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title="Modellbahn-Steuerung", version="0.1.0", lifespan=_lifespan)
    app.state.settings = settings

    broker = EventBroker()
    state = LayoutState()

    if transport is None:
        controller = LocoController(state=state, on_change=broker.publish)
        client = Z21UdpClient(
            host=settings.z21_host,
            port=settings.z21_port,
            on_raw=controller.on_raw,
            keepalive_interval_s=settings.keepalive_interval_s,
            local_port=settings.local_port,
            local_host=settings.local_host,
        )
        controller.set_transport(client)
        app.state.z21_client = client
    else:
        controller = LocoController(transport=transport, state=state, on_change=broker.publish)
        app.state.z21_client = None

    app.state.controller = controller
    app.state.broker = broker

    _register_routes(app, controller, broker, settings)
    return app


def _register_routes(
    app: FastAPI,
    controller: LocoController,
    broker: EventBroker,
    settings: Settings,
) -> None:
    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/system/status", response_model=SystemStatusResponse)
    def system_status() -> SystemStatusResponse:
        return SystemStatusResponse(
            connected=controller.state.connected,
            track_power_on=controller.state.track_power_on,
            z21_host=settings.z21_host,
            z21_port=settings.z21_port,
        )

    @app.post("/api/system/track-power", status_code=204)
    def set_track_power(req: TrackPowerRequest) -> Response:
        controller.set_track_power(req.on)
        return Response(status_code=204)

    @app.get("/api/locos/{address}", response_model=LocoStateResponse)
    def get_loco(address: int) -> LocoStateResponse:
        if address not in controller.state.locos:
            raise HTTPException(status_code=404, detail="Lok nicht bekannt")
        loco = controller.state.locos[address]
        return LocoStateResponse(
            address=loco.address,
            speed=loco.speed,
            forward=loco.forward,
            functions=loco.functions,
        )

    @app.post("/api/locos/{address}/subscribe", status_code=204)
    def subscribe_loco(address: int) -> Response:
        """Fordert den aktuellen Lok-Zustand bei der Zentrale an (rein lesend).

        Die Antwort trifft asynchron als LAN_X_LOCO_INFO ein und aktualisiert
        den Zustand; der Client erfaehrt dies ueber den SSE-Push.
        """
        controller.request_loco_info(address)
        return Response(status_code=204)

    @app.put("/api/locos/{address}/drive", status_code=204)
    def drive(address: int, req: DriveRequest) -> Response:
        controller.drive(address, req.speed, req.forward)
        return Response(status_code=204)

    @app.put("/api/locos/{address}/function", status_code=204)
    def set_function(address: int, req: FunctionRequest) -> Response:
        controller.set_function(address, req.function, req.on)
        return Response(status_code=204)

    @app.get("/api/events")
    async def events() -> StreamingResponse:
        """SSE-Stream: signalisiert Zustandsaenderungen ('changed')."""
        queue = broker.subscribe()

        async def event_stream() -> AsyncIterator[str]:
            try:
                while True:
                    event = await queue.get()
                    yield f"data: {json.dumps({'event': event})}\n\n"
            except asyncio.CancelledError:
                raise
            finally:
                broker.unsubscribe(queue)

        return StreamingResponse(event_stream(), media_type="text/event-stream")
