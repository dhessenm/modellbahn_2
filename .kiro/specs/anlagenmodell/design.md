# Design — Statisches Anlagenmodell (Stufe 1)

> Technischer Entwurf zu `requirements.md`. Entscheidet die dort gesammelten offenen Punkte mit
> Begründung und beschreibt Datenmodell, Persistenz, API, Frontend und Teststrategie. Fügt sich
> in die bestehende Schichtung ein (`z21` → `domain` → `api`, Abhängigkeiten nach innen) und das
> Single-Source-of-Truth-Muster (Controller hält Zustand, `on_change` → `EventBroker` → SSE).

## 1. Leitgedanken und Einordnung

Das statische Anlagenmodell ist **neu** gegenüber dem Bestand: Bisher spiegelt das Backend nur
den Live-Zustand der Z21 (`LayoutState`: Loks, Weichen, Melder, System). Das Modell ist dagegen
**persistent** und wird vom Anwender gepflegt, nicht von der Zentrale.

Zwei Zustandswelten bleiben strikt getrennt:

- **Statisches Modell (`Layout`)** — persistent, vom Anwender editiert: Blöcke, Topologie-
  Elemente, Melder-Zuordnungen, Fahrstraßen.
- **Live-Zustand (`LayoutState`)** — flüchtig, aus Z21-Broadcasts: Belegung, Weichenstellung,
  System. Bereits vorhanden.

Der **abgeleitete Blockzustand** (Anforderung 5) ist die einzige Verbindung: eine reine Funktion
`(Layout, LayoutState) → BlockRuntime[]`, read-only, nicht persistiert.

**Grundprinzip „Belegung vor Identität"** (Requirements): Belegung = ODER über alle zugeordneten
Melder; Identität = Menge der RailCom-Loks. Sicherheit (spätere Stufen) nur über Belegung.

## 2. Entscheidungen zu den offenen Design-Punkten

| # | Punkt | Entscheidung | Begründung |
|---|-------|--------------|------------|
| D1 | Längeneinheit | mm als `int`, überall intern/API/Persistenz | Requirements; keine Float-Fehler. |
| D2 | Persistenzformat | JSON | Requirements; verschachtelungsfreundlich, maschinengeschrieben. |
| D3 | Ablageort | `conf/layout.json` (konfigurierbar via `MB_layout_path`) | Neben bestehender `conf/`-Konvention; getrennt von `config.toml`. |
| D4 | Atomares Schreiben | Temp-Datei im selben Verzeichnis + `os.replace` | `os.replace` ist atomar auf einem Dateisystem; kein halber Stand. |
| D5 | Backups | `conf/layout-backups/layout-<UTC-ISO>.json`, Rotation auf N=10 | Zeitstempel sortierbar; feste Obergrenze. N via Setting. |
| D6 | Schema-Versionierung | Top-Level-Feld `"version": 1` | Erlaubt spätere Migrationen ohne Rätselraten. |
| D7 | ID-Vergabe | UUID4 als String, bei Erzeugung im Backend | Stabil, kollisionsfrei, unabhängig vom (änderbaren) Namen. |
| D8 | Namenseindeutigkeit | **getrennt je Entitätstyp** (Blöcke untereinander, Elemente untereinander, Fahrstraßen untereinander); Vergleich case-insensitive nach `strip()` | „Bahnhof 1" als Block und als Fahrstraße ist unproblematisch; Tippfehler-Dubletten innerhalb eines Typs werden verhindert. |
| D9 | DKW-Repräsentation | **eigener Elementtyp** mit **zwei** Zubehöradressen und Zustands-Enum (4 Zustände) | Hält DKW als eine Einheit; Fahrstraße referenziert ein Element + einen Zustand, nicht zwei lose Weichen. |
| D10 | Starre Kreuzung | eigener Typ ohne Adresse; nur als beanspruchte Ressource referenzierbar | Vollständige Topologie (Option b), kein Schaltbefehl, kein Pflicht-Adressfeld. |
| D11 | Melder-RailCom-Fähigkeit | **zur Laufzeit erkannt** (aus `DetectorInput.locos`), nicht im Modell vermerkt | Weniger Pflegeaufwand, keine veraltbare Konfiguration; die Fähigkeit ergibt sich aus den Live-Daten. |
| D12 | Löschsemantik | **harte Ablehnung** bei bestehenden Referenzen (409); die Antwort **benennt die blockierenden Referenzen konkret** (Typ, ID, Name), die UI zeigt sie an | „Sicherheit vor Komfort"; kein stilles Kaskadenlöschen. Anwender sieht genau, was zuerst aufzulösen ist. |
| D13 | Markierungs-Modell | `union`-Typ je (Block, Richtung): entweder `detector_ref` **oder** `position_mm` | Deckt beide Requirement-Varianten einheitlich ab; nur Datenhaltung in Stufe 1. |
| D14 | Konsistenz Längen | **Warnungen**, kein harter Fehler (außer negativ/overflow) | Teilkonfigurierte Modelle müssen speicherbar bleiben; Summe≠Blocklänge ist Hinweis, kein Verbot. |
| D15 | Initial-Einlesen | beim Start vorhandene Abfrage nutzen; Block-UI nutzt bestehenden `POST /api/detectors/refresh` | Kein neuer Mechanismus; Blockzustand speist sich aus denselben `detectors`. |

