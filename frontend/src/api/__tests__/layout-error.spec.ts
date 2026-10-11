import { describe, it, expect } from 'vitest'
import { LayoutApiError, layoutErrorFromResponse } from '../layout-error'

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

describe('layoutErrorFromResponse', () => {
  it('400 mit String-detail -> LayoutApiError ohne Blocker', async () => {
    const err = await layoutErrorFromResponse(jsonResponse(400, { detail: 'Name fehlt.' }))
    expect(err).toBeInstanceOf(LayoutApiError)
    expect(err.status).toBe(400)
    expect(err.detail).toBe('Name fehlt.')
    expect(err.blockedBy).toEqual([])
    expect(err.isConflict).toBe(false)
  })

  it('404 mit String-detail -> LayoutApiError', async () => {
    const err = await layoutErrorFromResponse(
      jsonResponse(404, { detail: "Block mit ID 'x' nicht gefunden." }),
    )
    expect(err.status).toBe(404)
    expect(err.detail).toContain('nicht gefunden')
    expect(err.blockedBy).toEqual([])
  })

  it('409 mit Objekt-detail -> blocked_by uebernommen (type/id/name)', async () => {
    const err = await layoutErrorFromResponse(
      jsonResponse(409, {
        detail: {
          detail: 'Block wird noch referenziert.',
          blocked_by: [
            { type: 'route', id: 'r1', name: 'Hauptgleis' },
            { type: 'route', id: 'r2', name: 'Nebengleis' },
          ],
        },
      }),
    )
    expect(err.status).toBe(409)
    expect(err.detail).toBe('Block wird noch referenziert.')
    expect(err.isConflict).toBe(true)
    expect(err.blockedBy).toHaveLength(2)
    expect(err.blockedBy[0]).toEqual({ type: 'route', id: 'r1', name: 'Hauptgleis' })
    expect(err.blockedBy[1]!.name).toBe('Nebengleis')
  })

  it('nicht-JSON-Body -> generische Meldung mit Status', async () => {
    const resp = new Response('<<kein json>>', {
      status: 500,
      statusText: 'Internal Server Error',
      headers: { 'content-type': 'text/plain' },
    })
    const err = await layoutErrorFromResponse(resp)
    expect(err.status).toBe(500)
    expect(err.detail).toContain('500')
    expect(err.blockedBy).toEqual([])
  })
})
