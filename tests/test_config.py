"""Tests fuer das Laden der Konfiguration (Defaults, TOML, Env-Praezedenz)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from modellbahn import config


def test_defaults_without_toml(monkeypatch: Any, tmp_path: Path) -> None:
    # Auf einen nicht existierenden Pfad zeigen -> nur Defaults.
    monkeypatch.setattr(config, "_CONFIG_PATH", tmp_path / "fehlt.toml")
    monkeypatch.delenv("MB_LOG_LEVEL", raising=False)
    s = config.get_settings()
    assert s.z21_host == "192.168.0.111"
    assert s.z21_port == 21105
    assert s.log_level == "DEBUG"


def test_toml_is_loaded(monkeypatch: Any, tmp_path: Path) -> None:
    cfg = tmp_path / "config.toml"
    cfg.write_text('log_level = "INFO"\nz21_host = "10.0.0.5"\nkeepalive_interval_s = 7.5\n')
    monkeypatch.setattr(config, "_CONFIG_PATH", cfg)
    monkeypatch.delenv("MB_LOG_LEVEL", raising=False)
    s = config.get_settings()
    assert s.log_level == "INFO"
    assert s.z21_host == "10.0.0.5"
    assert s.keepalive_interval_s == 7.5


def test_env_overrides_toml(monkeypatch: Any, tmp_path: Path) -> None:
    cfg = tmp_path / "config.toml"
    cfg.write_text('log_level = "INFO"\n')
    monkeypatch.setattr(config, "_CONFIG_PATH", cfg)
    monkeypatch.setenv("MB_LOG_LEVEL", "WARNING")
    s = config.get_settings()
    assert s.log_level == "WARNING"


def test_unknown_toml_keys_are_ignored(monkeypatch: Any, tmp_path: Path) -> None:
    cfg = tmp_path / "config.toml"
    cfg.write_text('unbekannt = "x"\nz21_port = 21106\n')
    monkeypatch.setattr(config, "_CONFIG_PATH", cfg)
    s = config.get_settings()
    assert s.z21_port == 21106
