# Projektstruktur

> Status: Das Repository befindet sich in einer frühen Phase. Es existiert noch kein
> Anwendungscode — bisher nur Steering-Dokumente und externe Referenzdokumentation. Dies
> beschreibt die aktuelle Struktur und die Konventionen für den Ausbau.

## Aktuelle Struktur

```
modellbahn_2/
├── .kiro/
│   └── steering/        # Steering-Dokumente für den KI-Assistenten (product.md, tech.md, structure.md)
└── external_docs/       # Externe Referenzdokumentation (nicht Teil des Quellcodes)
    ├── Programmbeschreibung.pdf    # Programmbeschreibung / Anforderungen
    └── z21-lan-protokoll.pdf       # Z21 LAN-Protokoll (Roco/Fleischmann Digitalzentrale)
```

Es existiert noch kein Anwendungs-, Test- oder Konfigurationscode.

## Verzeichnisse

- `.kiro/steering/` — Steering-Dokumente, die den KI-Assistenten anleiten. Aktuell halten.
- `external_docs/` — Externe Referenzen (PDFs) zu Produkt und Hardware-Protokoll. Dienen als
  Grundlage für Anforderungen und Implementierung, enthalten selbst keinen Code. Vom git-Repo
  ausgeschlossen (`.gitignore`).

## Vorgeschlagene Struktur (Python-Backend + Web-Frontend)

Das Projekt wird in **Python** mit einer **Web-UI** umgesetzt (Client-Server). Ein bewährter
Aufbau — als Vorschlag, bis die reale Struktur entsteht:

```
modellbahn_2/
├── pyproject.toml          # Projekt-/Abhängigkeits-Konfiguration (Paketmanager)
├── conf/                   # Laufzeit-/Umgebungskonfiguration (z. B. Z21-IP-Adresse, Ports)
├── src/
│   └── modellbahn/         # Python-Backend-Paket
│       ├── z21/            # Z21/UDP-Anbindung: Protokoll-Kodierung/-Dekodierung, Client
│       ├── domain/         # Fachlogik: Loks, Weichen, Rückmelder, Blöcke, Zugfahrten
│       ├── api/            # FastAPI-App: REST-Endpunkte + Push-Kanal (WebSocket/SSE)
│       └── main.py         # Einstiegspunkt (startet den FastAPI-Server)
├── frontend/               # Web-UI: Vue 3 + TypeScript, Build mit Vite
│   ├── package.json        # Frontend-Abhängigkeiten/Skripte
│   ├── e2e/                # Playwright-E2E-Tests (API gemockt)
│   └── src/
│       ├── App.vue         # App-Shell: Kopfzeile, Navigation, globale Verbindungsanzeige
│       ├── router/         # Vue-Router: eine Route je Arbeitsbereich
│       ├── views/          # Seiten je Bereich (Dashboard, Lokführerstand, Gleisplan, …)
│       ├── components/     # wiederverwendbare UI-Bausteine
│       ├── stores/         # zentraler Frontend-Zustand (einmal in der Shell gestartet)
│       └── api/            # REST-Client + SSE, Typen
├── tests/                  # Tests (Spiegelung der src-Struktur)
└── .kiro/steering/         # Steering-Dokumente
```

## Architektur-Leitlinien

- **Schichtentrennung (stark entkoppelt):** `z21/` (Hardware/Protokoll) ↔ `domain/` (Fachlogik)
  ↔ `api/` (Web-Schnittstelle). Abhängigkeiten zeigen nach innen: `api` → `domain` → `z21`,
  nicht umgekehrt.
  - `z21/`: reine Protokoll-Kodierung/-Dekodierung und UDP-Transport, ohne Fachlogik.
  - `domain/`: hängt **nicht** von FastAPI, HTTP oder UDP ab und ist ohne reale Zentrale
    testbar (z. B. gegen einen Fake-/Mock-Z21-Client).
  - `api/`: dünne FastAPI-Schicht, delegiert an `domain`.
- **Schnittstelle:** `api/` stellt die Z21-Funktionen so weit wie möglich als **REST-Endpunkte**
  bereit; der **WebSocket/SSE-Kanal** dient nur den asynchronen Push-Updates.
