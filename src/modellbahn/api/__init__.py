"""API-Schicht (FastAPI): REST-Endpunkte + Push-Kanal.

Duenne Schicht, die an die Fachlogik (domain) delegiert. Der Browser spricht
ausschliesslich mit dieser Schicht; die UDP-/Z21-Kommunikation bleibt im Backend.
"""

from modellbahn.api.app import create_app

__all__ = ["create_app"]
