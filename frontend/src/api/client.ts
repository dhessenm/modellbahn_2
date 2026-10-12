// REST-Client und SSE-Abonnement fuer das Backend.
// Die Web-UI spricht ausschliesslich ueber diese Schnittstelle mit dem Backend.

import type { DetectorInput, LocoState, SystemStatus, TurnoutState } from './types'
import type {
  BlockRuntime,
  BlockWrite,
  BlockWriteResponse,
  DetectorAssignmentsBody,
  ElementWrite,
  LayoutModel,
  Route,
  RouteWrite,
  TopologyElement,
} from './layout-types'
import type { LocoWrite, LocoWriteResponse, RosterResponse } from './roster-types'
import { layoutErrorFromResponse } from './layout-error'

async function request(path: string, init?: RequestInit): Promise<Response> {
  const resp = await fetch(path, init)
  if (!resp.ok) {
    throw new Error(`API-Fehler ${resp.status} bei ${path}`)
  }
  return resp
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await request(path, init)
  return (await resp.json()) as T
}

function jsonBody(body: unknown): RequestInit {
  return {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }
}

// Eigene Fehlerbehandlung fuer die Layout-Routen: Bei nicht-ok-Response
// (400/404/409 ...) wird der JSON-Body gelesen und eine `LayoutApiError`
// (mit status/detail/blocked_by) geworfen -- statt des generischen Error aus
// `request`. Das Verhalten der uebrigen Methoden (System/Lok/Weiche/Melder)
// bleibt dadurch unveraendert.
async function layoutRequest(path: string, init?: RequestInit): Promise<Response> {
  const resp = await fetch(path, init)
  if (!resp.ok) {
    throw await layoutErrorFromResponse(resp)
  }
  return resp
}

async function layoutJson<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await layoutRequest(path, init)
  return (await resp.json()) as T
}

async function layoutVoid(path: string, init?: RequestInit): Promise<void> {
  await layoutRequest(path, init)
}

function layoutBody(method: 'POST' | 'PUT', body: unknown): RequestInit {
  return {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }
}

