# Technologie-Stack

> Status: Es existiert noch kein Anwendungscode und keine Build-Konfiguration. Programmiersprache,
> Framework und Werkzeuge sind **noch nicht gewählt**. Bekannt sind bislang nur die externen
> technischen Rahmenbedingungen (Hardware-Protokoll). Diese Datei beim Festlegen des Stacks
> ergänzen.

## Externe Rahmenbedingungen (fix)

Diese ergeben sich aus der angebundenen Hardware und sind unabhängig von der Sprachwahl:

- **Digitalzentrale:** Z21 (Roco/Fleischmann), gesteuert über das **Z21 LAN-Protokoll** v1.13.
- **Transport:** UDP, Ports **21105** (bevorzugt) oder 21106.
- **Byte-Reihenfolge:** Little-Endian.
- **Nachrichtenformat:** Datensätze aus `DataLen (2 B) + Header (2 B) + Data`; X-Bus-Befehle
  unter Header `0x40` mit abschließender **XOR-Prüfsumme**.

Für Details siehe die Referenz-Steering-Datei `z21-protokoll.md` und das Original
`external_docs/z21-lan-protokoll.pdf`.

## Noch zu wählen

- Primäre Programmiersprache und Version.
- Framework(s) und zentrale Bibliotheken (insb. für UDP-Netzwerk und ggf. die
  Benutzeroberfläche), mit fixierten Versionen.
- Build-Werkzeug / Paketmanager.
- Linter und Formatter samt Konfigurationsdateien.
- Test-Framework.

## Technische Anforderungen an den Stack

Die Wahl sollte Folgendes gut unterstützen:

- **UDP-Netzwerkkommunikation** (Senden/Empfangen, asynchrone Broadcast-Meldungen der Zentrale).
- **Binäre Protokoll-Verarbeitung** (Little-Endian Serialisierung, Prüfsummen) — eine Sprache
  mit klarer Byte-/Buffer-Behandlung ist von Vorteil.
- Saubere Trennung zwischen Protokoll-/Hardware-Schicht und Fachlogik (Blöcke, Fahrten),
  damit die Fachlogik ohne reale Zentrale testbar ist.

## Häufige Befehle

Es sind noch keine Befehle definiert. Hier eintragen, sobald die Toolchain existiert, z. B.:

```sh
# Abhängigkeiten installieren
# <Befehl>

# bauen
# <Befehl>

# ausführen / Dev-Server
# <Befehl>

# testen
# <Befehl>

# Linten / Formatieren
# <Befehl>
```

## Konventionen

- Abhängigkeits-Versionen fixieren (keine offenen Versionsbereiche), sobald ein Manifest
  eingeführt wird.
- Gut gepflegte, weit verbreitete Bibliotheken bevorzugen.
- Die Z21-Anbindung hinter einer klar abgegrenzten Schnittstelle kapseln, damit die Fachlogik
  unabhängig vom Digitalsystem bleibt.
