# Design — Lokverwaltung

> Technischer Entwurf zu `requirements.md`. Entscheidet die offenen Punkte mit Begründung und
> beschreibt Datenmodell, Persistenz, API, Frontend (Lokverwaltung + Lokführerstand-Umbau +
> App-Shell-Statusleiste). Fügt sich in die bestehende Architektur ein.

## 1. Entscheidungstabelle

| # | Punkt | Entscheidung | Begründung |
|---|-------|--------------|------------|
| D1 | Persistenz-Ort | `conf/roster.json` (eigene Datei) | Requirements; getrennt vom Anlagenmodell, modularisierbar. |
| D2 | Domain-Platzierung | `domain/roster.py` (Modell) + `domain/roster_service.py` (Service) | Lok ist eigenständiges Domänenkonzept, nicht Teil der Topologie. |
| D3 | API-Präfix | `/api/roster` | Requirements; kurz, kollidiert nicht mit `/api/locos/{address}`. |
| D4 | Lok ↔ LocoState | reine Trennung; Stammdaten und Live-Zustand unabhängig | Requirements; Lokführerstand nimmt DCC-Adresse aus Stammdaten. |
| D5 | Dropdown | `<select>` | Requirements; Liste wird nicht lang genug für Autocomplete. |
| D6 | Fahrstufenmodus | Fahrregler passt Bereich an (14/28/128); Backend `build_loco_drive` parametrisiert; Default 128 | Requirements; Protokoll: DB0 = `0x10` (14), `0x12` (28), `0x13` (128). |
| D7 | Statusleisten-Layout | globale Leiste **integriert in die bestehende Kopfzeile** (`.app-header`): LED links, Navigation Mitte, TrackPower rechts | Kompakt, kein zusätzlicher Streifen; Mobile-tauglich. |
| D8 | TrackPower in CabView/Dashboard | **entfernen** aus CabView; im Dashboard bleibt die Anzeige (nur Status, kein Schalter) | Der globale Schalter ist auf jeder Seite da; Duplikat in CabView ist überflüssig. Dashboard zeigt weiterhin den Systemstatus inkl. TrackPower-Zustand als Info (read-only). |
| D9 | ID-Vergabe | UUID4 hex (wie Blöcke/Elemente) | Konsistent zum Anlagenmodell. |
| D10 | Persistenz-Mechanik | Wiederverwendung von `layout_store.load`/`save` (die sind generisch: dict→JSON atomar + Backup) | Kein doppelter Code; nur ein eigener `roster_codec.py` für die Roster-Serialisierung. |
| D11 | Vertikaler Slider | CSS `writing-mode: vertical-lr` + `direction: rtl` ODER `appearance: slider-vertical` + `transform` | Cross-Browser; Design entscheidet Implementierung in der Komponente. |

## 2. Datenmodell (`domain/roster.py`)

Neues Modul `src/modellbahn/domain/roster.py`. Reine Dataclasses, konsistent mit `layout.py`.

```python
@dataclass
class Locomotive:
    id: str                           # UUID4 hex
    name: str                         # eindeutig (case-insensitive, strip)
    address: int                      # DCC-Adresse 1..9999
    speed_steps: int = 128            # 14, 28 oder 128
    function_count: int = 28          # 0..28 (F0 bis Fn)
    length_mm: int | None = None      # Modellmaßstab, ganze mm
    max_speed_kmh: int | None = None  # Vorbild-Höchstgeschwindigkeit
    notes: str = ""                   # Freitext

@dataclass
class Roster:
    version: int = 1
    locomotives: dict[str, Locomotive] = field(default_factory=dict)
```

## 3. Serialisierung (`domain/roster_codec.py`)

Analog zu `layout_codec.py`: `to_dict(roster) → dict`, `from_dict(dict) → Roster`,
`RosterDecodeError`. Top-Level: `{"version": 1, "locomotives": [...]}`. Nutzt denselben
Stil (explizite Konvertierung, Schema-Version, deutsche Fehler).

## 4. Service (`domain/roster_service.py`)

`RosterService` kapselt ein `Roster`. Analog zu `LayoutService`:

