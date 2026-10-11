// Anzeigbare Fehlerinfo fuer die Layout-API.
//
// Hintergrund (verifiziert in src/modellbahn/api/layout_routes.py): FastAPI
// serialisiert `HTTPException(detail=...)` immer als Top-Level-Objekt
// `{ "detail": <wert> }`.
//   - 400 (Validierung) / 404 (unbekannte ID): `detail` ist ein STRING.
//   - 409 (Loeschkonflikt): `detail` ist ein OBJEKT
//       { detail: string, blocked_by: [{type,id,name}] }.
// Der Parser unterscheidet die beiden Faelle anhand der Form von `body.detail`.

import type { ReferenceBlocker } from './layout-types'

// Error-Unterklasse mit anzeigbarer Fehlerinfo. `blockedBy` ist nur bei 409
// gefuellt (sonst leeres Array).
export class LayoutApiError extends Error {
  readonly status: number
  readonly detail: string
  readonly blockedBy: ReferenceBlocker[]

  constructor(status: number, detail: string, blockedBy: ReferenceBlocker[] = []) {
    super(detail)
    this.name = 'LayoutApiError'
    this.status = status
    this.detail = detail
    this.blockedBy = blockedBy
  }

  // true, wenn ein Loeschkonflikt (409 mit benannten Blockern) vorliegt.
  get isConflict(): boolean {
    return this.status === 409 || this.blockedBy.length > 0
  }
}

interface ReferenceBlockerLike {
  type?: unknown
  id?: unknown
  name?: unknown
}

function isConflictDetail(detail: unknown): detail is { detail?: unknown; blocked_by: unknown[] } {
  return (
    typeof detail === 'object' &&
    detail !== null &&
    Array.isArray((detail as { blocked_by?: unknown }).blocked_by)
  )
}

function toBlocker(raw: ReferenceBlockerLike): ReferenceBlocker {
  return {
    type: typeof raw.type === 'string' ? raw.type : '',
    id: typeof raw.id === 'string' ? raw.id : '',
    name: typeof raw.name === 'string' ? raw.name : '',
  }
}

// Liest den (JSON-)Body einer fehlgeschlagenen Response und baut daraus eine
// `LayoutApiError`. Robust gegen fehlenden/nicht-JSON-Body (dann Status-Text).
export async function layoutErrorFromResponse(resp: Response): Promise<LayoutApiError> {
  let body: unknown = undefined
  try {
    body = await resp.json()
  } catch {
    // kein (gueltiger) JSON-Body -> generische Meldung unten
  }

  const detail = (body as { detail?: unknown } | undefined)?.detail

  if (isConflictDetail(detail)) {
    const message =
      typeof detail.detail === 'string' ? detail.detail : `Konflikt (HTTP ${resp.status}).`
    const blockedBy = detail.blocked_by.map((b) => toBlocker(b as ReferenceBlockerLike))
    return new LayoutApiError(resp.status, message, blockedBy)
  }

  if (typeof detail === 'string') {
    return new LayoutApiError(resp.status, detail)
  }

  const fallback = resp.statusText
    ? `API-Fehler ${resp.status}: ${resp.statusText}`
    : `API-Fehler ${resp.status}.`
  return new LayoutApiError(resp.status, fallback)
}
