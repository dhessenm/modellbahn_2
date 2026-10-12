// TypeScript-Typen fuer die Lokverwaltung (`/api/roster`).
//
// Exakt ausgerichtet an den Backend-Schemata in
//   src/modellbahn/api/schemas.py  (LocoRequest/LocoResponse/RosterResponse/
//   RosterWarningResponse/LocoWriteResponse)
//
// WICHTIG — Einheiten: `length_mm` ist GANZE Millimeter (int) bzw. null.
// Transport und Backend kennen ausschliesslich ganze mm; die Anzeige-Einheit
// (mm/cm/zoll) ist reine UI-Darstellung (siehe length-units.ts).

// Lok-Stammdaten (LocoResponse). Die interne `id` (UUID-Hex) ist die stabile
// Identitaet im Programm; `address` ist die DCC-Adresse und darf doppelt
// vorkommen (loest nur eine Warnung aus).
export interface Locomotive {
  id: string
  name: string
  address: number
  speed_steps: number
  function_count: number
  length_mm: number | null
  max_speed_kmh: number | null
  notes: string
}

// Gesamtliste (RosterResponse) fuer GET /api/roster.
export interface RosterResponse {
  locomotives: Locomotive[]
}

// Nicht-blockierende Warnung (RosterWarningResponse), z. B. Adress-Duplikat
// (code 'adresse_doppelt').
export interface RosterWarning {
  code: string
  message: string
}

// Wrapper-Antwort fuer Lok-Schreibzugriffe (LocoWriteResponse):
// POST/PUT /roster liefern diese Form (Entitaet plus Warnungen).
export interface LocoWriteResponse {
  entity: Locomotive
  warnings: RosterWarning[]
}

// Request-Payload (LocoRequest) ohne serverseitig vergebene `id`.
export interface LocoWrite {
  name: string
  address: number
  speed_steps: number
  function_count: number
  length_mm: number | null
  max_speed_kmh: number | null
  notes: string
}
