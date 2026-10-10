"""Konfiguration des Backends.

Umgebungs-/anlagenabhaengige Werte (Z21-IP, Port, Keep-Alive-Intervall) werden
nicht hartkodiert, sondern hier gebuendelt und aus Umgebung bzw. einer Datei
unter conf/ geladen. Siehe conf/config.example.toml.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Laufzeitkonfiguration; ueberschreibbar per Umgebungsvariablen (Prefix MB_)."""

    model_config = SettingsConfigDict(env_prefix="MB_", env_file=".env", extra="ignore")

    # Z21-Zentrale
    z21_host: str = "192.168.0.111"
    z21_port: int = 21105

    # Keep-Alive-/Poll-Intervall. Bewusst kurz (nicht nur < 60 s Z21-Timeout):
    # Die GET_STATUS-Antwort kommt zuverlaessig an den eigenen UDP-Port, waehrend
    # unaufgeforderte Broadcasts anfangs an einen alten, noch registrierten Port
    # gehen koennen. Haeufiges Pollen stellt die Verbindung daher schnell und
    # robust her (statt im schlechten Fall bis zum ersten Keep-Alive stumm zu bleiben).
    keepalive_interval_s: float = 5.0


def get_settings() -> Settings:
    """Liefert die geladene Konfiguration."""
    return Settings()
