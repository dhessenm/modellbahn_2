---
inclusion: manual
---

# Z21 LAN-Protokoll (Referenz)

> Abgeleitet aus `external_docs/z21-lan-protokoll.pdf` — "Z21 LAN Protokoll Spezifikation",
> Dokumentenversion 1.13 (06.11.2023), Herausgeber: Modelleisenbahn GmbH (Roco/Fleischmann).
> Diese Datei fasst die für die Implementierung relevanten Punkte zusammen. Im Zweifel ist
> das Original-PDF maßgeblich.

## Zweck

Das Z21 LAN-Protokoll steuert eine Z21-Digitalzentrale (bzw. kompatible Geräte wie
SmartRail) über das Netzwerk. Es dient zum Fahren von Loks, Schalten von Weichen/Zubehör,
Auslesen von Rückmeldern sowie zum Lesen/Schreiben von Decoder-CVs.

## Transport

- **Protokoll:** UDP.
- **Ports:** 21105 oder 21106. Client-Anwendungen (PC, App) sollten vorrangig **21105** verwenden.
- **Byte-Reihenfolge:** sofern nicht anders angegeben **Little-Endian** (zuerst Low-Byte).
- Mehrere unabhängige Z21-Datensätze dürfen in den Nutzdaten eines einzelnen UDP-Pakets
  kombiniert werden. Jeder Empfänger muss kombinierte Pakete wieder zerlegen können.

## Aufbau eines Datensatzes

```
+---------+--------+--------------+
| DataLen | Header | Data         |
| 2 Byte  | 2 Byte | n Byte       |
+---------+--------+--------------+
```

- **DataLen** (little endian): Gesamtlänge des Datensatzes inkl. DataLen, Header und Data.
- **Header** (little endian): Art des Datensatzes.
- **X-Bus-Befehle** laufen unter Z21-LAN-Header **0x40** (`LAN_X_xxx`). Innerhalb davon:
  `X-Header`, `DB0`, weitere Datenbytes und ein abschließendes **XOR-Prüfbyte** über den
  X-Bus-Befehl.
- LocoNet-Gateway nutzt die Header **0xA0/0xA1** (`LAN_LOCONET_Z21_RX/TX`) und **0xA2**
  (`LAN_LOCONET_FROM_LAN`).

## Wichtige Befehlsgruppen

- **System/Status:** `LAN_X_GET_VERSION`, `LAN_X_GET_STATUS`, `LAN_X_GET_FIRMWARE_VERSION`,
  `LAN_X_SET_TRACK_POWER_ON/OFF`, `LAN_X_SET_STOP`, zugehörige Broadcast-Meldungen
  (`LAN_X_BC_*`), `LAN_X_STATUS_CHANGED`, `LAN_X_UNKNOWN_COMMAND`.
- **Fahren (Loks):** `LAN_X_GET_LOCO_INFO`, `LAN_X_SET_LOCO_DRIVE`, `LAN_X_SET_LOCO_FUNCTION`,
  `LAN_X_SET_LOCO_FUNCTION_GROUP`, `LAN_X_SET_LOCO_BINARY_STATE`, `LAN_X_LOCO_INFO`,
  `LAN_X_SET_LOCO_E_STOP`, `LAN_X_PURGE_LOCO`.
- **Weichen/Zubehör:** `LAN_X_GET_TURNOUT_INFO` (X-Header `0x43`, Adresse),
  `LAN_X_SET_TURNOUT` (X-Header `0x53`, DB3 `10Q0A00P`: A=aktivieren/deaktivieren,
  P=Ausgang 0/1, Q=0 sofort), `LAN_X_TURNOUT_INFO` (empfangen, X-Header `0x43`, DB3 `000000ZZ`:
  00=unbekannt, 01=Position 0, 10=Position 1), `LAN_X_SET_EXT_ACCESSORY`,
  `LAN_X_GET_EXT_ACCESSORY_INFO`.
- **Decoder-Programmierung (CV):** `LAN_X_CV_READ`, `LAN_X_CV_WRITE`, `LAN_X_CV_NACK`,
  `LAN_X_CV_NACK_SC`, sowie DCC-/MM-Register-Befehle.
- **Broadcast-Flags:** `LAN_SET_BROADCASTFLAGS` steuert, welche Statusmeldungen die Zentrale
  unaufgefordert sendet.

## Hinweise für die Implementierung

- Prüfsumme (XOR über den X-Bus-Befehl) immer korrekt berechnen und validieren.
- Little-Endian beim Serialisieren/Deserialisieren konsequent beachten.
- Broadcast-/Status-Meldungen asynchron behandeln — die Zentrale sendet unaufgefordert.
- **Keep-Alive:** Jeder Client muss **mindestens einmal pro Minute** mit der Z21 kommunizieren,
  sonst wird er aus der Liste der aktiven Teilnehmer entfernt. Daher periodisch (deutlich unter
  60 s) eine Statusabfrage senden, z. B. `LAN_X_GET_STATUS` (Header `0x40`, X-Header `0x21`,
  DB0 `0x24`) oder `LAN_SYSTEMSTATE_GETDATA` (Header `0x85`).
- **Sauberes Abmelden:** Beim Beenden `LAN_LOGOFF` (Header `0x30`) senden; dabei dieselbe
  Portnummer wie bei der Anmeldung verwenden.
- **Gleisspannung/Status:** `LAN_X_SET_TRACK_POWER_ON` (DB0 `0x81`) /
  `LAN_X_SET_TRACK_POWER_OFF` (DB0 `0x80`); Systemstatus inkl. `CentralState` über
  `LAN_SYSTEMSTATE_DATACHANGED`/`LAN_SYSTEMSTATE_GETDATA`.
