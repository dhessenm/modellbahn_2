"""Z21-Anbindung: Protokoll-Kodierung/-Dekodierung und UDP-Transport.

Diese Schicht kennt KEINE Fachlogik. Sie serialisiert/deserialisiert
Z21-LAN-Datensaetze und transportiert sie per UDP zur Zentrale.
"""

from modellbahn.z21.protocol import build_dataset, xbus_checksum

__all__ = ["build_dataset", "xbus_checksum"]
