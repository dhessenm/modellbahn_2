# Projektstruktur

> Status: Das Repository befindet sich in einer frühen Phase. Es existiert noch kein
> Anwendungscode — bisher nur Steering-Dokumente und externe Referenzdokumentation. Dies
> beschreibt die aktuelle Struktur und die Konventionen für den Ausbau.

## Aktuelle Struktur

```
modellbahn_2/
├── .kiro/
│   └── steering/        # Steering-Dokumente für den KI-Assistenten (product.md, tech.md, structure.md)
└── external_docs/       # Externe Referenzdokumentation (nicht Teil des Quellcodes)
    ├── Programmbeschreibung.pdf    # Programmbeschreibung / Anforderungen
    └── z21-lan-protokoll.pdf       # Z21 LAN-Protokoll (Roco/Fleischmann Digitalzentrale)
```

Es existiert noch kein Anwendungs-, Test- oder Konfigurationscode.

## Verzeichnisse

- `.kiro/steering/` — Steering-Dokumente, die den KI-Assistenten anleiten. Aktuell halten.
- `external_docs/` — Externe Referenzen (PDFs) zu Produkt und Hardware-Protokoll. Dienen als
  Grundlage für Anforderungen und Implementierung, enthalten selbst keinen Code.

## Konventionen für die Zukunft

- Das Projekt-Wurzelverzeichnis übersichtlich halten: Quellcode in ein eigenes Verzeichnis
  (z. B. `src/`), Tests daneben oder in einem parallelen Verzeichnis gemäß den Gepflogenheiten
  des jeweiligen Ökosystems.
- Code nach Funktion/Domäne gruppieren, wo sinnvoll, statt nur nach Dateityp.
- Build-, Lint- und CI-Konfiguration im Wurzelverzeichnis ablegen.
- Referenzdokumente unter `external_docs/` belassen und nicht mit Quellcode vermischen.
- Die Dokumente unter `.kiro/steering/` aktuell halten — `product.md`, `tech.md` und diese
  Datei aktualisieren, sobald die reale Struktur, der Stack und die Produktdetails entstehen.

## Noch zu definieren

- Aufbau des obersten Quellcode-Verzeichnisses.
- Aufbau und Namensgebung des Test-Verzeichnisses.
- Wo Konfiguration, Assets und Dokumentation liegen.
