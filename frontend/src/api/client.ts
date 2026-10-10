// REST-Client und SSE-Abonnement fuer das Backend.
// Die Web-UI spricht ausschliesslich ueber diese Schnittstelle mit dem Backend.

import type { LocoState, SystemStatus } from './types'

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

  // SSE: ruft onChange bei jeder Zustandsaenderung im Backend auf.
  // Robust gegen Verbindungsabbrueche: reconnectet mit exponentiellem Backoff
  // und meldet jede (Wieder-)Verbindung ueber onReconnect, damit der Aufrufer
  // den Zustand frisch nachladen kann.
  subscribeEvents(
    onChange: () => void,
    onReconnect?: () => void,
  ): () => void {
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
