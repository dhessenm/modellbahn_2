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

## Zielplattform und Schnittstelle

Die Anwenderoberfläche ist eine **Web-UI** — die Anwender bedienen die Modellbahn über den
Browser. Die Architektur ist Client-Server:

- **Backend (Python):** kommuniziert per Z21 LAN-Protokoll (UDP) mit der Zentrale und stellt
  dem Web-Client die Schnittstelle bereit.
- **Web-UI (Browser):** zeigt Stellwerk, Loks und Status an und sendet Bedienbefehle.

Schnittstellen-Vorgaben:

- **REST-API als primäre Schnittstelle:** So weit wie möglich sollen alle Z21-Protokollfunktionen
  über REST-Endpunkte bereitgestellt werden — Loksteuerung, Weichen/Zubehör, Rückmelder,
  Gleisspannung/Nothalt, CV-Programmierung sowie System-/Statusabfragen. Kommandos und
  Zustandsabfragen bilden sich natürlich auf REST ab.
- **WebSocket/SSE für Push:** Die Z21 sendet unaufgefordert Meldungen (Belegtmelder,
  Statusänderungen, Lok-Info). Da REST keinen Server-Push erlaubt, wird ergänzend ein
  Echtzeit-Kanal (WebSocket oder SSE) für diese Broadcast-Updates zur Web-UI genutzt. REST
  bleibt für Befehle/Abfragen, der Push-Kanal nur für asynchrone Zustandsänderungen.
- Die UDP-/Z21-Anbindung bleibt vollständig im Backend; der Browser spricht nie direkt mit der
  Zentrale.

## Zielgruppe

Modellbahner, die ihre Anlage per Computer digital steuern und (teil-)automatisieren möchten.
Die Bedienung erfolgt im Browser, geräteunabhängig (Desktop, Tablet).

## Leitprinzipien

- Etablierte Modellbahn-Terminologie verwenden (Block, Rückmelder, Weiche, Zugfahrt), damit
  das Produkt für Anwender vertraut ist.
- Sicherheit vor Komfort: Blocklogik und Nothalt sind sicherheitskritisch.
- Fachlogik unabhängig von der konkreten Zentrale halten, auch wenn aktuell nur die Z21
  angebunden wird.
- **Starke Entkopplung** anstreben: klar getrennte Schichten (Hardware/Protokoll ↔ Fachlogik ↔
  Schnittstelle) mit definierten Grenzen, sodass jede Schicht einzeln austauschbar und ohne die
  anderen testbar ist.
- **Niedrige Latenz als Qualitätsziel:** Die direkte, manuelle Steuerung (Lok fahren, Weichen
  schalten) muss sich unmittelbar anfühlen — ohne spürbare Verzögerung zwischen Bedienung und
  Reaktion an der Anlage. Dieses Ziel hat bei Design-Entscheidungen Vorrang auf dem
  Steuer-Pfad. Im automatisierten Betrieb ist Latenz weniger kritisch, mit **einer wichtigen
  Ausnahme**: der Pfad **Gleisbelegtmeldung → Stop-Befehl** (punktgenaues Anhalten) muss
  ebenfalls möglichst verzögerungsarm sein. Belegtmeldungen sollen so schnell wie möglich
  erkannt und verarbeitet werden.

## MVP (erste Version)

Ziel der ersten Version: **eine einzelne Lok über die Web-UI steuern** — als virtueller
Lokführerstand (Führerstand/Fahrpult) im Browser. Gesteuert wird ausschließlich im
**DCC**-Format.

Funktionsumfang:

- **Lokadresse angeben:** Der Anwender gibt die (DCC-)Adresse der zu steuernden Lok in der
  Web-UI ein. Damit wird festgelegt, welche Lok der Führerstand bedient.
- **Fahrfunktionen:** Geschwindigkeit einstellen und Fahrtrichtung wählen; Anhalten. (Z21:
  `LAN_X_SET_LOCO_DRIVE`, Rückmeldung über `LAN_X_LOCO_INFO`.)
