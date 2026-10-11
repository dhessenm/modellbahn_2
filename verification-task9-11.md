# Verifikation Aufgaben 9, 10, 11 — API-Schicht Anlagenmodell

Worktree/cwd: `/Users/dirkhessenmueller/dev/modellbahn_2/.worktrees/anlagenmodell`
Branch: `feature/anlagenmodell`. Tools absolut aus dem Haupt-venv.

## Umfang (nur diese Dateien)

- `src/modellbahn/api/schemas.py` — erweitert: Request/Response-Schemata fuer
  Element, Block, Melder-Zuordnung, Marker, Route, Runtime, Warnung, 409-Body
  sowie Mapping-Helfer dataclass <-> Schema (nur lesend auf die domain-Modelle).
- `src/modellbahn/api/layout_routes.py` — neu: `build_layout_router(...)` mit den
  12 `/api/layout`-Routen, Fehlerregel 404/400/409, warnings-Durchreichung.
- `src/modellbahn/api/app.py` — Layout laden beim Start (LayoutDecodeError bricht
  create_app ab), `LayoutService` verdrahten, Backup-Dir ableiten, `on_mutation`
  (save + publish), Router registrieren. Danach `ruff format` angewandt (erlaubte
  Ausnahme fuer app.py).
- `tests/test_layout_api.py` — neu: 12 Tests (FastAPI-TestClient, FakeTransport,
  `layout_path` auf `tmp_path`).

Keine Aenderung an der domain-Schicht oder `config.py`. Kein Frontend. Es wurde
kein domain-Bug gefunden, der die API blockiert.

## Ausgefuehrte Befehle und Ergebnisse

### Baseline (vor Beginn)
`/Users/dirkhessenmueller/dev/modellbahn_2/.venv/bin/pytest -q`
-> **166 passed, 1 warning** (Ausgangspunkt).

### ruff check
`/Users/dirkhessenmueller/dev/modellbahn_2/.venv/bin/ruff check src tests`
-> **All checks passed!** (Exit 0).
(Zuerst gemeldet: 1x F401 unbenutzter Import `BlockResponse` in `layout_routes.py`
— entfernt; danach sauber.)

### ruff format --check (neue/geaenderte Dateien)
`/Users/dirkhessenmueller/dev/modellbahn_2/.venv/bin/ruff format --check src/modellbahn/api/schemas.py src/modellbahn/api/layout_routes.py src/modellbahn/api/app.py tests/test_layout_api.py`
-> **4 files already formatted** (Exit 0).
Vorher wurde `ruff format src/modellbahn/api/app.py src/modellbahn/api/layout_routes.py`
ausgefuehrt (2 files reformatted). Die 4 Fremddateien (`z21/messages.py`,
`z21/protocol.py`, `tests/test_client.py`, `tests/test_messages.py`) wurden NICHT
angefasst.

### mypy (strict)
`/Users/dirkhessenmueller/dev/modellbahn_2/.venv/bin/mypy src`
-> **Success: no issues found in 22 source files** (Exit 0).

### pytest (gesamt, nach Umsetzung)
`/Users/dirkhessenmueller/dev/modellbahn_2/.venv/bin/pytest -q`
-> **178 passed, 1 warning in 3.66s** (Exit 0).
166 -> 178, d. h. +12 neue Tests, keiner gebrochen.

Nur die neue Testdatei:
`/Users/dirkhessenmueller/dev/modellbahn_2/.venv/bin/pytest -q tests/test_layout_api.py`
-> **12 passed, 1 warning**.

## Abgedeckte Testfaelle (tests/test_layout_api.py)

1. `GET /api/layout` leer -> `{"blocks": [], "elements": [], "routes": []}`.
2. `POST /api/layout/blocks` -> 201, `entity.id` gesetzt, Block erscheint in
   `GET /api/layout`, Modelldatei unter `layout_path` existiert (Persistenz).
3. `POST` Block mit doppeltem Namen -> 400.
4. `PUT .../blocks/{id}/detectors` doppelter `order` -> 400; gueltige Liste -> 200
   mit `entity.detectors` in gesetzter Reihenfolge.
5. `POST .../elements` je Typ (turnout mit address, dkw mit address+address_b,
   crossing ohne Adresse) -> je 201; ungueltige Adressregel (Weiche ohne address,
   Kreuzung mit address) -> 400.
6. `POST .../routes` unbekannte Block-ID -> 400; gueltige IDs -> 201.
7. `DELETE .../blocks/{id}` eines referenzierten Blocks -> 409 mit `blocked_by`
   (genau ein Eintrag, `type=="route"`, korrekte `id`/`name`).
8. `GET .../runtime`: Block mit belegtem Melder -> `occupancy=="occupied"`;
   Block ohne Melder -> `occupancy=="unknown"`.
9. warnings-Durchreichung: Block mit `length_mm` + Teillaengen-Summe != length_mm
   -> `BlockWriteResponse.warnings` enthaelt `code=="laengensumme"`.
10. 404-Regel: PUT/DELETE auf unbekannte Block-/Element-/Route-ID -> 404.
11. Start-Abbruch: `layout_path` auf kaputte JSON-Datei -> `create_app` wirft
    `LayoutDecodeError`.

## Zentrale Design-Fixpunkte (umgesetzt wie im Plan)

- `ElementType` {turnout, dkw, crossing} direkt als Pydantic-Feld.
- `update_element` nutzt in Stufe 1 PUT = Vollersetzung; `_UNSET` wird importiert
  und bleibt dem spaeteren Partial-Patch vorbehalten (dokumentiert).
- `ReferenceConflictError.blocked_by` -> 409-Body `{detail, blocked_by:[{type,id,name}]}`.
- `derive_all_block_runtimes(layout, controller.state)` fuer `/runtime`.
- Backup-Verzeichnis aus `layout_path` abgeleitet (`<stem>-backups/` daneben).
- Nach jeder Mutation: `layout_store.save(...)` dann `broker.publish()`.
- `LayoutDecodeError` beim Laden propagiert und bricht `create_app` ab.