- **CRUD:** `create_locomotive(name, address, ...)` → UUID4-ID; `update_locomotive(id, ...)`; `delete_locomotive(id)`; `get_locomotive(id)`; `list_locomotives()`.
- **Validierung (hart):** Name Pflicht + eindeutig (case-insensitive/strip); Adresse 1–9999; speed_steps ∈ {14, 28, 128}; function_count 0–28; length_mm ≥ 0 (wenn gesetzt); max_speed_kmh ≥ 0 (wenn gesetzt). → `RosterValidationError`.
- **Warnung (weich):** Adresse bereits einer anderen Lok zugeordnet → `AddressDuplicateWarning` als strukturierte Info (code + message), nicht als harter Fehler. Rückgabe über eine Methode `address_warnings(locomotive_id)` oder direkt als Liste bei Create/Update (analog zu `block_warnings`).
- **Löschschutz:** In Stufe 1 keine Referenzen auf Loks (keine Zug-Objekte), daher **immer löschbar**. Wenn später Züge auf Loks verweisen, wird der Schutz ergänzt.

Eigene Exceptions: `RosterValidationError(ValueError)` — analog zu `LayoutValidationError`, kein HTTP-Bezug.

## 5. Persistenz

Wiederverwendung von `layout_store.load`/`save` (D10). Diese Funktionen sind generisch:
`load(path)` liest JSON + `from_dict`, `save(path, ...)` schreibt atomar + Backup. Damit:

- `roster_store.py`: dünner Wrapper, der `layout_store.load`/`save` mit `roster_codec.to_dict`/`from_dict` verbindet (alternativ: die bestehenden `load`/`save` direkt nutzen, da sie nur `to_dict`/`from_dict` + JSON-Layer machen — prüfe, ob ein generischer Store sinnvoll ist oder ob ein eigenes kleines `roster_store.py` sauberer bleibt). Der bestehende `layout_store` ist aktuell auf `layout_codec` hartcodiert (importiert `from_dict`/`to_dict` direkt). Daher: eigenes **`roster_store.py`** mit derselben Mechanik (atomar, Backup, Rotation), das `roster_codec` nutzt. Codeduplikation ist minimal (die Kern-Logik — atomar schreiben, Backup, Rotation — könnte man extrahieren, aber für zwei Stores ist Copy+Adapt pragmatischer als eine generische Abstraktion).

- `conf/roster.json` (git-ignoriert), `conf/roster-backups/` (Rotation N aus Settings).
- `conf/roster.example.json` als eingecheckte Vorlage.
- `config.py`: neue Settings `roster_path` (Default `conf/roster.json`), `roster_backup_count` (Default 10).

## 6. API (`/api/roster`)

Neues Routenmodul `api/roster_routes.py`, als `APIRouter` (wie `layout_routes.py`). In
`create_app` verdrahtet: `roster_store.load(settings.roster_path)` → `RosterService` → `app.state.roster_service`. Mutationen: save + `broker.publish()`.

Routen:
```
GET    /api/roster                  -> { locomotives: [LocoResponse] }
GET    /api/roster/{id}             -> LocoResponse (404 wenn unbekannt)
POST   /api/roster                  -> 201 { entity: LocoResponse, warnings: [...] }
PUT    /api/roster/{id}             -> 200 { entity: LocoResponse, warnings: [...] }
DELETE /api/roster/{id}             -> 204 (404 wenn unbekannt)
```

Fehlerabbildung: `RosterValidationError` → 400; unbekannte ID → 404.
Schreibantworten als Wrapper `{entity, warnings}` (wie Block-Schreibantworten). `warnings`
enthält die Adress-Duplikat-Warnung (code `adresse_doppelt`, message mit Name der Kollisions-Lok).

## 7. Backend: Fahrstufenmodus in `build_loco_drive`

Aktuell ist `build_loco_drive` auf 128 Fahrstufen hardcoded (DB0 = `0x13`). Erweiterung:

```python
def build_loco_drive(address: int, speed: int, forward: bool, speed_steps: int = 128) -> bytes:
    # DB0: 0x10 = 14 Stufen, 0x12 = 28 Stufen, 0x13 = 128 Stufen
    # Geschwindigkeitskodierung je nach Modus (Formel im Z21-Protokoll)
```

