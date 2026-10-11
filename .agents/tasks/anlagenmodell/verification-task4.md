# Verifikation — Aufgabe 4: Konsistenz-Warnungen + harte Checks

cwd: `/Users/dirkhessenmueller/dev/modellbahn_2/.worktrees/anlagenmodell`
Branch: `feature/anlagenmodell`
Werkzeuge aus dem venv des Haupt-Repos: `/Users/dirkhessenmueller/dev/modellbahn_2/.venv/bin/{ruff,mypy,pytest}`

## Geaenderte/neue Dateien dieser Aufgabe

- NEU: `src/modellbahn/domain/layout_consistency.py` — reine Warnungslogik
  (`ConsistencyWarning`, `WARN_*`-Konstanten, `block_consistency_warnings`).
- GEAENDERT: `src/modellbahn/domain/layout_service.py` — harte Non-Negative-Checks in
  `create_block`/`update_block`/`set_block_detectors`; neue Methoden `block_warnings`/
  `layout_warnings`; Modul-Docstring aktualisiert.
- NEU: `tests/test_layout_consistency.py` — Tests der reinen Warnungslogik.
- GEAENDERT: `tests/test_layout_service.py` — Tests fuer harte Fehler + Exposition.

## Befehle und Ergebnisse

### 1. `ruff check src tests`

```
All checks passed!
```
Exit 0.

### 2. `ruff format --check` (nur Dateien dieser Aufgabe)

Befehl:
`ruff format --check src/modellbahn/domain/layout_consistency.py src/modellbahn/domain/layout_service.py tests/test_layout_consistency.py tests/test_layout_service.py`

```
4 files already formatted
```
Exit 0.

Hinweis: Die 5 bereits auf main nicht format-konformen Dateien ausserhalb des Scopes
(api/app.py, z21/messages.py, z21/protocol.py, tests/test_client.py, tests/test_messages.py)
wurden bewusst NICHT angefasst; sie sind kein Fehler dieser Aufgabe.

### 3. `mypy src`

```
Success: no issues found in 19 source files
```
Exit 0.

### 4. `pytest -q`

```
144 passed, 1 warning in 3.09s
```
Exit 0. (Baseline war 119 gruen; +25 neue Tests, keiner gebrochen. Die eine Warnung ist eine
vorbestehende starlette-DeprecationWarning, ohne Bezug zu dieser Aufgabe.)
