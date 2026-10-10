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
├── src/
│   └── modellbahn/         # Python-Backend-Paket
│       ├── z21/            # Z21/UDP-Anbindung: Protokoll-Kodierung/-Dekodierung, Client
│       ├── domain/         # Fachlogik: Loks, Weichen, Rückmelder, Blöcke, Zugfahrten
│       ├── api/            # FastAPI-App: REST-Endpunkte + Push-Kanal (WebSocket/SSE)
│       └── main.py         # Einstiegspunkt (startet den FastAPI-Server)
├── frontend/               # Web-UI (Browser-Client); genaue Technik noch offen
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

## Konventionen

- Build-, Lint- und Projektkonfiguration (`pyproject.toml`) im Wurzelverzeichnis ablegen.
- Tests unter `tests/` an der `src/`-Struktur ausrichten.
- Referenzdokumente unter `external_docs/` belassen und nicht mit Quellcode vermischen.
- Die Dokumente unter `.kiro/steering/` aktuell halten und bei Struktur-/Stack-Änderungen
  nachführen.

## Noch zu definieren

- Konkrete Frontend-Technik und deren Verzeichnisaufbau unter `frontend/`.
- Ob das Backend als installierbares Paket (`src/`-Layout) oder flacher aufgebaut wird.
- Ablage von statischen Assets und Konfiguration (z. B. Verbindungsdaten der Zentrale).
