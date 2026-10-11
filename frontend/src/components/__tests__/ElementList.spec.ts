import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ElementList from '../ElementList.vue'
import type { TopologyElement } from '@/api/layout-types'
import { LayoutApiError } from '@/api/layout-error'

function makeElement(overrides: Partial<TopologyElement> = {}): TopologyElement {
  return { id: 'e1', name: 'W1', type: 'turnout', address: 5, address_b: null, ...overrides }
}

describe('ElementList', () => {
  it('zeigt Hinweis ohne Elemente', () => {
    const wrapper = mount(ElementList, { props: { elements: [] } })
    expect(wrapper.text()).toContain('Noch keine Elemente')
  })

  it('rendert Typ und Adressen je Element', () => {
    const elements = [
      makeElement({ id: 'e1', name: 'W1', type: 'turnout', address: 5 }),
      makeElement({ id: 'e2', name: 'D1', type: 'dkw', address: 10, address_b: 11 }),
      makeElement({ id: 'e3', name: 'K1', type: 'crossing', address: null, address_b: null }),
    ]
    const wrapper = mount(ElementList, { props: { elements } })
    const rows = wrapper.findAll('[data-testid="element-row"]')
    expect(rows).toHaveLength(3)
    expect(rows[0]!.get('[data-testid="element-type"]').text()).toBe('Weiche')
    expect(rows[1]!.get('[data-testid="element-type"]').text()).toBe('DKW')
    expect(rows[2]!.get('[data-testid="element-type"]').text()).toBe('Kreuzung')
    expect(rows[1]!.text()).toContain('10')
    expect(rows[1]!.text()).toContain('11')
  })

  it('Neuanlage: Adressfelder je Typ (turnout 1, dkw 2, crossing 0)', async () => {
    const wrapper = mount(ElementList, { props: { elements: [] } })
    const form = wrapper.get('[data-testid="element-create"]')
    const typeSelect = form.get('select[aria-label="Typ neues Element"]')

    // turnout: Adresse A vorhanden, B nicht
    expect(form.find('input[aria-label="Adresse A neues Element"]').exists()).toBe(true)
    expect(form.find('input[aria-label="Adresse B neues Element"]').exists()).toBe(false)

    // dkw: beide Adressfelder
    await typeSelect.setValue('dkw')
    expect(form.find('input[aria-label="Adresse A neues Element"]').exists()).toBe(true)
    expect(form.find('input[aria-label="Adresse B neues Element"]').exists()).toBe(true)

    // crossing: keine Adressfelder
    await typeSelect.setValue('crossing')
    expect(form.find('input[aria-label="Adresse A neues Element"]').exists()).toBe(false)
    expect(form.find('input[aria-label="Adresse B neues Element"]').exists()).toBe(false)
  })

  it('Neuanlage emittiert @create mit korrekten Adressfeldern (dkw)', async () => {
    const wrapper = mount(ElementList, { props: { elements: [] } })
    const form = wrapper.get('[data-testid="element-create"]')
    await form.get('input[aria-label="Name neues Element"]').setValue('D1')
    await form.get('select[aria-label="Typ neues Element"]').setValue('dkw')
    await form.get('input[aria-label="Adresse A neues Element"]').setValue('10')
    await form.get('input[aria-label="Adresse B neues Element"]').setValue('11')
    await form.trigger('submit')

    const emitted = wrapper.emitted('create')!
    expect(emitted[0]![0]).toEqual({ name: 'D1', type: 'dkw', address: 10, address_b: 11 })
  })

  it('crossing sendet keine Adressen (null)', async () => {
    const wrapper = mount(ElementList, { props: { elements: [] } })
    const form = wrapper.get('[data-testid="element-create"]')
    await form.get('input[aria-label="Name neues Element"]').setValue('K1')
    await form.get('select[aria-label="Typ neues Element"]').setValue('crossing')
    await form.trigger('submit')

    const emitted = wrapper.emitted('create')!
    expect(emitted[0]![0]).toEqual({ name: 'K1', type: 'crossing', address: null, address_b: null })
  })

  it('zeigt 409-blocked_by als benannte Liste', () => {
    const error = new LayoutApiError(409, 'Element referenziert.', [
      { type: 'route', id: 'r1', name: 'Fahrstraße A' },
    ])
    const wrapper = mount(ElementList, { props: { elements: [makeElement()], error } })
    const blocked = wrapper.get('[data-testid="element-blocked-by"]')
    expect(blocked.text()).toContain('Fahrstraße A')
  })
})
