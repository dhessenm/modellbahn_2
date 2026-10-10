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
- **Weichen/Zubehör:** `LAN_X_GET_TURNOUT_INFO`, `LAN_X_SET_TURNOUT` (mit Queue-Bit Q=0/1),
  `LAN_X_TURNOUT_INFO`, `LAN_X_SET_EXT_ACCESSORY`, `LAN_X_GET_EXT_ACCESSORY_INFO`.
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
