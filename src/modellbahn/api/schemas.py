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


class SystemStatusResponse(BaseModel):
    connected: bool
    track_power_on: bool
    z21_host: str
    z21_port: int