## 3. Datenmodell (`domain`)

Neues Modul `src/modellbahn/domain/layout.py` (statisches Modell, getrennt von `state.py`). Reine
Dataclasses, keine FastAPI-/IO-Abhängigkeit. Alle Längen `int` (mm).

```python
# Topologie-Elemente
class ElementType(str, Enum):
    TURNOUT = "turnout"       # Weiche: 1 Adresse, Stellung 0/1
    CROSSING_SWITCH = "dkw"   # Doppelkreuzungsweiche: 2 Adressen, 4 Zustände
    CROSSING = "crossing"     # starre Kreuzung: keine Adresse

@dataclass
class TopologyElement:
    id: str                       # UUID4
    name: str                     # eindeutig je Typgruppe
    type: ElementType
    address: int | None = None        # Weiche
    address_b: int | None = None      # nur DKW (zweite Zubehöradresse)

@dataclass
class DetectorAssignment:
    detector_nid: int             # verweist auf DetectorInput-Identität (nid, port)
    detector_port: int
    order: int                    # Anordnung im Block, eindeutig je Block
    length_mm: int | None = None  # Teillänge nur innerhalb dieses Blocks

# Markierung je Richtung: entweder Melderbezug ODER virtuelle mm-Position
@dataclass
class Marker:
    detector_ref: tuple[int, int] | None = None   # (nid, port)
    position_mm: int | None = None                # ab Blockanfang
    # genau eines von beiden gesetzt (Validierung)

@dataclass
class DirectionMarkers:
    stop: Marker | None = None
    brake: Marker | None = None

@dataclass
class Block:
    id: str
    name: str                                   # eindeutig unter Blöcken
    length_mm: int | None = None
    max_speed_kmh: int | None = None            # Vorbildgeschwindigkeit
    detectors: list[DetectorAssignment] = field(default_factory=list)
    markers_forward: DirectionMarkers = field(default_factory=DirectionMarkers)
    markers_backward: DirectionMarkers = field(default_factory=DirectionMarkers)

# Fahrstraße: Weg + Soll-Stellungen + beanspruchte Elemente
@dataclass
class ElementSetting:
    element_id: str               # schaltbares Element
    desired_state: int            # Weiche: 0/1; DKW: 0..3

@dataclass
class Route:
    id: str
    name: str
    start_block_id: str
    transit_block_ids: list[str] = field(default_factory=list)
    end_block_id: str = ""
    element_settings: list[ElementSetting] = field(default_factory=list)
    claimed_element_ids: list[str] = field(default_factory=list)  # inkl. starre Kreuzungen

@dataclass
class Layout:
    version: int = 1
    blocks: dict[str, Block] = field(default_factory=dict)
    elements: dict[str, TopologyElement] = field(default_factory=dict)
    routes: dict[str, Route] = field(default_factory=dict)
```

