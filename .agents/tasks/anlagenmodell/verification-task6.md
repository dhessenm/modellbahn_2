# Verifikation — Aufgabe 6: Abgeleiteter Blockzustand (`block_runtime.py`)

Worktree: `/Users/dirkhessenmueller/dev/modellbahn_2/.worktrees/anlagenmodell`
Branch: `feature/anlagenmodell`
cwd fuer alle Befehle: Worktree-Wurzel.

## Neue/geaenderte Dateien

- `src/modellbahn/domain/block_runtime.py` (neu) — reine, read-only Ableitung des
  Laufzeit-Blockzustands.
- `tests/test_block_runtime.py` (neu) — Tests fuer alle geforderten Faelle.

## Ausgefuehrte Befehle und Ergebnisse

### 1. ruff check

```
/Users/dirkhessenmueller/dev/modellbahn_2/.venv/bin/ruff check src tests
```

Ergebnis: `All checks passed!`

### 2. ruff format --check (nur die neuen Dateien)

```
/Users/dirkhessenmueller/dev/modellbahn_2/.venv/bin/ruff format --check \
  src/modellbahn/domain/block_runtime.py tests/test_block_runtime.py
```

Ergebnis: `2 files already formatted`

Hinweis: Die 5 bereits auf `main` nicht format-konformen Dateien ausserhalb des
Scopes (`api/app.py`, `z21/messages.py`, `z21/protocol.py`, `tests/test_client.py`,
`tests/test_messages.py`) wurden bewusst NICHT angefasst. Nur die beiden neuen
Dateien wurden geprueft und sind format-sauber.

### 3. mypy (strict)

```
/Users/dirkhessenmueller/dev/modellbahn_2/.venv/bin/mypy src
```

Ergebnis: `Success: no issues found in 21 source files`

### 4. pytest (gesamte Suite)

```
/Users/dirkhessenmueller/dev/modellbahn_2/.venv/bin/pytest -q
```

Ergebnis: `164 passed, 1 warning in 3.13s`

Vorher waren 155 Tests gruen; durch die 9 neuen Tests in
`tests/test_block_runtime.py` steigt die Zahl auf 164. Kein bestehender Test
bricht. (Die eine Warnung ist eine bereits vorhandene Starlette-DeprecationWarning
ausserhalb des Scopes.)

## Abgedeckte Testfaelle

- Block ohne zugeordnete Melder -> `unknown`, `loco_addresses == []`.
- Alle zugeordneten Melder live & frei -> `free`.
- Mindestens ein zugeordneter Melder belegt -> `occupied`.
- Zugeordnete Melder, aber keiner live bekannt -> `unknown` (nicht `free`),
  sicherheitsrelevanter Randfall.
- Mischung: ein live-freier + ein nicht live bekannter Melder -> `free`
  (Semantik im Test dokumentiert).
- Belegt ohne RailCom-Identitaet -> `occupied`, `loco_addresses == []`.
- Mehrere Loks ueber mehrere Melder inkl. Duplikat -> dedupliziert, aufsteigend
  sortiert, Richtung ignoriert.
- `derive_all_block_runtimes` liefert je Block einen Eintrag in Einfuegereihenfolge.
- `BlockRuntime` ist frozen (FrozenInstanceError beim Setzen eines Feldes).
