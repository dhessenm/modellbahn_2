# Implementierungsplan — Aufgabe 5: `LayoutStore` (JSON-Persistenz)

Spec `Anlagenmodell (Stufe 1)`, Aufgabe 5 der `tasks.md`. Umsetzung ausschliesslich im Worktree
`/Users/dirkhessenmueller/dev/modellbahn_2/.worktrees/anlagenmodell` auf Branch
`feature/anlagenmodell`. Scope: NUR das neue Modul `src/modellbahn/domain/layout_store.py` und
dessen Tests `tests/test_layout_store.py`. KEIN Service-Umbau, KEINE API/Frontend-Verdrahtung,
KEIN Laden-beim-Start (Aufgabe 10), KEINE neuen `config.py`-Settings (Aufgabe 8). `layout.py` und
`layout_codec.py` werden nur genutzt, nicht geaendert. `tasks.md` wird NICHT abgehakt.

## Designentscheidungen (mit Begruendung)

### E1 — Fehlertyp beim Laden: `LayoutDecodeError` wiederverwenden

Entscheidung: Beim Laden einer vorhandenen, aber kaputten Datei wird **`LayoutDecodeError`**
(aus `layout_codec`) geworfen — sowohl bei kaputtem JSON (`json.JSONDecodeError`) als auch bei
ungueltigem Schema (das `from_dict` ohnehin bereits als `LayoutDecodeError` meldet). Keine eigene
Store-Exception.

Begruendung: `from_dict` wirft bei strukturell/versionsseitig ungueltigem Inhalt schon
`LayoutDecodeError` mit deutscher Meldung. Wuerde der Store fuer kaputtes JSON eine andere
Exception einfuehren, muesste der spaetere Start-Code (Aufgabe 10) zwei verschiedene Typen fangen,
um "ungueltige Modelldatei -> Start mit klarer Meldung abbrechen" (Req. 6.3) umzusetzen. Ein
einziger Abbruch-Signaltyp fuer "Datei vorhanden, aber unbrauchbar" ist einfacher und
konsistent. Der Store faengt `json.JSONDecodeError` ab und wirft `LayoutDecodeError` mit einer
aussagekraeftigen deutschen Meldung, die den Dateipfad und die urspruengliche Fehlerursache
nennt (`raise LayoutDecodeError(...) from err`, Ursache bleibt verkettet). Wichtig: KEIN stiller
Fallback auf ein leeres `Layout`, wenn eine vorhandene Datei kaputt ist — nur die *fehlende*
Datei ergibt ein leeres `Layout`.

### E2 — Zeitstempel-Format der Backups

Entscheidung: Backup-Dateiname `layout-<UTC-Zeitstempel>.json` mit Zeitstempel im Format
`YYYYMMDDTHHMMSSffffff` (Jahr, Monat, Tag, `T`, Stunde, Minute, Sekunde, 6-stellige
Mikrosekunden), erzeugt aus `datetime.now(timezone.utc)`. Keine Doppelpunkte/`+`/`:` — der Name
bleibt dateisystemgueltig (auch Windows). Lexikografische Sortierung == chronologische Sortierung,
weil alle Felder fester Breite und absteigender Signifikanz sind und durchgaengig UTC gilt.
Beispiel: `layout-20240521T081503123456.json`.

### E3 — Kollisionsvermeidung bei identischer Mikrosekunde

Entscheidung: Erzeugt die Zeitstempel-Basis einen Namen, der im `backup_dir` bereits existiert,
wird ein numerisches Suffix `-NN` (zweistellig, Startwert `01`) angehaengt und bei Bedarf
hochgezaehlt, bis ein freier Name gefunden ist: `layout-<ts>-01.json`, `layout-<ts>-02.json`, …
Das Suffix ist zweistellig fester Breite, damit die lexikografische Ordnung innerhalb derselben
Mikrosekunde erhalten bleibt (`-01` < `-02`). Namen ohne Suffix (`layout-<ts>.json`) sortieren
lexikografisch vor dem ersten Suffix-Namen (`-01`), weil `.` (0x2E) vor `-` (0x2D)… — Achtung:
`-` (0x2D) ist KLEINER als `.` (0x2E). Daher: der suffixlose Name endet auf `.json`, der
Suffix-Name auf `-NN.json`; da `-` < `.`, sortiert `layout-<ts>-01.json` VOR
`layout-<ts>.json`. Das ist fuer die Rotation unkritisch, weil Backups innerhalb derselben
Mikrosekunde praktisch gleichzeitig sind und ihre relative Ordnung fuer "N neueste behalten"
nicht fachlich relevant ist. Die Rotation sortiert alle Backups lexikografisch; Dateien einer
spaeteren Mikrosekunde sortieren eindeutig hinter denen einer frueheren. Diese Randfall-Semantik
wird im Docstring dokumentiert.

