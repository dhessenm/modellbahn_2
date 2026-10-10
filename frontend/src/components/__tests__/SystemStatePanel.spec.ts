import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import SystemStatePanel from '../SystemStatePanel.vue'
import type { SystemStatus } from '@/api/types'

const base: SystemStatus = {
  connected: true,
  track_power_on: true,
  short_circuit: false,
  emergency_stop: false,
  temperature_c: 31,
  supply_voltage_mv: 15000,
  track_voltage_mv: 18000,
  z21_host: '192.168.0.111',
  z21_port: 21105,
}

describe('SystemStatePanel', () => {
  it('zeigt Hinweis ohne Daten', () => {
    const wrapper = mount(SystemStatePanel, { props: { status: null } })
    expect(wrapper.text()).toContain('Noch keine Daten')
  })

  it('zeigt Zentralenstatus inkl. umgerechneter Spannungen', () => {
    const wrapper = mount(SystemStatePanel, { props: { status: base } })
    const text = wrapper.text()
    expect(text).toContain('Gleisspannung')
    expect(text).toContain('ein')
    expect(text).toContain('31 °C')
    expect(text).toContain('15.00 V') // supply 15000 mV
    expect(text).toContain('18.00 V') // track 18000 mV
    expect(text).toContain('192.168.0.111:21105')
  })

  it('hebt Warnzustände hervor (Kurzschluss)', () => {
    const wrapper = mount(SystemStatePanel, {
      props: { status: { ...base, short_circuit: true } },
    })
    const warn = wrapper.find('dd.warn')
    expect(warn.exists()).toBe(true)
  })
})
