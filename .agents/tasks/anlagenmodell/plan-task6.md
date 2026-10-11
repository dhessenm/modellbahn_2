# Umsetzungsplan — Aufgabe 6: Abgeleiteter Blockzustand (`block_runtime.py`)

> Spec: `.kiro/specs/anlagenmodell` (requirements.md Anf. 5, design.md §3.2 und §1).
> Worktree: `/Users/dirkhessenmueller/dev/modellbahn_2/.worktrees/anlagenmodell`,
> Branch `feature/anlagenmodell`. cwd fuer alle Befehle = Worktree-Wurzel.
>
> Scope-Grenze (hart): NUR das neue Modul `src/modellbahn/domain/block_runtime.py`
> und dessen Tests `tests/test_block_runtime.py`. `state.py`/`layout.py` werden nur
> **gelesen**. KEIN Service-Umbau, KEINE Persistenz, KEINE config/app/API/Frontend-
> Aenderung, KEINE Mutationen, KEINE Z21-/FastAPI-Importe. `tasks.md` wird NICHT
> abgehakt. Nur Python-Standardbibliothek.

## Designentscheidungen (mit Begruendung)

- **D-A: Belegungstyp.** `Literal["free", "occupied", "unknown"]` als Modul-Alias
  `Occupancy` statt str-Enum. Begruendung: `design.md` §3.2 zeigt genau diesen
  `Literal`; er ist mypy-strict-tauglich, JSON-serialisierbar ohne Konvertierung
  (reine `str`-Werte) und kommt ohne zusaetzliche Klasse aus — passt zur Vorgabe
  „schlank halten". Die drei String-Konstanten werden auch als Modul-Konstanten
  (`FREE`, `OCCUPIED`, `UNKNOWN`) bereitgestellt, damit Tests und spaetere Aufrufer
  nicht auf Stringliterale angewiesen sind.
- **D-B: `BlockRuntime` frozen dataclass.** `@dataclass(frozen=True)` mit genau
  `block_id: str`, `occupancy: Occupancy`, `loco_addresses: list[int]`. Begruendung:
  read-only-Ableitung soll unveraenderlich sein (keine versehentliche Mutation durch
  Aufrufer); die Felder entsprechen 1:1 `design.md` §3.2. `loco_addresses` ist eine
  frisch erzeugte Liste (kein geteilter Zustand). Hinweis: `frozen=True` verbietet
  nur das Rebinden der Felder, nicht das Mutieren der Liste; da `derive_*` die Liste
  neu baut und niemand sie weitergibt, ist das akzeptabel und bleibt schlank.
- **D-C: Reine Funktion, keine Klasse/Service.** `derive_block_runtime` und
  `derive_all_block_runtimes` sind freie Funktionen ohne Zustand. Begruendung:
  `design.md` §1 nennt die Ableitung „eine reine Funktion `(Layout, LayoutState) ->
  BlockRuntime[]`, read-only, nicht persistiert". Entkopplung gemaess `structure.md`:
  `domain` ohne FastAPI/UDP.