### E4 — Verzeichnisanlage

Entscheidung: `save` legt das Zielverzeichnis (Parent von `path`) und, falls `backup_dir`
gesetzt ist, das `backup_dir` per `Path.mkdir(parents=True, exist_ok=True)` an. `load` legt
nichts an (fehlende Datei -> leeres `Layout`).

### E5 — Backup per Umbenennen vs. Kopieren

Entscheidung: Die bestehende Zieldatei wird vor dem Schreiben per `os.replace`/`shutil.copy2` als
Backup gesichert. Konkret: Es wird **kopiert** (`shutil.copy2`, erhaelt mtime), NICHT verschoben.
Begruendung: Der atomare Schreibablauf (E6) schreibt den neuen Stand in eine Temp-Datei und
ersetzt das Ziel per `os.replace`. Wuerde die bestehende Zieldatei vor dem `os.replace`
*weggeschoben*, gaebe es ein kurzes Fenster ohne gueltige `layout.json`; durch Kopieren bleibt
das Ziel bis zum finalen `os.replace` unveraendert und immer vorhanden. `shutil` ist Teil der
Standardbibliothek — keine Fremdlib. (Alternativ waere ein Hardlink moeglich, aber `copy2` ist
plattformunabhaengiger und einfacher.)

### E6 — Atomarer Schreibablauf

Temp-Datei IM SELBEN Zielverzeichnis (gleiches Dateisystem, damit `os.replace` atomar ist),
schreiben, `flush()` + `os.fsync(fileno)`, schliessen, dann `os.replace(tmp, path)`. Bei einem
Fehler nach dem Anlegen der Temp-Datei wird diese im `finally`/`except` wieder entfernt, damit
keine `*.tmp`-Reste liegen bleiben.

### E7 — Restore ist manuell (Stufe 1)

Dokumentierte Annahme (Modul-Docstring): Der Store bietet KEINE Restore-Funktion. Das
Wiederherstellen eines Backups erfolgt in Stufe 1 manuell (Backup-Datei nach `layout.json`
zuruueckkopieren). Das deckt Req. 6.6 ab.

## Signaturen (`src/modellbahn/domain/layout_store.py`)

Umsetzung als Modul-Funktionen (kein Zustand noetig; konsistent mit dem funktionalen Stil von
`layout_codec`). Nur Standardbibliothek: `json`, `os`, `shutil`, `datetime`, `pathlib`.

```python
from __future__ import annotations

from pathlib import Path

from modellbahn.domain.layout import Layout

TMP_SUFFIX = ".tmp"
BACKUP_PREFIX = "layout-"
BACKUP_SUFFIX = ".json"
DEFAULT_BACKUP_COUNT = 10


def load(path: str | Path) -> Layout:
    """Laedt das Layout aus 'path'. Fehlt die Datei -> leeres Layout().
    Kaputtes JSON oder ungueltiges Schema -> LayoutDecodeError (kein stiller Fallback)."""


def save(
    path: str | Path,
    layout: Layout,
    backup_dir: str | Path | None = None,
    backup_count: int = DEFAULT_BACKUP_COUNT,
) -> None:
    """Schreibt 'layout' atomar als JSON nach 'path'. Sichert optional die bestehende
    Zieldatei als rotiertes Backup unter 'backup_dir'."""
```

Interne Hilfsfunktionen (privat, `_`-Prefix): `_backup_timestamp()`,
`_unique_backup_path(backup_dir, timestamp)`, `_rotate_backups(backup_dir, backup_count)`.

## Ablauf `load`

1. `path` zu `Path`. Existiert die Datei nicht (`not p.exists()` bzw. `FileNotFoundError`) ->
   `return Layout()`.
