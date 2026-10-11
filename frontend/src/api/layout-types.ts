// TypeScript-Typen fuer das statische Anlagenmodell (`/api/layout`).
//
// Exakt ausgerichtet an den Backend-Schemata in
//   src/modellbahn/api/schemas.py  (Pydantic-Response-/Request-Modelle)
//   src/modellbahn/api/layout_routes.py  (Routen, Fehler-/Response-Formen)
//
// WICHTIG — Einheiten: Alle Laengen (`length_mm`, `position_mm`) sind GANZE
// Millimeter (int). Transport und Backend kennen ausschliesslich ganze mm; die
// Anzeige-Einheit (mm/cm/zoll) ist reine UI-Darstellung (siehe length-units.ts).

export type ElementType = 'turnout' | 'dkw' | 'crossing'

// Melder-Zuordnung eines Blocks (DetectorAssignmentModel).
export interface DetectorAssignment {
  detector_nid: number
  detector_port: number
  order: number
  length_mm: number | null
}

// Halt-/Bremsmarke (MarkerModel): entweder ein Melder-Bezug ODER eine Position
// in mm ab Blockanfang. Die xor-Regel prueft das Backend (400 bei Verstoss).
export interface Marker {
  detector_ref: [number, number] | null // (nid, port) als 2er-Array
  position_mm: number | null
}

// Richtungsabhaengige Marken (DirectionMarkersModel).
export interface DirectionMarkers {
  stop: Marker | null
  brake: Marker | null
}

// Block (BlockResponse).
export interface Block {
  id: string
  name: string
  length_mm: number | null
  max_speed_kmh: number | null
  detectors: DetectorAssignment[]
  markers_forward: DirectionMarkers
  markers_backward: DirectionMarkers
}

// Topologie-Element (ElementResponse): Weiche/DKW/Kreuzung.
export interface TopologyElement {
  id: string
  name: string
  type: ElementType
  address: number | null
  address_b: number | null
}

// Element-Stellung in einer Fahrstrasse (ElementSettingModel).
export interface ElementSetting {
  element_id: string
  desired_state: number
}

// Fahrstrasse (RouteResponse).
export interface Route {
  id: string
  name: string
  start_block_id: string
  transit_block_ids: string[]
  end_block_id: string
  element_settings: ElementSetting[]
  claimed_element_ids: string[]
}

// Laufzeitzustand eines Blocks (BlockRuntimeResponse).
export interface BlockRuntime {
  block_id: string
  occupancy: 'free' | 'occupied' | 'unknown'
  loco_addresses: number[]
}

// Nicht-blockierende Konsistenz-Warnung (WarningResponse).
export interface Warning {
  code: string
  message: string
}

// Wrapper-Antwort fuer Block-Schreibzugriffe (BlockWriteResponse):
// POST/PUT /blocks und PUT /blocks/{id}/detectors liefern diese Form.
// Element- und Route-Schreibzugriffe liefern dagegen die NACKTE Entitaet.
export interface BlockWriteResponse {
  entity: Block
  warnings: Warning[]
}

// Gesamtmodell (LayoutResponse) fuer GET /api/layout.
export interface LayoutModel {
  blocks: Block[]
  elements: TopologyElement[]
  routes: Route[]
}

// Loeschschutz-Blocker (ReferenceBlockerModel), Teil des 409-Konfliktkoerpers.
export interface ReferenceBlocker {
  type: string
  id: string
  name: string
}

// 409-Konfliktkoerper (inneres Objekt von `{ detail: ConflictBody }`).
export interface ConflictBody {
  detail: string
  blocked_by: ReferenceBlocker[]
}

// ---------------------------------------------------------------------------
// Request-Payload-Typen (ohne serverseitig vergebene `id`)
// ---------------------------------------------------------------------------

export interface BlockWrite {
  name: string
  length_mm: number | null
  max_speed_kmh: number | null
  markers_forward?: DirectionMarkers | null
  markers_backward?: DirectionMarkers | null
}

export interface ElementWrite {
  name: string
  type: ElementType
  address: number | null
  address_b: number | null
}

export interface RouteWrite {
  name: string
  start_block_id: string
  transit_block_ids: string[]
  end_block_id: string
  element_settings: ElementSetting[]
  claimed_element_ids: string[]
}

// Body fuer PUT /api/layout/blocks/{id}/detectors.
export interface DetectorAssignmentsBody {
  detectors: DetectorAssignment[]
}
