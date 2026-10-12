# Anforderungen — Lokverwaltung

> Neues Feature: persistente Lokverwaltung (CRUD) mit eigener UI-Seite und
> Anpassung des bestehenden Lokführerstands (Dropdown statt freier Adresseingabe).
> Loks werden als eigenständige, benannte Objekte mit DCC-Adresse und
> Stammdaten geführt — Grundlage für spätere Automatik (Einmessung, Zugbildung).
>
> Begriffe gemäß `.kiro/steering/traincontroller-domaene.md`. Architektur und
> Konventionen gemäß `product.md`/`tech.md`/`structure.md`.

## Kontext und Abgrenzung

Bisher ist eine Lok im System nur eine **flüchtige DCC-Adresse**: Der Anwender tippt eine Zahl
in den Lokführerstand, und der Live-Zustand (`LocoState`) existiert nur so lange, wie die
Zentrale Daten liefert. Es gibt kein benanntes, persistentes Lok-Objekt.

Dieses Feature führt eine **Lok-Bibliothek** ein: Loks werden angelegt, benannt, mit Stammdaten
versehen und persistent gespeichert. Der Lokführerstand wählt dann eine **verwaltete Lok** aus
einem Dropdown — das freie Adressfeld entfällt. Die interne Identifikation läuft über eine
stabile **Lok-ID** (UUID), nicht über die (änderbare) DCC-Adresse.

**Bewusst NICHT Teil dieses Features:**
- Einmessdaten (DCC-Fahrstufe → reale Geschwindigkeit) — kommen mit der Automatik-Stufe.
- Geschwindigkeitsanzeige in km/h im Lokführerstand — das Vmax-Feld wird als Stammdatum
  gespeichert, aber die Umrechnung Fahrstufe→km/h wird in diesem Feature noch nicht gebaut
  (nur das Fundament gelegt).
- Zug-Objekte (Lok + Wagen als Zusammenstellung) — spätere Stufe.
- Maßstabsumrechnung (Vorbild-km/h → Modell).
- Zuordnung Lok ↔ Block (Zugverfolgung).

## Glossar (dieses Feature)

- **Lok:** persistentes, benanntes Objekt mit stabiler ID und DCC-Adresse. Hat Stammdaten
  (Name, Adresse, Fahrstufenmodus, Funktionsanzahl, Länge, Höchstgeschwindigkeit, Notizen).
  Wird in der Lok-Bibliothek verwaltet und im Lokführerstand zur Steuerung ausgewählt.
- **Lok-Bibliothek:** die Gesamtheit der verwalteten Loks (persistiert, analog zum
  Anlagenmodell).
- **Fahrstufenmodus:** DCC-Fahrstufensystem der Lok (14, 28 oder 128 Fahrstufen). Bestimmt
  den Wertebereich des Fahrreglers. Aktuell ist 128 hardcoded; das Feld bereitet die spätere
  korrekte Ansteuerung vor.

---

## Anforderungen

### Anforderung 1 — Lok-Stammdaten modellieren und persistieren

**User Story:** Als Anwender möchte ich Loks mit ihren Stammdaten anlegen, bearbeiten und
löschen, damit ich eine Bibliothek meiner Fahrzeuge habe, die den Lokführerstand und die
spätere Automatik speist.

**Akzeptanzkriterien:**

1. WENN der Anwender eine Lok anlegt, DANN erhält sie eine stabile, eindeutige **ID** (UUID,
   intern vergeben — nicht die DCC-Adresse) und wird persistent gespeichert.
