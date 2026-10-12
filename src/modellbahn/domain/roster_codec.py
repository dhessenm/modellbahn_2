"""Serialisierung der Lok-Stammdaten zu/aus JSON-tauglichen Dicts.

Reine `dict`<->`dataclass`-Konvertierung des `Roster`-Modells aus `roster.py`
plus Pruefung der Schema-Version. Es wird nur die Standardbibliothek genutzt;
keine externen Libs, kein Pickle und kein `json.dumps/loads` (das Lesen/Schreiben
der Datei folgt in `roster_store`). Keine FastAPI-/HTTP-/UDP-Abhaengigkeit.

Zielstruktur (Top-Level EXAKT):

    {"version": 1, "locomotives": [...]}

Die Lokomotiven werden als Liste in Einfuegereihenfolge ausgegeben und beim
Laden nach `id` in das `dict`-Feld von `Roster` indiziert. Optionale Felder
werden immer als Schluessel mit `null` serialisiert (nie weggelassen); beim
Laden werden fehlende optionale Felder tolerant mit ihrem Default belegt.
"""

from __future__ import annotations

from modellbahn.domain.roster import Locomotive, Roster

SCHEMA_VERSION = 1

# Erlaubte Fahrstufenmodi (DCC: 14, 28, 128 Fahrstufen).
_ALLOWED_SPEED_STEPS = (14, 28, 128)


class RosterDecodeError(Exception):
    """Fehler beim Dekodieren eines Roster-Dicts (ungueltige Struktur/Version)."""


# ---------------------------------------------------------------------------
# Serialisierung (dataclass -> dict)
# ---------------------------------------------------------------------------


def to_dict(roster: Roster) -> dict[str, object]:
    """Serialisiert ein `Roster` in ein JSON-taugliches `dict`.

    Die Lokomotiven werden als Liste in Einfuegereihenfolge ausgegeben.
    Optionale Felder (`length_mm`, `max_speed_kmh`) sind immer als Schluessel
    mit `null` vorhanden.
    """
    return {
        "version": SCHEMA_VERSION,
        "locomotives": [_locomotive_to_dict(loco) for loco in roster.locomotives.values()],
    }


def _locomotive_to_dict(loco: Locomotive) -> dict[str, object]:
    return {
        "id": loco.id,
        "name": loco.name,
        "address": loco.address,
        "speed_steps": loco.speed_steps,
        "function_count": loco.function_count,
        "length_mm": loco.length_mm,
        "max_speed_kmh": loco.max_speed_kmh,
        "notes": loco.notes,
    }


# ---------------------------------------------------------------------------
# Deserialisierung (dict -> dataclass)
# ---------------------------------------------------------------------------


def from_dict(data: dict[str, object]) -> Roster:
    """Rekonstruiert ein `Roster` aus einem JSON-tauglichen `dict`.

    Prueft zuerst die Schema-Version, dann die Grundstruktur. Bei fehlender/
    unbekannter Version oder strukturell kaputtem Input wird `RosterDecodeError`
    mit deutscher Meldung geworfen (keine stille Falsch-Dekodierung).

    Pflichtfelder (`id`, `name`, `address`) muessen vorhanden sein. Optionale
    Felder (`speed_steps`, `function_count`, `length_mm`, `max_speed_kmh`,
    `notes`) werden tolerant mit ihrem Default belegt, falls sie fehlen. Ein
    gesetzter `speed_steps` muss in {14, 28, 128} liegen.
    """
    if not isinstance(data, dict):
        raise RosterDecodeError("Eingabe ist kein Objekt (dict erwartet).")

    _check_version(data.get("version"))

    roster = Roster(version=SCHEMA_VERSION)
    for raw in _require_list(data, "locomotives"):
        loco = _locomotive_from_dict(raw)
        roster.locomotives[loco.id] = loco
    return roster


def _check_version(version: object) -> None:
    # bool ist ein int-Subtyp; True/False ist keine gueltige Version.
    if version is None or isinstance(version, bool) or not isinstance(version, int):
        raise RosterDecodeError(
            f"Feld 'version' fehlt oder ist keine ganze Zahl (gefunden: {version!r})."
        )
    if version != SCHEMA_VERSION:
        raise RosterDecodeError(
            f"Unbekannte Schema-Version {version} (unterstuetzt: {SCHEMA_VERSION})."
        )


def _require_list(data: dict[str, object], key: str) -> list[object]:
    value = data.get(key)
    if not isinstance(value, list):
        raise RosterDecodeError(f"Feld '{key}' fehlt oder ist keine Liste.")
    return value


def _require_dict(raw: object, context: str) -> dict[str, object]:
    if not isinstance(raw, dict):
        raise RosterDecodeError(f"{context}: Eintrag ist kein Objekt (dict erwartet).")
    return raw


def _require_str(raw: dict[str, object], key: str, context: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str):
        raise RosterDecodeError(f"{context}: Pflichtfeld '{key}' fehlt oder ist kein String.")
    return value


def _require_int(raw: dict[str, object], key: str, context: str) -> int:
    value = raw.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise RosterDecodeError(f"{context}: Pflichtfeld '{key}' fehlt oder ist keine ganze Zahl.")
    return value


def _opt_int(raw: dict[str, object], key: str, context: str, default: int | None) -> int | None:
    value = raw.get(key, default)
    if value is None:
        return None
    # bool ist int-Subtyp, aber hier unerwuenscht.
    if isinstance(value, bool) or not isinstance(value, int):
        raise RosterDecodeError(f"{context}: Feld '{key}' ist keine ganze Zahl oder null.")
    return value


def _opt_str(raw: dict[str, object], key: str, context: str, default: str) -> str:
    value = raw.get(key, default)
    if not isinstance(value, str):
        raise RosterDecodeError(f"{context}: Feld '{key}' ist kein String.")
    return value


def _locomotive_from_dict(raw: object) -> Locomotive:
    obj = _require_dict(raw, "Lok")
    loco_id = _require_str(obj, "id", "Lok")
    context = f"Lok '{loco_id}'"
    name = _require_str(obj, "name", context)
    address = _require_int(obj, "address", context)

    speed_steps = obj.get("speed_steps", 128)
    if isinstance(speed_steps, bool) or not isinstance(speed_steps, int):
        raise RosterDecodeError(f"{context}: Feld 'speed_steps' ist keine ganze Zahl.")
    if speed_steps not in _ALLOWED_SPEED_STEPS:
        raise RosterDecodeError(
            f"{context}: ungueltiger speed_steps {speed_steps} "
            f"(erlaubt: {list(_ALLOWED_SPEED_STEPS)})."
        )

    function_count = obj.get("function_count", 28)
    if isinstance(function_count, bool) or not isinstance(function_count, int):
        raise RosterDecodeError(f"{context}: Feld 'function_count' ist keine ganze Zahl.")

    return Locomotive(
        id=loco_id,
        name=name,
        address=address,
        speed_steps=speed_steps,
        function_count=function_count,
        length_mm=_opt_int(obj, "length_mm", context, None),
        max_speed_kmh=_opt_int(obj, "max_speed_kmh", context, None),
        notes=_opt_str(obj, "notes", context, ""),
    )
