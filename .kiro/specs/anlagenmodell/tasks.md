# Aufgaben — Statisches Anlagenmodell (Stufe 1)

> Umsetzungsplan zu `requirements.md` und `design.md`. Reihenfolge: `domain`-Fundament → API →
> Frontend → Konfiguration/Doku. Jede Aufgabe ist inkrementell, test-getrieben und schließt mit
> grünen Prüfungen ab. Nummern in Klammern verweisen auf Akzeptanzkriterien der Requirements.
>
> Konventionen (gemäß `tech.md`/`structure.md`): Längen intern mm (`int`); `domain` ohne FastAPI/
> UDP; Abhängigkeiten nach innen; Backend-Tests `pytest`, Lint `ruff`, Typen `mypy`; Frontend
> `vitest`/`playwright`, `eslint`/`oxlint`/`vue-tsc`. Nach Backend-Codeänderung Dev-Server
> stop+start (kein Auto-Reload).

## A. Domain-Fundament (Datenmodell, Service, Persistenz, Blockzustand)

- [x] 1. Datenmodell anlegen (`src/modellbahn/domain/layout.py`)
  - `ElementType`-Enum (`TURNOUT`, `CROSSING_SWITCH`/DKW, `CROSSING`) und Dataclasses
    `TopologyElement`, `DetectorAssignment`, `Marker`, `DirectionMarkers`, `Block`,
    `ElementSetting`, `Route`, `Layout` gemäß Design §3.
  - Alle Längenfelder `int | None` in mm; Markierung mit `detector_ref` **xor** `position_mm`.
  - Reine Dataclasses, keine IO-/FastAPI-Importe.
  - _Requirements: 1, 2.6/2.7, 3, 4; Design §3_

- [x] 2. Serialisierung `to_dict`/`from_dict` + Schema-Version (im selben Modul oder
    `layout_codec.py`)
  - Top-Level `{"version": 1, "blocks": [...], "elements": [...], "routes": [...]}` (Listen im
    JSON, beim Laden nach ID indiziert).
  - `from_dict` validiert Grundstruktur und Version; unbekannte/kaputte Struktur → klare
    Exception.
  - Tests: Round-Trip `Layout → dict → Layout` für alle Entitätstypen inkl. DKW (2 Adressen,
    Zustand), Markierungen beider Richtungen, Fahrstraße mit Zwischenblöcken.
  - _Requirements: 5 (DKW), 6.3; Design §4, D6/D9_

- [x] 3. `LayoutService` mit CRUD + Validierung (`src/modellbahn/domain/layout_service.py`)
  - CRUD für Block, Element, Route, Melder-Zuordnungen; IDs als UUID4 bei Erzeugung (D7).
  - Validierungen: Namenseindeutigkeit je Typ, case-insensitive nach `strip()` (D8);
    Referenz-Existenz (Fahrstraße→Blöcke/Elemente); `order` je Block eindeutig; Marker-xor;
    Weiche-Zustand 0/1, DKW 0..3; starre Kreuzung nur in `claimed_element_ids`, nicht in
    `element_settings` (Req. 4.6).
  - Löschschutz (D12): Löschen referenzierter Entitäten abgelehnt; liefert strukturierte
    Blocker-Liste `(type, id, name)`.
  - Fehler als eigene Domain-Exceptions (z. B. `ValidationError`, `ReferenceConflictError`), damit
    die API sie auf 400/409 abbilden kann — `domain` kennt kein HTTP.
  - Tests: je Regel ein Positiv- und ein Negativfall; Löschschutz mit konkreter Blocker-Liste.
  - _Requirements: 1.3/1.4, 2.2/2.7, 3.5/3.6, 4.2/4.6, 7.2/7.4; Design §3.1, D7/D8/D12_

- [x] 4. Konsistenz-Warnungen (im Service, nicht blockierend)
  - Prüfungen: Summe Teillängen ≠ Blocklänge; Marke außerhalb der Blocklänge; Lücken/
    Überlappungen in der Anordnung. Rückgabe als `list[str]`/strukturierte Warnungen (D14).
  - Hart bleibt nur Unsinniges (negative Länge, Overflow) → `ValidationError`.
  - Tests: Warnung erscheint, Speichern bleibt möglich; harter Fehler bei negativer Länge.
  - _Requirements: 1.9, 2.7; Design §3.1, D14_