2. JEDE Lok hat folgende Stammdaten:
   - **Name** (Pflicht, Freitext, z. B. „BR 101 ICE"). Muss **eindeutig** sein (case-insensitive
     nach `strip()`, analog zu Blocknamen). Gilt bei Anlegen und Umbenennen.
   - **DCC-Adresse** (Pflicht, `int`, 1–9999). Doppelte Adressen sind **erlaubt** (mehrere Loks
     können dieselbe Adresse haben); beim Anlegen/Ändern wird jedoch eine **Warnung** ausgegeben,
     wenn die Adresse bereits einer anderen Lok zugeordnet ist (kein harter Fehler).
   - **Fahrstufenmodus** (`int`, Werte 14, 28 oder 128; Default 128).
   - **Anzahl Funktionen** (`int`, 0–28; Default 28): bestimmt, wie viele Funktionstasten
     (F0–Fn) der Lokführerstand für diese Lok anzeigt.
   - **Länge in mm** (`int | null`, optional): Fahrzeuglänge im Modellmaßstab. Ganzzahlige
     Millimeter, konsistent zum Anlagenmodell. Relevant für spätere Blockbelegung (Zuglänge vs.
     Blocklänge).
   - **Höchstgeschwindigkeit in km/h** (`int | null`, optional): Vorbildgeschwindigkeit (wie bei
     Blöcken, nicht Modellgeschwindigkeit). Fundament für spätere km/h-Anzeige im Lokführerstand
     (lineare Näherung: Fahrstufe 0 → 0 km/h, max. Fahrstufe → Vmax) und Einmessung.
   - **Notizen** (`str`, optional, Freitext): z. B. Decoder-Typ, Besonderheiten.
3. WENN der Anwender eine Lok ändert oder löscht, DANN wird die Änderung persistiert.
4. WENN das Backend neu startet, DANN sind alle zuvor gespeicherten Loks unverändert vorhanden.
5. DIE Persistenz folgt demselben Muster wie das Anlagenmodell: JSON-Datei, atomares Schreiben,
   versionierte Backups mit Rotation.

### Anforderung 2 — Lok-API (REST)

**User Story:** Als Frontend möchte ich Loks über REST lesen und bearbeiten, konsistent mit
der bestehenden API-Schicht.

**Akzeptanzkriterien:**

1. DIE API stellt Endpunkte zum Lesen aller Loks, Lesen einer Lok, Anlegen, Ändern und Löschen
   bereit (Routen im Design). Anlegen/Ändern liefert die Warnung „Adresse bereits vergeben" als
   `warnings`-Liste in der Antwort (analog zu Block-Schreibantworten), nicht als harten Fehler.
2. WENN eine Bearbeitung das Modell inkonsistent machen würde (leerer Name, Name-Duplikat,
   ungültiger Fahrstufenmodus, ungültige Adresse), DANN lehnt die API mit 400 ab.
3. WENN eine unbekannte Lok-ID adressiert wird, DANN 404.
4. DIE API-Schicht bleibt dünn und delegiert an die `domain`-Schicht.
5. NACH jeder erfolgreichen Mutation: Persistenz (save) + SSE-Push (`broker.publish()`), damit
   der Lokführerstand und andere UI-Bereiche die Änderung sofort sehen.

### Anforderung 3 — Web-UI: Lokverwaltung (eigene Seite)

**User Story:** Als Anwender möchte ich im Browser eine Lok-Bibliothek pflegen (anlegen,
bearbeiten, löschen), übersichtlich als Liste.

**Akzeptanzkriterien:**

1. DIE UI erhält einen eigenen Arbeitsbereich (neue Route, Navigationslink in der App-Shell),
   ohne die bestehenden Bereiche umzubauen.
2. DIE Seite zeigt eine **Liste aller verwalteten Loks** mit den wichtigsten Stammdaten
   (Name, Adresse, Fahrstufenmodus, ggf. Vmax).
3. DER Anwender kann Loks **anlegen**, **bearbeiten** und **löschen**; die Adress-Warnung
   (Duplikat) wird verständlich angezeigt; API-Fehler werden klar dargestellt.
4. LÄNGEN (mm) und Geschwindigkeit (km/h) werden in der gewählten Anzeige-Einheit dargestellt
   (konsistent zur Anlagenmodell-UI; Umrechnung an der UI-Kante, Transport in ganzen mm / km/h).