- **D-D: Sicherheitsrandfall „zugeordnet aber nie live gesehen".** Beim Nachschlagen
  via `state.detectors.get((nid, port))` kann `None` zurueckkommen (Melder zugeordnet,
  aber noch kein Live-Datensatz). Entscheidung fuer die Belegung:
  mindestens ein zugeordneter, live-bekannter Melder `occupied` -> `OCCUPIED`;
  sonst mindestens ein zugeordneter, live-bekannter Melder (also `get` liefert ein
  `DetectorInput`) -> `FREE`;
  sonst (kein einziger zugeordneter Melder ist live bekannt) -> `UNKNOWN` (NICHT
  `FREE`). Begruendung „kein falsches Sicherheitsgefuehl" (Anf. 5.3): ein nie live
  gesehener Melder ist keine Freimeldung — ihn als „frei" zu werten wuerde einen
  belegten Block faelschlich als frei zeigen. Nur ein tatsaechlich live gesehener,
  nicht belegter Melder rechtfertigt `FREE`. Dies ist die konsequente Ausdehnung von
  Anf. 5.3 („keine Melder -> unknown") auf „keine *live bekannten* Melder -> unknown".
- **D-E: Identitaet (Dedup/Sortierung).** `loco_addresses` = aufsteigend sortierte,
  deduplizierte Vereinigung aller `addr` aus `DetectorInput.locos` ueber ALLE
  zugeordneten, live bekannten Melder. Dedup ueber die **Adresse** (erstes Tupel-
  Element); die Richtung (zweites Element) wird ignoriert. Begruendung: Anf. 5.2 +
  offener Design-Punkt „Lok ueber mehrere Melder nur einmal zaehlen". Sortierung
  macht das Ergebnis deterministisch und testbar. Umsetzung ueber ein `set[int]`,
  dann `sorted(...)`.
- **D-F: Belegung und Identitaet sind entkoppelt.** `loco_addresses` wird unabhaengig
  vom Belegungszustand aggregiert (ein belegter Melder ohne RailCom liefert
  `OCCUPIED` + `[]`; „Belegung vor Identitaet", `design.md` §1). Es findet KEINE
  Querpruefung statt (z. B. „occupied erfordert loco_addresses").

## Verifiziertes Fundament (bereits im Code vorhanden, nur gelesen)

- `layout.Block.detectors: list[DetectorAssignment]`;
  `DetectorAssignment` hat `detector_nid: int`, `detector_port: int`, `order: int`,
  `length_mm: int | None`.
- `layout.Layout.blocks: dict[str, Block]` (Einfuegereihenfolge = dict-Reihenfolge).
- `state.LayoutState.detectors: dict[tuple[int, int], DetectorInput]`, Schluessel
  `(nid, port)`.
- `state.DetectorInput` hat u. a. `occupied: bool` und
  `locos: list[tuple[int, str]]` (je Element `(lok_adresse: int, richtung: str)`).

Alle Zugriffspfade oben wurden gegen `src/modellbahn/domain/layout.py` und
`src/modellbahn/domain/state.py` geprueft.

## Arbeitsschritte

- [ ] 1. Modul `src/modellbahn/domain/block_runtime.py` anlegen (reine Ableitung).
      Inhalt: Modul-Docstring (read-only, keine Mutation/Persistenz; Prinzip
      „Belegung vor Identitaet"); `from __future__ import annotations`; Imports nur
      aus Standardbibliothek (`dataclasses.dataclass`, `typing.Literal`) sowie den
      Domain-Typen (`from .layout import Block, Layout`,
      `from .state import LayoutState`).
      Definiere: `Occupancy = Literal["free", "occupied", "unknown"]`; Konstanten
      `FREE: Occupancy = "free"`, `OCCUPIED: Occupancy = "occupied"`,
      `UNKNOWN: Occupancy = "unknown"`;
      `@dataclass(frozen=True) class BlockRuntime` mit `block_id: str`,
      `occupancy: Occupancy`, `loco_addresses: list[int]`.
      Implementiere `derive_block_runtime(block: Block, state: LayoutState) ->
      BlockRuntime` gemaess D-A..D-F:
        * `if not block.detectors:` -> `BlockRuntime(block.id, UNKNOWN, [])`.
        * Sonst ueber `block.detectors` iterieren, je Assignment
          `state.detectors.get((a.detector_nid, a.detector_port))` nachschlagen;
          `None` ueberspringen (nicht live bekannt).
          Merker `any_live` (mind. ein `DetectorInput` gefunden), `any_occupied`
          (mind. ein gefundener mit `.occupied`), und ein `set[int]` fuer Adressen
          aus `.locos` (`addr for addr, _direction in di.locos`).
        * Belegung: `OCCUPIED` wenn `any_occupied`; sonst `FREE` wenn `any_live`;
          sonst `UNKNOWN`.
        * `loco_addresses = sorted(addr_set)`.
      Implementiere `derive_all_block_runtimes(layout: Layout, state: LayoutState) ->
      list[BlockRuntime]` als `[derive_block_runtime(b, state) for b in
      layout.blocks.values()]` (ein Eintrag je Block in Einfuegereihenfolge).
      Files: `src/modellbahn/domain/block_runtime.py`
      Verify: `python -m mypy src/modellbahn/domain/block_runtime.py` laeuft ohne
      Fehler (strict ist in `pyproject.toml` gesetzt), und
      `python -c "from modellbahn.domain import block_runtime"` importiert fehlerfrei
      (via `pythonpath=["src"]`; falls direkt aufgerufen: `PYTHONPATH=src`).

- [ ] 2. Tests `tests/test_block_runtime.py` anlegen (alle geforderten Faelle).
      Stil wie bestehende Domain-Tests (`tests/test_layout_consistency.py`):
      `from __future__ import annotations`, Modul-Docstring, direkte Konstruktion der
      Dataclasses, kleine Helfer. Importiere `Block`, `DetectorAssignment` aus
      `modellbahn.domain.layout`, `Layout` aus `modellbahn.domain.layout`,
      `LayoutState`, `DetectorInput` aus `modellbahn.domain.state`,
      sowie `BlockRuntime`, `derive_block_runtime`, `derive_all_block_runtimes`,
      `FREE`, `OCCUPIED`, `UNKNOWN` aus `modellbahn.domain.block_runtime`.
      Helfer:
        * `_assignment(nid, port, order)` -> `DetectorAssignment`.
        * `_block(detectors=...)` -> `Block(id="b1", name="A", detectors=[...])`.
        * `_state(*detector_inputs)` -> `LayoutState` mit
          `detectors={(di.nid, di.port): di for di in detector_inputs}`.
      Zu deckende Faelle (je ein Test, Namen sprechend):
        a. Keine Melder -> `UNKNOWN`, `loco_addresses == []`
           (Block ohne `detectors`).
        b. Alle zugeordneten Melder live und frei -> `FREE`.
        c. Mind. ein zugeordneter Melder belegt -> `OCCUPIED` (auch wenn andere frei).
        d. Melder zugeordnet, aber KEINER live bekannt (`state.detectors` leer bzw.
           ohne passende Schluessel) -> `UNKNOWN` (NICHT `FREE`) — Sicherheitsrandfall
           D-D; Kommentar im Test, der die Semantik dokumentiert.
        e. Mischung: ein zugeordneter Melder live & frei, ein weiterer zugeordnet aber
           nicht live bekannt -> `FREE` (mind. ein live-freier vorhanden); Kommentar
           zur dokumentierten Semantik.
        f. Belegt ohne RailCom-Loks (`occupied=True`, `locos=[]`) -> `OCCUPIED`,
           `loco_addresses == []` („belegt ohne Identitaet").
        g. Mehrere Loks ueber mehrere Melder inkl. Duplikat und unsortierter Eingabe
           (z. B. Melder1 `locos=[(10,"fwd"),(3,"bwd")]`, Melder2 `locos=[(10,"fwd")]`)
           -> `loco_addresses == [3, 10]` (dedupliziert, aufsteigend sortiert,
           Richtung ignoriert); Belegung passend (mind. einer occupied -> `OCCUPIED`).
        h. `derive_all_block_runtimes`: `Layout` mit mehreren Bloecken in bekannter
           Einfuegereihenfolge -> Ergebnisliste hat je Block genau einen Eintrag, in
           derselben Reihenfolge (`[r.block_id for r in result]` == Einfuege-IDs);
           je Eintrag plausibler Zustand (z. B. ein Block ohne Melder -> `UNKNOWN`,
           ein Block mit belegtem Melder -> `OCCUPIED`).
      Zusaetzlich sinnvoll: `BlockRuntime` ist frozen (ein Test, der
      `with pytest.raises(FrozenInstanceError)` beim Setzen eines Feldes prueft —
      Import `from dataclasses import FrozenInstanceError`).
      Files: `tests/test_block_runtime.py`
      Verify: `python -m pytest tests/test_block_runtime.py -q` — alle neuen Tests
      gruen.

- [ ] 3. Qualitaet des neuen Codes sicherstellen (nur die beiden neuen Dateien).
      Files: keine weiteren Aenderungen; ggf. Formatkorrekturen in
      `src/modellbahn/domain/block_runtime.py` und `tests/test_block_runtime.py`.
      Verify (alle in der Worktree-Wurzel, erwartete Ausgabe: keine Fehler):
        * `python -m ruff check src/modellbahn/domain/block_runtime.py tests/test_block_runtime.py`
        * `python -m ruff format --check src/modellbahn/domain/block_runtime.py tests/test_block_runtime.py`
        * `python -m mypy src/modellbahn/domain/block_runtime.py tests/test_block_runtime.py`
          (strict; `mypy_path=src` ist in `pyproject.toml` gesetzt)
        * `python -m pytest tests/test_block_runtime.py -q`
      Zur Sicherheit, dass nichts Bestehendes bricht: `python -m pytest -q`
      (gesamte Suite) — alles gruen.

## Hinweise fuer den Implementierer

- `pyproject.toml` setzt `pythonpath=["src"]` fuer pytest und `mypy_path=src`;
  ad-hoc `python -c`-Importe brauchen ggf. `PYTHONPATH=src`.
- Keine neuen Abhaengigkeiten; alles aus der Standardbibliothek plus den vorhandenen
  Domain-Modulen.
- Dateien committen auf `feature/anlagenmodell` (deutsche Commit-Message), NICHT
  pushen, NICHT `tasks.md` abhaken (das erledigt eine spaetere Aufgabe).
```