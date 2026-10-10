"""Fachlogik: Loks, Weichen, Rueckmelder, Bloecke, Zugfahrten.

Diese Schicht haengt NICHT von FastAPI, HTTP oder UDP ab und ist ohne reale
Zentrale testbar. Sie haelt den massgeblichen Anlagenzustand (Single Source
of Truth), der sowohl REST-Antworten als auch Push-Events speist.
"""

from modellbahn.domain.controller import LocoController
from modellbahn.domain.state import LayoutState, LocoState

__all__ = ["LayoutState", "LocoController", "LocoState"]
