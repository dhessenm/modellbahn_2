# Produkt

> Status: frühe Projektphase. Zweck und Rahmenbedingungen sind aus der Referenzdokumentation
> unter `external_docs/` abgeleitet; es existiert noch kein Anwendungscode. Diese Datei
> aktualisieren, sobald konkrete Anforderungen und Code entstehen.

## Überblick

`modellbahn_2` ist eine Software zur Steuerung einer digitalen Modellbahn-Anlage — vermutlich
die zweite Iteration eines früheren Versuchs. Die Anlage wird über eine **Z21-Digitalzentrale**
(Roco/Fleischmann) per Netzwerk angesteuert. Fachlich orientiert sich das Projekt an den
etablierten Konzepten der Steuerungssoftware **TrainController™**.

Grundlage dieser Einordnung sind die beiden Referenzdokumente in `external_docs/`:

- **z21-lan-protokoll.pdf** — Z21 LAN Protokoll Spezifikation v1.13 (Hardware-Anbindung).
- **Programmbeschreibung.pdf** — TrainController™ Gold/Silver v10 (fachliche Konzepte).

## Zweck und Funktionsumfang (angestrebt)

- **Loksteuerung:** Geschwindigkeit, Fahrtrichtung und Funktionen (Licht, Sound) einzelner
  Loks sowie Mehrfachtraktionen.
- **Weichen/Zubehör:** Schalten von Weichen und Zubehörartikeln, Abbildung im Stellwerk.
- **Rückmeldung:** Auslesen von Belegtmeldern zur Ermittlung von Zugpositionen.
- **Blocksteuerung:** Aufteilung der Anlage in Blöcke zur Überwachung und Sicherung.
- **Automatik:** geplante Zugfahrten über Blockfolgen, inkl. Haltepositionen; manuelle
  Spontanfahrten bleiben möglich.
- **Decoderprogrammierung:** Lesen/Schreiben von CVs.

## Zielgruppe

Modellbahner, die ihre Anlage per Computer digital steuern und (teil-)automatisieren möchten.

## Leitprinzipien

- Etablierte Modellbahn-Terminologie verwenden (Block, Rückmelder, Weiche, Zugfahrt), damit
  das Produkt für Anwender vertraut ist.
- Sicherheit vor Komfort: Blocklogik und Nothalt sind sicherheitskritisch.
- Fachlogik unabhängig von der konkreten Zentrale halten, auch wenn aktuell nur die Z21
  angebunden wird.

## Noch zu klären

- Zielplattform(en) und Bedienoberfläche (Desktop, Web, Mobil).
- Genauer Funktionsumfang der ersten Version (MVP).
- Ob neben der Z21 weitere Digitalsysteme unterstützt werden sollen.

Siehe auch die Referenz-Steering-Dateien `z21-protokoll.md` und `traincontroller-domaene.md`
(manuell per `#` einbindbar).
