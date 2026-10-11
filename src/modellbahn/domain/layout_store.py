"""Datei-Persistenz des statischen Anlagenmodells als JSON.

Dieses Modul liest und schreibt das `Layout`-Modell (aus `layout.py`) als JSON-
Datei. Die eigentliche `dict`<->`dataclass`-Umwandlung uebernimmt ausschliesslich
`layout_codec` (`to_dict`/`from_dict`); hier wird NICHT Feld fuer Feld serialisiert.
Es wird nur die Standardbibliothek genutzt (keine Fremdlibs, keine FastAPI/HTTP/UDP).

Eigenschaften (gemaess Design D2/D4/D5/D6, Anforderung 6):

- Schreiben ist **atomar**: der neue Stand wird in eine Temp-Datei im selben
  Zielverzeichnis geschrieben, mit `flush`+`os.fsync` auf Platte gebracht und per
  `os.replace` an die Zieldatei gesetzt. Dadurch gibt es keinen halb geschriebenen,
  korrupten Stand.
- Vor dem Ersetzen wird die bestehende Zieldatei optional als **versioniertes
  Backup** gesichert (`backup_dir`) und die Backups auf die `backup_count` neuesten
  **rotiert** (aeltere werden geloescht).
- Laden einer fehlenden Datei ergibt ein leeres `Layout()`. Eine vorhandene, aber
  kaputte Datei (ungueltiges JSON ODER ungueltiges Schema) fuehrt zu einer klaren
  `LayoutDecodeError` — es gibt KEINEN stillen Rueckfall auf ein leeres Modell.

Backup-Benennung: `layout-<UTC-Zeitstempel>.json` mit Zeitstempel-Format
`YYYYMMDDTHHMMSSffffff` (feste Breite, nur ASCII, dateisystemgueltig). Dadurch ist
die lexikografische Sortierung gleich der chronologischen. Entstehen in derselben
Mikrosekunde mehrere Backups, wird ein zweistelliges Suffix `-NN` angehaengt
(`layout-<ts>-01.json`, `-02`, …), damit die Namen eindeutig bleiben.

Pfade werden als Parameter uebergeben; dieses Modul kennt keinen festen Speicherort
(der Ablageort `conf/layout.json` wird erst in der App-Verdrahtung gesetzt).

Wiederherstellen eines Backups erfolgt in Stufe 1 **manuell** (Backup-Datei zurueck
nach `layout.json` kopieren); eine Restore-Funktion ist bewusst nicht Teil dieses
Moduls.
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

from modellbahn.domain.layout import Layout
from modellbahn.domain.layout_codec import LayoutDecodeError, from_dict, to_dict

TMP_SUFFIX = ".tmp"
BACKUP_PREFIX = "layout-"
BACKUP_SUFFIX = ".json"
DEFAULT_BACKUP_COUNT = 10


def load(path: str | Path) -> Layout:
    """Laedt das Layout aus 'path'.

    Fehlt die Datei, wird ein leeres `Layout()` zurueckgegeben. Enthaelt eine
    vorhandene Datei kein gueltiges JSON oder ein ungueltiges Schema, wird eine
    `LayoutDecodeError` mit deutscher Meldung geworfen (kein stiller Rueckfall auf
    ein leeres Modell).
    """
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8")
    except FileNotFoundError:
        return Layout()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as err:
        raise LayoutDecodeError(f"Modelldatei {p} enthaelt kein gueltiges JSON: {err}") from err

    return from_dict(data)


def save(
    path: str | Path,
    layout: Layout,
    backup_dir: str | Path | None = None,
    backup_count: int = DEFAULT_BACKUP_COUNT,
) -> None:
    """Schreibt 'layout' atomar als JSON nach 'path'.

    Das Zielverzeichnis wird bei Bedarf angelegt. Existiert bereits eine Zieldatei
    UND ist 'backup_dir' gesetzt, wird die bisherige Datei vor dem Ersetzen als
    versioniertes Backup dorthin kopiert und die Backups auf die 'backup_count'
    neuesten rotiert. Das JSON wird mit `ensure_ascii=False` und `indent=2`
    geschrieben.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    if backup_dir is not None and p.exists():
        backup_root = Path(backup_dir)
        backup_root.mkdir(parents=True, exist_ok=True)
        target = _unique_backup_path(backup_root, _backup_timestamp())
        shutil.copy2(p, target)
        _rotate_backups(backup_root, backup_count)

    payload = json.dumps(to_dict(layout), ensure_ascii=False, indent=2) + "\n"

    tmp = p.with_name(p.name + TMP_SUFFIX)
    try:
        with open(tmp, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, p)
    except BaseException:
        # Keine Temp-Reste hinterlassen, falls das Schreiben/Ersetzen scheitert.
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def _backup_timestamp() -> str:
    """Liefert einen UTC-Zeitstempel 'YYYYMMDDTHHMMSSffffff' fester Breite.

    Nur ASCII, keine Doppelpunkte/Pluszeichen; dadurch dateisystemgueltig und
    lexikografisch == chronologisch sortierbar.
    """
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")


def _unique_backup_path(backup_dir: Path, timestamp: str) -> Path:
    """Bestimmt einen im 'backup_dir' noch freien Backup-Pfad fuer 'timestamp'.

    Ist `layout-<ts>.json` bereits vorhanden (gleiche Mikrosekunde), wird ein
    zweistelliges Suffix `-01`, `-02`, … angehaengt, bis ein freier Name gefunden
    ist. Das feste Breitensuffix erhaelt die lexikografische Ordnung.
    """
    candidate = backup_dir / f"{BACKUP_PREFIX}{timestamp}{BACKUP_SUFFIX}"
    if not candidate.exists():
        return candidate
    counter = 1
    while True:
        candidate = backup_dir / f"{BACKUP_PREFIX}{timestamp}-{counter:02d}{BACKUP_SUFFIX}"
        if not candidate.exists():
            return candidate
        counter += 1


def _rotate_backups(backup_dir: Path, backup_count: int) -> None:
    """Behaelt nur die 'backup_count' neuesten Backups im 'backup_dir'.

    Beruecksichtigt ausschliesslich Dateien nach dem Backup-Namensschema
    (`layout-*.json`); fremde Dateien bleiben unberuehrt. Bei `backup_count <= 0`
    werden alle Backups entfernt.
    """
    backups = sorted(
        entry
        for entry in backup_dir.iterdir()
        if entry.is_file()
        and entry.name.startswith(BACKUP_PREFIX)
        and entry.name.endswith(BACKUP_SUFFIX)
    )
    if backup_count <= 0:
        obsolete = backups
    else:
        obsolete = backups[:-backup_count] if len(backups) > backup_count else []
    for entry in obsolete:
        entry.unlink()
