import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import BlockList from '../BlockList.vue'
import type { Block, BlockRuntime } from '@/api/layout-types'
import { LayoutApiError } from '@/api/layout-error'

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

describe('BlockList', () => {
  it('zeigt Hinweis ohne Bloecke', () => {
    const wrapper = mount(BlockList, {
      props: { blocks: [], runtime: [], unit: 'cm' },
    })
    expect(wrapper.text()).toContain('Noch keine Blöcke')
  })

  it('rendert Laufzeitzustand frei/belegt/unbekannt (LED + Text)', () => {
    const blocks = [
      makeBlock({ id: 'b1', name: 'A' }),
      makeBlock({ id: 'b2', name: 'B' }),
      makeBlock({ id: 'b3', name: 'C' }),
    ]
    const runtime: BlockRuntime[] = [
      { block_id: 'b1', occupancy: 'occupied', loco_addresses: [3, 42] },
      { block_id: 'b2', occupancy: 'free', loco_addresses: [] },
      // b3 fehlt in runtime -> unknown
    ]
    const wrapper = mount(BlockList, { props: { blocks, runtime, unit: 'cm' } })
    const rows = wrapper.findAll('[data-testid="block-row"]')
    expect(rows).toHaveLength(3)

    expect(rows[0]!.get('[data-testid="block-led"]').classes()).toContain('on')
    expect(rows[0]!.get('[data-testid="block-occupancy"]').text()).toBe('belegt')
    expect(rows[0]!.get('[data-testid="block-locos"]').text()).toContain('3')
    expect(rows[0]!.get('[data-testid="block-locos"]').text()).toContain('42')

    expect(rows[1]!.get('[data-testid="block-led"]').classes()).toContain('off')
    expect(rows[1]!.get('[data-testid="block-occupancy"]').text()).toBe('frei')

    expect(rows[2]!.get('[data-testid="block-led"]').classes()).toContain('unknown')
    expect(rows[2]!.get('[data-testid="block-occupancy"]').text()).toBe('unbekannt')
  })

  it('zeigt warnings als nicht-blockierende Hinweise', () => {
    const wrapper = mount(BlockList, {
      props: {
        blocks: [makeBlock()],
        runtime: [],
        unit: 'cm',
        warnings: [{ code: 'no_length', message: 'Keine Länge gesetzt.' }],
      },
    })
    const warn = wrapper.get('[data-testid="block-warning"]')
    expect(warn.text()).toBe('Keine Länge gesetzt.')
  })

  it('zeigt 409-blocked_by als benannte Liste', () => {
    const error = new LayoutApiError(409, 'Block referenziert.', [
      { type: 'route', id: 'r1', name: 'Hauptgleis' },
    ])
    const wrapper = mount(BlockList, {
      props: { blocks: [makeBlock()], runtime: [], unit: 'cm', error },
    })
    const blocked = wrapper.get('[data-testid="block-blocked-by"]')
    expect(blocked.text()).toContain('route')
    expect(blocked.text()).toContain('Hauptgleis')
  })

  it('Neuanlage emittiert @create mit mm-Payload (cm -> mm)', async () => {
    const wrapper = mount(BlockList, { props: { blocks: [], runtime: [], unit: 'cm' } })
    const form = wrapper.get('[data-testid="block-create"]')
    await form.get('input[aria-label="Name neuer Block"]').setValue('Neu')
    await form.get('input[aria-label="Länge (cm)"]').setValue('100')
    await form.get('input[aria-label="Höchstgeschwindigkeit (km/h)"]').setValue('80')
    await form.trigger('submit')

    const emitted = wrapper.emitted('create')
    expect(emitted).toBeTruthy()
    expect(emitted![0]![0]).toEqual({ name: 'Neu', length_mm: 1000, max_speed_kmh: 80 })
  })

  it('Zoll-Eingabe wird auf ganze mm gerundet und sichtbar gemacht', async () => {
    const wrapper = mount(BlockList, { props: { blocks: [], runtime: [], unit: 'zoll' } })
    const form = wrapper.get('[data-testid="block-create"]')
    await form.get('input[aria-label="Name neuer Block"]').setValue('Zoll')
    await form.get('input[aria-label="Länge (″)"]').setValue('40')
    await form.trigger('submit')

    const emitted = wrapper.emitted('create')!
    // 40 Zoll * 25,4 = 1016 mm
    expect((emitted[0]![0] as { length_mm: number }).length_mm).toBe(1016)
    expect(wrapper.get('[data-testid="block-rounding"]').text()).toContain('1016 mm')
  })

  it('Editor emittiert @update mit mm-Payload und Markierungen', async () => {
    const block = makeBlock({ id: 'b1', length_mm: 1000 })
    const wrapper = mount(BlockList, { props: { blocks: [block], runtime: [], unit: 'cm' } })
    await wrapper.get('[data-testid="block-row"] button').trigger('click') // Bearbeiten
    const editor = wrapper.get('[data-testid="block-editor"]')
    await editor.get('input[aria-label="Blockname"]').setValue('Umbenannt')
    await editor.get('input[aria-label="Länge (cm)"]').setValue('150')
    // Halt-Marke vorwaerts per Position (cm)
    await editor.get('input[aria-label="forward stop Position"]').setValue('50')

    // Speichern-Button gezielt
    const saveBtn = editor.findAll('button').find((b) => b.text() === 'Speichern')
    await saveBtn!.trigger('click')

    const emitted = wrapper.emitted('update')!
    const [id, body] = emitted[emitted.length - 1]! as [
      string,
      Block & { markers_forward: Block['markers_forward'] },
    ]
    expect(id).toBe('b1')
    expect((body as { length_mm: number }).length_mm).toBe(1500)
    expect(body.markers_forward.stop).toEqual({ detector_ref: null, position_mm: 500 })
  })
})
