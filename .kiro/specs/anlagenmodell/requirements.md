# Anforderungen — Statisches Anlagenmodell (Stufe 1)

> Spec-Stufe 1 auf dem Weg zum automatischen Zugbetrieb. Diese Stufe schafft das
> **statische Anlagenmodell** (Topologie) mit **Persistenz** und einer **Editor-API**,
> plus eine schema-/listenartige Web-UI zum Pflegen und Ansehen. Bewusst **keine**
> Automatik, **keine** Verriegelung, **keine** Fahrstraßen-Ausführung — diese bauen in
> späteren Stufen darauf auf.
>
> Begriffe gemäß `.kiro/steering/traincontroller-domaene.md` (Block, Rückmelder, Fahrstraße,
> Zugfahrt, Halteposition). Architektur- und Latenzleitlinien gemäß `product.md`/`tech.md`/
> `structure.md`.

## Kontext und Abgrenzung

Bisher ist das Backend **zustandslos** im Sinne der Topologie: Es spiegelt nur den Live-Zustand
der Z21 (Loks, Weichen, Belegtmelder, Systemstatus). Für automatischen Betrieb braucht es ein
**persistentes Modell der Anlage** — welche Blöcke es gibt, welche Melder zu welchem Block
gehören, welche Fahrstraßen Blöcke über Weichen verbinden. Dieses Modell ist die erste echte
Persistenz im Projekt.

**Leitprinzip „Belegung vor Identität" (durchgängig in allen Stufen):**

- **Belegung** (`frei`/`belegt`) ist die primäre, verlässliche Wahrheit. Ein Block gilt als
  belegt, sobald **irgendein** zugeordneter Melder anschlägt — unabhängig von der Ursache
  (Lok **oder** antriebsloser Wagen ohne Adresse).
- **Identität** (`unbekannt`/`Lok N`) ist eine **optionale Anreicherung** aus RailCom. Liegt
  RailCom vor, wird sie genutzt; fehlt sie, bleibt der Block korrekt als belegt geführt, nur
  ohne bekannte Identität.
- Sicherheitsrelevante Logik (spätere Stufen) darf sich **nie** auf RailCom/Identität verlassen,
  immer nur auf Belegung.

In Stufe 1 wird dieses Prinzip im Datenmodell und in der abgeleiteten Blockanzeige verankert;
die sicherheitskritische Auswertung (Verriegelung, Stop) folgt in späteren Stufen.

## Was Stufe 1 ausdrücklich NICHT umfasst

- Keine automatische **Zugfahrt**, kein Stellen/Verriegeln/Auflösen von Fahrstraßen zur Laufzeit.
- Kein Kollisionsschutz, keine Blockreservierung, kein automatischer Stop.
- Keine automatische **Fahrstraßensuche/Routing** zwischen Blöcken (mehrere/parallele Wege sind
  im Modell möglich, werden aber nicht automatisch gefunden oder gewählt).
- Keine **Zug**- oder **Lok-Objekte** mit Eigenschaften (Zuglänge, Einmessdaten,
  DCC-Fahrstufe→Geschwindigkeit). Diese kommen mit der Fahrdynamik-/Automatik-Stufe.
- Keine **Bremskurvenberechnung / Einmessung**; die Markierungen/Längen werden nur modelliert,
  damit die spätere Berechnung darauf aufsetzen kann.
- Keine Maßstabsumrechnung (reale km/h → Modellgeschwindigkeit → DCC-Fahrstufe).
- Kein gezeichnetes Gleisbild (Geometrie/Raster) — nur schema-/listenartige Darstellung.
- Keine Zugverfolgung über Blockgrenzen hinweg (nur die aus Meldern **direkt** ableitbare
  Belegung/Identität je Block, read-only).

## Glossar (Stufe 1)

- **Block:** benannter logischer Gleisabschnitt mit stabiler ID und Anzeigenamen. Trägt
  geometrische/betriebliche Eigenschaften: Gesamtlänge (in **mm**, ganzzahlig),
  Höchstgeschwindigkeit (km/h, reale Bahn), Halte-/Bremsmarkierungen je Fahrtrichtung
  (siehe Anforderung 1).
- **Längeneinheit:** Alle Längen werden intern, in der API und in der Persistenz einheitlich in
  **Millimeter als ganze Zahl** (`int`) geführt. Begründung: keine Fließkommafehler beim
  Aufsummieren/Vergleichen von Teillängen, keine Scheingenauigkeit unter 1 mm. Die UI darf zur
  Anzeige/Eingabe cm verwenden, konvertiert dann aber verlustfrei auf ganze mm.
