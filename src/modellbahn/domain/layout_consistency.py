"""Nicht-blockierende Konsistenz-WARNUNGEN fuer die Blockgeometrie.

Dieses Modul ist eine reine, zustandslose Konsistenzpruefung ueber EINEN
`Block` aus `layout.py`. Es meldet ausschliesslich WARNUNGEN (keine harten
Fehler): verdaechtige, aber nicht per se unzulaessige Geometrie-Angaben, die
der Anwender pruefen sollte. Harte Fachregeln und harte Fehler fuer unsinnige
Werte liegen dagegen im `LayoutService`.

Reine Standardbibliothek; keine IO-/FastAPI-/HTTP-/UDP-Abhaengigkeit. Die
Funktion ist ohne Service-/Layout-Aufbau isoliert testbar und kann spaeter von
der API direkt genutzt werden.

Geprueft werden:
- `laengensumme`: Summe der gesetzten Teillaengen weicht von der Blocklaenge ab.
- `teillaenge_fehlt`: nicht alle Melder haben eine Teillaenge (Summenpruefung
  dadurch unvollstaendig).
- `marke_ausserhalb`: eine virtuelle Positionsmarke liegt ausserhalb
  `[0, length_mm]`.
- `order_luecke`: die order-Werte der Melder sind nicht lueckenlos fortlaufend.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from modellbahn.domain.layout import Block, DirectionMarkers

WARN_LENGTH_SUM: Final = "laengensumme"
WARN_PARTIAL_LENGTH_MISSING: Final = "teillaenge_fehlt"
WARN_MARKER_OUT_OF_RANGE: Final = "marke_ausserhalb"
WARN_ORDER_GAP: Final = "order_luecke"


@dataclass(frozen=True)
class ConsistencyWarning:
    """Eine nicht-blockierende Konsistenz-Warnung.

    `code` ist ein stabiler, maschinell filterbarer Schluessel (eine der
    `WARN_*`-Konstanten); `message` eine verstaendliche deutsche Erlaeuterung.
    """

    code: str
    message: str


def block_consistency_warnings(block: Block) -> list[ConsistencyWarning]:
    """Ermittelt alle Konsistenz-Warnungen fuer EINEN Block.

    Gibt eine (ggf. leere) Liste zurueck; ein sauber konfigurierter Block
    liefert keine Warnung. Reihenfolge: Laengensumme, Teillaenge-fehlt,
    Marke-ausserhalb (forward.stop, forward.brake, backward.stop,
    backward.brake), order-Luecke.
    """
    warnings: list[ConsistencyWarning] = []
    warnings.extend(_length_sum_warnings(block))
    warnings.extend(_marker_warnings(block))
    warnings.extend(_order_gap_warnings(block))
    return warnings


def _length_sum_warnings(block: Block) -> list[ConsistencyWarning]:
    """Prueft Teillaengen-Summe und fehlende Teillaengen (nur bei gesetzter Blocklaenge)."""
    if block.length_mm is None or not block.detectors:
        return []
    partials = [a.length_mm for a in block.detectors if a.length_mm is not None]
    if not partials:
        return []
    warnings: list[ConsistencyWarning] = []
    total = sum(partials)
    if total != block.length_mm:
        warnings.append(
            ConsistencyWarning(
                WARN_LENGTH_SUM,
                f"Summe der Teillaengen ({total} mm) weicht von der "
                f"Blocklaenge ({block.length_mm} mm) ab.",
            )
        )
    if any(a.length_mm is None for a in block.detectors):
        warnings.append(
            ConsistencyWarning(
                WARN_PARTIAL_LENGTH_MISSING,
                "Nicht alle Melder haben eine Teillaenge; die Summenpruefung ist unvollstaendig.",
            )
        )
    return warnings


def _marker_warnings(block: Block) -> list[ConsistencyWarning]:
    """Prueft, ob virtuelle Positionsmarken ausserhalb [0, length_mm] liegen."""
    if block.length_mm is None:
        return []
    length = block.length_mm
    warnings: list[ConsistencyWarning] = []
    for markers, direction in (
        (block.markers_forward, "vorwaerts"),
        (block.markers_backward, "rueckwaerts"),
    ):
        warnings.extend(_direction_marker_warnings(markers, direction, length))
    return warnings


def _direction_marker_warnings(
    markers: DirectionMarkers, direction: str, length: int
) -> list[ConsistencyWarning]:
    """Prueft Halt- und Bremsmarke einer Fahrtrichtung gegen die Blocklaenge."""
    warnings: list[ConsistencyWarning] = []
    for marker, label in ((markers.stop, "Haltemarke"), (markers.brake, "Bremsmarke")):
        if marker is None or marker.position_mm is None:
            continue
        position = marker.position_mm
        if position < 0 or position > length:
            warnings.append(
                ConsistencyWarning(
                    WARN_MARKER_OUT_OF_RANGE,
                    f"{label} {direction} ({position} mm) liegt ausserhalb der "
                    f"Blocklaenge ({length} mm).",
                )
            )
    return warnings


def _order_gap_warnings(block: Block) -> list[ConsistencyWarning]:
    """Prueft, ob die order-Werte der Melder lueckenlos fortlaufend sind.

    Doppelte order-Werte sind ein harter Fehler aus Aufgabe 3 und werden hier
    dedupliziert, damit nicht faelschlich eine Luecke gemeldet wird. Der
    Startwert ist nicht auf 0 fixiert.
    """
    if len(block.detectors) < 2:
        return []
    orders = sorted({a.order for a in block.detectors})
    if orders[-1] - orders[0] + 1 == len(orders):
        return []
    return [
        ConsistencyWarning(
            WARN_ORDER_GAP,
            f"Die order-Werte der Melder sind nicht lueckenlos fortlaufend: {orders}.",
        )
    ]