export const api = {
  getSystemStatus(): Promise<SystemStatus> {
    return requestJson<SystemStatus>('/api/system/status')
  },

  async setTrackPower(on: boolean): Promise<void> {
    await request('/api/system/track-power', jsonBody({ on }))
  },

  getLoco(address: number): Promise<LocoState> {
    return requestJson<LocoState>(`/api/locos/${address}`)
  },

  async subscribeLoco(address: number): Promise<void> {
    await request(`/api/locos/${address}/subscribe`, { method: 'POST' })
  },

  async drive(address: number, speed: number, forward: boolean): Promise<void> {
    await request(`/api/locos/${address}/drive`, {
      ...jsonBody({ speed, forward }),
      method: 'PUT',
    })
  },

  async setFunction(address: number, func: number, on: boolean): Promise<void> {
    await request(`/api/locos/${address}/function`, {
      ...jsonBody({ function: func, on }),
      method: 'PUT',
    })
  },

  getTurnout(address: number): Promise<TurnoutState> {
    return requestJson<TurnoutState>(`/api/turnouts/${address}`)
  },

  async subscribeTurnout(address: number): Promise<void> {
    await request(`/api/turnouts/${address}/subscribe`, { method: 'POST' })
  },

  async setTurnout(address: number, position: number): Promise<void> {
    await request(`/api/turnouts/${address}`, {
      ...jsonBody({ position }),
      method: 'PUT',
    })
  },

  async getDetectors(): Promise<DetectorInput[]> {
    const resp = await requestJson<{ detectors: DetectorInput[] }>('/api/detectors')
    return resp.detectors
  },

  async refreshDetectors(): Promise<void> {
    await request('/api/detectors/refresh', { method: 'POST' })
  },

  // --- Anlagenmodell (/api/layout) ---
  // Lesemethoden liefern das Gesamtmodell bzw. den Laufzeitzustand.
  // Schreibmethoden fuer Bloecke liefern den Wrapper { entity, warnings };
  // fuer Elemente/Routen die nackte Entitaet. DELETE liefert void (204);
  // bei Referenz-Konflikt wirft die Methode eine LayoutApiError (409).

  getLayout(): Promise<LayoutModel> {
    return layoutJson<LayoutModel>('/api/layout')
  },

  getLayoutRuntime(): Promise<BlockRuntime[]> {
    return layoutJson<BlockRuntime[]>('/api/layout/runtime')
  },

  createBlock(body: BlockWrite): Promise<BlockWriteResponse> {
    return layoutJson<BlockWriteResponse>('/api/layout/blocks', layoutBody('POST', body))
  },

  updateBlock(id: string, body: BlockWrite): Promise<BlockWriteResponse> {
    return layoutJson<BlockWriteResponse>(`/api/layout/blocks/${id}`, layoutBody('PUT', body))
  },

  deleteBlock(id: string): Promise<void> {
    return layoutVoid(`/api/layout/blocks/${id}`, { method: 'DELETE' })
  },

  setBlockDetectors(id: string, body: DetectorAssignmentsBody): Promise<BlockWriteResponse> {
    return layoutJson<BlockWriteResponse>(
      `/api/layout/blocks/${id}/detectors`,
      layoutBody('PUT', body),
    )
  },

  createElement(body: ElementWrite): Promise<TopologyElement> {
    return layoutJson<TopologyElement>('/api/layout/elements', layoutBody('POST', body))
  },

  updateElement(id: string, body: ElementWrite): Promise<TopologyElement> {
    return layoutJson<TopologyElement>(`/api/layout/elements/${id}`, layoutBody('PUT', body))
  },

  deleteElement(id: string): Promise<void> {
    return layoutVoid(`/api/layout/elements/${id}`, { method: 'DELETE' })
  },

  createRoute(body: RouteWrite): Promise<Route> {
    return layoutJson<Route>('/api/layout/routes', layoutBody('POST', body))
  },

  updateRoute(id: string, body: RouteWrite): Promise<Route> {
    return layoutJson<Route>(`/api/layout/routes/${id}`, layoutBody('PUT', body))
  },

  deleteRoute(id: string): Promise<void> {
    return layoutVoid(`/api/layout/routes/${id}`, { method: 'DELETE' })
  },

  // --- Lokverwaltung (/api/roster) ---
  // Lesemethode liefert die Gesamtliste. Schreibmethoden liefern den Wrapper
  // { entity, warnings }; DELETE liefert void (204). 400/404 werden ueber
  // layoutRequest in eine LayoutApiError ({detail:string}) uebersetzt.

  getRoster(): Promise<RosterResponse> {
    return layoutJson<RosterResponse>('/api/roster')
  },

  createLoco(body: LocoWrite): Promise<LocoWriteResponse> {
    return layoutJson<LocoWriteResponse>('/api/roster', layoutBody('POST', body))
  },

  updateLoco(id: string, body: LocoWrite): Promise<LocoWriteResponse> {
    return layoutJson<LocoWriteResponse>(`/api/roster/${id}`, layoutBody('PUT', body))
  },

  deleteLoco(id: string): Promise<void> {
    return layoutVoid(`/api/roster/${id}`, { method: 'DELETE' })
  },

  // SSE: ruft onChange bei jeder Zustandsaenderung im Backend auf.
  // Robust gegen Verbindungsabbrueche: reconnectet mit exponentiellem Backoff
  // und meldet jede (Wieder-)Verbindung ueber onReconnect, damit der Aufrufer
  // den Zustand frisch nachladen kann.
  subscribeEvents(onChange: () => void, onReconnect?: () => void): () => void {
    let source: EventSource | null = null
    let retryTimer: ReturnType<typeof setTimeout> | null = null
    let backoffMs = 1000
    const maxBackoffMs = 15000
    let closed = false

    const connect = (): void => {
      if (closed) return
      console.debug('[sse] verbinde mit /api/events')
      source = new EventSource('/api/events')

      source.onopen = () => {
        console.debug('[sse] verbunden')
        backoffMs = 1000 // nach erfolgreicher Verbindung zuruecksetzen
        onReconnect?.()
      }
      source.onmessage = () => {
        console.debug('[sse] event: changed')
        onChange()
      }
      source.onerror = () => {
        console.warn('[sse] Fehler/Abbruch, reconnect in', backoffMs, 'ms')
        // EventSource schliessen und selbst mit Backoff neu verbinden.
        source?.close()
        source = null
        if (closed) return
        retryTimer = setTimeout(connect, backoffMs)
        backoffMs = Math.min(backoffMs * 2, maxBackoffMs)
      }
    }

    connect()

    return () => {
      closed = true
      if (retryTimer !== null) clearTimeout(retryTimer)
      source?.close()
    }
  },
}