### Anforderung 4 — Lokführerstand: Lok-Auswahl per Dropdown + UX-Verbesserungen

**User Story:** Als Anwender möchte ich im Lokführerstand eine Lok aus meiner Bibliothek
auswählen und sie mit einem ergonomischen Fahrregler steuern, der sich an die Lok anpasst.

**Akzeptanzkriterien:**

1. DAS bisherige Zahleneingabefeld für die DCC-Adresse wird durch ein **Dropdown** (`<select>`)
   ersetzt, das alle verwalteten Loks (Name + Adresse) anzeigt.
2. NUR verwaltete Loks sind auswählbar; die freie Adresseingabe entfällt.
3. WENN der Anwender eine Lok auswählt, DANN wird automatisch die DCC-Adresse der Lok für
   die Steuerung übernommen und der Lok-Zustand bei der Zentrale angefragt.
4. DIE Funktionstasten passen sich an die **Anzahl Funktionen** der gewählten Lok an
   (F0–Fn statt pauschal F0–F28).
5. DER **Fahrstufenmodus** (14/28/128) der gewählten Lok bestimmt den Wertebereich des
   Fahrreglers. Ist kein Modus gesetzt, gilt Default 128.
6. WENN keine Loks in der Bibliothek sind, DANN zeigt der Lokführerstand einen Hinweis
   (z. B. „Bitte zuerst eine Lok in der Lokverwaltung anlegen") statt eines leeren Dropdowns.
7. WENN sich die Lok-Bibliothek ändert (SSE), DANN aktualisiert sich das Dropdown live.
8. DER **Fahrstufen-Schieberegler** wird **vertikal** dargestellt: niedrigste Fahrstufe unten,
   höchste oben. Das ist ergonomischer, besonders bei Bedienung über den Handy-Browser
   (Daumen-Bewegung nach oben = schneller).
9. DAS **Lokinformationsfeld** (Key-Value-Paare: Geschwindigkeit, Richtung, Funktionen) wird
   **einklappbar/ausklappbar** unter den anderen Elementen platziert (Default: eingeklappt).
   Die Detailinformationen sind für den täglichen Betrieb nicht primär nötig, aber für
   Fehlersuche hilfreich.

### Anforderung 5 — Qualität, Tests, Konsistenz mit dem Bestand

**User Story:** Als Entwickler möchte ich, dass die neue Funktionalität den etablierten
Qualitätsstandards des Projekts entspricht.

**Akzeptanzkriterien:**

1. DIE `domain`-Logik (Lok-CRUD, Validierung, Adress-Warnung) ist mit `pytest` abgedeckt.
2. DIE Persistenz ist getestet (Save→Load-Rundlauf, fehlende/ungültige Datei).
3. DIE API ist über den FastAPI-TestClient getestet (Erfolg + Ablehnung + Warnung).
4. DAS Frontend hat Unit-/Component-Tests (Vitest) und einen E2E-Grundpfad (Playwright).
5. `ruff`, `mypy` (Backend) sowie `eslint`/`oxlint`/`vue-tsc` (Frontend) sind sauber; CI grün.
6. `NEXT.md` und ggf. betroffene Steering-Dateien werden nachgeführt.

### Anforderung 6 — App-Shell: globale Statusleiste

**User Story:** Als Anwender möchte ich den Verbindungsstatus und die Gleisspannung jederzeit
auf einen Blick sehen und bedienen, ohne auf eine bestimmte Seite wechseln zu müssen.

**Hintergrund:** Aktuell zeigt `ConnectionStatus` den Verbindungsstatus als Text mit IP-Adresse
in der App-Shell-Kopfzeile, und der Gleisspannungs-Schalter lebt nur in der CabView und dem
Dashboard. Beide sollen in eine **kompakte Statusleiste** am oberen Fensterrand wandern, die
auf allen Seiten sichtbar ist.

**Akzeptanzkriterien:**

1. DIE App-Shell erhält eine **globale Statusleiste** am oberen Rand (oberhalb oder als Teil
   der bestehenden Kopfzeile), die auf **allen** Unterseiten sichtbar ist.
2. DER **Verbindungsstatus** wird als **kleine runde LED** dargestellt: grün = verbunden,
   aus/grau = nicht verbunden. **Kein Text** (keine IP-Adresse, kein „Verbunden"). Die bestehende
   `ConnectionStatus`-Komponente wird entsprechend umgebaut oder durch eine schlankere Variante
   ersetzt.
3. DER **Gleisspannungs-Schalter** (Track Power on/off) wird in die Statusleiste verlegt, damit
   er von jeder Seite aus bedienbar ist (nicht nur aus CabView/Dashboard). Die bisherigen
   seitenspezifischen TrackPower-Widgets entfallen oder verweisen auf den globalen Schalter.
4. DIE Statusleiste ist **kompakt** und nimmt minimal Bildschirmhöhe ein (besonders auf Handy
   wichtig).
5. DIE bestehende Navigation (Menülinks) bleibt erhalten; sie kann in derselben Zeile oder
   direkt darunter liegen (Design entscheidet das Layout).

---

## Offene Design-Punkte (im Design zu entscheiden)

- **Persistenz-Ort:** **entschieden** — eigene Datei `conf/roster.json` (getrennt vom
  Anlagenmodell; erleichtert spätere Modularisierung, z. B. reines Lokfahren ohne
  Anlagen-Layout). Atomares Schreiben + Backups analog zum Anlagenmodell-Store.
- **Domain-Platzierung:** Empfehlung: eigene Module `domain/roster.py` +
  `domain/roster_service.py` (Lok ist ein eigenständiges Domänenkonzept, nicht Teil der
  Topologie).
- **API-Routen-Präfix:** **entschieden** — `/api/roster` (kurz, idiomatisch; „Roster" = Bestand;
  klar getrennt vom bestehenden `/api/locos/{address}` für Live-Steuerung).
- **Beziehung verwaltete Lok ↔ flüchtiger LocoState:** **entschieden** — reine Trennung. Die
  Lokverwaltung pflegt Stammdaten; der Lokführerstand liest die DCC-Adresse der verwalteten Lok
  und nutzt sie, um den Live-`LocoState` zu adressieren. Keine Verknüpfung in der
  Verwaltungs-API; die beiden Konzepte bleiben unabhängig.
- **Dropdown-Variante:** **entschieden** — einfaches `<select>` (Liste wird nicht so lang).
- **Fahrstufenmodus im Fahrregler:** **entschieden** — der Fahrregler (LocoThrottle) passt
  seinen Wertebereich an den Fahrstufenmodus der gewählten Lok an (14/28/128). Default 128 wenn
  nicht gesetzt. Betrifft die LocoThrottle-Komponente und ggf. das Backend
  (`build_loco_drive`-Parametrisierung).
- **Statusleisten-Layout:** Wie genau die Statusleiste in die bestehende App-Shell-Kopfzeile
  integriert wird (eigene Zeile oberhalb der Navigation vs. integriert in eine Zeile mit den
  Nav-Links). Kompakt halten, besonders auf Mobile.
- **Kontextabhängige Menüleiste (Ausblick):** Die Idee, dass die Statusleiste je nach
  Unterseite unterschiedliche Kontexteinträge zeigt, ist eine eigenständige UX-Erweiterung,
  die über dieses Feature hinausgeht. Hier wird nur die Grundstruktur (LED + TrackPower global)
  geschaffen; eine kontextabhängige Erweiterung ist als Merker für später notiert.
- **TrackPower-Entfernung aus CabView/Dashboard:** Wenn der Gleisspannungs-Schalter in die
  globale Statusleiste wandert, werden die bisherigen seitenspezifischen Widgets überflüssig.
  Design klärt, ob sie entfernt, ausgeblendet oder als Zweit-Schalter erhalten bleiben.
