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


def test_layout_settings_defaults(monkeypatch: Any, tmp_path: Path) -> None:
    # Ohne TOML/Env greifen die Defaults fuer das Anlagenmodell.
    monkeypatch.setattr(config, "_CONFIG_PATH", tmp_path / "fehlt.toml")
    s = config.get_settings()
    assert s.layout_path == config._DEFAULT_LAYOUT_PATH
    assert s.layout_path.name == "layout.json"
    assert s.layout_backup_count == 10


def test_layout_settings_env_override(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setattr(config, "_CONFIG_PATH", tmp_path / "fehlt.toml")
    custom = tmp_path / "eigenes-layout.json"
    monkeypatch.setenv("MB_LAYOUT_PATH", str(custom))
    monkeypatch.setenv("MB_LAYOUT_BACKUP_COUNT", "3")
    s = config.get_settings()
    assert s.layout_path == custom
    assert s.layout_backup_count == 3


def test_roster_settings_defaults(monkeypatch: Any, tmp_path: Path) -> None:
    # Ohne TOML/Env greifen die Defaults fuer die Lok-Stammdaten.
    monkeypatch.setattr(config, "_CONFIG_PATH", tmp_path / "fehlt.toml")
    s = config.get_settings()
    assert s.roster_path == config._DEFAULT_ROSTER_PATH
    assert s.roster_path.name == "roster.json"
    assert s.roster_backup_count == 10


def test_roster_settings_env_override(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setattr(config, "_CONFIG_PATH", tmp_path / "fehlt.toml")
    custom = tmp_path / "eigenes-roster.json"
    monkeypatch.setenv("MB_ROSTER_PATH", str(custom))
    monkeypatch.setenv("MB_ROSTER_BACKUP_COUNT", "3")
    s = config.get_settings()
    assert s.roster_path == custom
    assert s.roster_backup_count == 3
