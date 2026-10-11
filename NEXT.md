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
- **Gleisbelegtmeldung — Anzeige** (Roco Z21 Detector 10808, CAN): `LAN_CAN_DETECTOR`
  (Header `0xC4`), Broadcast-Flag `0x00080000`. Dekodierung → `DetectorInput`-Zustand
  (Schlüssel `(nid, port)`) → REST `GET /api/detectors` + `POST /api/detectors/refresh` +
  SSE → UI-Seite „Belegtmelder" (LED belegt/frei, Statustext, RailCom-Lokadressen mit
  Richtung, Überlast-Hervorhebung). **Live gegen real angeschlossenen 10808 verifiziert:**
  Belegt-Änderungen (inkl. RailCom-Lok) erscheinen per Broadcast in der Web-UI.
- **Infrastruktur**: TOML-Konfig, DEBUG-Logging, Dev-Skript, Tests, CI mit Status-Badge.

## Als Nächstes: Automatik Belegtmeldung → Stop

Die **Anzeige** der Belegtmeldung ist erledigt und live gegen den realen 10808 verifiziert
(siehe Stand oben). Offen bleibt:

- **Latenzkritische Automatik Belegtmeldung → Stop** (punktgenaues Halten): ereignisgesteuert,
  minimale Verzögerung (siehe Latenz-Leitlinie in `tech.md`). Baut auf der vorhandenen Anzeige
  auf, erfordert Blocklogik und einen schnellen Stop-Pfad.
- **Merker Anzeige:** Melder werden über die stabile **NId** gruppiert (Moduladresse `addr`
  kommt real oft als `0`); Eingänge sind in der UI 1-basiert (`Port+1`), intern 0-basiert.
- **Merker Broadcast-Empfang:** Die Z21 sendet CAN-Broadcasts an den registrierten Client.
  Blieben Broadcasts aus, lag es an einem **verwaisten uvicorn-Prozess**, der den UDP-Socket
  (und damit den Z21-Client-Slot) weiter belegte, obwohl er kein TCP:8000 mehr hielt. `dev.sh
  stop`/`status` räumen bzw. zeigen solche Prozesse jetzt mit ab. Nicht am Socket-Typ drehen
  (unverbundenes `0.0.0.0`-Socket ist korrekt).

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
