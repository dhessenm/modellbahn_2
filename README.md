# modellbahn_2

Steuerung einer digitalen Modellbahn-Anlage über eine **Z21-Digitalzentrale** (Roco/Fleischmann).
Client-Server-Architektur: **FastAPI**-Backend (Python) mit REST-API + Push-Kanal, **Vue 3 + TypeScript**-Frontend (Web-UI).

Details zu Produkt, Technik und Struktur siehe `.kiro/steering/`.

## Projektstruktur

```
.
├── pyproject.toml          # Backend-Projekt-/Abhängigkeitskonfiguration
├── conf/                   # Laufzeitkonfiguration (Z21-IP, Port, Keep-Alive)
├── src/modellbahn/         # Backend-Paket
│   ├── z21/                # Z21/UDP-Protokollschicht (keine Fachlogik)
│   ├── domain/             # Fachlogik + zentraler Anlagenzustand
│   ├── api/                # FastAPI-App (REST + Push)
│   └── main.py             # Einstiegspunkt
├── tests/                  # Backend-Tests (pytest)
└── frontend/               # Vue 3 + TS (Vite)
```

## Backend

```sh
# virtuelle Umgebung anlegen und Abhängigkeiten installieren
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"

# Dev-Server starten (eigenes Terminal)
.venv/bin/uvicorn modellbahn.main:app --reload

# Tests, Linting, Typprüfung
.venv/bin/pytest
.venv/bin/ruff check src tests
.venv/bin/mypy src
```

Das Backend lauscht standardmäßig auf `http://127.0.0.1:8000` (siehe `/health`, `/api/system/status`).

## Frontend

```sh
cd frontend
npm install

# Dev-Server (eigenes Terminal)
npm run dev

# Unit-/Component-Tests, Typprüfung + Build, Linting
npm run test:unit
npm run build
npm run lint

# End-to-End-Tests (Playwright; startet Vite selbst, API wird gemockt)
npm run test:e2e
```

## Dev-Umgebung starten/stoppen

Komfort-Skript, das Backend (Port 8000, ohne `--reload`) und Frontend (Port 5173)
startet und beim Stoppen zuverlässig aufräumt (inkl. verwaister uvicorn-Prozesse,
die sonst den UDP-Socket zur Z21 blockieren):

```sh
scripts/dev.sh start     # beide starten
scripts/dev.sh status    # anzeigen, was läuft
scripts/dev.sh stop      # beide sauber beenden
scripts/dev.sh restart   # stop + start
```

Logs landen unter `.dev-logs/`.

## Konfiguration

Anlagenabhängige Werte liegen unter `conf/`. Als Vorlage dient `conf/config.example.toml`
(Z21-IP, Port, Keep-Alive-Intervall). Werte lassen sich alternativ per Umgebungsvariablen mit
dem Präfix `MB_` setzen (z. B. `MB_Z21_HOST`).
