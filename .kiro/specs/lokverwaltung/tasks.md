# Aufgaben — Lokverwaltung

> Umsetzungsplan zu `requirements.md` und `design.md`. Reihenfolge: Backend-Domain → Backend-API
> → Frontend (Roster-Seite → Lokführerstand-Umbau → App-Shell-Statusleiste) → Abschluss.
> Jede Aufgabe ist inkrementell, test-getrieben und schließt mit grünen Prüfungen ab.
>
> Konventionen wie beim Anlagenmodell: Längen intern mm (`int`); `domain` ohne FastAPI/UDP;
> Backend `pytest`/`ruff`/`mypy`; Frontend `vitest`/`playwright`/`eslint`/`oxlint`/`vue-tsc`.
> Feature-Branch `feature/lokverwaltung` (Worktree `.worktrees/lokverwaltung`).

## A. Backend-Domain (Datenmodell, Serialisierung, Service, Persistenz)

- [x] 1. Datenmodell (`src/modellbahn/domain/roster.py`)
  - `Locomotive` (id, name, address, speed_steps=128, function_count=28, length_mm, max_speed_kmh,
    notes) und `Roster` (version=1, locomotives dict) als reine Dataclasses.
  - Keine IO, keine FastAPI. Stil wie `layout.py`.
  - _Requirements: 1.1/1.2; Design §2_

- [x] 2. Serialisierung (`src/modellbahn/domain/roster_codec.py`)
  - `to_dict`/`from_dict`, `RosterDecodeError`, Schema-Version.
  - Top-Level: `{"version": 1, "locomotives": [...]}`.
  - Tests: Round-Trip, Enum/Defaults, Version-Fehler, kaputter Input.
  - _Requirements: 1.5; Design §3_

- [x] 3. Service (`src/modellbahn/domain/roster_service.py`)
  - `RosterService`: CRUD, UUID4-IDs, Validierung (Name eindeutig case-insensitive/strip,
    Adresse 1–9999, speed_steps ∈ {14,28,128}, function_count 0–28, length_mm/max_speed_kmh ≥ 0).
  - `RosterValidationError` (analog `LayoutValidationError`).
  - Adress-Duplikat-Warnung (weich): code `adresse_doppelt`, Rückgabe als strukturierte Info.
  - Löschen immer erlaubt (keine Referenzen in Stufe 1).
  - Tests: je Regel Positiv/Negativ, Warnung bei Adress-Duplikat.
  - _Requirements: 1.2/1.3, 2.1/2.2; Design §4_

- [x] 4. Persistenz (`src/modellbahn/domain/roster_store.py`)
  - `load`/`save` analog zu `layout_store.py`: atomar (Temp + fsync + os.replace), Backups
    (Rotation auf N), fehlende Datei → leeres Roster, kaputte Datei → Exception.
  - Tests: Save→Load, fehlende/korrupte Datei, Backups.
  - _Requirements: 1.4/1.5; Design §5_

- [x] 5. Konfiguration + Vorlage
  - `config.py`: `roster_path` (Default `conf/roster.json`), `roster_backup_count` (Default 10).
  - `conf/roster.example.json` anlegen; `conf/roster.json` + `conf/roster-backups/` in
    `.gitignore`.
  - Tests: Settings-Defaults und Env-Override.
  - _Design §5_

- [x] 6. Fahrstufenmodus in `build_loco_drive` (`z21/protocol.py`)
  - Neuer Parameter `speed_steps: int = 128`. DB0: `0x10` (14), `0x12` (28), `0x13` (128).
    Speed-Kodierung je Modus. Controller + API-Route + Schema durchgereicht.
  - Tests: build_loco_drive mit 14/28/128, bestehende Tests grün.
  - _Requirements: 4.5; Design §7_

- [x] 7. Qualität Backend abschließen
  - ruff, mypy sauber; 250 Tests grün (Baseline 182, +68).
  - _Requirements: 5.1/5.2/5.5_

## B. Backend-API

- [x] 8. Roster-Schemas + Routen + Verdrahtung
  - Pydantic-Schemas: `LocoRequest`, `LocoResponse`, `RosterResponse`, `LocoWriteResponse`
    (entity + warnings).
  - Routenmodul `api/roster_routes.py` (`APIRouter`, Präfix `/api/roster`): GET (alle + einzeln),
    POST, PUT, DELETE; Fehler 400/404; `warnings` bei Adress-Duplikat.
  - `app.py`: RosterService verdrahten (load beim Start, save + publish nach Mutation).
  - Kaputte Roster-Datei bricht Start ab (wie Layout).
  - Tests (TestClient): CRUD happy-path, 400 (Name/Adresse/speed_steps), 404, Warnung
    (Adress-Duplikat), Start-Abbruch bei kaputter Datei.
  - _Requirements: 2.1–2.5; Design §6_

