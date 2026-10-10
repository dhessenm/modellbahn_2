"""Konfiguration des Backends.

Umgebungs-/anlagenabhaengige Werte werden nicht hartkodiert, sondern zentral
hier gebuendelt. Quellen in absteigender Praezedenz:

    1. Umgebungsvariablen mit Prefix MB_ (z. B. MB_Z21_HOST, MB_LOG_LEVEL)
    2. conf/config.toml (flache Schluessel = Einstellungsnamen)
    3. eingebaute Defaults

Siehe conf/config.example.toml als Vorlage.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

# conf/config.toml liegt im Projektwurzelverzeichnis (zwei Ebenen ueber dieser Datei:
# src/modellbahn/config.py -> Projektwurzel).
_CONFIG_PATH = Path(__file__).resolve().parents[2] / "conf" / "config.toml"


class _TomlConfigSource(PydanticBaseSettingsSource):
    """Liest Einstellungen aus conf/config.toml (flache Schluessel)."""

    def _load(self) -> dict[str, Any]:
        if not _CONFIG_PATH.is_file():
            return {}
        with _CONFIG_PATH.open("rb") as fh:
            return tomllib.load(fh)

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
        # Von __call__ nicht benoetigt; Schnittstelle verlangt die Methode.
        return None, field_name, False

    def __call__(self) -> dict[str, Any]:
        data = self._load()
        # Nur bekannte Felder uebernehmen; Unbekanntes still ignorieren.
        return {k: v for k, v in data.items() if k in self.settings_cls.model_fields}


class Settings(BaseSettings):
    """Laufzeitkonfiguration.

    Praezedenz: Umgebungsvariablen (MB_*) > conf/config.toml > Defaults.
    """

    model_config = SettingsConfigDict(env_prefix="MB_", env_file=".env", extra="ignore")

    # Z21-Zentrale
    z21_host: str = "192.168.0.111"
    z21_port: int = 21105

    # Lokaler UDP-Quellport. 0 = vom OS gewaehlter, freier Port (empfohlen).
    local_port: int = 0

    # Lokale Bind-Adresse (Interface). Leer = 0.0.0.0 (OS waehlt gemaess Routing).
    local_host: str = ""

    # Keep-Alive-/Poll-Intervall (bewusst kurz; stellt die Verbindung schnell her).
    keepalive_interval_s: float = 5.0

    # Log-Level: DEBUG protokolliert u. a. jedes gesendete/empfangene Z21-Paket.
    log_level: str = "DEBUG"

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Reihenfolge = Praezedenz (frueheste gewinnt):
        # init > Umgebung > .env > conf/config.toml > Defaults.
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            _TomlConfigSource(settings_cls),
        )


def get_settings() -> Settings:
    """Liefert die geladene Konfiguration."""
    return Settings()
