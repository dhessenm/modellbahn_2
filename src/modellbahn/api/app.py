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
    DetectorInputResponse,
    DetectorLocoResponse,
    DetectorsResponse,
    DriveRequest,
    FunctionRequest,
    LocoStateResponse,
    SystemStatusResponse,
    TrackPowerRequest,
    TurnoutRequest,
    TurnoutStateResponse,
)
from modellbahn.config import Settings, get_settings
from modellbahn.domain.controller import LocoController
from modellbahn.domain.state import DetectorInput, LayoutState
from modellbahn.logging_setup import configure_logging
from modellbahn.z21.client import Z21Transport, Z21UdpClient


def _detector_status_text(d: DetectorInput) -> str:
    """Leitet den menschenlesbaren deutschen Belegtstatus aus den Flags ab.

    Zentral in der api-Schicht, damit REST (und darueber die UI) genau einen
    Text verwenden; das domain-Modell bleibt reiner Zustand.
    """
    if d.overload:
        return f"besetzt (Ueberlast {d.overload_level})"
    besetzt = "besetzt" if d.occupied else "frei"
    spannung = "mit Spannung" if d.with_power else "ohne Spannung"
    return f"{besetzt} ({spannung})"


def _detector_to_response(d: DetectorInput) -> DetectorInputResponse:
    return DetectorInputResponse(
        nid=d.nid,
        addr=d.addr,
        port=d.port,
        occupied=d.occupied,
        with_power=d.with_power,
        overload=d.overload,
        overload_level=d.overload_level,
        status_text=_detector_status_text(d),
        locos=[
            DetectorLocoResponse(address=address, direction=direction)
            for address, direction in d.locos
        ],
    )


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
        sys_info = controller.state.system
        return SystemStatusResponse(
            connected=controller.state.connected,
            track_power_on=controller.state.track_power_on,
            short_circuit=sys_info.short_circuit,
            emergency_stop=sys_info.emergency_stop,
            temperature_c=sys_info.temperature_c,
            supply_voltage_mv=sys_info.supply_voltage_mv,
            track_voltage_mv=sys_info.track_voltage_mv,
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

    @app.get("/api/turnouts/{address}", response_model=TurnoutStateResponse)
    def get_turnout(address: int) -> TurnoutStateResponse:
        turnout = controller.state.turnouts.get(address)
        position = turnout.position if turnout is not None else None
        return TurnoutStateResponse(address=address, position=position)

    @app.post("/api/turnouts/{address}/subscribe", status_code=204)
    def subscribe_turnout(address: int) -> Response:
        """Fordert den aktuellen Weichen-Zustand bei der Zentrale an (lesend)."""
        controller.request_turnout_info(address)
        return Response(status_code=204)

    @app.put("/api/turnouts/{address}", status_code=204)
    async def set_turnout(address: int, req: TurnoutRequest) -> Response:
        """Schaltet eine Weiche: Ausgang aktivieren, kurz danach deaktivieren.

        Das Deaktivieren laeuft als Hintergrund-Task, damit der Request sofort
        antwortet. Zusammen ergeben beide Phasen den vollstaendigen
        DCC-Zubehoer-Schaltbefehl; die Antriebsansteuerung uebernimmt der
        Weichendecoder (z. B. ESU SwitchPilot).
        """
        controller.set_turnout(address, req.position)

        async def deactivate_later() -> None:
            await asyncio.sleep(settings.turnout_pulse_s)
            controller.deactivate_turnout(address, req.position)

        asyncio.create_task(deactivate_later())
        return Response(status_code=204)

    @app.get("/api/detectors", response_model=DetectorsResponse)
    def get_detectors() -> DetectorsResponse:
        """Liefert alle bekannten CAN-Belegtmelder-Eingaenge (Single Source of Truth).

        Sortiert nach (addr, port) mit nid als stabilem Tiebreaker, damit die
        Reihenfolge auch bei addr=0 (Moduladresse nicht gesetzt) deterministisch
        bleibt.
        """
        detectors = sorted(
            controller.state.detectors.values(),
            key=lambda d: (d.addr, d.nid, d.port),
        )
        return DetectorsResponse(
            detectors=[_detector_to_response(d) for d in detectors]
        )

    @app.post("/api/detectors/refresh", status_code=204)
    def refresh_detectors() -> Response:
        """Fordert den Belegtstatus aller CAN-Melder einmalig an (rein lesend).

        Die Antworten treffen asynchron als LAN_CAN_DETECTOR-Meldungen ein und
        aktualisieren den Zustand; der Client erfaehrt dies ueber den SSE-Push.
        """
        controller.request_detectors()
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
