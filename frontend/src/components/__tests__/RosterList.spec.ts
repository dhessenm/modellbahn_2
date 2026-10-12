import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import RosterList from '../RosterList.vue'
import type { Locomotive, RosterWarning } from '@/api/roster-types'
import { LayoutApiError } from '@/api/layout-error'

function makeLoco(overrides: Partial<Locomotive> = {}): Locomotive {
  return {
    id: 'loco-1',
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

describe('RosterList', () => {
  it('zeigt je Lok eine Zeile mit Name und Adresse', () => {
    const locos = [
      makeLoco({ id: 'l1', name: 'BR 101', address: 101 }),
      makeLoco({ id: 'l2', name: 'BR 218', address: 218 }),
    ]
    const wrapper = mount(RosterList, {
      props: { locomotives: locos, unit: 'cm' },
    })
    const rows = wrapper.findAll('[data-testid="roster-row"]')
    expect(rows).toHaveLength(2)
    expect(rows[0]!.text()).toContain('BR 101')
    expect(rows[0]!.text()).toContain('101')
    expect(rows[1]!.text()).toContain('BR 218')
    expect(rows[1]!.text()).toContain('218')
  })

  it('Neuanlage-Formular emittiert create mit korrektem LocoWrite (Defaults + Laenge in mm)', async () => {
    const wrapper = mount(RosterList, {
      props: { locomotives: [], unit: 'cm' },
    })
    const form = wrapper.find('[data-testid="roster-create"]')

    // Pflichtfelder ausfuellen; Fahrstufenmodus und Funktionsanzahl lassen wir
    // auf Default (128 / 28), Laenge auf 5 cm -> 50 mm.
    await form.find('input[aria-label="Name neue Lok"]').setValue('BR 101')
    await form.find('input[aria-label="DCC-Adresse neue Lok"]').setValue('101')
    await form.find('input[aria-label="Länge neue Lok (cm)"]').setValue('5')
    await form.trigger('submit')

    const emitted = wrapper.emitted('create')
    expect(emitted).toBeTruthy()
    expect(emitted).toHaveLength(1)
    const body = emitted![0]![0] as Record<string, unknown>
    expect(body.name).toBe('BR 101')
    expect(body.address).toBe(101)
    expect(body.speed_steps).toBe(128)
    expect(body.function_count).toBe(28)
    expect(body.length_mm).toBe(50) // 5 cm -> 50 mm
  })

  it('zeigt Adress-Duplikat-Warnung, wenn in Props uebergeben', () => {
    const warnings: RosterWarning[] = [
      { code: 'adresse_doppelt', message: 'Adresse 3 ist bereits der Lok \'BR 218\' zugeordnet.' },
    ]
    const wrapper = mount(RosterList, {
      props: { locomotives: [], unit: 'cm', warnings },
    })
    const warnEls = wrapper.findAll('[data-testid="roster-warning"]')
    expect(warnEls).toHaveLength(1)
    expect(warnEls[0]!.text()).toContain('Adresse 3')
  })

  it('zeigt Fehlertext, wenn error-Prop gesetzt', () => {
    const err = new LayoutApiError(400, 'Name darf nicht leer sein.')
    const wrapper = mount(RosterList, {
      props: { locomotives: [], unit: 'cm', error: err },
    })
    const errorEl = wrapper.find('[data-testid="roster-error"]')
    expect(errorEl.exists()).toBe(true)
    expect(errorEl.text()).toContain('Name darf nicht leer sein.')
  })
})