- **Belegtmelder (Melder):** physischer Eingang eines Z21 Detectors, identifiziert über
  `(nid, port)` (bestehende `DetectorInput`-Identität). Existiert unabhängig vom Modell und hat
  **selbst keine Länge**.
- **Melder→Block-Zuordnung:** ordnet einen Melder genau einem Block zu. Ein Block kann mehrere
  Melder haben; ein Melder gehört zu höchstens einem Block. Die Zuordnung — **nicht der Melder** —
  trägt die blockspezifische **Teillänge** und die **Anordnung** (Reihenfolge) des Melders im
  Block. Derselbe Melder hat nur innerhalb genau eines Blocks genau eine Länge.
- **Fahrstraße:** benannter gerichteter Weg von einem Startblock zu einem Zielblock, inklusive
  der Weichenstellungen entlang des Wegs und der dabei beanspruchten (durchfahrenen) Blöcke.
  Zwischen zwei Blöcken kann es **mehrere** Fahrstraßen geben (parallele/alternative Wege). In
  Stufe 1 nur **modelliert und gespeichert**, nicht ausgeführt und nicht automatisch gesucht.
- **Zug:** eine oder mehrere Loks, optional mit Wagen, als benennbare Zusammenstellung. Hat
  später eigene Eigenschaften (z. B. Zuglänge; Einmessdaten gehören zur **Lok**, nicht zum
  Anlagenmodell). **Nicht Teil von Stufe 1** — nur als Begriff geführt.
- **Zugfahrt:** die (später gesicherte, automatische) Fahrt eines Zuges von einem Startblock zu
  einem Zielblock — auch wenn der Zug nur aus einer Lok besteht. Dies ist der Begriff der
  **Automatik**. Abzugrenzen von der **Fahrstraße**: Die Fahrstraße ist der physische Weg (mit
  Weichenstellungen); die Zugfahrt ist der Auftrag „bringe Zug X von A nach B", der eine oder
  mehrere Fahrstraßen nutzt. **Nicht Teil von Stufe 1.**
- **Lok:** steuerbares Fahrzeug mit DCC-Adresse. Später ein eigenes Objekt mit Attributen, u. a.
  Einmessdaten (Zuordnung DCC-Fahrstufe → reale Geschwindigkeit) für Bremskurvenberechnung und
  punktgenaues Halten. **Nicht Teil von Stufe 1** — nur als Begriff geführt.
- **Halte-/Bremsmarkierung:** Punkt innerhalb eines Blocks, an dem ein Zug hält (Halt) bzw. ab
  dem er bremst (Bremse). Je **Fahrtrichtung** getrennt. Entweder direkt ein Melder (dessen
  Anschlagen das Ereignis ist) oder eine **virtuelle Positionsmarke** als Längenangabe (SI) ab
  Blockanfang, die über die Melder-Teillängen auf „welcher Melder, wie weit hinein" abgebildet
  wird. In Stufe 1 nur **modelliert**, nicht zur Laufzeit ausgewertet.
- **Blockzustand (abgeleitet):** zur Laufzeit aus den zugeordneten Meldern berechnet:
  Belegung = ODER über alle zugeordneten Melder; Identität = **Menge** der RailCom-Loks aller
  zugeordneten Melder (Doppeltraktion/mehrere Loks möglich). Read-only, nicht persistiert.

---

## Anforderungen

### Anforderung 1 — Blöcke modellieren und persistieren

**User Story:** Als Anwender möchte ich Blöcke mit ihren Eigenschaften anlegen, umbenennen und
löschen, damit ich meine Anlage in logische Abschnitte gliedern kann, die den automatischen
Betrieb später tragen.

**Akzeptanzkriterien:**

1. WENN der Anwender einen Block mit Namen anlegt, DANN erhält der Block eine stabile,
   eindeutige ID und wird persistent gespeichert.
2. WENN der Anwender einen Block umbenennt, DANN bleibt die ID unverändert und der neue Name
   wird persistiert, sofern er eindeutig ist (siehe Kriterium 4).
