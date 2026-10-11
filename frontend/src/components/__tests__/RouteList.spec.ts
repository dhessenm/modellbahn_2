import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import RouteList from '../RouteList.vue'
import type { Block, Route, TopologyElement } from '@/api/layout-types'
import { LayoutApiError } from '@/api/layout-error'

function makeBlock(id: string, name: string): Block {
  return {
    id,
    name,
    length_mm: null,
    max_speed_kmh: null,
    detectors: [],
    markers_forward: { stop: null, brake: null },
    markers_backward: { stop: null, brake: null },
  }
}

function makeElement(
  id: string,
  name: string,
  type: TopologyElement['type'] = 'turnout',
): TopologyElement {
  return { id, name, type, address: 1, address_b: null }
}

const blocks = [makeBlock('b1', 'Start'), makeBlock('b2', 'Mitte'), makeBlock('b3', 'Ziel')]
const elements = [makeElement('e1', 'W1'), makeElement('e2', 'K1', 'crossing')]

function makeRoute(overrides: Partial<Route> = {}): Route {
  return {
    id: 'r1',
    name: 'Route 1',
    start_block_id: 'b1',
    transit_block_ids: ['b2'],
    end_block_id: 'b3',
    element_settings: [{ element_id: 'e1', desired_state: 1 }],
    claimed_element_ids: ['e2'],
    ...overrides,
  }
}

describe('RouteList', () => {
  it('zeigt Hinweis ohne Fahrstrassen', () => {
    const wrapper = mount(RouteList, { props: { routes: [], blocks, elements } })
    expect(wrapper.text()).toContain('Noch keine Fahrstraßen')
  })

  it('rendert Pfad Start -> [Zwischen] -> Ziel mit Blocknamen', () => {
    const wrapper = mount(RouteList, { props: { routes: [makeRoute()], blocks, elements } })
    const path = wrapper.get('[data-testid="route-path"]')
    expect(path.text()).toBe('Start → Mitte → Ziel')
  })

  it('rendert Element-Stellungen und beanspruchte Elemente mit Namen', () => {
    const wrapper = mount(RouteList, { props: { routes: [makeRoute()], blocks, elements } })
    expect(wrapper.get('[data-testid="route-settings"]').text()).toContain('W1=1')
    expect(wrapper.get('[data-testid="route-claimed"]').text()).toContain('K1')
  })

  it('Neuanlage emittiert @create mit aufgeloesten Feldern', async () => {
    const wrapper = mount(RouteList, { props: { routes: [], blocks, elements } })
    const form = wrapper.get('[data-testid="route-create"]')
    await form.get('input[aria-label="Name neue Fahrstraße"]').setValue('Neu')
    await form.get('select[aria-label="Startblock neue Fahrstraße"]').setValue('b1')
    await form.get('select[aria-label="Zielblock neue Fahrstraße"]').setValue('b3')
    await form.trigger('submit')

    const emitted = wrapper.emitted('create')!
    const body = emitted[0]![0] as Route
    expect(body.name).toBe('Neu')
    expect(body.start_block_id).toBe('b1')
    expect(body.end_block_id).toBe('b3')
  })

  it('Stellungs-Auswahl bietet nur schaltbare Elemente (keine crossing)', async () => {
    const wrapper = mount(RouteList, { props: { routes: [], blocks, elements } })
    const form = wrapper.get('[data-testid="route-create"]')
    const addBtn = form.findAll('button').find((b) => b.text() === 'Stellung hinzufügen')
    await addBtn!.trigger('click')

    const settingSelect = form.get('select[aria-label="Element der Stellung (neu)"]')
    const optionValues = settingSelect.findAll('option').map((o) => o.attributes('value'))
    // crossing (e2) darf NICHT als Stellungs-Element waehlbar sein
    expect(optionValues).toContain('e1')
    expect(optionValues).not.toContain('e2')
  })

  it('zeigt 409-blocked_by als benannte Liste', () => {
    const error = new LayoutApiError(409, 'Fahrstraße referenziert.', [
      { type: 'route', id: 'r9', name: 'Andere' },
    ])
    const wrapper = mount(RouteList, { props: { routes: [makeRoute()], blocks, elements, error } })
    expect(wrapper.get('[data-testid="route-blocked-by"]').text()).toContain('Andere')
  })
})
