"""REST-Routen fuer die Lokverwaltung (`/api/roster`).

Duenne Delegation an den `RosterService` (domain). Alle Fachregeln liegen im
Service; die Routen klassifizieren Fehler und reichen Ergebnisse als Pydantic-
Schemata zurueck.

Fehlerregel:
    - 404: im Pfad adressierte Lok-ID existiert nicht (vorab-Check).
    - 400: Fachregelverstoss (`RosterValidationError`).

Persistenz/SSE: nach jeder erfolgreichen Mutation ruft die Route `on_mutation()`
auf (save + broker.publish(), von `app.py` bereitgestellt).
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, HTTPException, Response

from modellbahn.api.schemas import (
    LocoRequest,
    LocoResponse,
    LocoWriteResponse,
    RosterResponse,
    loco_to_response,
    roster_warnings_to_models,
)
from modellbahn.domain.roster_service import RosterService, RosterValidationError


def build_roster_router(
    get_service: Callable[[], RosterService],
    on_mutation: Callable[[], None],
) -> APIRouter:
    """Erzeugt den `APIRouter` fuer die Lokverwaltung.

    `get_service` liefert den `RosterService`, `on_mutation` fuehrt Persistenz +
    SSE-Push aus.
    """
    router = APIRouter(prefix="/api/roster", tags=["roster"])

    def _require_exists(service: RosterService, loco_id: str) -> None:
        if loco_id not in service.roster.locomotives:
            raise HTTPException(
                status_code=404,
                detail=f"Lok mit ID {loco_id!r} nicht gefunden.",
            )

    def _write_response(service: RosterService, loco_id: str) -> LocoWriteResponse:
        loco = service.get_locomotive(loco_id)
        return LocoWriteResponse(
            entity=loco_to_response(loco),
            warnings=roster_warnings_to_models(service.address_warnings(loco_id)),
        )

    # ------------------------------------------------------------------
    # Lese-Routen
    # ------------------------------------------------------------------
    @router.get("", response_model=RosterResponse)
    def get_roster() -> RosterResponse:
        service = get_service()
        return RosterResponse(
            locomotives=[loco_to_response(loco) for loco in service.list_locomotives()]
        )

    @router.get("/{loco_id}", response_model=LocoResponse)
    def get_locomotive(loco_id: str) -> LocoResponse:
        service = get_service()
        _require_exists(service, loco_id)
        return loco_to_response(service.get_locomotive(loco_id))

    # ------------------------------------------------------------------
    # Schreib-Routen
    # ------------------------------------------------------------------
    @router.post("", status_code=201, response_model=LocoWriteResponse)
    def create_locomotive(req: LocoRequest) -> LocoWriteResponse:
        service = get_service()
        try:
            loco = service.create_locomotive(
                name=req.name,
                address=req.address,
                speed_steps=req.speed_steps,
                function_count=req.function_count,
                length_mm=req.length_mm,
                max_speed_kmh=req.max_speed_kmh,
                notes=req.notes,
            )
        except RosterValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        on_mutation()
        return _write_response(service, loco.id)

    @router.put("/{loco_id}", response_model=LocoWriteResponse)
    def update_locomotive(loco_id: str, req: LocoRequest) -> LocoWriteResponse:
        service = get_service()
        _require_exists(service, loco_id)
        try:
            service.update_locomotive(
                loco_id,
                name=req.name,
                address=req.address,
                speed_steps=req.speed_steps,
                function_count=req.function_count,
                length_mm=req.length_mm,
                max_speed_kmh=req.max_speed_kmh,
                notes=req.notes,
            )
        except RosterValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        on_mutation()
        return _write_response(service, loco_id)

    @router.delete("/{loco_id}", status_code=204)
    def delete_locomotive(loco_id: str) -> Response:
        service = get_service()
        _require_exists(service, loco_id)
        try:
            service.delete_locomotive(loco_id)
        except RosterValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        on_mutation()
        return Response(status_code=204)

    return router