3. WENN der Anwender einen Block löscht, DER noch Melder-Zuordnungen oder Fahrstraßen-Bezüge
   hat, DANN verweigert das System das Löschen mit einer verständlichen Begründung ODER verlangt
   eine ausdrückliche Bestätigung (Entscheidung im Design) — ein inkonsistentes Modell darf
   nicht entstehen.
4. DER Blockname muss **eindeutig** sein (zusätzlich zur eindeutigen ID). WENN ein Block mit
   einem bereits vergebenen Namen angelegt ODER ein Block auf einen bereits vergebenen Namen
   umbenannt werden soll, DANN lehnt das System dies mit verständlichem Fehler ab und ändert
   nichts. Die genaue Vergleichsregel (z. B. Groß-/Kleinschreibung, führende/abschließende
   Leerzeichen) legt das Design fest.
5. WENN das Backend neu startet, DANN sind alle zuvor gespeicherten Blöcke unverändert vorhanden.
6. DER Anwender KANN je Block eine **Gesamtlänge in mm** (ganzzahlig) konfigurieren. Die Länge
   ist optional, aber Voraussetzung für virtuelle Positionsmarken (Kriterium 8). Die UI darf cm
   anzeigen/eingeben, speichert aber ganze mm.
7. DER Anwender KANN je Block eine **Höchstgeschwindigkeit in km/h** konfigurieren. Diese bezieht
   sich auf die **reale Bahn** (Vorbild), nicht auf das Modell; die Umrechnung auf Maßstab und
   DCC-Fahrstufe erfolgt bewusst **erst später** und ist nicht Teil von Stufe 1.
8. DER Anwender KANN je Block **Halte- und (optional) Bremsmarkierungen getrennt für beide
   Fahrtrichtungen** festlegen. Eine Markierung ist entweder ein zugeordneter Melder oder eine
   virtuelle Positionsmarke als Längenangabe in **mm** (ganzzahlig) ab Blockanfang. Zum späteren
   Beenden einer
   Zugfahrt in einem Block ist eine Haltemarkierung für die betreffende Richtung nötig; in
   Stufe 1 wird sie nur modelliert, nicht erzwungen oder ausgewertet.
9. WENN eine virtuelle Positionsmarke oder Teillängen gesetzt sind, DANN KANN das System eine
   Konsistenzprüfung anbieten (z. B. Summe der Melder-Teillängen = Blocklänge; Marke liegt
   innerhalb der Blocklänge) und Abweichungen als Warnung melden, ohne das Speichern zwingend zu
   verhindern (Design legt fest, was Fehler vs. Warnung ist).

### Anforderung 2 — Melder den Blöcken zuordnen

**User Story:** Als Anwender möchte ich Belegtmelder einem Block zuordnen, damit das System weiß,
welche physischen Sensoren zu welchem logischen Abschnitt gehören.

**Akzeptanzkriterien:**

1. WENN der Anwender einen Melder `(nid, port)` einem Block zuordnet, DANN wird die Zuordnung
   persistiert.
2. WENN ein Melder bereits einem Block zugeordnet ist UND einem anderen Block zugeordnet werden
   soll, DANN wird die alte Zuordnung ersetzt (ein Melder gehört zu höchstens einem Block).
3. WENN der Anwender eine Zuordnung entfernt, DANN ist der Melder danach keinem Block mehr
   zugeordnet und dies ist persistiert.
4. WENN ein Melder zugeordnet wird, DER aktuell (noch) nicht live gesehen wurde, DANN ist die
   Zuordnung dennoch möglich (das Modell ist unabhängig davon, ob der Melder gerade sendet).
5. DAS System KANN pro Melder vermerken, ob er RailCom-Identität liefert (für die spätere
   Identitäts-Aggregation), ODER dies wird zur Laufzeit aus den Live-Daten erkannt (Design
   entscheidet).
6. DIE Zuordnung — nicht der Melder — trägt eine **Anordnung** (Reihenfolge/Position des Melders
   innerhalb des Blocks) und eine optionale **Teillänge in mm** (ganzzahlig). Derselbe Melder hat
   außerhalb dieses Blocks keine Länge; die Länge gilt nur innerhalb genau dieses Blocks.
7. WENN mehrere Melder einem Block zugeordnet sind, DANN ist ihre Anordnung eindeutig
   (keine doppelten Positionen); das Modell erlaubt die ideale Konfiguration „nahtlos
   hintereinander, Summe der Teillängen = Blocklänge" (Konsistenzprüfung siehe Anforderung 1.9).

