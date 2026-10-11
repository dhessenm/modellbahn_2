import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import DetectorList from '../DetectorList.vue'
import type { DetectorInput } from '@/api/types'

function makeInput(overrides: Partial<DetectorInput>): DetectorInput {
  return {
    nid: 0xd764,
    addr: 0,
    port: 0,
    occupied: false,
    with_power: true,
    overload: false,
    overload_level: 0,
    status_text: 'frei (mit Spannung)',
    locos: [],
    ...overrides,
  }
}

describe('DetectorList', () => {
  it('zeigt Hinweis ohne Daten', () => {
    const wrapper = mount(DetectorList, { props: { detectors: [] } })
    expect(wrapper.text()).toContain('Noch keine Belegtmelder-Daten')
  })

  it('freier Eingang -> LED aus (off)', () => {
    const wrapper = mount(DetectorList, {
      props: { detectors: [makeInput({ occupied: false })] },
    })
    const led = wrapper.get('[data-testid="detector-led"]')
    expect(led.classes()).toContain('off')
    expect(led.classes()).not.toContain('on')
  })

  it('besetzter Eingang -> LED an (on) und status_text', () => {
    const wrapper = mount(DetectorList, {
      props: {
        detectors: [
          makeInput({ occupied: true, status_text: 'besetzt (mit Spannung)' }),
        ],
      },
    })
    const led = wrapper.get('[data-testid="detector-led"]')
    expect(led.classes()).toContain('on')
    expect(wrapper.get('[data-testid="detector-status"]').text()).toBe('besetzt (mit Spannung)')
  })

  it('rendert Lokadressen mit Richtungssymbol, mehrere komma-getrennt', () => {
    const wrapper = mount(DetectorList, {
      props: {
        detectors: [
          makeInput({
            occupied: true,
            locos: [
              { address: 3, direction: 'forward' },
              { address: 42, direction: 'backward' },
              { address: 7, direction: 'unknown' },
            ],
          }),
        ],
      },
    })
    const text = wrapper.get('[data-testid="detector-locos"]').text()
    expect(text).toBe('▶ 3, ◀ 42, 7')
  })

  it('Ueberlast wird hervorgehoben (CSS-Klasse)', () => {
    const wrapper = mount(DetectorList, {
      props: {
        detectors: [
          makeInput({
            occupied: true,
            overload: true,
            overload_level: 2,
            status_text: 'besetzt (Ueberlast 2)',
          }),
        ],
      },
    })
    expect(wrapper.get('[data-testid="detector-status"]').classes()).toContain('overload')
  })

  it('besetzt ohne Lokadresse erzeugt kein Fehlerstyling (leeres Lok-Feld)', () => {
    const wrapper = mount(DetectorList, {
      props: {
        detectors: [makeInput({ occupied: true, status_text: 'besetzt (mit Spannung)' })],
      },
    })
    const status = wrapper.get('[data-testid="detector-status"]')
    expect(status.classes()).not.toContain('overload')
    expect(wrapper.get('[data-testid="detector-locos"]').text()).toBe('')
  })

  it('zeigt den Eingang 1-basiert (Port+1)', () => {
    const wrapper = mount(DetectorList, {
      props: { detectors: [makeInput({ port: 0 }), makeInput({ port: 1 })] },
    })
    const rows = wrapper.findAll('[data-testid="detector-row"]')
    expect(rows).toHaveLength(2)
    expect(rows[0]!.text()).toContain('Eingang 1')
    expect(rows[1]!.text()).toContain('Eingang 2')
  })
})