- [x] 5. Persistenz `LayoutStore` (`src/modellbahn/domain/layout_store.py`)
  - `load(path) -> Layout` (fehlt → leeres `Layout`; ungültig → Exception) und
    `save(path, layout)`.
  - Atomar: Temp-Datei im Zielverzeichnis + `fsync` + `os.replace` (D4).
  - Backup vor Ersetzen: Kopie nach `conf/layout-backups/layout-<UTC-ISO>.json`, danach Rotation
    auf N neueste (D5).
  - Tests: Save→Load-Rundlauf; fehlende Datei → leer; korrupte Datei → Fehler; nach mehreren
    Saves genau N Backups, älteste entfernt; Temp-Datei bleibt nicht liegen.
  - _Requirements: 6.1–6.6; Design §4, D3/D4/D5_

- [x] 6. Abgeleiteter Blockzustand (`src/modellbahn/domain/block_runtime.py`)
  - `derive_block_runtime(block, state) -> BlockRuntime` und eine Hilfsfunktion über das ganze
    Layout. Regeln: keine Melder → `unknown`; sonst `occupied`, wenn ein zugeordneter Melder
    belegt; sonst `free`. `loco_addresses` = dedup. Vereinigung der RailCom-Loks (D-Punkt
    „einmal zählen").
  - Nutzt `(nid, port)` als Melderschlüssel gegen `LayoutState.detectors`; **nur lesend**.
  - Tests: `unknown` ohne Melder; `occupied`/`free`-Aggregation über mehrere Melder; „belegt ohne
    Identität"; mehrere Loks (Doppeltraktion) dedupliziert.
  - _Requirements: 4.1–4.4; Design §3.2_

- [x] 7. Qualität Domain abschließen
  - `ruff`, `mypy` sauber; alle neuen Tests grün (`pytest`). Nach Aufgabe 6: ruff/mypy strict
    sauber, pytest 164 passed. Domain-Fundament vollständig (layout, codec, service,
    consistency, store, block_runtime).
  - _Requirements: 9.1/9.2/9.5_

## B. API-Schicht

- [x] 8. Konfiguration erweitern (`src/modellbahn/config.py`)
  - Settings `layout_path` (Default `conf/layout.json`) und `layout_backup_count` (Default 10);
    Präzedenz `MB_*` > `config.toml` > Default.
  - `conf/layout.example.json` als Vorlage anlegen; `conf/layout.json` und
    `conf/layout-backups/` in `.gitignore`.
  - Tests: Settings-Defaults und Override via Env.
  - _Requirements: 6.5; Design §4_

- [x] 9. Pydantic-Schemas ergänzen (`src/modellbahn/api/schemas.py`)
  - Request/Response-Modelle für Block, Element (Weiche/DKW/Kreuzung), Melder-Zuordnung, Route,
    `BlockRuntime`; Schreibantworten mit optionalem `warnings`; 409-Body mit `blocked_by`
    (Liste `type/id/name`).
  - _Requirements: 7.1/7.2; Design §5, D12_

- [x] 10. Layout-Service verdrahten + Laden beim Start (`src/modellbahn/api/app.py`)
  - In `create_app`: `LayoutStore.load(settings.layout_path)` → `LayoutService`, in
    `app.state.layout_service`; nach Mutationen `save` + `broker.publish()`.
  - Ungültige Modelldatei bricht den Start mit klarer Meldung ab (Req. 6.3).
  - _Requirements: 6.1–6.4, 7.3/7.5; Design §4/§5_

- [x] 11. REST-Routen `/api/layout` (neues Routenmodul, in `app.py` registriert)
  - `GET /api/layout`, `GET /api/layout/runtime`; CRUD für blocks/elements/routes;
    `PUT .../blocks/{id}/detectors`.
  - Fehlerabbildung: Domain-Exceptions → 400 (Validierung), 404 (unbekannte ID), 409
    (`blocked_by`); `warnings` durchreichen. Dünne Delegation an den Service.
  - Mutationen latenzunkritisch, getrennt vom Steuer-Pfad.
  - Tests (FastAPI-TestClient): Happy-Path je Entität; 400 (doppelter Name, ungültige Referenz,
    ungültiger Zustand); 404; 409 mit `blocked_by`; `runtime` gegen gesetzten `LayoutState`;
    `warnings`-Durchreichung.
  - _Requirements: 7.1–7.5, 9.3; Design §5, D12/D14_

- [x] 12. Qualität API abschließen
  - `ruff`, `mypy` sauber; API-Tests grün. Nach Aufgabe 9-11: ruff/mypy strict sauber,
    pytest 182 passed. API-Schicht vollständig (schemas, layout_routes, app-Verdrahtung).
  - _Requirements: 9.1/9.3/9.5_

## C. Frontend

- [x] 13. API-Client + Typen (`frontend/src/api/`)
  - Funktionen für alle `/api/layout`-Routen; TypeScript-Typen zu den Schemas; Fehlerparsing
    (400/404/409 inkl. `blocked_by`, `warnings`).
  - _Requirements: 8.3/8.5; Design §6_

- [x] 14. Store (`frontend/src/stores/anlage.ts` — eigener Store, NICHT der bestehende layout.ts)
  - Lädt `/api/layout` + `/api/layout/runtime`; CRUD-Aktionen; abonniert bestehendes SSE und lädt
    bei „changed" den Runtime-Zustand neu. Einheiten-Konfiguration (mm/cm/Zoll) zentral; Umrechnung
    nur hier/an der UI-Kante, nicht-metrisch gerundet auf ganze mm.
  - Tests (Vitest): Laden, Mutationsaufruf, SSE-Refresh, Einheiten-Umrechnung inkl. Zoll-Rundung.
  - _Requirements: 8.4/8.5; Design §6, D1_

- [x] 15. View + Navigation (`frontend/src/views/LayoutView.vue`, Router, App-Shell)
  - Neue Route `/layout` („Anlage"), Navigationslink in der Shell; bestehende Bereiche unverändert.
  - _Requirements: 8.1; Design §6_

- [x] 16. Komponenten schema-/listenartig
  - `BlockList.vue` (Zustand frei/belegt/unbekannt + RailCom-Loks, Editor für Eigenschaften &
    Melder-Zuordnung mit Reihenfolge/Teillänge), `ElementList.vue` (Weiche/DKW/Kreuzung),
    `RouteList.vue` (Start → [Zwischen] → Ziel, Element-Stellungen, beanspruchte Elemente).
  - Kein gezeichnetes Gleisbild. Fehler (400/404) und 409-`blocked_by` als benannte Liste anzeigen;
    `warnings` als nicht-blockierende Hinweise.
  - Tests (Vitest/Component): Rendern der Zustände; Fehler-/Warnungsanzeige; 409-Blocker-Liste.
  - _Requirements: 8.2/8.3/8.4; Design §6, D12_

- [x] 17. E2E-Grundpfad (`frontend/e2e/`, API gemockt)
  - Block anlegen → Melder zuordnen → Element anlegen → Fahrstraße anlegen → Runtime-Zustand
    sichtbar; ein 409-Löschversuch zeigt die Blocker-Liste.
  - _Requirements: 9.4; Design §7_

- [x] 18. Qualität Frontend abschließen
  - `eslint`, `oxlint`, `vue-tsc`, `vitest`, Playwright grün; Produktions-Build ok. Verifiziert:
    build (inkl. vue-tsc) ok, vitest 43 passed (9 Dateien), playwright 6 passed.
  - _Requirements: 9.4/9.5_

## D. Abschluss: Konfiguration, Doku, Verifikation

- [ ] 19. Live-Verifikation gegen echte Z21 (Blockzustand)
  - Realen Melder einem Block zuordnen; Umschalten → Blockzustand/`runtime` live in der UI prüfen
    (nutzt bestehendes Initial-Einlesen/Refresh). Beobachtung dokumentieren.
  - _Requirements: 4.5/4.6; Design §5, D15_

- [x] 20. Doku und Steering nachführen
  - `NEXT.md` (Stufe 1 erledigt, nächster Schritt), ggf. `structure.md`/`tech.md` um das
    Anlagenmodell + Persistenz ergänzen; Terminologie konsistent zu `traincontroller-domaene.md`.
  - _Requirements: 9.6_

- [x] 21. CI prüfen und Stufe abschließen
  - Alles committen/pushen (deutsche Commit-Messages); CI grün (`gh run list`). Feature-Branch
    per Fast-Forward nach main gemergt (3503dbe), CI success, Worktree + Branch entfernt.
  - _Requirements: 9.5_
