# Verifikation — Aufgabe 5: `LayoutStore` (JSON-Persistenz)

Worktree: `/Users/dirkhessenmueller/dev/modellbahn_2/.worktrees/anlagenmodell`
Branch: `feature/anlagenmodell`
Werkzeuge aus `/Users/dirkhessenmueller/dev/modellbahn_2/.venv/bin`.

## Umgesetzter Scope

- Neu: `src/modellbahn/domain/layout_store.py` — `load`/`save` + private Helfer
  (`_backup_timestamp`, `_unique_backup_path`, `_rotate_backups`).
- Neu: `tests/test_layout_store.py` — 11 Tests mit `tmp_path`.
- `layout.py` / `layout_codec.py` unveraendert (nur genutzt).
- Keine `config.py`-/`app.py`-Aenderungen, kein Blockzustand, keine API/Frontend. `tasks.md`
  nicht abgehakt.

## Ausgefuehrte Befehle und Ergebnisse

### ruff check (Lint)

```
.venv/bin/ruff check src tests
-> All checks passed!   (RUFF=0)
```

Hinweis waehrend der Umsetzung: Ein `UP017`-Befund (`datetime.timezone.utc` ->
`datetime.UTC`) wurde durch Umstieg auf `from datetime import UTC` behoben (Python 3.11+).

### ruff format --check (nur neue Dateien im Scope)

```
.venv/bin/ruff format --check src/modellbahn/domain/layout_store.py tests/test_layout_store.py
-> 2 files already formatted   (FMT=0)
```

Die 5 bereits auf `main` nicht format-konformen Dateien (api/app.py, z21/messages.py,
z21/protocol.py, tests/test_client.py, tests/test_messages.py) wurden bewusst NICHT angefasst.

### mypy

```
.venv/bin/mypy src
-> Success: no issues found in 20 source files   (EXIT=0)
```

### pytest (gesamte Suite)

```
.venv/bin/pytest -q
-> 155 passed, 1 warning in 3.43s   (EXIT=0)
```

Vorher 144 gruen; jetzt 155 (11 neue Tests), kein bestehender Test gebrochen. Die eine Warnung
ist eine vorbestehende Starlette-`DeprecationWarning`, unabhaengig von dieser Aufgabe.

## Abgedeckte Testfaelle (`tests/test_layout_store.py`)

1. `test_load_missing_file_returns_empty_layout` — fehlende Datei -> leeres `Layout()`.
2. `test_save_then_load_roundtrip` — Save->Load-Rundlauf mit nicht-trivialem Layout
   (Block mit Laenge/Detektoren/Markierungen, DKW mit 2 Adressen, Fahrstrasse) == dataclass-eq.
3. `test_load_corrupt_json_raises` — kaputtes JSON -> `LayoutDecodeError` (Meldung nennt Pfad),
   kein stilles leeres Layout.
4. `test_load_invalid_schema_raises` — `version: 999` -> `LayoutDecodeError` (aus `from_dict`).
5. `test_atomic_write_no_tmp_leftover` — nach `save` existiert Zieldatei, keine `*.tmp` bleibt.
6. `test_save_creates_target_directory` — Zielverzeichnis wird angelegt.
7. `test_first_save_without_existing_file_creates_no_backup` — erstes Speichern -> kein Backup.
8. `test_backup_created_on_overwrite_with_previous_content` — Ueberschreiben erzeugt genau EIN
   Backup; Inhalt == vorheriger Stand; Zieldatei == neuer Stand.
9. `test_backup_rotation_keeps_n_newest` — nach > N+1 Saves genau N Backups, eindeutige Namen.
10. `test_unique_backup_path_disambiguates_same_timestamp` — identische Mikrosekunde -> eindeutige
    Namen mit `-01`/`-02`-Suffix; Suffix-Namen fester Breite sortieren chronologisch.
11. `test_rotation_ignores_foreign_files` — fremde Datei (`README.txt`) bleibt unberuehrt.

## Hinweis zur Backup-Namensordnung (Design E3)

Wie im Plan (E3) dokumentiert, sortiert der suffixlose Name `layout-<ts>.json` wegen `-` (0x2D)
< `.` (0x2E) lexikografisch HINTER den `-NN`-Varianten derselben Mikrosekunde. Das ist fuer die
Rotation unkritisch (Backups derselben Mikrosekunde sind praktisch gleichzeitig); Backups
unterschiedlicher Mikrosekunden sortieren eindeutig. Der Test prueft daher Eindeutigkeit und die
chronologische Ordnung der Suffix-Namen untereinander, nicht eine Gesamtordnung inklusive des
suffixlosen Namens.