### Anforderung 3 — Weichen, Kreuzungen und schaltbare Elemente modellieren

**User Story:** Als Anwender möchte ich Weichen, Doppelkreuzungsweichen und starre Kreuzungen als
Topologie-Elemente anlegen, damit Fahrstraßen die Verbindungen zwischen Blöcken und die nötigen
Stellungen präzise beschreiben können.

**Hintergrund:** Weichen existieren bereits als *steuerbares Live-Element* (`TurnoutState`:
Adresse, Position 0/1). Diese Anforderung ergänzt das **Topologie-/Modellobjekt**, auf das
Fahrstraßen verweisen. Die Topologie wird bewusst **vollständig** modelliert (auch nicht
schaltbare Elemente), damit sie als Grundlage für die spätere Verriegelung komplett ist.

**Akzeptanzkriterien:**

1. DAS Modell unterscheidet Topologie-Elemente mindestens nach Typ: **Weiche** (schaltbar, eine
   DCC-Zubehöradresse, Stellung 0/1), **Doppelkreuzungsweiche (DKW)** (schaltbar, mehr als zwei
   Zustände) und **starre Kreuzung** (nicht schaltbar, keine Adresse). Jedes Element hat eine
   stabile ID und einen eindeutigen Anzeigenamen.
2. WENN der Anwender ein schaltbares Element anlegt, DANN gibt er dessen DCC-Zubehöradresse(n)
   an; das Element wird persistiert und kann in Fahrstraßen referenziert werden.
3. DAS Modell MUSS eine **DKW korrekt abbilden** können — mehr als zwei Zustände und (in DCC
   üblich) ggf. mehr als eine Zubehöradresse. Die konkrete Repräsentation (eigener Typ mit zwei
   Adressen vs. Komposition aus zwei logischen Weichen) legt das Design fest.
4. EINE **starre Kreuzung** trägt **keine** Adresse und wird **nicht** geschaltet; sie dient nur
   als Topologie-/Verriegelungsressource. In Stufe 1 wird sie modelliert, aber nicht aktiv
   genutzt (keine Verriegelung).
5. WENN der Anwender ein Element ändert oder löscht, DAS noch von einer Fahrstraße referenziert
   wird, DANN wahrt das System die Konsistenz (Ablehnung oder Bestätigung analog zur
   Block-Löschsemantik; Design entscheidet).
6. DER Elementname muss **eindeutig** sein (analog zu Blocknamen); IDs sind in jedem Fall
   eindeutig.
7. WENN das Backend neu startet, DANN sind alle Topologie-Elemente unverändert vorhanden.

### Anforderung 4 — Fahrstraßen modellieren und persistieren

**User Story:** Als Anwender möchte ich Fahrstraßen zwischen Blöcken anlegen, die durchfahrene
Blöcke und die nötigen Element-Stellungen festhalten, damit später eine Automatik gesicherte
Wege stellen kann.

**Akzeptanzkriterien:**

1. WENN der Anwender eine Fahrstraße anlegt, DANN gibt er an: **Startblock**, optional eine
   geordnete Folge **durchfahrener Zwischenblöcke**, **Zielblock**, die geordnete Liste der
   **Element-Stellungen** entlang des Wegs (Referenz auf ein schaltbares Element aus
   Anforderung 3 + geforderte Soll-Stellung) sowie die entlang des Wegs **beanspruchten**
   Elemente (auch starre Kreuzungen). Die Fahrstraße erhält eine stabile ID und wird persistiert.
2. WENN eine Fahrstraße auf einen Block oder ein Topologie-Element verweist, DANN muss dieses im
   Modell **existieren** (Verweis über ID); sonst wird die Fahrstraße abgelehnt.
3. WENN der Anwender eine Fahrstraße ändert oder löscht, DANN wird die Änderung persistiert und
   die Konsistenz der Verweise gewahrt.
4. DIE Fahrstraße ist gerichtet (Start→Ziel); eine Gegenrichtung ist eine eigene Fahrstraße
   (Design kann einen Komfort-Weg zum Spiegeln vorsehen, ist aber nicht gefordert).
5. ZWISCHEN denselben zwei Blöcken dürfen **mehrere** Fahrstraßen existieren (parallele/
   alternative Wege, ggf. über unterschiedliche Zwischenblöcke und Element-Stellungen). Die
   automatische **Auswahl/Suche** eines Wegs ist nicht Teil von Stufe 1.
