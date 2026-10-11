# Technologie-Stack

> Status: früh. Festgelegt sind **Python** + **FastAPI** (Backend) und **Vue 3 + TypeScript**
> (Frontend), Client-Server. Paketmanager und Python-Mindestversion noch offen. Es existiert
> noch kein Anwendungscode. Diese Datei beim Festlegen der offenen Punkte ergänzen.

## Festgelegt

- **Sprache:** Python 3 (konkrete Mindestversion noch festzulegen, empfohlen aktuell ≥ 3.11).
- **Backend-Framework:** **FastAPI** (ausgeführt mit `uvicorn`). Async-fähig, gut geeignet für
  die parallele UDP-Kommunikation und einen Echtzeit-Kanal.
- **Architektur:** Client-Server, stark entkoppelt.
  - **Backend (Python):** kommuniziert per Z21 LAN-Protokoll (UDP) mit der Zentrale und stellt
    dem Web-Client die Schnittstelle bereit.
  - **Frontend:** **Vue 3 + TypeScript** (SPA im Browser), spricht ausschließlich mit dem
    Backend über dessen REST-API und den Push-Kanal.
- **Frontend-Stack:** **Vue 3** mit **TypeScript**, Build mit **Vite**. Begründung: reaktive
  State-Updates passen gut zu den Live-Pushes, flache Lernkurve, gute Testbarkeit, wächst von
  MVP bis Stellwerk mit. TypeScript ergänzt die Typsicherheit analog zu `mypy`/`pyright` im
  Backend.
- **Schnittstelle Backend ↔ Web-UI:**
  - **REST-API (primär):** so weit wie möglich alle Z21-Funktionen (Kommandos + Abfragen) über
    REST-Endpunkte bereitstellen.
  - **WebSocket/SSE (ergänzend):** für asynchrone Z21-Broadcasts (Belegtmelder, Status, Lok-Info)
    als Push an die Web-UI, da REST keinen Server-Push erlaubt.

## Externe Rahmenbedingungen (fix)

Ergeben sich aus der angebundenen Hardware:

- **Digitalzentrale:** Z21 (Roco/Fleischmann), gesteuert über das **Z21 LAN-Protokoll** v1.13.
- **Transport:** UDP, Ports **21105** (bevorzugt) oder 21106.
- **Byte-Reihenfolge:** Little-Endian.
- **Nachrichtenformat:** Datensätze aus `DataLen (2 B) + Header (2 B) + Data`; X-Bus-Befehle
  unter Header `0x40` mit abschließender **XOR-Prüfsumme**.
- **Gleisprotokoll:** ausschließlich **DCC** — zum Fahren und Steuern sowohl von Loks als auch
  von Zubehör. Andere Gleisformate (z. B. Motorola/MM) werden nicht genutzt. In der Z21 bedeutet
  das u. a.: Lok-Adressen gemäß DCC (Adresse ≥ 256 ist in der Z21 automatisch DCC), Weichen/Zubehör
  im DCC-Format.

Details siehe `z21-protokoll.md` und das Original `external_docs/z21-lan-protokoll.pdf`.

### Weichen / Zubehör

- Geschaltet wird über `LAN_X_SET_TURNOUT` (DCC-Zubehöradresse, Position 0/1). Ein vollständiger
  Schaltvorgang besteht aus **Aktivieren** (A=1) und kurz darauf **Deaktivieren** (A=0)
  desselben Ausgangs — das ist Teil des DCC-Zubehörprotokolls, **nicht** eine Spulen-Schutzzeit.
- Die eigentliche Antriebsansteuerung übernimmt der **Weichendecoder** an der Anlage, z. B. der
  **ESU SwitchPilot Servo** (Servoantrieb, keine Spule). Das Backend kennt den Antriebstyp
  nicht und sendet nur die Schaltbefehle; der Dekoder fährt den Servo selbstständig und entlastet
  ihn. Die Impulsdauer zwischen A=1 und A=0 ist daher kurz (`turnout_pulse_s`, Default 0,2 s).
- Weichenzustände werden über `LAN_X_TURNOUT_INFO` gelesen (`LAN_X_GET_TURNOUT_INFO` bzw.
  Broadcasts). **Dies ist nur der von der Z21 geführte Soll-Zustand, keine Ist-Rückmeldung der
  Weiche** — `LAN_X_SET_TURNOUT` wird nicht quittiert. Ein echter Ist-Zustand ist erst mit
  Rückmeldern/Belegtmeldung möglich (siehe spätere Erweiterungen). Details in `z21-protokoll.md`.
