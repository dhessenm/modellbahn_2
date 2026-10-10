"""Zentrales Logging-Setup fuer das Backend.

Das Log-Level ist konfigurierbar (Settings.log_level bzw. Umgebungsvariable
MB_LOG_LEVEL). Auf DEBUG werden u. a. alle gesendeten/empfangenen Z21-Pakete
protokolliert, was die Diagnose der Verbindung erleichtert.
"""

from __future__ import annotations

import logging


def configure_logging(level: str) -> None:
    """Konfiguriert das Root-Logging einmalig mit dem gewuenschten Level."""
    numeric = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        force=True,
    )
