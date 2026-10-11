"""Abgeleiteter Laufzeit-Blockzustand (read-only, nicht persistiert).

Dieses Modul leitet aus dem statischen Block (`layout.Block`) und dem fluechtigen
Live-Zustand (`state.LayoutState`) den Laufzeit-Blockzustand ab: Belegung und die
per RailCom erkannten Lokadressen. Die Ableitung ist eine reine Funktion ohne
Seiteneffekte — sie greift nur LESEND auf `layout` und `state` zu, mutiert nichts
und persistiert nichts. Keine FastAPI-/HTTP-/UDP-Abhaengigkeit.

Leitprinzip „Belegung vor Identitaet": Die Belegung wird unabhaengig von der
Identitaet bestimmt; ein belegter Melder ohne RailCom-Erkennung liefert dennoch
`OCCUPIED` (dann mit leerer `loco_addresses`-Liste).

Sicherheitsrandfall (kein falsches Sicherheitsgefuehl): Ein Melder, der dem Block
zwar zugeordnet, aber noch nie live gesehen wurde, liefert keine Freimeldung. Ein
Block gilt nur dann als `FREE`, wenn mindestens ein zugeordneter Melder live
bekannt und nicht belegt ist. Ist kein zugeordneter Melder live bekannt, bleibt
die Belegung `UNKNOWN` (nicht `FREE`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .layout import Block, Layout
from .state import LayoutState

Occupancy = Literal["free", "occupied", "unknown"]
"""Belegungszustand eines Blocks (mypy-strict- und JSON-tauglich)."""

FREE: Occupancy = "free"
OCCUPIED: Occupancy = "occupied"
UNKNOWN: Occupancy = "unknown"


@dataclass(frozen=True)
class BlockRuntime:
    """Abgeleiteter Laufzeitzustand eines Blocks.

    `block_id` verweist auf den statischen Block. `occupancy` ist die abgeleitete
    Belegung. `loco_addresses` ist die deduplizierte, aufsteigend sortierte Menge
    der per RailCom erkannten Lokadressen (leere Liste = keine/unbekannte
    Identitaet). Unveraenderlich (frozen), da reine Ableitung.
    """

    block_id: str
    occupancy: Occupancy
    loco_addresses: list[int]


def derive_block_runtime(block: Block, state: LayoutState) -> BlockRuntime:
    """Leitet den Laufzeitzustand eines Blocks aus Live-Daten ab (read-only).

    Belegung: Ohne zugeordnete Melder `UNKNOWN`. Sonst wird je `DetectorAssignment`
    der `DetectorInput` ueber `(nid, port)` nachgeschlagen; nicht live bekannte
    Melder werden uebersprungen. Mindestens ein belegter -> `OCCUPIED`; sonst
    mindestens ein live bekannter freier -> `FREE`; sonst `UNKNOWN`.

    Identitaet: deduplizierte, aufsteigend sortierte Vereinigung der Lokadressen
    aus den `locos` aller zugeordneten, live bekannten Melder. Die Richtung wird
    fuer die Identitaetsmenge ignoriert.
    """
    if not block.detectors:
        return BlockRuntime(block_id=block.id, occupancy=UNKNOWN, loco_addresses=[])

    any_live = False
    any_occupied = False
    addresses: set[int] = set()
    for assignment in block.detectors:
        detector = state.detectors.get((assignment.detector_nid, assignment.detector_port))
        if detector is None:
            continue
        any_live = True
        if detector.occupied:
            any_occupied = True
        for address, _direction in detector.locos:
            addresses.add(address)

    if any_occupied:
        occupancy: Occupancy = OCCUPIED
    elif any_live:
        occupancy = FREE
    else:
        occupancy = UNKNOWN

    return BlockRuntime(block_id=block.id, occupancy=occupancy, loco_addresses=sorted(addresses))


def derive_all_block_runtimes(layout: Layout, state: LayoutState) -> list[BlockRuntime]:
    """Leitet den Laufzeitzustand aller Bloecke ab (ein Eintrag je Block).

    Liefert die `BlockRuntime`-Eintraege in Einfuegereihenfolge der Bloecke.
    Reiner, read-only Durchlauf ueber `layout.blocks`.
    """
    return [derive_block_runtime(block, state) for block in layout.blocks.values()]
