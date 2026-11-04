# Deployment (Raspberry Pi)

> Status: **umgesetzt und getestet.** Das Backend liefert im Produktivbetrieb das gebaute
> Frontend selbst aus (Single-Service, ein Prozess, ein Port). Erfolgreich auf einem
> Raspberry Pi 5 (Debian 13 „Trixie", Python 3.13) in Betrieb genommen; die Web-UI ist im
> LAN unter `http://<pi-ip>/` erreichbar und spricht mit der Z21.

## Entwicklung vs. Produktion

| | Entwicklung | Produktion (Pi) |
|---|---|---|
| Frontend | Vite-Dev-Server `:5173` (Hot-Reload) | statisch gebaut (`frontend/dist/`), vom Backend ausgeliefert |
| Backend | `uvicorn :8000` | `uvicorn :80` als systemd-Dienst |
| Prozesse/Ports | zwei (5173 + 8000) | **einer** (nur 80) |
| Start | `scripts/dev.sh` | `systemctl` (Autostart beim Booten) |

Der Single-Service-Mount ist in `api/app.py` (`_mount_frontend`): Existiert
`settings.frontend_dist_path` (Default `frontend/dist`), liefert FastAPI die UI unter `/` aus,
inkl. SPA-Fallback für Vue-Router-Deep-Links; `/api/*`, `/health` und SSE behalten Vorrang.
Fehlt `dist/`, bleibt das Backend reine API — der Dev-Betrieb ist unberührt.

## Voraussetzungen auf dem Pi

- Raspberry Pi OS / Debian **≥ 13** (Python **≥ 3.11** wegen `tomllib`; Pi 5 hat 3.13).
- `python3 -m venv` verfügbar (Paket `python3-venv`, bei Trixie vorhanden).
- Pi und Z21 im selben Netz; feste Z21-IP (hier `192.168.0.111`).
- SSH-Zugang zum Pi (hier Host `raspi`, User `hessen`).

## Schritt für Schritt

Die folgenden Schritte wurden real durchgeführt (Mac = Build-/Quellrechner, Pi = Ziel).

### 1. Frontend auf dem Mac bauen

```sh
cd frontend
npm run build          # erzeugt frontend/dist/ (vue-tsc + vite build)
```

Auf dem Pi 5 könnte man auch direkt bauen (Node nötig); hier wurde auf dem Mac gebaut und nur
`dist/` kopiert (Variante „kopieren").

### 2. Code + gebautes Frontend auf den Pi kopieren

Vom Mac aus, aus dem Projektwurzelverzeichnis. **Wichtig:** `frontend/dist` muss auf dem Pi
unter `frontend/dist` landen (nicht im Projektroot), damit der StaticFiles-Mount es findet.

```sh
ssh raspi 'mkdir -p /home/hessen/modellbahn_2/frontend'

rsync -az --delete \
  --exclude '.git' --exclude '.venv' --exclude 'node_modules' \
  --exclude '__pycache__' --exclude '*.pyc' \
  --exclude '.mypy_cache' --exclude '.pytest_cache' --exclude '.ruff_cache' \
  src pyproject.toml README.md scripts conf \
  raspi:/home/hessen/modellbahn_2/

rsync -az --delete frontend/dist/ raspi:/home/hessen/modellbahn_2/frontend/dist/
```

Hinweis: `conf/` wird mitkopiert. Die lokalen, git-ignorierten Dateien (`config.toml`,
`layout.json`, `roster.json`) kommen dabei mit — auf dem Pi ggf. bereinigen oder durch eine
Pi-spezifische `config.toml` ersetzen (siehe Schritt 4). Für ein sauberes Erst-Deployment nur
die `*.example.*`-Vorlagen kopieren und die echten Dateien auf dem Pi neu anlegen.

### 3. Python-venv anlegen und Backend installieren (editable!)

```sh
ssh raspi
cd /home/hessen/modellbahn_2
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -e .          # WICHTIG: -e (editable)
```

**Warum `-e` (editable) und nicht `pip install .`?** Die App berechnet ihre Default-Pfade
(`conf/config.toml`, `conf/layout.json`, `conf/roster.json`, `frontend/dist`) relativ zur Lage
von `config.py` (zwei Ebenen nach oben = Projektwurzel). Bei einem normalen `pip install .`
wird `config.py` ins venv kopiert, und diese Pfadberechnung zeigt dann ins venv-Verzeichnis
statt ins Projekt — Config und Frontend werden nicht gefunden. Mit `-e` bleibt `config.py` im
Projekt (`src/modellbahn/`), und alle projektrelativen Pfade stimmen automatisch, ohne absolute
Pfade in der Config setzen zu müssen.

### 4. Konfiguration auf dem Pi

`conf/config.toml` mit den realen Werten (die Datei ist git-ignoriert und maschinenspezifisch):

```toml
z21_host = "192.168.0.111"
z21_port = 21105
log_level = "INFO"          # DEBUG ist fuer Produktion zu geschwaetzig
```

Die Pfade (`layout_path`, `roster_path`, `frontend_dist_path`) müssen bei editable-Install
**nicht** gesetzt werden — die Defaults treffen das Projektverzeichnis. (Nur bei einem
Nicht-editable-Install müsste man sie absolut setzen.)

Prüfen, dass die Pfade stimmen:

```sh
.venv/bin/python -c "from modellbahn.config import get_settings as g; s=g(); \
  print(s.z21_host, s.layout_path, s.frontend_dist_path, s.log_level)"
```

### 5. Als systemd-Dienst einrichten (Port 80 ohne root)

`/etc/systemd/system/modellbahn.service`:

```ini
[Unit]
Description=Modellbahn-Steuerung (FastAPI, Single-Service)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=hessen
WorkingDirectory=/home/hessen/modellbahn_2
ExecStart=/home/hessen/modellbahn_2/.venv/bin/uvicorn modellbahn.main:app --host 0.0.0.0 --port 80
Restart=on-failure
RestartSec=3
# Port 80 (privilegiert) binden duerfen, ohne als root zu laufen:
AmbientCapabilities=CAP_NET_BIND_SERVICE
CapabilityBoundingSet=CAP_NET_BIND_SERVICE

[Install]
WantedBy=multi-user.target
```

Aktivieren und starten:

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now modellbahn
systemctl is-active modellbahn        # -> active
sudo journalctl -u modellbahn -n 20   # Log pruefen
```

Im Log sollten stehen: „Frontend wird aus .../frontend/dist ausgeliefert (Single-Service)",
„Z21-UDP-Socket geoeffnet ... ziel=192.168.0.111:21105", „Uvicorn running on http://0.0.0.0:80".

### 6. Funktionstest

```sh
# Auf dem Pi:
curl -s http://localhost/health                 # {"status":"ok"}
curl -s http://localhost/api/system/status       # connected:true, wenn Z21 an

# Vom Mac/Netz:
curl -s -o /dev/null -w "%{http_code}\n" http://<pi-ip>/          # 200
curl -s -o /dev/null -w "%{http_code}\n" http://<pi-ip>/roster    # 200 (SPA-Deep-Link)
```

Browser: `http://<pi-ip>/` (hier `http://192.168.0.110/`) — die komplette UI.

## Updates einspielen

1. Auf dem Mac: `cd frontend && npm run build`.
2. Code + `dist/` per `rsync` auf den Pi kopieren (Schritt 2).
3. Bei geänderten Dependencies: `.venv/bin/pip install -e .` erneut.
4. `sudo systemctl restart modellbahn`.

## Dienst verwalten

```sh
sudo systemctl status modellbahn      # Zustand
sudo systemctl restart modellbahn     # neu starten (z. B. nach Update)
sudo systemctl stop modellbahn        # anhalten
sudo journalctl -u modellbahn -f      # Live-Log
```

## Bekannte Stolpersteine (aus der echten Inbetriebnahme)

- **`pip install .` statt `-e`** führt dazu, dass Config und Frontend nicht gefunden werden
  (Pfadberechnung zeigt ins venv). → immer `-e` verwenden (siehe Schritt 3).
- **`frontend/dist` am falschen Ort:** Wird `dist` versehentlich in den Projektroot kopiert,
  findet der Mount es nicht. Zielpfad muss `frontend/dist` sein.
- **Mitkopierte Mac-Config:** `rsync` bringt die lokalen `config.toml`/`layout.json`/
  `roster.json` mit. Für ein sauberes Deployment die echten Dateien auf dem Pi prüfen/neu anlegen.

## Offene Punkte / optional

- **Reverse-Proxy / TLS:** Für reines LAN nicht nötig. Für HTTPS oder mehrere Dienste später
  nginx/Caddy vor uvicorn.
- **Automatisches Deploy:** CI baut/testet nur, deployt nicht. Ein `rsync`-Deploy-Skript wäre
  ein späteres, separates Thema.
- **macOS Local Network Privacy** betrifft nur die Entwicklung auf dem Mac, nicht den Pi.
