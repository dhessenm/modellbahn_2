"""Tests fuer die Single-Service-Auslieferung des gebauten Frontends.

Prueft beide Betriebsarten:
- Ohne `frontend/dist` (Entwicklung): Backend bleibt reine API, kein SPA-Fallback.
- Mit `frontend/dist` (Produktion): Backend liefert die Web-UI aus; API-/SSE-/
  Health-Pfade behalten Vorrang, Deep-Links liefern index.html.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from modellbahn.api import create_app
from modellbahn.config import Settings


class FakeTransport:
    def __init__(self) -> None:
        self.sent: list[bytes] = []

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    def send(self, dataset: bytes) -> None:
        self.sent.append(dataset)


def _settings(tmp_path: Path, frontend_dist: Path) -> Settings:
    return Settings(
        layout_path=tmp_path / "layout.json",
        roster_path=tmp_path / "roster.json",
        frontend_dist_path=frontend_dist,
    )


def _build_fake_dist(tmp_path: Path) -> Path:
    """Erzeugt ein minimales, realistisches frontend/dist-Verzeichnis."""
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text(
        "<!doctype html><title>Modellbahn</title><div id=app></div>", encoding="utf-8"
    )
    (dist / "assets" / "index-abc123.js").write_text("console.log('ui')", encoding="utf-8")
    (dist / "favicon.ico").write_text("icon", encoding="utf-8")
    return dist


# ---------------------------------------------------------------------------
# Ohne dist: reine API
# ---------------------------------------------------------------------------
def test_without_dist_is_api_only(tmp_path: Path) -> None:
    settings = _settings(tmp_path, tmp_path / "dist")  # existiert nicht
    client = TestClient(create_app(settings=settings, transport=FakeTransport()))

    # API funktioniert.
    assert client.get("/health").status_code == 200
    # Kein SPA-Fallback: unbekannter Pfad -> 404 (keine index.html).
    resp = client.get("/roster")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Mit dist: Single-Service
# ---------------------------------------------------------------------------
def test_with_dist_serves_index_at_root(tmp_path: Path) -> None:
    dist = _build_fake_dist(tmp_path)
    client = TestClient(create_app(settings=_settings(tmp_path, dist), transport=FakeTransport()))

    resp = client.get("/")
    assert resp.status_code == 200
    assert "<div id=app>" in resp.text


def test_with_dist_spa_deeplink_returns_index(tmp_path: Path) -> None:
    dist = _build_fake_dist(tmp_path)
    client = TestClient(create_app(settings=_settings(tmp_path, dist), transport=FakeTransport()))

    # Vue-Router-Deep-Link -> index.html (SPA-Fallback), nicht 404.
    resp = client.get("/roster")
    assert resp.status_code == 200
    assert "<div id=app>" in resp.text


def test_with_dist_serves_real_file(tmp_path: Path) -> None:
    dist = _build_fake_dist(tmp_path)
    client = TestClient(create_app(settings=_settings(tmp_path, dist), transport=FakeTransport()))

    # Eine real existierende Datei wird direkt geliefert (nicht index.html).
    resp = client.get("/favicon.ico")
    assert resp.status_code == 200
    assert resp.text == "icon"


def test_with_dist_api_keeps_precedence(tmp_path: Path) -> None:
    dist = _build_fake_dist(tmp_path)
    client = TestClient(create_app(settings=_settings(tmp_path, dist), transport=FakeTransport()))

    # /health bleibt JSON, nicht index.html.
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

    # Reale API-Route liefert echte Daten (kein HTML).
    roster = client.get("/api/roster")
    assert roster.status_code == 200
    assert roster.json() == {"locomotives": []}


def test_with_dist_unknown_api_path_is_404_not_index(tmp_path: Path) -> None:
    dist = _build_fake_dist(tmp_path)
    client = TestClient(create_app(settings=_settings(tmp_path, dist), transport=FakeTransport()))

    # Unbekannter /api-Pfad -> ehrliches 404, keine HTML-Seite.
    resp = client.get("/api/gibtsnicht")
    assert resp.status_code == 404
    assert "<div id=app>" not in resp.text
