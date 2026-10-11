"""Pydantic-Schemata fuer die REST-API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TrackPowerRequest(BaseModel):
    on: bool


class DriveRequest(BaseModel):
    speed: int = Field(ge=0, le=126, description="DCC-Fahrstufe 0..126 (0 = Stop)")
    forward: bool = True


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
