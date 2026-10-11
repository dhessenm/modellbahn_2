# Deployment (Plan)

> Status: **geplant, noch nicht umgesetzt.** Dieses Dokument beschreibt, wie das Produktiv-
> Deployment aussehen soll (Backend + Frontend auf einem Raspberry Pi). Die Umsetzung erfolgt
> später; bis dahin bleibt der Entwicklungsbetrieb (`scripts/dev.sh`) unverändert.

## Entwicklung vs. Produktion

| | Entwicklung (heute) | Produktion (Ziel) |
|---|---|---|
| Frontend | Vite-Dev-Server `:5173` (Hot-Reload, Vue DevTools) | statisch gebaut (`frontend/dist/`), vom Backend ausgeliefert |
| Backend | `uvicorn :8000` | `uvicorn :8000` (einziger Prozess) |
| Prozesse/Ports | zwei (5173 + 8000), Vite proxyt `/api` → 8000 | **einer** (nur 8000) |
| Vue DevTools | sichtbar | **nicht vorhanden** |

**Vue DevTools:** Das schwebende Vue-Symbol kommt vom Plugin `vite-plugin-vue-devtools` und
erscheint **nur** im Dev-Modus (`npm run dev`). Ein Produktions-Build (`npm run build`) enthält
es nicht. Im Produktivbetrieb wird `dist/` ausgeliefert, nicht der Dev-Server — damit sind die
DevTools automatisch weg. Es ist also keine separate "Abschalten"-Aktion nötig.

## Zielarchitektur: Single-Service

Im Produktivbetrieb liefert das **FastAPI-Backend** sowohl die API als auch das gebaute
Frontend aus. Nur ein Prozess, ein Port:

```
Browser → FastAPI (:8000)
            ├── /api/*   → REST + SSE  (unverändert)
            └── /*       → statische Frontend-Dateien aus frontend/dist/
```

Vorteile auf dem Pi:
- Nur ein Dienst zu starten/überwachen (ein systemd-Service).
- Kein Node/Vite im Betrieb nötig (nur zum **Bauen**).
- Kein Proxy-/CORS-Thema: Frontend und API kommen von derselben Herkunft.

## Umsetzungsschritte (später)

1. **Backend liefert `dist/` aus:** StaticFiles-Mount in der FastAPI-App, das `frontend/dist/`
   unter `/` bereitstellt — **nur wenn das Verzeichnis existiert**, damit der Dev-Betrieb
   unverändert bleibt. SPA-Fallback (unbekannte Pfade → `index.html`) für den Vue-Router.
   `/api/*` und der SSE-Endpunkt müssen Vorrang behalten.
2. **Frontend bauen:** `cd frontend && npm run build` erzeugt `frontend/dist/`.
   - Build-Ort: auf einem schwächeren Pi (z. B. Pi 3) besser auf dem Mac bauen und nur `dist/`
     auf den Pi kopieren. Auf Pi 4/5 kann direkt dort gebaut werden.
3. **Backend auf dem Pi:** Python-venv + `pip install -e .` (ohne `[dev]`), Start über
   `uvicorn modellbahn.main:app --host 0.0.0.0 --port 8000`.
4. **Als Dienst (systemd):** Unit-File, das das Backend beim Booten startet und neu startet bei
   Absturz. Beispiel-Skizze:

   ```ini
   # /etc/systemd/system/modellbahn.service
   [Unit]
   Description=Modellbahn-Steuerung (FastAPI)
   After=network-online.target
   Wants=network-online.target

   [Service]
   WorkingDirectory=/home/pi/modellbahn_2
   ExecStart=/home/pi/modellbahn_2/.venv/bin/uvicorn modellbahn.main:app --host 0.0.0.0 --port 8000
   Restart=on-failure
   User=pi

   [Install]
   WantedBy=multi-user.target
   ```

   Aktivieren: `sudo systemctl enable --now modellbahn`.
5. **Konfiguration auf dem Pi:** `conf/config.toml` mit der realen `z21_host` und `log_level`
   (z. B. `INFO`). Env `MB_*` überschreibt bei Bedarf.

## Offene Punkte / zu klären

- **Pi-Modell** (bestimmt, ob auf dem Pi gebaut wird oder nur `dist/` kopiert wird).
- **Python-Version auf dem Pi** (muss ≥ 3.11 sein wegen `tomllib`; Raspberry Pi OS prüfen).
- **Portwahl:** Port 8000 beibehalten oder Standard-HTTP (80)? Für 80 braucht uvicorn erhöhte
  Rechte oder einen vorgelagerten Reverse-Proxy.
- **Reverse-Proxy (optional):** nginx/Caddy vor uvicorn — nur nötig für TLS, Port 80/443 oder
  mehrere Dienste. Für ein reines LAN-Setup verzichtbar.
- **Autostart der Z21-Erreichbarkeit:** Pi und Z21 müssen im selben Netz sein; feste IP für die
  Z21 ist bereits gesetzt (192.168.0.111).
- **macOS Local Network Privacy** betrifft nur die Entwicklung auf dem Mac, nicht den Pi.

## Nicht Teil des Deployments

- CI (GitHub Actions) baut/testet nur, deployt nicht. Ein automatisches Deploy auf den Pi wäre
  ein späteres, separates Thema.