Der Controller (`LocoController.drive`) reicht `speed_steps` durch. Die CabView übergibt den
Fahrstufenmodus der gewählten verwalteten Lok. Bestehendes Verhalten (Default 128) bleibt
abwärtskompatibel.

Speed-Bereiche:
- 128 Stufen: 0–126 (0 = Stop, 1 = Nothalt reserviert, 2–127 = Fahrstufen 1–126)
- 28 Stufen: 0–28 (0 = Stop, 1 = Nothalt reserviert, 2–29 = Fahrstufen 1–28)
- 14 Stufen: 0–14 (0 = Stop, 1 = Nothalt reserviert, 2–15 = Fahrstufen 1–14)

Der Fahrregler (LocoThrottle) bekommt den max-Wert als Prop: 126 / 28 / 14 je nach Modus.

## 8. Frontend

### 8.1 Lokverwaltung — neue Seite

- **Route:** `/roster` (name `roster`), lazy import, Navigationslink „Lokomotiven" in der
  App-Shell (nach „Anlage").
- **View:** `views/RosterView.vue` — bindet `RosterList.vue` ein.
- **Store:** `stores/roster.ts` (`useRosterStore`) — analoges Composable zu `anlage.ts`:
  Refs für `locomotives`, CRUD-Aktionen, SSE-Abo bei Mounten der View. Nutzt den bestehenden
  `api`-Client (erweitert um Roster-Methoden).
- **Komponente:** `components/RosterList.vue` — Lok-Liste mit Stammdaten, Anlegen/Bearbeiten/
  Löschen. Adress-Warnung (Duplikat) als Hinweis. Länge in Anzeige-Einheit (mm/cm/Zoll via
  `length-units.ts`).

### 8.2 Lokführerstand — Umbau CabView

**Lok-Auswahl:**
- Das Zahleneingabefeld (`<input type="number">` + „Übernehmen"-Button) entfällt.
- Neues `<select>` mit allen verwalteten Loks: Anzeige `„{name} (Adr. {address})"`.
- Bei Auswahl: `store.selectLoco(loco.address)` + Fahrstufenmodus/Funktionsanzahl übernehmen.
- Bei leerer Bibliothek: Hinweistext statt leeres Select.
- Select aktualisiert sich live via SSE (Roster-Änderung → Store → Select-Options reaktiv).

**Fahrregler (LocoThrottle):**
- Neuer Prop `maxSpeed: number` (126 / 28 / 14, je nach Fahrstufenmodus). Default 126.
- Slider vertikal: `<input type="range" orient="vertical">` + CSS für vertikale Darstellung,
  min unten (niedrigste Stufe), max oben (höchste). Die Richtungstasten (Vorwärts/Rückwärts) und
  STOP bleiben unterhalb des Sliders. Fahrstufenanzeige neben dem Slider.
- `onSpeedInput` begrenzt auf `0..maxSpeed`.

**Funktionstasten (FunctionButtons):**
- Bereits Prop `count` vorhanden (Default 29). CabView übergibt `count = loco.function_count + 1`
  (F0 bis Fn, also n+1 Buttons). Keine Änderung an FunctionButtons selbst nötig.

**Lokinformationsfeld (LocoInfoFrame):**
- Wird in ein `<details>`/`<summary>`-Element gewrappt (nativ einklappbar, kein JS nötig).
  Default: geschlossen (`<details>` ohne `open`-Attribut). Label: „Lok-Details".

**TrackPower:**
- Entfällt aus CabView (wandert in die globale Statusleiste, Anforderung 6).

### 8.3 App-Shell-Statusleiste (Anforderung 6)

Umbau der bestehenden `.app-header` in `App.vue`:

```
┌─ LED ─┬─────── Navigation ──────────┬─ TrackPower ─┐
│  ●    │ Dashboard | Lok | Weichen …  │  ⚡ EIN/AUS  │
└───────┴──────────────────────────────┴──────────────┘
```

- **Links:** Verbindungs-LED (rund, grün wenn verbunden, grau wenn nicht). **Kein Text**, keine
  IP-Adresse. Die bestehende `ConnectionStatus`-Komponente wird auf eine reine LED reduziert
  (Props: nur `connected: boolean`; entfernte Props `host`/`port`). Tooltip (title-Attribut) zeigt
  bei Hover die Verbindungsinfo.
- **Mitte:** bestehende `<nav>` mit RouterLinks (unverändert, plus neuer Link „Lokomotiven").
- **Rechts:** kompakter Gleisspannungs-Schalter (bestehende `TrackPower`-Komponente, evtl.
  visuell kompakter: LED + Toggle-Button statt zwei Buttons). Wird von `App.vue` direkt über
  den zentralen Store (`useLayoutStore`) gesteuert (der Store hat bereits `setTrackPower`).
- Die Kopfzeile bleibt **einzeilig** (flex-wrap für kleine Screens). Gesamthöhe möglichst ≤ 48px.

Dashboard (`DashboardView`): behält die SystemState-Anzeige (Temperaturen, Spannungen,
Kurzschluss/Nothalt) als Detailansicht. Der TrackPower-**Schalter** wird dort entfernt (steht
jetzt global); der TrackPower-**Status** (EIN/AUS) bleibt als Teil des SystemState sichtbar.

## 9. Teststrategie

**Backend (pytest):**
- `domain`: Lok-CRUD, Validierung (Name-Eindeutigkeit, Adressbereiche, speed_steps ∈ {14,28,128},
  function_count 0–28, Länge/Vmax ≥ 0), Adress-Warnung (Duplikat + kein Fehler).
- `roster_codec`: Round-Trip Roster ↔ dict, Schema-Version, ungültiges Dict.
- `roster_store`: Save→Load, fehlende Datei, korrupte Datei.
- `api`: TestClient — CRUD happy-path, 400 (Name-Duplikat, ungültige Werte), 404,
  `warnings`-Durchreichung (Adress-Duplikat). Start-Abbruch bei kaputter Roster-Datei.
- `protocol`: `build_loco_drive` mit speed_steps 14/28/128, korrekte DB0-Werte und
  Speed-Kodierung je Modus.

**Frontend (vitest / playwright):**
- Component: RosterList rendern, Anlegen/Fehler/Warnung; LocoThrottle vertikal + maxSpeed;
  FunctionButtons mit count; ConnectionStatus nur LED; CabView mit Select statt Eingabe.
- E2E: Lok anlegen → im Lokführerstand auswählen → Slider/Funktionen passen sich an;
  Statusleiste LED + TrackPower sichtbar auf mehreren Seiten.

## 10. Auswirkungen auf den Bestand

**Neu:**
- `domain/roster.py`, `domain/roster_codec.py`, `domain/roster_service.py`,
  `domain/roster_store.py`; `api/roster_routes.py`; API-Schemas.
- `views/RosterView.vue`, `components/RosterList.vue`, `stores/roster.ts`.
- `conf/roster.example.json`.

**Geändert:**
- `config.py`: +`roster_path`, `roster_backup_count`.
- `api/app.py`: RosterService verdrahten, Router registrieren.
- `z21/protocol.py`: `build_loco_drive` + `speed_steps`-Parameter.
- `domain/controller.py`: `drive` + `speed_steps` durchreichen.
- `api/schemas.py`: DriveRequest + `speed_steps`; Roster-Schemas.
- `api/app.py` drive-Route: `speed_steps` durchreichen.
- `frontend/src/api/client.ts` + `types.ts`: Roster-Methoden + Typen.
- `frontend/src/components/LocoThrottle.vue`: vertikal + `maxSpeed`-Prop.
- `frontend/src/components/ConnectionStatus.vue`: nur LED, kein Text.
- `frontend/src/components/TrackPower.vue`: ggf. kompaktere Variante.
- `frontend/src/views/CabView.vue`: Select statt Input, Throttle-Props, TrackPower entfernt,
  LocoInfoFrame einklappbar.
- `frontend/src/views/DashboardView.vue`: TrackPower-Schalter entfernt (Status bleibt).
- `frontend/src/App.vue`: Statusleiste (LED + TrackPower global), neuer Nav-Link.
- `frontend/src/router/index.ts`: `/roster`-Route.
- `.gitignore`: `conf/roster.json`, `conf/roster-backups/`.

**Unberührt:** Anlagenmodell (`layout*`), Weichensteuerung, Belegtmeldung, Z21-Client.
