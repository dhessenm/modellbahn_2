# Technologie-Stack

> Status: früh. Festgelegt sind **Python**, **FastAPI** als Backend-Framework und eine **Web-UI**
> (Client-Server). Konkrete Frontend-Technik und Paketmanager sind noch offen. Es existiert noch
> kein Anwendungscode. Diese Datei beim Festlegen der offenen Punkte ergänzen.

## Festgelegt

- **Sprache:** Python 3 (konkrete Mindestversion noch festzulegen, empfohlen aktuell ≥ 3.11).
- **Backend-Framework:** **FastAPI** (ausgeführt mit `uvicorn`). Async-fähig, gut geeignet für
  die parallele UDP-Kommunikation und einen Echtzeit-Kanal.
- **Architektur:** Client-Server, stark entkoppelt.
  - **Backend (Python):** kommuniziert per Z21 LAN-Protokoll (UDP) mit der Zentrale und stellt
    dem Web-Client die Schnittstelle bereit.
  - **Frontend:** Web-UI im Browser, spricht ausschließlich mit dem Backend.
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

### Spätere Hardware-Erweiterungen (nicht MVP)

Für das Scoping hier festgehalten, in der ersten Version aber nicht umgesetzt:

- **Gleisbelegtmeldung:** Roco **Z21 Detector (10808)**, angebunden per **CAN-Bus** an die
  Z21-Zentrale. Auswertung über die CAN-/Detector-Meldungen des Z21-Protokolls.
- **RailCom:** zur **Identifikation von Loks** (welche Lok in welchem Abschnitt). Nutzung der
  RailCom-Daten (`LAN_RAILCOM_*`) in Verbindung mit der Belegtmeldung.

## Noch zu wählen

- **Echtzeit-Kanal:** WebSocket oder Server-Sent Events für die Push-Updates (beides von
  FastAPI unterstützt; SSE genügt für reine Server→Client-Updates, WebSocket bei bidirektionalem
  Bedarf).
- **Frontend-Technik:** einfaches HTML/JS oder ein Framework (z. B. React/Vue) — abhängig vom
  Umfang des Stellwerks/der UI.
- **Paketmanager / Umgebung:** z. B. `uv`, `poetry` oder `pip` + `venv` mit `pyproject.toml`.
- **Python-Mindestversion** verbindlich festlegen.

## Empfohlene Werkzeuge (Python-üblich)

Als Vorschlag, sobald der Stack fixiert wird:

- **Test:** `pytest`.
- **Linter/Formatter:** `ruff` (Linting + Formatierung) oder `black` + `flake8`.
- **Typprüfung:** `mypy` oder `pyright` (empfohlen bei binärer Protokoll-Verarbeitung).

## Technische Anforderungen an den Stack

- **UDP-Netzwerk:** Senden/Empfangen und asynchrone Broadcast-Meldungen der Zentrale. Python
  bietet dies über `asyncio` (Datagram-Endpoints) oder `socket`.
- **Binäre Protokoll-Verarbeitung:** Little-Endian Serialisierung und XOR-Prüfsummen, z. B.
  mit dem `struct`-Modul und `bytes`/`bytearray`.
- **Echtzeit zum Browser:** Backend verarbeitet die unaufgefordert gesendeten Zentralen-Meldungen
  und reicht sie über den WebSocket/SSE-Kanal an die Web-Clients weiter.
- **Zentrale Zustandsquelle (Single Source of Truth):** Das Backend führt genau einen
  maßgeblichen Anlagenzustand (Loks, Weichen, Rückmelder, Systemstatus) in der Fachlogik. Dieser
  wird aus den Z21-Broadcasts aktualisiert und speist **sowohl** REST-Antworten **als auch**
  Push-Events — kein zweiter, getrennter Datenpfad. Damit sind REST und Push widerspruchsfrei.
  Nebenläufige Zugriffe (UDP-Empfang, REST-Requests, Push) müssen den Zustand konsistent halten
  (geeignete Synchronisation / ein zentraler Zustandshalter).
- **Keep-Alive gegen Z21-Timeout:** Die Z21 entfernt einen Client, der nicht mindestens
  **einmal pro Minute** (≈ 60 s) kommuniziert. Das Backend muss daher periodisch (Intervall
  deutlich unter 60 s, z. B. 15–30 s) eine Statusabfrage senden (`LAN_X_GET_STATUS` oder
  `LAN_SYSTEMSTATE_GETDATA`), um die Registrierung aufrechtzuerhalten. Als Nebeneffekt dient der
  Erfolg/Misserfolg dieser Abfragen als Grundlage für den **Verbindungsstatus zur Zentrale**.
  Beim Beenden per `LAN_LOGOFF` sauber abmelden. Der Keep-Alive läuft als Hintergrund-Task im
  Backend (z. B. `asyncio`-Task), unabhängig von Client-Requests.
- **Entkopplung:** Die Schichten klar trennen und über Schnittstellen/Abstraktionen koppeln:
  - **Z21/Protokoll-Schicht:** reine Kodierung/Dekodierung und UDP-Transport, kennt keine
    Fachlogik.
  - **Fachlogik-Schicht:** Loks, Weichen, Rückmelder, Blöcke, Fahrten — hängt **nicht** von
    FastAPI, HTTP oder UDP ab und ist ohne reale Zentrale testbar (z. B. gegen einen Fake-/Mock-
    Z21-Client).
  - **API-Schicht (FastAPI):** REST-Endpunkte + Push-Kanal; dünn, delegiert an die Fachlogik.
  - Abhängigkeiten zeigen nach innen (API → Fachlogik → Protokoll), nicht umgekehrt.

## Häufige Befehle

Platzhalter — konkretisieren, sobald Paketmanager und Framework feststehen:

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

> Hinweis: Lang laufende Prozesse wie der Dev-Server im eigenen Terminal starten, nicht als
> blockierenden Einmalbefehl.

## Konventionen

- Abhängigkeits-Versionen in `pyproject.toml` pinnen (keine offenen Bereiche).
- Gut gepflegte, weit verbreitete Bibliotheken bevorzugen.
- Die Z21-Anbindung hinter einer klar abgegrenzten Schnittstelle kapseln, damit die Fachlogik
  unabhängig vom Digitalsystem bleibt und ohne Hardware getestet werden kann.
- PEP 8 folgen; Formatierung und Linting dem gewählten Tool (z. B. `ruff`) überlassen.