- **Design-Leitlinie für die spätere Automatik ("unconditional setting"):** Beim Stellen einer
  Fahrstraße jede Weiche **immer explizit** in die benötigte Lage schalten — unabhängig vom
  geführten Status, da der reale Weichenstand unbekannt ist (manuell verstellt, nach Neustart,
  Decoder zwischenzeitlich stromlos). Nicht auf den gemeldeten Zustand verlassen und das Schalten
  "sparen"; lieber den Schaltbefehl idempotent erneut senden.

### Gleisbelegtmeldung (Hardware: Roco Z21 Detector 10808)

- **Anzeige umgesetzt:** Roco **Z21 Detector (10808)**, per **CAN-Bus** an die Z21 angebunden.
  Auslesen über `LAN_CAN_DETECTOR` (Header `0xC4`, **kein** X-Bus/XOR), Broadcast-Flag
  `0x00080000` (`BROADCAST_CAN_DETECTOR`). Dekodierung in `z21/messages.py` →
  Zustand in `domain/state.py` (`DetectorInput`, Schlüssel `(nid, port)`) → REST
  `GET /api/detectors` + `POST /api/detectors/refresh` → SSE-Push → UI-Seite „Belegtmelder".
  Byte-Layout und Wertetabellen in `z21-protokoll.md`.
- **Weiterhin offen:** latenzkritische **Automatik Belegtmeldung → Stop** (punktgenaues
  Halten) — bewusst noch nicht umgesetzt (siehe Latenz-Leitlinie oben).
- **Lokadress-Erkennung nur mit RailCom:** Die Lokadressen in der Belegtmeldung (`Typ 0x11..`)
  liefert nur RailCom. Ohne RailCom meldet der Detector lediglich belegt/frei — „besetzt ohne
  Lokadresse" ist normal.

## Noch zu wählen

- **Echtzeit-Kanal:** WebSocket oder Server-Sent Events für die Push-Updates (beides von
  FastAPI unterstützt; SSE genügt für reine Server→Client-Updates, WebSocket bei bidirektionalem
  Bedarf).
- **Frontend-Paketmanager:** npm, pnpm oder yarn (für das Vue/Vite-Projekt).
- **Backend-Paketmanager / Umgebung:** z. B. `uv`, `poetry` oder `pip` + `venv` mit
  `pyproject.toml`.
- **Python-Mindestversion** verbindlich festlegen.

## Empfohlene Werkzeuge (Python-üblich)

**Backend (Python):**

- **Test:** `pytest` (API-Tests über den FastAPI-TestClient, Fachlogik gegen Mock-Z21-Client).
- **Linter/Formatter:** `ruff` (Linting + Formatierung) oder `black` + `flake8`.
- **Typprüfung:** `mypy` oder `pyright` (empfohlen bei binärer Protokoll-Verarbeitung).

**Frontend (Vue 3 + TypeScript):**

- **Build/Dev:** `Vite`.
- **Unit-/Component-Test:** `Vitest` + `@vue/test-utils` bzw. Vue Testing Library.
- **E2E-Test:** `Playwright` (oder Cypress).
- **Linter/Formatter:** `ESLint` + `Prettier`.
- **Typprüfung:** `vue-tsc` (TypeScript).

## Technische Anforderungen an den Stack

- **UDP-Netzwerk:** Senden/Empfangen und asynchrone Broadcast-Meldungen der Zentrale. Python
  bietet dies über `asyncio` (Datagram-Endpoints) oder `socket`.
- **Binäre Protokoll-Verarbeitung:** Little-Endian Serialisierung und XOR-Prüfsummen, z. B.
  mit dem `struct`-Modul und `bytes`/`bytearray`.
- **Echtzeit zum Browser:** Backend verarbeitet die unaufgefordert gesendeten Zentralen-Meldungen
  und reicht sie über den WebSocket/SSE-Kanal an die Web-Clients weiter.
- **Niedrige Latenz auf dem Steuer-Pfad (Design-Leitlinie):** Die direkte Steuerung
  (Lok fahren, Weichen schalten) sowie der Pfad **Belegtmeldung → Stop-Befehl** (punktgenaues
  Halten) sollen minimale Verzögerung haben. Konkret:
  - Steuerbefehle **ohne Umwege** zur Zentrale senden — keine künstlichen Puffer, Warte-
    schlangen oder Sammel-/Debounce-Verzögerungen auf dem Befehlsweg.
  - Eingehende Belegtmeldungen **sofort** verarbeiten (ereignisgesteuert, nicht per langsamem
    Polling) und daraus abgeleitete Reaktionen (z. B. Stop) unmittelbar auslösen.
  - Blockierende Arbeit vom `asyncio`-Event-Loop fernhalten, damit UDP-Senden/-Empfangen nicht
    verzögert wird.
  - Latenzunkritische Aufgaben (Logging, Persistenz, UI-Aggregation) dürfen den Steuer-Pfad
    nicht ausbremsen. Im automatisierten Betrieb ist Latenz sonst unkritisch — außer bei der
    o. g. Belegtmeldung-/Stop-Kette.
