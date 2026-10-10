"""FastAPI-App-Factory und Basis-Endpunkte.

Der MVP-Funktionsumfang (Lokfuehrerstand, Track-Power, Status) wird schrittweise
als REST-Endpunkte ergaenzt. Dieses Geruest stellt bereits den Anlagenzustand
und einen Health-Endpunkt bereit.
"""

from __future__ import annotations

from fastapi import FastAPI

from modellbahn.config import Settings, get_settings
from modellbahn.domain.state import LayoutState


def create_app(settings: Settings | None = None) -> FastAPI:
    """Erzeugt die FastAPI-App. Zustand wird als App-State gehalten."""
    settings = settings or get_settings()

    app = FastAPI(title="Modellbahn-Steuerung", version="0.1.0")
    app.state.settings = settings
    app.state.layout = LayoutState()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/system/status")
    def system_status() -> dict[str, object]:
        layout: LayoutState = app.state.layout
        return {
            "connected": layout.connected,
            "track_power_on": layout.track_power_on,
            "z21_host": settings.z21_host,
            "z21_port": settings.z21_port,
        }

    return app