6. EINE starre Kreuzung kann als **beanspruchtes** Element in einer Fahrstraße vorkommen, aber
   **nicht** als Element-Stellung (sie wird nicht geschaltet).
7. IN Stufe 1 wird eine Fahrstraße ausschließlich gespeichert und angezeigt, **nicht** gestellt
   oder verriegelt.

### Anforderung 5 — Abgeleiteter Blockzustand (read-only)

**User Story:** Als Anwender möchte ich zu jedem Block sehen, ob er belegt ist und — falls
bekannt — welche Lok(s) darin stehen, damit ich das Modell gegen die reale Anlage prüfen kann.

**Akzeptanzkriterien:**

1. WENN mindestens ein dem Block zugeordneter Melder belegt ist, DANN wird der Block als
   **belegt** angezeigt; sind alle frei, als **frei**.
2. WENN zugeordnete Melder RailCom-Lokdaten liefern, DANN wird die **Menge** der erkannten
   Lok(en) als Identität des Blocks angezeigt (mehrere Loks sind möglich — z. B. Doppeltraktion,
   oder mehrere Loks über mehrere Melder desselben Blocks); liefert keiner RailCom, DANN ist die
   Identität **unbekannt**, der Belegungszustand bleibt davon unberührt.
3. WENN ein Block keine zugeordneten Melder hat, DANN ist sein Belegungszustand **unbekannt**
   (nicht „frei"), damit kein falsches Sicherheitsgefühl entsteht.
4. DER abgeleitete Blockzustand wird **nicht persistiert**; er wird aus dem Live-Zustand
   (`LayoutState.detectors`) und dem statischen Modell zur Laufzeit berechnet.
5. WENN sich ein zugeordneter Melder ändert (Broadcast), DANN spiegelt der abgeleitete
   Blockzustand dies zeitnah wider (über denselben SSE-Push-Mechanismus wie die Melderanzeige).
6. NACH dem Start von Software/Zentrale MUSS der Blockzustand den **tatsächlichen** Belegtzustand
   widerspiegeln, OHNE auf eine zufällige Änderung warten zu müssen. Da Broadcasts nur
   Änderungen liefern, ist ein aktives **Initial-Einlesen** aller Belegtmelder nötig (die
   bestehende Melderanzeige nutzt dafür bereits eine Initial-Abfrage beim Verbindungsaufbau
   sowie `POST /api/detectors/refresh`). Das genaue Vorgehen — einmalig vs. zur Robustheit
   mehrfach wiederholt, und ob die Block-UI einen eigenen Refresh anbietet oder den bestehenden
   mitnutzt — ist **Design-/Task-Thema**.

### Anforderung 6 — Persistenz des statischen Modells

**User Story:** Als Anwender möchte ich, dass mein Anlagenmodell dauerhaft erhalten bleibt,
damit ich es nicht nach jedem Neustart neu anlegen muss.

**Akzeptanzkriterien:**

1. DAS statische Modell (Blöcke, Topologie-Elemente, Melder-Zuordnungen, Fahrstraßen) wird in
   einer Datei im Projekt gespeichert (Ablageort wird im Design festgelegt).
2. WENN das Modell gespeichert wird, DANN geschieht dies **atomar** (kein halb geschriebener,
   korrupter Stand bei Absturz/Stromausfall).
3. WENN beim Start eine vorhandene Modelldatei gefunden wird, DANN wird sie geladen und
   validiert; ist sie ungültig, DANN startet das System mit klarer Fehlermeldung statt still
   mit falschem Modell.
4. WENN keine Modelldatei existiert, DANN startet das System mit einem leeren Modell.
5. DIE Modelldatei ist von der Laufzeitkonfiguration (`conf/config.toml`) getrennt; der
   Speicherort folgt den Projektkonventionen (Design legt ihn fest, z. B. unter `conf/` oder
   einem Datenverzeichnis) und enthält **keine** Geheimnisse. Format: **JSON** (maschinen-
   geschrieben, verschachtelungsfreundlich; bewusst getrennt vom menschlich gepflegten TOML).
6. BEIM Speichern SOLL der bisherige Modellstand als **versioniertes Backup** gesichert werden,
   bevor die aktuelle Datei ersetzt wird — zusätzlich zum atomaren Schreiben (Kriterium 2).
   Dadurch sind frühere Stände wiederherstellbar (z. B. nach versehentlichem Löschen). Die
   Backups werden **rotiert** (nur die letzten N Stände werden aufgehoben, ältere entfernt). Das
   *Erzeugen und Rotieren* der Backups ist automatisch; das *Wiederherstellen* erfolgt in
   Stufe 1 manuell (Datei zurückkopieren) — eine Recovery-UI ist nicht Teil von Stufe 1.
   Anzahl N, Benennung (Zeitstempel vs. laufende Nummer) und Ablageort legt das Design fest.

### Anforderung 7 — Editor-API (REST)

**User Story:** Als Frontend möchte ich das Anlagenmodell über REST lesen und bearbeiten, damit
die Web-UI es pflegen kann, konsistent mit der bestehenden API-Schicht.

**Akzeptanzkriterien:**

1. DIE API stellt Endpunkte zum Lesen des gesamten Modells sowie zum Anlegen/Ändern/Löschen von
   Blöcken, Topologie-Elementen (Weichen/DKW/Kreuzungen), Melder-Zuordnungen und Fahrstraßen
   bereit (konkrete Routen im Design).
2. WENN eine Bearbeitung das Modell inkonsistent machen würde (ungültige Verweise, doppelte
   Melder-Zuordnung entgegen Regel, doppelter Name), DANN lehnt die API mit einem klaren Fehler
   (4xx) ab und ändert nichts.
3. DIE API-Schicht bleibt **dünn** und delegiert alle Fachregeln an die `domain`-Schicht
   (Abhängigkeiten nach innen, gemäß `structure.md`).
4. DIE Fachlogik des Modells ist **ohne FastAPI/HTTP/UDP** testbar (reine `domain`-Logik gegen
   Mock-/Fake-Daten).
5. DIE Modelländerungen laufen **nicht** über den latenzkritischen Steuer-Pfad (Fahren/Stop)
   und dürfen diesen nicht beeinflussen (Editieren ist latenzunkritisch, gemäß `tech.md`).

### Anforderung 8 — Web-UI: Anlagenmodell pflegen und ansehen (schema-/listenartig)

**User Story:** Als Anwender möchte ich im Browser Blöcke, Topologie-Elemente, Melder-Zuordnungen
und Fahrstraßen in einer übersichtlichen Liste/Schemaform pflegen und den abgeleiteten
Blockzustand live sehen.

**Akzeptanzkriterien:**

1. DIE UI erhält einen eigenen Arbeitsbereich (neue Route in der App-Shell, gemäß
   `structure.md`), ohne die bestehenden Bereiche umzubauen.
2. DIE Darstellung ist **listen-/schemaartig** (Blöcke/Elemente als Liste/Kacheln, Verbindungen/
   Fahrstraßen als Text/Liste) — **kein** gezeichnetes Gleisbild in Stufe 1.
3. DER Anwender kann Blöcke, Topologie-Elemente, Melder-Zuordnungen und Fahrstraßen
   anlegen/ändern/löschen; Fehler aus der API werden verständlich angezeigt.
4. ZU jedem Block zeigt die UI den abgeleiteten Zustand: belegt/frei/unbekannt und — falls
   vorhanden — die RailCom-Identität, live aktualisiert über SSE.
5. DIE UI nutzt den bestehenden zentralen Store und den vorhandenen SSE-/REST-Client (Single
   Source of Truth bleibt das Backend).

### Anforderung 9 — Qualität, Tests, Konsistenz mit dem Bestand

**User Story:** Als Entwickler möchte ich, dass die neue Funktionalität den etablierten
Qualitätsstandards des Projekts entspricht, damit das Fundament für die Automatik tragfähig ist.

**Akzeptanzkriterien:**

1. DIE `domain`-Modelllogik ist mit `pytest` abgedeckt (Anlegen/Ändern/Löschen, Validierung,
   abgeleiteter Blockzustand inkl. der Fälle „belegt ohne Identität" und „kein Melder").
2. DIE Persistenz ist getestet (Speichern→Laden-Rundlauf, Umgang mit fehlender und ungültiger
   Datei, atomares Schreiben).
3. DIE API ist über den FastAPI-TestClient getestet (Erfolg + Ablehnung inkonsistenter Edits).
4. DAS Frontend hat Unit-/Component-Tests für die neuen Ansichten (Vitest) und einen
   E2E-Grundpfad (Playwright, API gemockt), konsistent mit dem Bestand.
5. `ruff`, `mypy` (Backend) sowie `eslint`/`oxlint`/`vue-tsc` (Frontend) sind sauber; CI bleibt
   grün.
6. DIE Terminologie folgt `traincontroller-domaene.md`; `NEXT.md` und betroffene Steering-Dateien
   werden nachgeführt.

---

## Offene Design-Punkte (im Design zu entscheiden)

- **Identitäts-Aggregation je Block:** Belegung = ODER aller Melder, Identität = Vereinigung
  (Menge) der RailCom-Loks der zugeordneten Melder — bestätigen und Randfälle klären
  (Lok über mehrere Melder desselben Blocks nur einmal zählen).
- **Längeneinheit:** **entschieden** — intern/API/Persistenz einheitlich mm als `int`. Die
  **Anzeige-/Eingabeeinheit ist reine Frontend-Präsentation** (mm/cm/Zoll …), zentral in der UI
  konfigurierbar; Umrechnung passiert ausschließlich an der UI-Kante, das Backend sieht immer nur
  ganze mm. Offen (UI): Konfigurationsort der Einheit; Rundung/Transparenz bei nicht-metrischen
  Einheiten (z. B. 1 Zoll = 25,4 mm → auf ganze mm runden und sichtbar machen) sowie
  Eingabe-Validierung.
- **Markierungs-Modell:** einheitliche Repräsentation für „Markierung = Melder" vs. „Markierung =
  virtuelle Längenposition", je Richtung; wie die virtuelle Position auf Melder+Offset abgebildet
  wird (nur Datenmodell in Stufe 1).
- **Konsistenzprüfung Längen:** was ist harter Fehler (Speichern verhindern) vs. Warnung
  (Summe Teillängen ≠ Blocklänge, Marke außerhalb der Blocklänge, überlappende/doppelte
  Anordnung).
- **Höchstgeschwindigkeit:** Einheit/Bereich (km/h Vorbild), optionales Feld; keine Umrechnung in
  Stufe 1.
- **Persistenz-Ablageort & Schema:** Format ist **entschieden (JSON)**. Offen: Ablageort
  (unter `conf/` vs. eigenem Datenverzeichnis), Versionsfeld im Schema für spätere Migrationen,
  Umsetzung des atomaren Schreibens (temporäre Datei + atomares Umbenennen).
- **Versionierte Backups:** Anzahl N der aufbewahrten Stände, Benennung (Zeitstempel vs.
  laufende Nummer), Ablageort (z. B. `backups/`-Unterordner), Rotationsstrategie. Recovery in
  Stufe 1 nur manuell.
- **Löschsemantik:** harte Ablehnung bei Abhängigkeiten vs. kaskadierend mit Bestätigung.
- **Melder-RailCom-Fähigkeit:** statisch im Modell vermerkt vs. zur Laufzeit erkannt.
- **ID-Vergabe:** Schema stabiler IDs (laufende Nummer, UUID, Slug aus Name) für Blöcke,
  Topologie-Elemente und Fahrstraßen.
- **DKW-Repräsentation:** eigener Elementtyp mit zwei Zubehöradressen und einer Zustandsmenge
  vs. Komposition aus zwei logischen Weichen; wie Fahrstraßen die DKW-Soll-Stellung referenzieren.
- **Namenseindeutigkeit:** gilt für Blöcke bestätigt; für Topologie-Elemente ebenso — klären, ob
  ein gemeinsamer Namensraum oder je Typ getrennt (Design), sowie die Vergleichsregel
  (Groß-/Kleinschreibung, Leerzeichen) einheitlich festlegen.
- **Starre Kreuzung in Stufe 1:** modelliert, aber ungenutzt — sicherstellen, dass sie weder
  Schaltbefehle noch Pflichtfelder (Adresse) erzwingt.
- **Fahrstraßen-Modell:** minimal nötige Felder für Stufe 1 (Start/Zwischen/Ziel-Blöcke,
  Element-Stellungen, beanspruchte Elemente) vs. schon Vorhalten von Feldern, die die spätere
  Verriegelung/das Routing brauchen (ohne sie zu nutzen).
- **Begriffe Zug/Zugfahrt/Lok:** in Stufe 1 nur im Glossar; sicherstellen, dass das Stufe-1-
  Datenmodell deren spätere Einführung nicht verbaut (keine widersprüchlichen Annahmen).