- **Zentrale Zustandsquelle (Single Source of Truth):** Das Backend führt genau einen
  maßgeblichen Anlagenzustand (Loks, Weichen, Rückmelder, Systemstatus) in der Fachlogik. Dieser
  wird aus den Z21-Broadcasts aktualisiert und speist **sowohl** REST-Antworten **als auch**
  Push-Events — kein zweiter, getrennter Datenpfad. Damit sind REST und Push widerspruchsfrei.
  Nebenläufige Zugriffe (UDP-Empfang, REST-Requests, Push) müssen den Zustand konsistent halten
  (geeignete Synchronisation / ein zentraler Zustandshalter).
- **Keep-Alive gegen Z21-Timeout:** Die Z21 entfernt einen Client, der nicht mindestens
  **einmal pro Minute** (≈ 60 s) kommuniziert. Das Backend sendet daher periodisch (Default
  **5 s**, deutlich unter 60 s) eine Statusabfrage (`LAN_X_GET_STATUS` /
  `LAN_SYSTEMSTATE_GETDATA`) und erneuert die Broadcast-Flags, um die Registrierung aktiv zu
  halten. Die (zuverlässig an den eigenen Port kommende) Status-Antwort dient zugleich als
  Grundlage für den **Verbindungsstatus zur Zentrale**. Beim Beenden per `LAN_LOGOFF` sauber
  abmelden. Der Keep-Alive läuft als `asyncio`-Hintergrund-Task, unabhängig von Client-Requests.
- **Konfiguration auslagern:** Umgebungs-/anlagenabhängige Werte nicht hartkodieren, sondern aus
  **`conf/config.toml`** (Format TOML) laden. Dazu gehören u. a. **Z21-IP-Adresse**, UDP-Port
  (21105/21106), Keep-Alive-Intervall und Log-Level. Präzedenz: Umgebungsvariablen (`MB_*`) >
  `conf/config.toml` > Defaults. Beispielvorlage `conf/config.example.toml` einchecken, echte
  Werte lokal halten (`conf/config.toml` ist git-ignoriert), keine Geheimnisse committen.
- **Entkopplung:** Die Schichten klar trennen und über Schnittstellen/Abstraktionen koppeln:
  - **Z21/Protokoll-Schicht:** reine Kodierung/Dekodierung und UDP-Transport, kennt keine
    Fachlogik.
  - **Fachlogik-Schicht:** Loks, Weichen, Rückmelder, Blöcke, Fahrten — hängt **nicht** von
    FastAPI, HTTP oder UDP ab und ist ohne reale Zentrale testbar (z. B. gegen einen Fake-/Mock-
    Z21-Client).
  - **API-Schicht (FastAPI):** REST-Endpunkte + Push-Kanal; dünn, delegiert an die Fachlogik.
  - Abhängigkeiten zeigen nach innen (API → Fachlogik → Protokoll), nicht umgekehrt.

## Häufige Befehle

Teils noch Platzhalter — konkretisieren, sobald die Paketmanager feststehen.

**Backend (Python):**

```sh
# virtuelle Umgebung anlegen und aktivieren
python3 -m venv .venv && source .venv/bin/activate

# Abhängigkeiten installieren (Beispiel; je nach Paketmanager)
pip install -e .            # oder: uv sync / poetry install

# Backend / Dev-Server starten (FastAPI + uvicorn) — im eigenen Terminal
uvicorn modellbahn.main:app --reload

# Tests ausführen
pytest

# Linten / Formatieren (Beispiel ruff)
# ruff check . && ruff format .
```

**Frontend (Vue 3 + TS, im Verzeichnis `frontend/`):**

```sh
# Abhängigkeiten installieren
npm install

# Dev-Server starten — im eigenen Terminal
npm run dev

# Unit-/Component-Tests
npm run test

# E2E-Tests (Playwright)
npm run test:e2e

# Typprüfung + Produktions-Build
npm run build

# Linten / Formatieren
npm run lint
```

> Hinweis: Lang laufende Prozesse wie die Dev-Server (`uvicorn ... --reload`, `npm run dev`) im
> eigenen Terminal starten, nicht als blockierenden Einmalbefehl.

## Konventionen

- Abhängigkeits-Versionen in `pyproject.toml` pinnen (keine offenen Bereiche).
- Gut gepflegte, weit verbreitete Bibliotheken bevorzugen.
- Die Z21-Anbindung hinter einer klar abgegrenzten Schnittstelle kapseln, damit die Fachlogik
  unabhängig vom Digitalsystem bleibt und ohne Hardware getestet werden kann.
- PEP 8 folgen; Formatierung und Linting dem gewählten Tool (z. B. `ruff`) überlassen.