Hinweis: Der Melderbezug nutzt `(nid, port)` — dieselbe stabile Identität wie `DetectorInput`.
Die Moduladresse `addr` ist bewusst **nicht** Schlüssel (kann 0 sein).

### 3.1 Modell-Service (Fachregeln)

`LayoutService` in `domain/layout_service.py` kapselt alle Mutationen und Validierungen; die API
delegiert nur. So bleibt die Fachlogik ohne FastAPI testbar (Anforderung 7.4).

Verantwortlichkeiten:
- CRUD für Block / Element / Route / Melder-Zuordnung.
- Validierung: Namenseindeutigkeit (D8), Referenz-Existenz, eindeutige `order` je Block,
  genau-eines-von (`detector_ref` xor `position_mm`), DKW-Zustand 0..3, Weiche 0/1,
  starre Kreuzung nur in `claimed_element_ids`, nicht in `element_settings` (Req. 4.6).
- Löschschutz (D12): Löschen abgelehnt, wenn referenziert; Rückgabe der blockierenden Referenzen
  als strukturierte Liste `(type, id, name)` — die API bildet sie auf `blocked_by` ab, die UI
  zeigt sie an. Beispiel-Blocker: ein Block ist in `start/transit/end` einer Fahrstraße; ein
  Element ist in `element_settings`/`claimed_element_ids` einer Fahrstraße.
- Konsistenz-Warnungen (D14): Summe Teillängen ≠ Blocklänge, Marke außerhalb der Blocklänge,
  Lücken/Überlappungen in der Anordnung — als Liste von Warnungen, kein Hard-Fail.
- Persistenz anstoßen nach erfolgreicher Mutation.

### 3.2 Abgeleiteter Blockzustand

Reine Funktion in `domain/block_runtime.py`:

```python
@dataclass
class BlockRuntime:
    block_id: str
    occupancy: Literal["free", "occupied", "unknown"]
    loco_addresses: list[int]          # Menge, aus RailCom; leer = unbekannt/keine

def derive_block_runtime(block: Block, state: LayoutState) -> BlockRuntime: ...
```

