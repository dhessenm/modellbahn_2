"""REST-Routen fuer das statische Anlagenmodell (`/api/layout`).

Diese Schicht ist eine duenne Delegation an den `LayoutService` (domain). Sie
enthaelt KEINE Fachvalidierung; alle Fachregeln liegen im Service. Die Routen
klassifizieren lediglich die Fehler und reichen die Service-Ergebnisse als
Pydantic-Schemata (aus `schemas.py`) zurueck.

Fehlerregel (404 vs. 400 vs. 409):
    - 404: Die im Pfad adressierte Ressource ({id}) existiert nicht. Das wird
      vorab per read-only Dict-Lookup auf `service.layout.{blocks,elements,routes}`
      geprueft (`_require_exists`), weil der Service unbekannte IDs nicht von
      Fachregelverstoessen trennt (beide -> `LayoutValidationError`).
    - 400: Die adressierte Ressource existiert, aber die Operation/Nutzlast ist
      fachlich ungueltig (`LayoutValidationError`) -- inkl. Referenzen auf fremde,
      nicht existierende Entitaeten in der Nutzlast.
    - 409: Loeschen abgelehnt, weil die Entitaet noch referenziert wird
      (`ReferenceConflictError`); Body `{detail, blocked_by:[{type,id,name}]}`.

Persistenz/SSE: Nach jeder erfolgreichen Service-Mutation ruft die Route
`on_mutation()` auf (von `app.py` bereitgestellt: `save` + `broker.publish()`).
Scheitert die Service-Validierung, wird `on_mutation` NICHT aufgerufen (Modell
unveraendert, nichts gespeichert/publiziert).
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, HTTPException, Response

from modellbahn.api.schemas import (
    BlockRequest,
    BlockRuntimeResponse,
    BlockWriteResponse,
    DetectorAssignmentsRequest,
    ElementRequest,
    ElementResponse,
    LayoutResponse,
    RouteRequest,
    RouteResponse,
    block_to_response,
    element_to_response,
    model_to_assignment,
    model_to_direction_markers,
    model_to_element_setting,
    route_to_response,
    runtime_to_response,
    warnings_to_models,
)
from modellbahn.domain.block_runtime import derive_all_block_runtimes
from modellbahn.domain.layout_service import (
    LayoutService,
    LayoutValidationError,
    ReferenceConflictError,
)
from modellbahn.domain.state import LayoutState


def build_layout_router(
    get_service: Callable[[], LayoutService],
    get_state: Callable[[], LayoutState],
    on_mutation: Callable[[], None],
) -> APIRouter:
    """Erzeugt den `APIRouter` fuer das Anlagenmodell.

    Die Abhaengigkeiten werden als Callables uebergeben (Closure-Stil wie in
    `app.py`, keine FastAPI-`Depends`-Mechanik):
    `get_service` liefert den `LayoutService`, `get_state` den Live-`LayoutState`
    (fuer `/runtime`) und `on_mutation` fuehrt Persistenz + SSE-Push aus.
    """
    router = APIRouter(prefix="/api/layout", tags=["layout"])

    def _require_exists(service: LayoutService, kind: str, entity_id: str) -> None:
        """Wirft 404, wenn die Pfad-ID in der jeweiligen Collection fehlt."""
        if kind == "block":
            exists = entity_id in service.layout.blocks
            label = "Block"
        elif kind == "element":
            exists = entity_id in service.layout.elements
            label = "Element"
        else:  # route
            exists = entity_id in service.layout.routes
            label = "Fahrstrasse"
        if not exists:
            raise HTTPException(
                status_code=404,
                detail=f"{label} mit ID {entity_id!r} nicht gefunden.",
            )

    def _block_write_response(service: LayoutService, block_id: str) -> BlockWriteResponse:
        """Baut die Block-Schreibantwort (Entitaet + Konsistenz-Warnungen)."""
        block = service.get_block(block_id)
        return BlockWriteResponse(
            entity=block_to_response(block),
            warnings=warnings_to_models(service.block_warnings(block_id)),
        )

    # ------------------------------------------------------------------
    # Lese-Routen
    # ------------------------------------------------------------------
    @router.get("", response_model=LayoutResponse)
    def get_layout() -> LayoutResponse:
        service = get_service()
        return LayoutResponse(
            blocks=[block_to_response(b) for b in service.list_blocks()],
            elements=[element_to_response(e) for e in service.list_elements()],
            routes=[route_to_response(r) for r in service.list_routes()],
        )

    @router.get("/runtime", response_model=list[BlockRuntimeResponse])
    def get_runtime() -> list[BlockRuntimeResponse]:
        service = get_service()
        runtimes = derive_all_block_runtimes(service.layout, get_state())
        return [runtime_to_response(rt) for rt in runtimes]

    # ------------------------------------------------------------------
    # Block-Routen
    # ------------------------------------------------------------------
    @router.post("/blocks", status_code=201, response_model=BlockWriteResponse)
    def create_block(req: BlockRequest) -> BlockWriteResponse:
        service = get_service()
        try:
            block = service.create_block(
                name=req.name,
                length_mm=req.length_mm,
                max_speed_kmh=req.max_speed_kmh,
            )
        except ReferenceConflictError as exc:
            raise _conflict(exc) from exc
        except LayoutValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        on_mutation()
        return _block_write_response(service, block.id)

    @router.put("/blocks/{block_id}", response_model=BlockWriteResponse)
    def update_block(block_id: str, req: BlockRequest) -> BlockWriteResponse:
        service = get_service()
        _require_exists(service, "block", block_id)
        # PUT = Vollersetzung der editierbaren Felder (Stufe 1): nicht gesendete
        # Marker-Felder kommen als None an und bleiben damit unveraendert.
        markers_forward = (
            model_to_direction_markers(req.markers_forward)
            if req.markers_forward is not None
            else None
        )
        markers_backward = (
            model_to_direction_markers(req.markers_backward)
            if req.markers_backward is not None
            else None
        )
        try:
            service.update_block(
                block_id,
                name=req.name,
                length_mm=req.length_mm,
                max_speed_kmh=req.max_speed_kmh,
                markers_forward=markers_forward,
                markers_backward=markers_backward,
            )
        except ReferenceConflictError as exc:
            raise _conflict(exc) from exc
        except LayoutValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        on_mutation()
        return _block_write_response(service, block_id)

    @router.delete("/blocks/{block_id}", status_code=204)
    def delete_block(block_id: str) -> Response:
        service = get_service()
        _require_exists(service, "block", block_id)
        try:
            service.delete_block(block_id)
        except ReferenceConflictError as exc:
            raise _conflict(exc) from exc
        except LayoutValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        on_mutation()
        return Response(status_code=204)

    @router.put("/blocks/{block_id}/detectors", response_model=BlockWriteResponse)
    def set_block_detectors(block_id: str, req: DetectorAssignmentsRequest) -> BlockWriteResponse:
        service = get_service()
        _require_exists(service, "block", block_id)
        assignments = [model_to_assignment(m) for m in req.detectors]
        try:
            service.set_block_detectors(block_id, assignments)
        except ReferenceConflictError as exc:
            raise _conflict(exc) from exc
        except LayoutValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        on_mutation()
        return _block_write_response(service, block_id)

    # ------------------------------------------------------------------
    # Element-Routen
    # ------------------------------------------------------------------
    @router.post("/elements", status_code=201, response_model=ElementResponse)
    def create_element(req: ElementRequest) -> ElementResponse:
        service = get_service()
        try:
            element = service.create_element(
                name=req.name,
                type=req.type,
                address=req.address,
                address_b=req.address_b,
            )
        except ReferenceConflictError as exc:
            raise _conflict(exc) from exc
        except LayoutValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        on_mutation()
        return element_to_response(element)

    @router.put("/elements/{element_id}", response_model=ElementResponse)
    def update_element(element_id: str, req: ElementRequest) -> ElementResponse:
        service = get_service()
        _require_exists(service, "element", element_id)
        # PUT = Vollersetzung (Stufe 1): address/address_b werden immer uebergeben
        # (inkl. None); der Service prueft die Adressregeln auf dem Zielzustand.
        # Der _UNSET-Sentinel bleibt der Partial-Update-Faellen vorbehalten.
        try:
            element = service.update_element(
                element_id,
                name=req.name,
                type=req.type,
                address=req.address,
                address_b=req.address_b,
            )
        except ReferenceConflictError as exc:
            raise _conflict(exc) from exc
        except LayoutValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        on_mutation()
        return element_to_response(element)

    @router.delete("/elements/{element_id}", status_code=204)
    def delete_element(element_id: str) -> Response:
        service = get_service()
        _require_exists(service, "element", element_id)
        try:
            service.delete_element(element_id)
        except ReferenceConflictError as exc:
            raise _conflict(exc) from exc
        except LayoutValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        on_mutation()
        return Response(status_code=204)

    # ------------------------------------------------------------------
    # Route-Routen (Fahrstrassen)
    # ------------------------------------------------------------------
    @router.post("/routes", status_code=201, response_model=RouteResponse)
    def create_route(req: RouteRequest) -> RouteResponse:
        service = get_service()
        try:
            route = service.create_route(
                name=req.name,
                start_block_id=req.start_block_id,
                end_block_id=req.end_block_id,
                transit_block_ids=list(req.transit_block_ids),
                element_settings=[model_to_element_setting(s) for s in req.element_settings],
                claimed_element_ids=list(req.claimed_element_ids),
            )
        except ReferenceConflictError as exc:
            raise _conflict(exc) from exc
        except LayoutValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        on_mutation()
        return route_to_response(route)

    @router.put("/routes/{route_id}", response_model=RouteResponse)
    def update_route(route_id: str, req: RouteRequest) -> RouteResponse:
        service = get_service()
        _require_exists(service, "route", route_id)
        try:
            route = service.update_route(
                route_id,
                name=req.name,
                start_block_id=req.start_block_id,
                end_block_id=req.end_block_id,
                transit_block_ids=list(req.transit_block_ids),
                element_settings=[model_to_element_setting(s) for s in req.element_settings],
                claimed_element_ids=list(req.claimed_element_ids),
            )
        except ReferenceConflictError as exc:
            raise _conflict(exc) from exc
        except LayoutValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        on_mutation()
        return route_to_response(route)

    @router.delete("/routes/{route_id}", status_code=204)
    def delete_route(route_id: str) -> Response:
        service = get_service()
        _require_exists(service, "route", route_id)
        try:
            service.delete_route(route_id)
        except ReferenceConflictError as exc:
            raise _conflict(exc) from exc
        except LayoutValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        on_mutation()
        return Response(status_code=204)

    return router


def _conflict(exc: ReferenceConflictError) -> HTTPException:
    """Baut die 409-HTTPException mit `{detail, blocked_by}`-Body.

    FastAPI serialisiert ein Dict-`detail` direkt als JSON-Body; damit entsteht
    exakt der von der Spec geforderte Koerper.
    """
    return HTTPException(
        status_code=409,
        detail={
            "detail": str(exc),
            "blocked_by": [{"type": b.type, "id": b.id, "name": b.name} for b in exc.blocked_by],
        },
    )
