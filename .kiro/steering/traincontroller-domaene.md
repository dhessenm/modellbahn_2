---
inclusion: manual
---

# TrainController™ — Domänenwissen (Referenz)

> Abgeleitet aus `external_docs/Programmbeschreibung.pdf` — "RAILROAD & CO. TrainController™
> Gold und Silver, Version 10, Programmbeschreibung" (Freiwald Software, Januar 2025).
> Diese Datei fasst die Fachbegriffe und Konzepte der Domäne zusammen, an denen sich das
> Projekt orientiert. Im Zweifel ist das Original-PDF maßgeblich.

## Kontext

TrainController™ ist eine etablierte PC-Software zur Steuerung von Modellbahn-Anlagen
(Editionen Gold und Silver). Die Programmbeschreibung dient hier als fachliche Referenz für
Begriffe, Datenmodell und Betriebsabläufe einer Modellbahnsteuerung — unabhängig davon, in
welcher Sprache/Technik `modellbahn_2` umgesetzt wird.

## Zentrale Begriffe (Glossar)

- **Digitalsystem / Zentrale:** die angeschlossene Hardware, die Gleisbefehle erzeugt (im
  Projekt die Z21, siehe `z21-protokoll.md`). Mehrere Digitalsysteme können parallel genutzt
  werden.
- **Lok / Lokomotive:** steuerbares Fahrzeug mit (DCC-)Adresse, Geschwindigkeit, Fahrtrichtung
  und Funktionen (Licht, Sound usw.).
- **Mehrfachtraktion:** mehrere mechanisch gekoppelte Loks, die gemeinsam gesteuert werden.
- **Weiche / Zubehör / Stellwerk:** schaltbare Gleiselemente; im Gleisbildstellwerk wird die
  Anlage als Schema abgebildet und bedient.
- **Rückmelder:** Sensoren (Belegtmelder), die melden, ob ein Gleisabschnitt belegt ist.
- **Block:** logischer Gleisabschnitt zur Überwachung und Sicherung von Zugpositionen; Basis
  der Automatik. Rückmelder werden Blöcken zugeordnet.
- **Halteposition:** definierter Punkt innerhalb eines Blocks, an dem ein Zug anhält.
- **Zugfahrt:** gesicherte, geplante Fahrt eines Zuges über eine Folge von Blöcken.
- **AutoTrain™:** schnelles Starten einer gesicherten Fahrt per Drag & Drop.
- **Spontanfahrt:** manuelles Fahren ohne vollständige Streckenplanung.
- **CV (Configuration Variable):** Konfigurationsregister im Lokdecoder; wird gelesen/geschrieben
  (Decoderprogrammierung).

## Typische Betriebsabläufe

1. Digitalsystem einrichten und Verbindung testen (Gleisspannung ein/aus, Nothalt).
2. Loks anlegen (Adresse, Funktionen) und manuell steuern.
3. Weichen im Stellwerk anlegen und schalten.
4. Anlage in Blöcke aufteilen, Rückmelder den Blöcken zuordnen.
5. Zugpositionen überwachen; Fahrten manuell (Spontanfahrt), per AutoTrain oder als geplante
   Zugfahrt automatisch ausführen.
6. Sicherung: Blöcke verhindern Kollisionen; Nothalt-Zustände sauber behandeln.

## Leitlinien für die Umsetzung

- Dieselbe, etablierte Terminologie verwenden (Block, Rückmelder, Weiche, Zugfahrt,
  Halteposition), damit das Datenmodell für Modellbahner nachvollziehbar bleibt.
- Sicherheit priorisieren: Blocklogik und Nothalt sind sicherheitskritisch — Zustände müssen
  eindeutig und widerspruchsfrei sein.
- Die Steuerungslogik (Blöcke, Fahrten) von der konkreten Hardware-Anbindung (Z21-Protokoll)
  trennen, damit die Fachlogik unabhängig vom Digitalsystem testbar bleibt.
