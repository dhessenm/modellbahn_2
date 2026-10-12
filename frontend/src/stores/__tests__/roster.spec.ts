import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { Locomotive, LocoWriteResponse, RosterResponse } from '@/api/roster-types'
import { LayoutApiError } from '@/api/layout-error'

// Gemockter API-Client. vi.hoisted stellt sicher, dass das Mock-Objekt vor dem
// (gehoisteten) vi.mock-Factory existiert.
const mockApi = vi.hoisted(() => ({
  getRoster: vi.fn<() => Promise<unknown>>(),
  createLoco: vi.fn<(body: unknown) => Promise<unknown>>(),
  updateLoco: vi.fn<(id: string, body: unknown) => Promise<unknown>>(),
  deleteLoco: vi.fn<(id: string) => Promise<void>>(),
  subscribeEvents: vi.fn<(onChange: () => void, onReconnect?: () => void) => () => void>(),
}))

vi.mock('@/api/client', () => ({ api: mockApi }))

function makeLoco(overrides: Partial<Locomotive> = {}): Locomotive {
  return {
    id: 'l1',
    name: 'BR 218',
    address: 218,
    speed_steps: 128,
    function_count: 28,
    length_mm: 163,
    max_speed_kmh: 140,
    notes: '',
    ...overrides,
  }
}

function emptyRoster(): RosterResponse {
  return { locomotives: [] }
}

// Store einmal importieren (gleiche Modulinstanz wie LayoutApiError -> instanceof
// funktioniert). Der Zustand wird je Test ueber start() frisch geladen.
import { useRosterStore } from '../roster'

describe('useRosterStore', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockApi.getRoster.mockResolvedValue(emptyRoster())
    mockApi.subscribeEvents.mockReturnValue(() => {})
  })

  it('start() laedt die Loks und registriert ein SSE-Abo', async () => {
    const loco = makeLoco()
    mockApi.getRoster.mockResolvedValue({ locomotives: [loco] })

    const store = useRosterStore()
    store.clearError()
    await store.start()

    expect(mockApi.getRoster).toHaveBeenCalledTimes(1)
    expect(mockApi.subscribeEvents).toHaveBeenCalledTimes(1)
    expect(store.locomotives.value).toHaveLength(1)
    expect(store.locomotives.value[0]!.name).toBe('BR 218')
  })

  it('SSE-onChange laedt den Zustand erneut', async () => {
    let onChange: () => void = () => {}
    mockApi.subscribeEvents.mockImplementation((cb: () => void) => {
      onChange = cb
      return () => {}
    })

    const store = useRosterStore()
    await store.start()
    expect(mockApi.getRoster).toHaveBeenCalledTimes(1)

    onChange()
    await Promise.resolve()
    await Promise.resolve()
    expect(mockApi.getRoster).toHaveBeenCalledTimes(2)
  })

  it('createLoco ruft die API, laedt neu und uebernimmt warnings', async () => {
    const loco = makeLoco()
    const resp: LocoWriteResponse = {
      entity: loco,
      warnings: [{ code: 'adresse_doppelt', message: 'Adresse 218 bereits vergeben.' }],
    }
    mockApi.createLoco.mockResolvedValue(resp)

    const store = useRosterStore()
    await store.start()
    mockApi.getRoster.mockClear()

    const result = await store.createLoco({
      name: 'BR 218',
      address: 218,
      speed_steps: 128,
      function_count: 28,
      length_mm: 163,
      max_speed_kmh: 140,
      notes: '',
    })

    expect(mockApi.createLoco).toHaveBeenCalledTimes(1)
    expect(result.id).toBe('l1')
    expect(mockApi.getRoster).toHaveBeenCalledTimes(1) // refreshAll nach Erfolg
    expect(store.warnings.value).toHaveLength(1)
    expect(store.warnings.value[0]!.code).toBe('adresse_doppelt')
  })

  it('deleteLoco mit LayoutApiError legt den Fehler ab und wirft weiter', async () => {
    const err = new LayoutApiError(404, 'Lok unbekannt.')
    mockApi.deleteLoco.mockRejectedValue(err)

    const store = useRosterStore()
    await store.start()

    await expect(store.deleteLoco('l1')).rejects.toBe(err)
    expect(store.error.value).toBe('Lok unbekannt.')
    expect(store.lastError.value?.status).toBe(404)
  })

  it('stop() ruft die Unsubscribe-Funktion auf', async () => {
    const unsubscribe = vi.fn<() => void>()
    mockApi.subscribeEvents.mockReturnValue(unsubscribe)

    const store = useRosterStore()
    await store.start()
    store.stop()

    expect(unsubscribe).toHaveBeenCalledTimes(1)
  })
})