2. Datei als Text (UTF-8) lesen.
3. `data = json.loads(text)` — `json.JSONDecodeError` abfangen und als
   `LayoutDecodeError(f"Modelldatei {p} enthaelt kein gueltiges JSON: {err}")` erneut werfen
   (`from err`).
4. `layout_codec.from_dict(data)` aufrufen; die daraus moeglicherweise geworfene
   `LayoutDecodeError` (ungueltiges Schema/Version) unveraendert durchreichen.
5. Rueckgabe des rekonstruierten `Layout`.

## Ablauf `save`

1. `path` zu `Path`; Zielverzeichnis `p.parent` mit `mkdir(parents=True, exist_ok=True)` anlegen.
2. Wenn `backup_dir` gesetzt UND `p` bereits existiert: `backup_dir` anlegen; Zeitstempel per
   `_backup_timestamp()` bilden; kollisionsfreien Zielnamen per `_unique_backup_path` bestimmen;
   bestehende `p` per `shutil.copy2` dorthin kopieren; danach `_rotate_backups(backup_dir,
   backup_count)` aufrufen.
3. `payload = json.dumps(layout_codec.to_dict(layout), ensure_ascii=False, indent=2) + "\n"`.
4. Temp-Datei im selben Verzeichnis erzeugen (z. B. `p.with_name(p.name + TMP_SUFFIX)` oder
   `tempfile.NamedTemporaryFile(dir=p.parent, delete=False)`); `payload` schreiben; `flush()` +
   `os.fsync(f.fileno())`; schliessen.
5. `os.replace(tmp, p)`.
6. Fehlerpfad: Falls nach dem Anlegen der Temp-Datei etwas fehlschlaegt, Temp-Datei entfernen
   (`os.unlink`, `missing_ok`/`try-except`), damit keine `*.tmp`-Reste liegen bleiben.

## Backup-/Rotationslogik `_rotate_backups`

1. Alle Dateien im `backup_dir`, deren Name mit `BACKUP_PREFIX` beginnt und auf `BACKUP_SUFFIX`
   endet, einsammeln (keine fremden Dateien beruehren).
2. Lexikografisch nach Dateiname sortieren (== chronologisch, siehe E2); neueste zuletzt.
3. Solange mehr als `backup_count` Dateien vorhanden sind, die aeltesten (vorderste) loeschen.
4. `backup_count <= 0` -> alle gefundenen Backups loeschen (Grenzfall sauber behandeln).

## Dokumentierte Annahmen (Modul-Docstring)

- Nur Standardbibliothek; keine FastAPI/HTTP/UDP, keine Fremdlibs.
- Serialisierung ausschliesslich ueber `layout_codec.to_dict/from_dict` — der Store serialisiert
  NICHT Feld fuer Feld.
- Pfade werden als Parameter uebergeben; KEINE Hardcodierung von `conf/layout.json`.
- Restore ist in Stufe 1 manuell (keine Restore-Funktion), siehe E7.
- Zeitstempel-Format und Kollisionssuffix siehe E2/E3.

## Testmatrix (`tests/test_layout_store.py`)

Stil wie `tests/test_layout_codec.py` (`from __future__ import annotations`, `pytest`, Hilfs-
funktion `_full_layout()` ggf. aus einem kleinen Minimal-Layout; `tmp_path`-Fixture fuer
Dateisystem). Gefordert laut Aufgabe 5 / Design §7:

1. `test_load_missing_file_returns_empty_layout` — `load` auf nicht existierenden Pfad gibt
   `Layout()` (leer: keine blocks/elements/routes, version==1) zurueck.
2. `test_save_then_load_roundtrip` — vollstaendiges Layout (alle Entitaetstypen inkl. DKW mit
   2 Adressen, Markierungen beider Richtungen, Fahrstrasse mit Zwischenbloecken) speichern, dann
   laden; Ergebnis gleicht dem Original (Vergleich der `to_dict`-Repraesentation oder der
   dataclasses).
3. `test_load_corrupt_json_raises` — Datei mit kaputtem JSON (`"{ not json"`) -> `load` wirft
   `LayoutDecodeError`; Meldung nennt den Pfad; KEIN leeres Layout.
