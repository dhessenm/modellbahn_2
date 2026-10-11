import { describe, it, expect, vi, beforeEach } from 'vitest'
import type {
  Block,
  BlockRuntime,
  BlockWriteResponse,
  LayoutModel,
  TopologyElement,
} from '@/api/layout-types'
import { LayoutApiError } from '@/api/layout-error'

// Gemockter API-Client. vi.hoisted stellt sicher, dass das Mock-Objekt vor dem
// (gehoisteten) vi.mock-Factory existiert.
const mockApi = vi.hoisted(() => ({
  getLayout: vi.fn<() => Promise<unknown>>(),
  getLayoutRuntime: vi.fn<() => Promise<unknown>>(),
  createBlock: vi.fn<(body: unknown) => Promise<unknown>>(),
  updateBlock: vi.fn<(id: string, body: unknown) => Promise<unknown>>(),
  deleteBlock: vi.fn<(id: string) => Promise<void>>(),
  setBlockDetectors: vi.fn<(id: string, body: unknown) => Promise<unknown>>(),
  createElement: vi.fn<(body: unknown) => Promise<unknown>>(),
  updateElement: vi.fn<(id: string, body: unknown) => Promise<unknown>>(),
  deleteElement: vi.fn<(id: string) => Promise<void>>(),
  createRoute: vi.fn<(body: unknown) => Promise<unknown>>(),
  updateRoute: vi.fn<(id: string, body: unknown) => Promise<unknown>>(),
  deleteRoute: vi.fn<(id: string) => Promise<void>>(),
  subscribeEvents: vi.fn<(onChange: () => void, onReconnect?: () => void) => () => void>(),
}))

vi.mock('@/api/client', () => ({ api: mockApi }))

function makeBlock(overrides: Partial<Block> = {}): Block {
  return {
    id: 'b1',
    name: 'Block 1',
    length_mm: 1000,
    max_speed_kmh: 60,
    detectors: [],
    markers_forward: { stop: null, brake: null },
    markers_backward: { stop: null, brake: null },
    ...overrides,
  }
}

function makeElement(overrides: Partial<TopologyElement> = {}): TopologyElement {
  return { id: 'e1', name: 'W1', type: 'turnout', address: 5, address_b: null, ...overrides }
}

function emptyModel(): LayoutModel {
  return { blocks: [], elements: [], routes: [] }
}

function makeWriteResponse(block: Block, warnings = []): BlockWriteResponse {
  return { entity: block, warnings }
}

// Store einmal importieren (gleiche Modulinstanz wie LayoutApiError -> instanceof
// funktioniert). Der Zustand wird je Test ueber start() frisch geladen.
import { useAnlageStore } from '../anlage'

async function freshStore() {
  const store = useAnlageStore()
  // Zustand neutralisieren, damit Tests isoliert bleiben.
  store.clearError()
  return store
}

describe('useAnlageStore', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // sinnvolle Defaults
    mockApi.getLayout.mockResolvedValue(emptyModel())
    mockApi.getLayoutRuntime.mockResolvedValue([] as BlockRuntime[])
    mockApi.subscribeEvents.mockReturnValue(() => {})
  })

  it('start() laedt Modell + runtime und registriert ein SSE-Abo', async () => {
    const block = makeBlock()
    const element = makeElement()
    const runtime: BlockRuntime[] = [{ block_id: 'b1', occupancy: 'occupied', loco_addresses: [3] }]
    mockApi.getLayout.mockResolvedValue({ blocks: [block], elements: [element], routes: [] })
    mockApi.getLayoutRuntime.mockResolvedValue(runtime)

    const store = await freshStore()
    await store.start()

    expect(mockApi.getLayout).toHaveBeenCalledTimes(1)
    expect(mockApi.getLayoutRuntime).toHaveBeenCalledTimes(1)
    expect(mockApi.subscribeEvents).toHaveBeenCalledTimes(1)
    expect(store.blocks.value).toHaveLength(1)
    expect(store.elements.value).toHaveLength(1)
    expect(store.runtime.value[0]!.occupancy).toBe('occupied')
  })

  it('SSE-onChange laedt den Zustand erneut', async () => {
    let onChange: () => void = () => {}
    mockApi.subscribeEvents.mockImplementation((cb: () => void) => {
      onChange = cb
      return () => {}
    })

    const store = await freshStore()
    await store.start()
    expect(mockApi.getLayout).toHaveBeenCalledTimes(1)

    onChange()
    // Mikrotasks abarbeiten
    await Promise.resolve()
    await Promise.resolve()
    expect(mockApi.getLayout).toHaveBeenCalledTimes(2)
    expect(mockApi.getLayoutRuntime).toHaveBeenCalledTimes(2)
  })

  it('createBlock ruft die API, laedt neu und uebernimmt warnings', async () => {
    const block = makeBlock()
    mockApi.createBlock.mockResolvedValue(
      makeWriteResponse(block, [{ code: 'no_length', message: 'Keine Länge gesetzt.' }] as never),
    )

    const store = await freshStore()
    await store.start()
    mockApi.getLayout.mockClear()

    const result = await store.createBlock({ name: 'Block 1', length_mm: 1000, max_speed_kmh: 60 })

    expect(mockApi.createBlock).toHaveBeenCalledWith({
      name: 'Block 1',
      length_mm: 1000,
      max_speed_kmh: 60,
    })
    expect(result.id).toBe('b1')
    expect(mockApi.getLayout).toHaveBeenCalledTimes(1) // refreshAll nach Erfolg
    expect(store.warnings.value).toHaveLength(1)
    expect(store.warnings.value[0]!.code).toBe('no_length')
  })

  it('deleteBlock mit 409 legt den Fehler strukturiert ab und wirft weiter', async () => {
    const conflict = new LayoutApiError(409, 'Block referenziert.', [
      { type: 'route', id: 'r1', name: 'Hauptgleis' },
    ])
    mockApi.deleteBlock.mockRejectedValue(conflict)

    const store = await freshStore()
    await store.start()

    await expect(store.deleteBlock('b1')).rejects.toBe(conflict)
    expect(store.error.value).toBe('Block referenziert.')
    expect(store.lastError.value?.status).toBe(409)
    expect(store.lastError.value?.blockedBy[0]!.name).toBe('Hauptgleis')
  })

  it('stop() ruft die Unsubscribe-Funktion auf', async () => {
    const unsubscribe = vi.fn<() => void>()
    mockApi.subscribeEvents.mockReturnValue(unsubscribe)

    const store = await freshStore()
    await store.start()
    store.stop()

    expect(unsubscribe).toHaveBeenCalledTimes(1)
  })

  it('Einheiten: toMm/fromMm rechnen korrekt und runden auf ganze mm', async () => {
    const store = await freshStore()

    store.setUnit('zoll')
    expect(store.unit.value).toBe('zoll')
    expect(store.toMm(2.54)).toBe(65) // 2,54 * 25,4 = 64,516 -> 65
    expect(store.toMm(1)).toBe(25) // 25,4 -> 25

    store.setUnit('cm')
    expect(store.toMm(5)).toBe(50)
    expect(store.fromMm(50)).toBe(5)

    store.setUnit('mm')
    expect(store.toMm(123)).toBe(123)
    expect(store.fromMm(123)).toBe(123)
  })
})
