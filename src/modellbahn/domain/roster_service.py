"""Fachlogik-Service fuer die Lok-Stammdaten (`Roster`).

Der `RosterService` kapselt genau ein `Roster` aus `roster.py` und ist der
einzige Weg, es zu veraendern. Alle Mutationen (Lok anlegen, aendern, loeschen)
laufen ueber den Service und werden VOR dem Schreiben hart validiert: schlaegt
eine Validierung fehl, bleibt das Modell unveraendert.

Bewusste Abgrenzung: Dieses Modul macht KEINE Datei-IO/Persistenz (das uebernimmt
`roster_store`), KEINE API/HTTP-Bindung und kennt keinen fluechtigen Live-Zustand
der Lok. Reine Standardbibliothek; keine FastAPI-/HTTP-/UDP-Abhaengigkeit.

Harte Fachregel-Verstoesse werden als domaeneneigene `RosterValidationError`
(erbt von `ValueError`, kein HTTP-Bezug) geworfen. Die Adress-Doppelbelegung ist
KEIN harter Fehler, sondern eine weiche `RosterWarning` (code + message), die
ueber `address_warnings` abgefragt wird. IDs vergibt ausschliesslich der Service
(UUID4 als 32-Zeichen-Hex).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum

from modellbahn.domain.roster import Locomotive, Roster

# Erlaubte Fahrstufenmodi (DCC: 14, 28, 128 Fahrstufen).
_ALLOWED_SPEED_STEPS = (14, 28, 128)

# Grenzen fuer die DCC-Adresse und die Funktionsanzahl.
_MIN_ADDRESS = 1
_MAX_ADDRESS = 9999
_MIN_FUNCTION_COUNT = 0
_MAX_FUNCTION_COUNT = 28

WARN_ADDRESS_DUPLICATE = "adresse_doppelt"


class RosterValidationError(ValueError):
    """Harte Verletzung einer Lok-Fachregel (deutsche Meldung).

    Domaeneneigen und ohne HTTP-Bezug. Erbt von `ValueError`, damit Aufrufer
    Fachfehler als Wertfehler behandeln koennen; die spaetere API bildet dies
    selbst auf einen passenden Statuscode ab.
    """


@dataclass(frozen=True)
class RosterWarning:
    """Eine nicht-blockierende Hinweis-Warnung zu einer Lok.

    `code` ist ein stabiler, maschinell filterbarer Schluessel (z. B.
    `WARN_ADDRESS_DUPLICATE`); `message` eine verstaendliche deutsche
    Erlaeuterung.
    """

    code: str
    message: str


class _Unset(Enum):
    """Sentinel-Typ fuer "nicht uebergeben" bei optionalen Feldern.

    `None` ist bei `update_locomotive` fuer `length_mm`/`max_speed_kmh` ein
    gueltiger Zielwert (auf "nicht gesetzt" zuruecksetzen) und kann daher nicht
    "unveraendert" bedeuten. Als Enum ist der Sentinel fuer mypy sauber
    typisierbar (`int | None | _Unset`).
    """

    TOKEN = 0


_UNSET = _Unset.TOKEN


class RosterService:
    """Kapselt ein `Roster` und uebernimmt alle Mutationen samt Validierung."""

    def __init__(self, roster: Roster | None = None) -> None:
        """Haelt das uebergebene `Roster` oder legt ein leeres an."""
        self.roster = roster if roster is not None else Roster()

    # ------------------------------------------------------------------
    # Interne Helfer
    # ------------------------------------------------------------------
    @staticmethod
    def _new_id() -> str:
        """Erzeugt eine neue, kollisionsfreie Lok-ID (UUID4-Hex)."""
        return uuid.uuid4().hex

    @staticmethod
    def _norm(name: str) -> str:
        """Normalisiert einen Namen fuer den Eindeutigkeitsvergleich.

        Vergleich case-insensitive nach `strip()`; `casefold()` ist robuster als
        `lower()` (z. B. fuer "ss"/"ss").
        """
        return name.strip().casefold()

    @staticmethod
    def _require_nonempty_name(name: str) -> str:
        """Stellt sicher, dass ein Name nach `strip()` nicht leer ist."""
        if not name.strip():
            raise RosterValidationError("Name darf nicht leer sein.")
        return name

    def _require_locomotive(self, loco_id: str) -> Locomotive:
        loco = self.roster.locomotives.get(loco_id)
        if loco is None:
            raise RosterValidationError(f"Unbekannte Lok-ID: {loco_id!r}.")
        return loco

    def _check_name_unique(self, name: str, *, exclude_id: str | None = None) -> None:
        """Prueft die Namenseindeutigkeit ueber alle Loks.

        Vergleicht `_norm(name)` gegen alle vorhandenen Namen; `exclude_id`
        schliesst die eigene Lok aus (Umbenennen auf den eigenen Namen ist
        erlaubt).
        """
        target = self._norm(name)
        for loco_id, loco in self.roster.locomotives.items():
            if loco_id == exclude_id:
                continue
            if self._norm(loco.name) == target:
                raise RosterValidationError(
                    f"Lok-Name {name!r} ist bereits vergeben (gegen {loco.name!r})."
                )

    @staticmethod
    def _validate_address(address: int) -> None:
        """Prueft, dass die DCC-Adresse im gueltigen Bereich liegt."""
        if address < _MIN_ADDRESS or address > _MAX_ADDRESS:
            raise RosterValidationError(
                f"DCC-Adresse muss zwischen {_MIN_ADDRESS} und {_MAX_ADDRESS} liegen."
            )

    @staticmethod
    def _validate_speed_steps(speed_steps: int) -> None:
        """Prueft, dass der Fahrstufenmodus in {14, 28, 128} liegt."""
        if speed_steps not in _ALLOWED_SPEED_STEPS:
            raise RosterValidationError(
                f"speed_steps muss einer von {list(_ALLOWED_SPEED_STEPS)} sein."
            )

    @staticmethod
    def _validate_function_count(function_count: int) -> None:
        """Prueft, dass die Funktionsanzahl im Bereich 0..28 liegt."""
        if function_count < _MIN_FUNCTION_COUNT or function_count > _MAX_FUNCTION_COUNT:
            raise RosterValidationError(
                f"function_count muss zwischen {_MIN_FUNCTION_COUNT} und "
                f"{_MAX_FUNCTION_COUNT} liegen."
            )

    @staticmethod
    def _validate_non_negative(value: int | None, label: str) -> None:
        """Wirft bei negativem Wert; `None` ist erlaubt (nicht gesetzt)."""
        if value is not None and value < 0:
            raise RosterValidationError(f"{label} darf nicht negativ sein.")

    # ------------------------------------------------------------------
    # Lok-CRUD
    # ------------------------------------------------------------------
    def create_locomotive(
        self,
        name: str,
        address: int,
        speed_steps: int = 128,
        function_count: int = 28,
        length_mm: int | None = None,
        max_speed_kmh: int | None = None,
        notes: str = "",
    ) -> Locomotive:
        """Legt eine neue Lok an und gibt sie mit vergebener ID zurueck.

        Validiert vollstaendig vor der Mutation; bei Fehler bleibt das Roster
        unveraendert. Eine doppelte Adresse ist KEIN Fehler (siehe
        `address_warnings`).
        """
        self._require_nonempty_name(name)
        self._check_name_unique(name)
        self._validate_address(address)
        self._validate_speed_steps(speed_steps)
        self._validate_function_count(function_count)
        self._validate_non_negative(length_mm, "Laenge")
        self._validate_non_negative(max_speed_kmh, "Hoechstgeschwindigkeit")
        loco = Locomotive(
            id=self._new_id(),
            name=name,
            address=address,
            speed_steps=speed_steps,
            function_count=function_count,
            length_mm=length_mm,
            max_speed_kmh=max_speed_kmh,
            notes=notes,
        )
        self.roster.locomotives[loco.id] = loco
        return loco

    def update_locomotive(
        self,
        loco_id: str,
        *,
        name: str | None = None,
        address: int | None = None,
        speed_steps: int | None = None,
        function_count: int | None = None,
        length_mm: int | None | _Unset = _UNSET,
        max_speed_kmh: int | None | _Unset = _UNSET,
        notes: str | None = None,
    ) -> Locomotive:
        """Aktualisiert einzelne Felder einer Lok (None = unveraendert).

        Da `None` fuer `length_mm`/`max_speed_kmh` ein gueltiger Zielwert ist
        (auf "nicht gesetzt" zuruecksetzen), unterscheidet ein Sentinel `_UNSET`
        zwischen "nicht uebergeben" und "auf None setzen". Validiert vollstaendig
        vor der Mutation; bei Fehler bleibt die Lok unveraendert.
        """
        loco = self._require_locomotive(loco_id)
        if name is not None:
            self._require_nonempty_name(name)
            self._check_name_unique(name, exclude_id=loco_id)
        if address is not None:
            self._validate_address(address)
        if speed_steps is not None:
            self._validate_speed_steps(speed_steps)
        if function_count is not None:
            self._validate_function_count(function_count)
        if length_mm is not _UNSET:
            self._validate_non_negative(length_mm, "Laenge")
        if max_speed_kmh is not _UNSET:
            self._validate_non_negative(max_speed_kmh, "Hoechstgeschwindigkeit")

        if name is not None:
            loco.name = name
        if address is not None:
            loco.address = address
        if speed_steps is not None:
            loco.speed_steps = speed_steps
        if function_count is not None:
            loco.function_count = function_count
        if length_mm is not _UNSET:
            loco.length_mm = length_mm
        if max_speed_kmh is not _UNSET:
            loco.max_speed_kmh = max_speed_kmh
        if notes is not None:
            loco.notes = notes
        return loco

    def delete_locomotive(self, loco_id: str) -> None:
        """Loescht eine Lok.

        In Stufe 1 verweist nichts auf eine Lok (keine Zug-Objekte); Loks sind
        daher immer loeschbar (nur die Existenz wird geprueft).
        """
        self._require_locomotive(loco_id)
        del self.roster.locomotives[loco_id]

    def get_locomotive(self, loco_id: str) -> Locomotive:
        """Liefert die Lok zur ID oder wirft `RosterValidationError`."""
        return self._require_locomotive(loco_id)

    def list_locomotives(self) -> list[Locomotive]:
        """Liefert alle Loks in Einfuegereihenfolge."""
        return list(self.roster.locomotives.values())

    def address_warnings(self, loco_id: str) -> list[RosterWarning]:
        """Ermittelt Adress-Doppelbelegungs-Warnungen fuer EINE Lok.

        Gibt je ANDERER Lok mit derselben DCC-Adresse eine Warnung mit code
        `adresse_doppelt` zurueck. Doppelte Adressen sind erlaubt; dies ist nur
        ein Hinweis fuer den Anwender, kein Fehler. Gibt eine (ggf. leere) Liste
        zurueck.
        """
        loco = self._require_locomotive(loco_id)
        warnings: list[RosterWarning] = []
        for other_id, other in self.roster.locomotives.items():
            if other_id == loco_id:
                continue
            if other.address == loco.address:
                warnings.append(
                    RosterWarning(
                        WARN_ADDRESS_DUPLICATE,
                        f"Adresse {loco.address} ist bereits der Lok "
                        f"'{other.name}' zugeordnet.",
                    )
                )
        return warnings