Regeln (Requirements Anf. 5): keine zugeordneten Melder → `unknown`; sonst `occupied`, wenn
mindestens ein zugeordneter Melder `occupied`; sonst `free`. `loco_addresses` = Vereinigung der
`DetectorInput.locos`-Adressen aller zugeordneten Melder (dedupliziert — löst D-Punkt
„Lok über mehrere Melder nur einmal zählen").

## 4. Persistenz (`domain/layout_store.py`)

- **Serialisierung:** `Layout` ↔ JSON über explizite `to_dict`/`from_dict` (kein Pickle, keine
  Fremdlib). Top-Level `{"version": 1, "blocks": [...], "elements": [...], "routes": [...]}`
  (Listen statt Dicts im JSON, Reihenfolge stabil; beim Laden nach ID indiziert).
- **Atomar (D4):** in `conf/.layout.json.tmp` schreiben, `fsync`, dann `os.replace` auf
  `conf/layout.json`.
- **Backup (D5):** vor dem `os.replace` die bestehende `layout.json` nach
  `conf/layout-backups/layout-<UTC-ISO>.json` kopieren; danach Verzeichnis auf die N neuesten
  rotieren (ältere löschen). N aus Settings (`layout_backup_count`, Default 10).
- **Laden:** fehlt die Datei → leeres `Layout`. Vorhanden, aber ungültig (JSON-/Schema-Fehler) →
  Exception, die den Start mit klarer Meldung abbricht (Anforderung 6.3). Validierung über
  `from_dict` + `LayoutService`-Konsistenzprüfung (nur harte Fehler brechen ab; Warnungen
  werden geloggt).
- **Konfiguration:** neue Settings in `config.py` (`layout_path`, `layout_backup_count`),
  Präzedenz `MB_*` > `config.toml` > Default, wie bestehend. `conf/layout.json` und
  `conf/layout-backups/` kommen in `.gitignore` (anlagenspezifisch, kein Repo-Inhalt);
  `conf/layout.example.json` wird als Vorlage eingecheckt.

## 5. API-Schicht (`api`)

Dünne Endpunkte, delegieren an `LayoutService`. Neues Routen-Modul, in `create_app` verdrahtet
(der Service wird wie `controller`/`broker` in `app.state` gehalten). Pydantic-Modelle in
`api/schemas.py` ergänzt. Mutationen lösen `broker.publish()` aus (SSE „changed"), damit die UI
sich aktualisiert — konsistent mit dem bestehenden Muster.

Routen (REST, Präfix `/api/layout`):

```
GET    /api/layout                      gesamtes Modell (blocks, elements, routes)
GET    /api/layout/runtime              abgeleitete Blockzustände (BlockRuntime[])

POST   /api/layout/blocks               Block anlegen
PUT    /api/layout/blocks/{id}          Block ändern (Name, Längen, Speed, Markierungen)
DELETE /api/layout/blocks/{id}          Block löschen (409 bei Referenzen)
PUT    /api/layout/blocks/{id}/detectors   Melder-Zuordnungen des Blocks setzen (Liste)

POST   /api/layout/elements             Element anlegen (Weiche/DKW/Kreuzung)
PUT    /api/layout/elements/{id}        Element ändern
DELETE /api/layout/elements/{id}        Element löschen (409 bei Referenzen)

POST   /api/layout/routes               Fahrstraße anlegen
PUT    /api/layout/routes/{id}          Fahrstraße ändern
DELETE /api/layout/routes/{id}          Fahrstraße löschen
```

Fehlerabbildung:
- Validierungsfehler (ungültige Referenz, doppelter Name, ungültiger Zustand) → `400`
  mit `{"detail": "..."}`.
- Löschen trotz Referenzen → `409`; die Antwort enthält die blockierenden Referenzen
  **strukturiert**, z. B. `{"detail": "...", "blocked_by": [{"type": "route", "id": "...",
  "name": "Einfahrt Gleis 2"}, ...]}`, damit die UI sie als klickbare/benannte Liste anzeigen
  kann (nicht nur generischer Text).
- Unbekannte ID → `404`.
- Konsistenz-**Warnungen** blockieren nicht; sie werden in der Antwort des jeweiligen
  Schreibzugriffs als `warnings: [...]` mitgeliefert, damit die UI sie anzeigen kann.

`GET /api/layout/runtime` kombiniert `Layout` (Service) und `LayoutState` (Controller) über
`derive_block_runtime`. Latenzunkritisch, getrennt vom Steuer-Pfad (Anforderung 7.5).

## 6. Frontend (`frontend/src`)

Neuer Arbeitsbereich, konsistent mit `structure.md` (eine Route je Bereich, App-Shell-Navigation).

- **Route/View:** `/layout` → `views/LayoutView.vue` („Anlage"), Navigationslink in der Shell.
- **Store:** `stores/layout.ts` — lädt `/api/layout` und `/api/layout/runtime`, bietet CRUD-
  Aktionen (REST), abonniert das bestehende SSE-Signal und lädt bei „changed" den Runtime-Zustand
  neu (Single Source of Truth bleibt Backend).
- **Komponenten (schema-/listenartig, kein Gleisbild):**
  - `BlockList.vue` — Blöcke als Kacheln/Liste mit abgeleitetem Zustand (frei/belegt/unbekannt,
    LED-Analog zur Melderanzeige) und RailCom-Loks; Editor-Dialog für Eigenschaften und
    Melder-Zuordnung (Reihenfolge, Teillänge).
  - `ElementList.vue` — Weichen/DKW/Kreuzungen mit Typ, Adresse(n).
  - `RouteList.vue` — Fahrstraßen als Text: Start → [Zwischenblöcke] → Ziel, Element-Stellungen,
    beanspruchte Elemente.
- **Längeneinheit (D1):** interne/Transport-Einheit mm; UI-Anzeige-Einheit (mm/cm/Zoll) zentral
  konfigurierbar (z. B. im Store/Settings), Umrechnung nur an der UI-Kante; nicht-metrisch wird
  beim Senden auf ganze mm gerundet und die Rundung sichtbar gemacht.
- **Fehler/Warnungen:** API-`400/404` als verständliche Meldung; `409` zeigt die
  `blocked_by`-Referenzen (Typ + Name) als Liste an, damit der Anwender sieht, welche Fahrstraßen/
  Zuordnungen er zuerst auflösen muss; `warnings` aus Schreibantworten als nicht-blockierende
  Hinweise.

## 7. Teststrategie

Backend (`pytest`), spiegelt `src`-Struktur:
- `domain`: CRUD + Validierung (Namenseindeutigkeit, Referenzen, `order`-Eindeutigkeit,
  Marker-xor, DKW/Weichen-Zustände, Löschschutz), Konsistenz-Warnungen.
- `block_runtime`: `unknown` ohne Melder, `occupied`/`free`-Aggregation, Lok-Mengen-Dedup
  („belegt ohne Identität", „mehrere Loks").
- `layout_store`: Speichern→Laden-Rundlauf; fehlende Datei → leer; ungültige Datei → Fehler;
  atomares Schreiben; Backup-Erzeugung und Rotation auf N.
- `api`: FastAPI-TestClient — Erfolg und Ablehnung (400/404/409), `warnings`-Durchreichung,
  `runtime`-Endpunkt gegen gesetzten `LayoutState`.

Frontend:
- Vitest/Component: `BlockList`/`RouteList` rendern Zustände/Fehler; Einheiten-Umrechnung
  (inkl. Zoll-Rundung).
- Playwright (API gemockt): Grundpfad Block anlegen → Melder zuordnen → Fahrstraße anlegen →
  Runtime-Zustand sichtbar.

Qualität: `ruff`, `mypy`, `eslint`/`oxlint`/`vue-tsc` sauber; CI grün (Anforderung 9).

## 8. Auswirkungen auf den Bestand

- **Neu:** `domain/layout.py`, `domain/layout_service.py`, `domain/layout_store.py`,
  `domain/block_runtime.py`; API-Routenmodul + Schemas; Frontend-View/Store/Komponenten.
- **Geändert (additiv):** `config.py` (neue Settings), `api/app.py` (Service verdrahten, Routen
  registrieren, `app.state.layout_service`), Frontend-Router + Navigation, `.gitignore`,
  `conf/layout.example.json`.
- **Unberührt:** `z21`-Schicht, bestehende Steuer-/Melder-Pfade. Kein Eingriff in den
  latenzkritischen Pfad. `LayoutState` wird nur **gelesen** (für `runtime`).

## 9. Bewusste Nicht-Ziele (Stufe 1)

Keine Automatik, keine Verriegelung/Reservierung, kein Stellen von Fahrstraßen, kein Routing,
keine Zug-/Lok-Objekte/Einmessung, keine Maßstabsumrechnung, kein gezeichnetes Gleisbild, keine
blockübergreifende Zugverfolgung, keine Recovery-UI. Das Modell ist jedoch so angelegt, dass
diese Stufen additiv darauf aufsetzen können (Element-Zustände, beanspruchte Ressourcen,
Markierungen, mm-Geometrie sind bereits vorhanden).
```