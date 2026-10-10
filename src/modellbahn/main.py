"""Einstiegspunkt: startet den FastAPI-Server.

Start im Entwicklungsmodus (eigenes Terminal):

    uvicorn modellbahn.main:app --reload
"""

from __future__ import annotations

from modellbahn.api import create_app

app = create_app()