- **Zentrale Zustandsquelle (Single Source of Truth):** Das Backend hält genau **einen**
  maßgeblichen Zustand der Anlage (Loks, Weichen, Rückmelder, Systemstatus) in der
  `domain`-Schicht. Dieser Zustand wird durch die eingehenden Z21-Broadcasts aktualisiert und
  speist **sowohl** die REST-Antworten **als auch** die Push-Events. REST-GET und Push liefern
  so immer denselben Zustand und können nicht auseinanderlaufen — kein zweiter, getrennter Pfad.
- Der Browser spricht ausschließlich mit der `api`-Schicht; die UDP-/Z21-Kommunikation bleibt
  vollständig im Backend.
- Fachcode nach Domäne gruppieren (Block, Rückmelder, Weiche, Zugfahrt), nicht nur nach Dateityp.

## UI-Architektur (Frontend)

Die Web-UI ist auf **Erweiterbarkeit** ausgelegt — eine App-Shell mit Navigation und je einem
Arbeitsbereich pro Route, sodass neue Bereiche ohne Umbau hinzukommen.

- **App-Shell (`App.vue`):** Kopfzeile mit Navigation und **globaler** Verbindungsanzeige;
  startet den zentralen Store **einmal** und teilt ihn mit allen Seiten.
- **Routen/Views (ein Bereich = eine Route):**
  - `/` **Dashboard** (Startseite): Zentralenstatus (SystemState), Verbindung, Track-Power —
    die anlagenweiten Infos.
  - `/throttle` **Lokführerstand** (Fahren/Funktionen).
  - `/track-plan` **Gleisplan-Anzeige** und `/track-edit` **Gleisplan-Modellierung** — aktuell
    Platzhalter (`ComingSoon`), als Zielstruktur bereits in der Navigation sichtbar.
- **Neuen Bereich hinzufügen:** View unter `views/` anlegen, Route im `router/` registrieren,
  Navigationslink in der Shell ergänzen. Gemeinsamer Zustand kommt aus dem Store.
- **Store** (`stores/`) spiegelt den maßgeblichen Backend-Zustand und lädt ihn bei SSE-Signalen
  frisch nach — die Single Source of Truth bleibt das Backend.

## Konfiguration und Assets

- **Konfiguration** (umgebungs-/anlagenabhängige Werte wie **Z21-IP-Adresse**, Ports,
  Keep-Alive-Intervall, Log-Level) liegt in **`conf/config.toml`** (Format **TOML**, geladen
  über `src/modellbahn/config.py`). Vorlage: `conf/config.example.toml` (eingecheckt);
  `conf/config.toml` ist lokal und von git ignoriert.
- **Präzedenz:** Umgebungsvariablen mit Präfix `MB_` > `conf/config.toml` > Defaults. Die
  TOML-Schlüssel entsprechen 1:1 den Einstellungsnamen (flach, z. B. `z21_host`, `log_level`).
- **Keine Geheimnisse** in das Repo committen; `.env`- und `conf/config.toml`-Dateien sind in
  `.gitignore`.
- **Statische Assets** der Web-UI (Icons, Grafiken, CSS) unter `frontend/assets/` ablegen,
  getrennt vom Backend-Code.

## Konventionen

- Build-, Lint- und Projektkonfiguration (`pyproject.toml`) im Wurzelverzeichnis ablegen.
- Laufzeitkonfiguration unter `conf/`, statische UI-Assets unter `frontend/assets/`.
- Tests unter `tests/` an der `src/`-Struktur ausrichten.
- Referenzdokumente unter `external_docs/` belassen und nicht mit Quellcode vermischen.
- Die Dokumente unter `.kiro/steering/` aktuell halten und bei Struktur-/Stack-Änderungen
  nachführen.

## Noch zu definieren

- Interner Aufbau von `frontend/src/` (Komponenten, Views, State-Management, API-Client).
- Ob das Backend als installierbares Paket (`src/`-Layout) oder flacher aufgebaut wird.