- [x] 9. Qualität API abschließen
  - `ruff`, `mypy`, API-Tests grün.
  - _Requirements: 5.3/5.5_

## C. Frontend — Lokverwaltung (neue Seite)

- [x] 10. API-Client + Typen (Roster-Erweiterung)
  - `api/client.ts`: Roster-Methoden (getRoster, createLoco, updateLoco, deleteLoco).
  - `api/types.ts` oder `api/roster-types.ts`: TS-Typen für Locomotive, RosterResponse,
    LocoWriteResponse, Warnung.
  - _Requirements: 3; Design §8.1_

- [x] 11. Store + View + Komponente
  - `stores/roster.ts` (`useRosterStore`): Refs, CRUD-Aktionen, SSE-Abo.
  - `views/RosterView.vue`, `components/RosterList.vue`: Lok-Liste, Anlegen/Bearbeiten/Löschen,
    Adress-Warnung als Hinweis, Länge in Anzeige-Einheit.
  - Route `/roster` in `router/index.ts`, Nav-Link „Lokomotiven" in `App.vue`.
  - Tests (Vitest): RosterList rendern, Anlegen, Fehler/Warnung.
  - _Requirements: 3.1–3.4; Design §8.1_

## D. Frontend — Lokführerstand-Umbau

- [x] 12. LocoThrottle vertikal + maxSpeed
  - Neuer Prop `maxSpeed` (Default 126). Slider vertikal (CSS), min unten, max oben.
  - Tests: Rendern vertikal, maxSpeed-Prop begrenzt Bereich.
  - _Requirements: 4.5/4.8; Design §8.2_

- [x] 13. CabView-Umbau
  - Adressfeld → `<select>` aus Roster-Store (Name + Adresse); bei Auswahl: DCC-Adresse,
    speed_steps, function_count übernehmen.
  - `LocoThrottle` bekommt `maxSpeed` passend zum Fahrstufenmodus (14→14, 28→28, 128→126).
  - `FunctionButtons` bekommt `count = function_count + 1`.
  - `LocoInfoFrame` in `<details>` gewrappt (Default eingeklappt).
  - `TrackPower` entfernt (wandert in Statusleiste, Aufgabe 15).
  - Hinweis bei leerer Lok-Bibliothek.
  - Tests (Vitest): Select statt Input, Funktionsanzahl angepasst, Hinweis bei leer.
  - _Requirements: 4.1–4.7/4.9; Design §8.2_

## E. Frontend — App-Shell-Statusleiste

- [x] 14. ConnectionStatus → LED only
  - Props reduziert auf `connected: boolean`. Runde LED (grün/grau), kein Text. Tooltip mit
    Verbindungsinfo (host:port) bei Hover.
  - Tests: LED-Klasse bei connected/disconnected, kein Text-Element.
  - _Requirements: 6.2; Design §8.3_

- [x] 15. App-Shell-Kopfzeile: Statusleiste mit LED + TrackPower
  - `App.vue`: LED links, Navigation Mitte, TrackPower rechts. Kompakt (≤ 48px).
  - TrackPower: evtl. kompaktere Variante (LED + Toggle statt zwei Buttons).
  - `DashboardView`: TrackPower-Schalter entfernt (Status bleibt als Teil von SystemState).
  - Tests: E2E — LED + TrackPower auf mehreren Seiten sichtbar.
  - _Requirements: 6.1/6.3/6.4/6.5; Design §8.3, D7/D8_

## F. Frontend-Qualität + E2E

- [x] 16. E2E-Grundpfad (Playwright)
  - Lok anlegen (Roster-Seite) → im Lokführerstand auswählen → Slider/Funktionen passen sich an
    Fahrstufenmodus/Funktionsanzahl an; Statusleiste LED + TrackPower auf mehreren Seiten.
  - _Requirements: 5.4; Design §9_

- [x] 17. Qualität Frontend abschließen
  - `eslint`, `oxlint`, `vue-tsc`, `vitest`, Playwright grün; Produktions-Build ok.
  - _Requirements: 5.5_

## G. Abschluss

- [ ] 18. Live-Verifikation
  - Backend + Frontend starten, Lok anlegen (Test-Lok Adresse 3), im Lokführerstand auswählen,
    Fahren testen (vertikaler Slider, richtige Fahrstufenanzahl, Funktionen). Statusleiste:
    LED + TrackPower auf allen Seiten sichtbar.
  - _Requirements: alle_

- [x] 19. Doku nachführen
  - `NEXT.md` aktualisiert (Lokverwaltung + Lokführerstand-Umbau als Stand).
  - _Requirements: 5.6_

- [x] 20. CI prüfen und Feature abschließen
  - Nach main gemergt (afdeaab, Fast-Forward), CI grün, Worktree + Branch entfernt.
  - _Requirements: 5.5_
