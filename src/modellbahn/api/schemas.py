"""Pydantic-Schemata fuer die REST-API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from modellbahn.domain.block_runtime import BlockRuntime
from modellbahn.domain.layout import (
    Block,
    DetectorAssignment,
    DirectionMarkers,
    ElementSetting,
    ElementType,
    Marker,
    Route,
    TopologyElement,
)
from modellbahn.domain.layout_consistency import ConsistencyWarning
from modellbahn.domain.layout_service import ReferenceBlocker


class TrackPowerRequest(BaseModel):
    on: bool


class DriveRequest(BaseModel):
    # Die genaue, modusabhaengige Range-Pruefung (0..13/27/126 je nach
    # Fahrstufenmodus) erfolgt in build_loco_drive; hier nur speed >= 0.
    speed: int = Field(ge=0, description="DCC-Fahrstufe (0 = Stop)")
    forward: bool = True
    speed_steps: int = Field(default=128, description="Fahrstufenmodus: 14, 28 oder 128")


class FunctionRequest(BaseModel):
    function: int = Field(ge=0, le=31, description="Funktionsindex F0..F31")
    on: bool


class LocoStateResponse(BaseModel):
    address: int
    speed: int
    forward: bool
    functions: dict[int, bool]


class TurnoutRequest(BaseModel):
    position: int = Field(ge=0, le=1, description="Weichenausgang 0 oder 1")


class TurnoutStateResponse(BaseModel):
    address: int
    position: int | None  # 0, 1 oder null (noch nicht geschaltet)


class DetectorLocoResponse(BaseModel):
    address: int
    direction: str  # "forward", "backward" oder "unknown"


class DetectorInputResponse(BaseModel):
    nid: int  # unveraenderbare CAN-NetworkID (stabile Melder-Identitaet)
    addr: int  # konfigurierbare Moduladresse (nur Anzeigeinfo, ggf. 0)
    port: int  # Eingang 0..7 (intern 0-basiert; die UI zeigt Port+1 an)
    occupied: bool
    with_power: bool
    overload: bool
    overload_level: int
    status_text: str  # menschenlesbar deutsch, in der api-Schicht abgeleitet
    locos: list[DetectorLocoResponse]


class DetectorsResponse(BaseModel):
    detectors: list[DetectorInputResponse]


class SystemStatusResponse(BaseModel):
    connected: bool
    track_power_on: bool
    short_circuit: bool
    emergency_stop: bool
    temperature_c: int
    supply_voltage_mv: int
    track_voltage_mv: int
    z21_host: str
    z21_port: int


# ---------------------------------------------------------------------------
# Anlagenmodell (statisches Layout): Request-/Response-Schemata
# ---------------------------------------------------------------------------
#
# Diese Modelle bilden die domain-Dataclasses (`layout.py`) fuer die REST-API ab.
# Fachvalidierung bleibt vollstaendig im `LayoutService`; die Schemata pruefen nur
# die Grundform (Typen, Pflichtfelder). PUT wird in Stufe 1 als Vollersetzung der
# editierbaren Felder interpretiert (siehe `layout_routes.py`).


class ElementRequest(BaseModel):
    name: str
    type: ElementType  # "turnout" | "dkw" | "crossing"
    address: int | None = None  # Weiche/DKW: Zubehoeradresse A
    address_b: int | None = None  # nur DKW: zweite Zubehoeradresse


class ElementResponse(BaseModel):
    id: str
    name: str
    type: ElementType
    address: int | None
    address_b: int | None


class DetectorAssignmentModel(BaseModel):
    """Melder-Zuordnung eines Blocks (Request-Element und Response-Bestandteil)."""

    detector_nid: int
    detector_port: int
    order: int
    length_mm: int | None = None


class MarkerModel(BaseModel):
    """Halt- oder Bremsmarke; die xor-Regel prueft der Service, nicht das Schema."""

    detector_ref: tuple[int, int] | None = None  # (nid, port) als 2er-Array
    position_mm: int | None = None  # ab Blockanfang, mm


class DirectionMarkersModel(BaseModel):
    stop: MarkerModel | None = None
    brake: MarkerModel | None = None


class BlockRequest(BaseModel):
    name: str
    length_mm: int | None = None
    max_speed_kmh: int | None = None
    markers_forward: DirectionMarkersModel | None = None
    markers_backward: DirectionMarkersModel | None = None


class BlockResponse(BaseModel):
    id: str
    name: str
    length_mm: int | None
    max_speed_kmh: int | None
    detectors: list[DetectorAssignmentModel]
    markers_forward: DirectionMarkersModel
    markers_backward: DirectionMarkersModel


class DetectorAssignmentsRequest(BaseModel):
    """Body fuer `PUT /api/layout/blocks/{id}/detectors`."""

    detectors: list[DetectorAssignmentModel] = Field(default_factory=list)


class ElementSettingModel(BaseModel):
    element_id: str
    desired_state: int


class RouteRequest(BaseModel):
    name: str
    start_block_id: str
    transit_block_ids: list[str] = Field(default_factory=list)
    end_block_id: str
    element_settings: list[ElementSettingModel] = Field(default_factory=list)
    claimed_element_ids: list[str] = Field(default_factory=list)


class RouteResponse(BaseModel):
    id: str
    name: str
    start_block_id: str
    transit_block_ids: list[str]
    end_block_id: str
    element_settings: list[ElementSettingModel]
    claimed_element_ids: list[str]


class LayoutResponse(BaseModel):
    """Gesamtmodell fuer `GET /api/layout`."""

    blocks: list[BlockResponse]
    elements: list[ElementResponse]
    routes: list[RouteResponse]


class BlockRuntimeResponse(BaseModel):
    block_id: str
    occupancy: Literal["free", "occupied", "unknown"]
    loco_addresses: list[int]


class WarningResponse(BaseModel):
    code: str
    message: str


class BlockWriteResponse(BaseModel):
    """Wrapper fuer Block-Schreibzugriffe: Entitaet plus Konsistenz-Warnungen."""

    entity: BlockResponse
    warnings: list[WarningResponse]


class ReferenceBlockerModel(BaseModel):
    type: str
    id: str
    name: str


class ConflictResponse(BaseModel):
    """Dokumentiertes 409-Body-Schema (Loeschschutz)."""

    detail: str
    blocked_by: list[ReferenceBlockerModel]


# ---------------------------------------------------------------------------
# Mapping-Helfer dataclass <-> Schema (nur Lesen der domain-Modelle)
# ---------------------------------------------------------------------------


def element_to_response(element: TopologyElement) -> ElementResponse:
    """Bildet ein `TopologyElement` auf das Response-Schema ab."""
    return ElementResponse(
        id=element.id,
        name=element.name,
        type=element.type,
        address=element.address,
        address_b=element.address_b,
    )


def assignment_to_model(assignment: DetectorAssignment) -> DetectorAssignmentModel:
    """Bildet eine `DetectorAssignment` auf das Schema ab."""
    return DetectorAssignmentModel(
        detector_nid=assignment.detector_nid,
        detector_port=assignment.detector_port,
        order=assignment.order,
        length_mm=assignment.length_mm,
    )


def model_to_assignment(model: DetectorAssignmentModel) -> DetectorAssignment:
    """Bildet ein Melder-Zuordnungs-Schema auf die Dataclass ab."""
    return DetectorAssignment(
        detector_nid=model.detector_nid,
        detector_port=model.detector_port,
        order=model.order,
        length_mm=model.length_mm,
    )


def marker_to_model(marker: Marker | None) -> MarkerModel | None:
    """Bildet einen optionalen `Marker` auf das Schema ab (`None` bleibt `None`)."""
    if marker is None:
        return None
    return MarkerModel(detector_ref=marker.detector_ref, position_mm=marker.position_mm)


def model_to_marker(model: MarkerModel | None) -> Marker | None:
    """Bildet ein optionales Marker-Schema auf die Dataclass ab."""
    if model is None:
        return None
    return Marker(detector_ref=model.detector_ref, position_mm=model.position_mm)


def direction_markers_to_model(markers: DirectionMarkers) -> DirectionMarkersModel:
    """Bildet `DirectionMarkers` auf das Schema ab."""
    return DirectionMarkersModel(
        stop=marker_to_model(markers.stop),
        brake=marker_to_model(markers.brake),
    )


def model_to_direction_markers(model: DirectionMarkersModel) -> DirectionMarkers:
    """Bildet ein `DirectionMarkersModel` auf die Dataclass ab."""
    return DirectionMarkers(
        stop=model_to_marker(model.stop),
        brake=model_to_marker(model.brake),
    )


def block_to_response(block: Block) -> BlockResponse:
    """Bildet einen `Block` auf das Response-Schema ab."""
    return BlockResponse(
        id=block.id,
        name=block.name,
        length_mm=block.length_mm,
        max_speed_kmh=block.max_speed_kmh,
        detectors=[assignment_to_model(a) for a in block.detectors],
        markers_forward=direction_markers_to_model(block.markers_forward),
        markers_backward=direction_markers_to_model(block.markers_backward),
    )


def element_setting_to_model(setting: ElementSetting) -> ElementSettingModel:
    """Bildet ein `ElementSetting` auf das Schema ab."""
    return ElementSettingModel(
        element_id=setting.element_id,
        desired_state=setting.desired_state,
    )


def model_to_element_setting(model: ElementSettingModel) -> ElementSetting:
    """Bildet ein `ElementSettingModel` auf die Dataclass ab."""
    return ElementSetting(element_id=model.element_id, desired_state=model.desired_state)


def route_to_response(route: Route) -> RouteResponse:
    """Bildet eine `Route` auf das Response-Schema ab."""
    return RouteResponse(
        id=route.id,
        name=route.name,
        start_block_id=route.start_block_id,
        transit_block_ids=list(route.transit_block_ids),
        end_block_id=route.end_block_id,
        element_settings=[element_setting_to_model(s) for s in route.element_settings],
        claimed_element_ids=list(route.claimed_element_ids),
    )


def runtime_to_response(runtime: BlockRuntime) -> BlockRuntimeResponse:
    """Bildet einen `BlockRuntime` auf das Response-Schema ab."""
    return BlockRuntimeResponse(
        block_id=runtime.block_id,
        occupancy=runtime.occupancy,
        loco_addresses=list(runtime.loco_addresses),
    )


def warnings_to_models(warnings: list[ConsistencyWarning]) -> list[WarningResponse]:
    """Bildet Konsistenz-Warnungen auf das Response-Schema ab."""
    return [WarningResponse(code=w.code, message=w.message) for w in warnings]


def blockers_to_models(blockers: list[ReferenceBlocker]) -> list[ReferenceBlockerModel]:
    """Bildet Loeschschutz-Blocker auf das Response-Schema ab."""
    return [ReferenceBlockerModel(type=b.type, id=b.id, name=b.name) for b in blockers]
