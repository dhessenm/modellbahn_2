# Projektstand & nächste Schritte

Kurzer Faden für den Wiedereinstieg. Für Architektur, Technik und Protokolldetails siehe
`.kiro/steering/` (`product.md`, `tech.md`, `structure.md`, `z21-protokoll.md`,
`traincontroller-domaene.md`). Dieses Dokument ergänzt nur den aktuellen Arbeitsstand.

## Schneller Wiedereinstieg

- Dev-Umgebung starten: `scripts/dev.sh start` (Backend :8000 ohne `--reload`, Frontend :5173).
  Stoppen: `scripts/dev.sh stop`. Logs unter `.dev-logs/`.
- Backend-Code geändert? Immer `dev.sh stop` + `start` (kein Auto-Reload). Frontend lädt via Vite
  automatisch neu.
- Konfiguration: `conf/config.toml` (z. B. `log_level`, `z21_host`). Env `MB_*` überschreibt.
- Z21 real erreichbar unter **192.168.0.111:21105**. Test-Lok: **Adresse 3**.
- Tests: Backend `.venv/bin/pytest -q`; Frontend `npm run build`, `npx vitest run`,
  `npx playwright test` (im `frontend/`). CI läuft bei jedem Push (GitHub Actions).

## Stand (fertig, gegen echte Z21 verifiziert)

- **Backend** (FastAPI + UDP-Z21-Client): Verbindung mit Keep-Alive, Broadcast-Flags,
  unverbundenes Socket; zentraler Zustand (Single Source of Truth); REST + SSE-Push.
- **Loksteuerung** (DCC, 128 Fahrstufen): Fahren, Richtung, Funktionen F0–F28; Fahrtest bis
  Fahrstufe 60 erfolgreich.
- **SystemState**: Gleisspannung, Kurzschluss, Nothalt, Temperatur, Spannungen.
- **Weichensteuerung**: `LAN_X_SET_TURNOUT` (Aktivieren→Deaktivieren), `TURNOUT_INFO` lesen.
- **Web-UI** (Vue 3 + TS), App-Shell mit Navigation + globaler Verbindungsanzeige:
  Dashboard (Zentralenstatus), Lokführerstand, Weichen; Gleisplan-Anzeige/-Modellierung als
  Platzhalter. Im LAN erreichbar (Desktop + iPhone).
- **Infrastruktur**: TOML-Konfig, DEBUG-Logging, Dev-Skript, Tests, CI mit Status-Badge.

## Als Nächstes: Gleisbelegtmeldung

Ziel: schnell und zuverlässig erkennen, wenn ein Gleisabschnitt belegt wird (latenzkritisch —
siehe Latenz-Leitlinie in `tech.md`; wichtig für späteres punktgenaues Halten).

- Hardware: Roco **Z21 Detector 10808**, per **CAN-Bus** an die Z21 angebunden.
- Protokoll: CAN-Belegtmeldungen über `LAN_CAN_DETECTOR` (X-Header `0xC4`). Vor Implementierung
  Byte-Layout in `external_docs/z21-lan-protokoll.pdf` nachschlagen (Kapitel 10, CAN).
- Broadcast-Flags: passendes CAN-Flag in `LAN_SET_BROADCASTFLAGS` ergänzen, damit Meldungen
  eintreffen (analog zum heutigen Vorgehen bei SystemState/Lok-Info).
- Umsetzung voraussichtlich: `messages.py` (Dekodierung) → `domain` (Belegt-Zustand) →
  REST + SSE → UI-Anzeige. Ereignisgesteuert verarbeiten, kein Polling.
- Hinweis: Hardware ist noch nicht installiert — zunächst Dekodierung/Tests gegen Beispieldaten,
  Live-Test später.

## Offene Punkte / Merker

- **Weichen-Adresszählung:** Backend/UI nutzen die LAN-Adresse **ab 0**; Apps/multiMaus zählen
  oft **ab 1**. Beim echten Weichendecoder (ESU SwitchPilot) prüfen und ggf. UI auf „ab 1"
  umstellen.
- **Weichen-Rückmeldung:** `SET_TURNOUT` wird nicht quittiert; `TURNOUT_INFO` ist nur der
  Soll-Zustand. Für Fahrstraßen „unconditional setting" (immer explizit stellen). Details in
  `z21-protokoll.md` / `tech.md`.
- **Log-Rauschen:** Bei DEBUG ist das uvicorn-Zugriffslog + Keep-Alive geschwätzig. Optional
  später: uvicorn-Access-Log leiser, nur `modellbahn.*` auf DEBUG.
- **macOS Local Network Privacy:** UDP ins LAN scheitert mit „No route to host", wenn die
  ausführende App (z. B. iTerm) die Berechtigung „Lokales Netzwerk" nicht (mehr) hat. Lösung:
  in den Systemeinstellungen aus-/einschalten + App neu starten.

## Mögliche Themen danach

- Gleisplan-Bereiche mit Inhalt füllen (Anzeige + Modellierung).
- Weichen-Komfort: Benennung, mehrere Weichen, Adresszählung ab 1.
- RailCom zur Lok-Identifikation (zusammen mit Belegtmeldung).
- uvicorn-Access-Log konfigurieren.
- **Produktiv-Deployment** (Backend + Frontend auf Raspberry Pi, Single-Service): geplant,
  siehe `docs/deployment.md`. Noch nicht umgesetzt.