4. `test_load_invalid_schema_raises` — Datei mit gueltigem JSON aber ungueltigem Schema (z. B.
   `{"version": 99, ...}` oder fehlendem `blocks`) -> `LayoutDecodeError` (durchgereicht aus
   `from_dict`).
5. `test_atomic_write_no_tmp_leftover` — nach erfolgreichem `save` existiert `path`, aber keine
   `*.tmp`-Datei im Zielverzeichnis; Inhalt ist valides JSON mit `"version": 1`.
6. `test_save_creates_target_directory` — `save` auf Pfad in noch nicht existierendem
   Unterverzeichnis legt das Verzeichnis an und schreibt die Datei.
7. `test_backup_created_on_overwrite` — zweites `save` mit `backup_dir` legt genau ein Backup
   `layout-*.json` an, dessen Inhalt dem ERSTEN gespeicherten Stand entspricht; ohne vorhandene
   Zieldatei (erstes `save`) wird KEIN Backup erzeugt.
8. `test_backup_rotation_keeps_n_newest` — mit `backup_count=N` (z. B. 3) mehrfach (> N+1) mit
   wechselndem Inhalt speichern; danach genau N Backups im `backup_dir`; die aeltesten entfernt,
   die N neuesten (lexikografisch groessten Namen) vorhanden. Falls noetig Zeitstempel-Kollisionen
   durch das Suffix pruefen (zwei Backups "gleichzeitig" -> beide eindeutige Namen).
9. `test_backup_timestamp_sortable` (optional, staerkt E2/E3) — mehrere `_unique_backup_path`-
   Aufrufe mit demselben erzwungenen Zeitstempel liefern eindeutige, aufsteigend sortierbare
   Namen (`-01`, `-02`, …).
10. `test_rotation_ignores_foreign_files` — eine fremde Datei im `backup_dir` (z. B.
    `README.txt`) wird von der Rotation nicht geloescht.

## Verifikation

Alle Befehle mit `cwd = /Users/dirkhessenmueller/dev/modellbahn_2/.worktrees/anlagenmodell`:

- `python -m pytest tests/test_layout_store.py -q` — alle neuen Tests gruen.
- `python -m pytest -q` — bestehende Suite bleibt gruen (keine Regression).
- `ruff check src/modellbahn/domain/layout_store.py tests/test_layout_store.py` — keine Lint-Fehler.
- `ruff format --check src/modellbahn/domain/layout_store.py tests/test_layout_store.py` — formatiert.
- `mypy src/modellbahn/domain/layout_store.py` — strict, keine Typfehler.

## Umsetzungsreihenfolge (ein Schritt pro Punkt, jeder lässt das Repo baubar)

- [ ] 1. Modul `src/modellbahn/domain/layout_store.py` mit `load`/`save` und privaten Helfern
      gemaess Signaturen und Abläufen oben anlegen (E1–E7). Nur Standardbibliothek; Nutzung von
      `layout_codec.to_dict/from_dict` und `LayoutDecodeError`.
      Files: src/modellbahn/domain/layout_store.py
      Verify: `ruff check …` und `mypy src/modellbahn/domain/layout_store.py` fehlerfrei.

- [ ] 2. Tests `tests/test_layout_store.py` gemaess Testmatrix (Punkte 1–10) anlegen; `tmp_path`
      fuer Datei-/Backup-Verzeichnisse nutzen; Stil an `tests/test_layout_codec.py`.
      Files: tests/test_layout_store.py
      Verify: `python -m pytest tests/test_layout_store.py -q` — alle Tests gruen.

- [ ] 3. Gesamtqualitaet absichern.
      Files: (keine weiteren)
      Verify: `python -m pytest -q`, `ruff check`, `ruff format --check`,
      `mypy src/modellbahn/domain/layout_store.py` — alles sauber.

## Scope-Grenzen (Erinnerung)

Nur `layout_store.py` + `test_layout_store.py`. KEINE `config.py`-Settings (Aufgabe 8), KEINE
`app.py`-Verdrahtung/Laden-beim-Start (Aufgabe 10), kein Blockzustand, keine API/Frontend. Pfade
als Parameter. `layout_codec.py`/`layout.py` nur nutzen, nicht aendern. `tasks.md` NICHT abhaken.