- **Lokfunktionen:** Schalten der DCC-Funktionen (z. B. Licht, Sound) der adressierten Lok.
  (Z21: `LAN_X_SET_LOCO_FUNCTION`.)
- **Lokinformations-Frame:** ein Bereich in der Web-UI, der alle Lokinformationen als Text in
  **Key-Value-Paaren** anzeigt (z. B. `Geschwindigkeit: 42`, `Richtung: vorwärts`,
  `F0: ein`, `F1: aus`, …). Der Zustand kommt aus `LAN_X_LOCO_INFO` und wird bei Änderungen
  aktualisiert.
- **Gleisspannung (Track Power):** Ein- und Ausschalten der Gleisspannung über die UI, plus
  Anzeige des aktuellen Zustands (ein/aus, Nothalt/Kurzschluss). (Z21:
  `LAN_X_SET_TRACK_POWER_ON` / `LAN_X_SET_TRACK_POWER_OFF`, Status über `LAN_X_GET_STATUS`
  bzw. `LAN_SYSTEMSTATE_GETDATA`.)
- **Verbindungsanzeige:** Die UI zeigt an, ob eine Verbindung zur Z21-Zentrale besteht. Der
  Zustand ergibt sich im Backend aus erfolgreicher Kommunikation mit der Zentrale (siehe
  Keep-Alive unten).

### Keep-Alive (Z21-Timeout)

Die Z21 entfernt einen Client aus der Liste der aktiven Teilnehmer, wenn dieser nicht
mindestens **einmal pro Minute** (≈ 60 s) mit der Zentrale kommuniziert. Das **Backend** muss
daher ein **Keep-Alive** implementieren: in einem Intervall deutlich unter 60 s eine
Statusabfrage (z. B. `LAN_X_GET_STATUS` oder `LAN_SYSTEMSTATE_GETDATA`) senden, damit die
Verbindung bestehen bleibt. Bleiben Antworten aus, gilt die Verbindung als getrennt (steuert
die Verbindungsanzeige). Beim Beenden sollte sich der Client per `LAN_LOGOFF` sauber abmelden.

### UI-Aufbau und Erweiterbarkeit

Die Web-UI ist als **App mit mehreren Arbeitsbereichen** aufgebaut, nicht als Einzelseite —
damit künftige Funktionen ohne Umbau Platz finden:

- **Dashboard (Startseite):** zeigt den **Zentralenstatus** (Gleisspannung, Kurzschluss,
  Nothalt, Temperatur, Versorgungs-/Gleisspannung), die Verbindung und den Track-Power-Schalter.
- **Lokführerstand:** die manuelle Loksteuerung (siehe oben).
- **Gleisplan-Anzeige** und **Gleisplan-Modellierung:** als Bereiche bereits in der Navigation
  vorgesehen, Inhalt folgt später.
- Navigation zwischen den Bereichen über ein Menü in der App-Shell; die Verbindungsanzeige ist
  global sichtbar.

Bewusst **nicht** im MVP (für spätere Versionen):

- Weichen/Stellwerk, Blöcke, automatische Zugfahrten.
- **Gleisbelegtmeldung** über den Roco **Z21 Detector (10808)**, per **CAN-Bus** an die
  Zentrale angebunden.
- **RailCom** zur Identifikation von Loks (welche Lok belegt welchen Abschnitt), in Verbindung
  mit der Belegtmeldung.
- Mehrfachtraktion, Decoderprogrammierung (CV).
- Verwaltung mehrerer Loks gleichzeitig / Lok-Bibliothek.

Gleisprotokoll insgesamt: Das Projekt nutzt ausschließlich **DCC** zum Fahren und Steuern von
Loks und Zubehör (keine anderen Gleisformate).

## Noch zu klären

- Ob neben der Z21 weitere Digitalsysteme unterstützt werden sollen.

Siehe auch die Referenz-Steering-Dateien `z21-protokoll.md` und `traincontroller-domaene.md`
(manuell per `#` einbindbar).
