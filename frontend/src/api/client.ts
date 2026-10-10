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
  subscribeEvents(onChange: () => void): () => void {
    const source = new EventSource('/api/events')
    source.onmessage = () => onChange()
    return () => source.close()
  },
}