- Konkrete Byte-Layouts, Werte und Flags vor der Implementierung im Original-PDF nachschlagen.

## Weichen-Rückmeldung: wichtige Einschränkung

- **`LAN_X_SET_TURNOUT` hat keine Quittung** — die Spezifikation sagt ausdrücklich
  "Antwort von Z21: keine". Es gibt also keine Bestätigung, dass der Schaltbefehl ankam oder
  die Weiche gestellt wurde.
- **`LAN_X_GET_TURNOUT_INFO` → `LAN_X_TURNOUT_INFO`** liefert nur den von der Z21 **geführten
  Soll-Zustand** (zuletzt kommandierte Lage, `ZZ`), **nicht** den realen Weichenstand. Direkt
  nach dem Start ist er `00` (unbekannt), bis einmal geschaltet/abgefragt wurde.
- Grund: DCC ist Richtung Gleis **unidirektional**; ein einfacher Schaltdecoder meldet nichts
  zurück. Ein echter Ist-Zustand ist nur über **Rückmelder/Belegtmeldung** möglich (später:
  Z21 Detector 10808, ggf. RailCom) — nicht über den Schaltbefehl selbst.
- Bleibt ein Befehl ungültig, antwortet die Z21 mit `LAN_X_UNKNOWN_COMMAND`; dessen Ausbleiben
  ist nur ein schwaches Indiz für Erfolg (UDP ist zudem verbindungslos).

## Gleisbelegtmeldung: `LAN_CAN_DETECTOR` (Roco Z21 Detector 10808)

> Kapitel 10/10.1 des Protokolls. Umgesetzt ist die **Anzeige** des Belegtstatus (siehe
> `product.md`). Der Detector 10808 ist per **CAN-Bus** an die Z21 angebunden.

- **Header `0xC4`** — eigener Z21-LAN-Header, **kein** X-Bus-Befehl (also **kein** Header
  `0x40` und **kein** XOR-Prüfbyte). Gebaut wie `LAN_SYSTEMSTATE` über
  `build_dataset(0xC4, data)`.
- **Abfrage (Request):** `Data = Typ(8 Bit)=0x00 | CAN-NetworkID(16 Bit, little endian)`. Die
  NetworkID `0xD000` adressiert **alle** CAN-Belegtmelder. Voller Datensatz (alle Melder):
  `07 00 C4 00 00 00 D0`.
- **Antwort/Broadcast:** Header `0xC4`, `DataLen = 0x000E` (14). Datenstruktur (little endian):

  ```
  NId(16) | Addr(16) | Port(8) | Typ(8) | Value1(16) | Value2(16)
    NId  : unveränderbare CAN-NetworkID (stabile Melder-Identität)
    Addr : konfigurierbare Moduladresse (nur Anzeigeinfo)
    Port : Eingang 0..7
  ```

  **Wichtig (an echter Hardware bestätigt):** `Addr` kommt oft als `0`, auch wenn am Gerät
  eine Moduladresse eingestellt wurde. Deshalb den Melder über die **NId** identifizieren/
  gruppieren, nicht über `Addr`. Interner Zustands-Schlüssel: `(nid, port)`. Der physische
  „Eingang 1" am Gerät ist im Protokoll `Port = 0` (0-basiert) — in der UI wird daher `Port+1`
  angezeigt (analog zur Weichen-Adresszählung).

- **Typ `0x01` = Belegtstatus** (`Value1` maßgeblich):

  | Value1 | Bedeutung                 | occupied | with_power | overload |
  | ------ | ------------------------- | -------- | ---------- | -------- |
  | 0x0000 | frei / ohne Spannung      | nein     | nein       | nein     |
  | 0x0100 | frei / mit Spannung       | nein     | ja         | nein     |
  | 0x1000 | besetzt / ohne Spannung   | ja       | nein       | nein     |
  | 0x1100 | besetzt / mit Spannung    | ja       | ja         | nein     |
  | 0x1201 | besetzt / Überlast 1      | ja       | ja         | ja (1)   |
  | 0x1202 | besetzt / Überlast 2      | ja       | ja         | ja (2)   |
  | 0x1203 | besetzt / Überlast 3      | ja       | ja         | ja (3)   |

  Regel: `Value1 >= 0x1000` ⇒ besetzt; High-Byte `0x12` ⇒ Überlast (Level = Low-Byte);
  `with_power = Überlast oder (Value1 & 0x0100) != 0`.

- **Typ `0x11..0x1F` = RailCom-Lokadressen**, zwei Adressen pro Meldung (`Value1`, `Value2`).
  Jeder 16-Bit-Wert: Bits 15..14 = Richtung (`00` unbekannt, `10` vorwärts, `11` rückwärts),
  Bits 13..0 = Lokadresse. **Adresse 0 = Listenende** (restliche Werte ignorieren). `0x11`
  beginnt eine neue Liste; `0x12..0x1F` hängen weitere Paare an.

- **Broadcast-Flag:** `0x00080000` (`BROADCAST_CAN_DETECTOR`) in `LAN_SET_BROADCASTFLAGS`
  setzen, damit CAN-Belegtmeldungen unaufgefordert eintreffen (ereignisgesteuert, kein Polling).

- **Lokadressen nur mit RailCom:** Ohne RailCom meldet der Detector nur „besetzt/frei", aber
  keine Lokadresse. **„besetzt ohne Lokadresse" ist daher normal** und kein Fehler.
