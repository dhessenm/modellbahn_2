import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import type { Locomotive } from '@/api/roster-types'
import type { LocoState, SystemStatus } from '@/api/types'

// --- Roster-Store mocken ---------------------------------------------------
// Modul-weite Refs, die wir je Test befuellen koennen.
const rosterLocomotives = vi.hoisted(() => ({ value: [] as Locomotive[] }))
const rosterStart = vi.hoisted(() => vi.fn<() => Promise<void>>())
const rosterStop = vi.hoisted(() => vi.fn<() => void>())

vi.mock('@/stores/roster', () => ({
  useRosterStore: () => ({
    locomotives: rosterLocomotives,
    start: rosterStart,
    stop: rosterStop,
  }),
}))

// --- Layout-Store mocken ---------------------------------------------------
const layoutStatus = vi.hoisted(() => ({ value: null as SystemStatus | null }))
const layoutLoco = vi.hoisted(() => ({ value: null as LocoState | null }))
const layoutActiveAddress = vi.hoisted(() => ({ value: null as number | null }))
const layoutSelectLoco = vi.hoisted(() => vi.fn<(address: number) => Promise<void>>())
const layoutDrive = vi.hoisted(() =>
  vi.fn<(speed: number, forward: boolean, speedSteps?: number) => Promise<void>>(),
)
const layoutSetFunction = vi.hoisted(() => vi.fn<(func: number, on: boolean) => Promise<void>>())

vi.mock('@/stores/layout', () => ({
  useLayoutStore: () => ({
    status: layoutStatus,
    loco: layoutLoco,
    activeAddress: layoutActiveAddress,
    selectLoco: layoutSelectLoco,
    drive: layoutDrive,
    setFunction: layoutSetFunction,
  }),
}))

import CabView from '../CabView.vue'
import LocoThrottle from '@/components/LocoThrottle.vue'

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

const stubs = {
  // RouterLink durch ein einfaches Element ersetzen (kein Router im Unit-Test).
  RouterLink: { template: '<a><slot /></a>' },
}

describe('CabView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    rosterLocomotives.value = []
    layoutStatus.value = { track_power_on: true } as SystemStatus
    layoutLoco.value = null
    layoutActiveAddress.value = null
  })

  it('rendert ein <select> statt eines Adress-Nummernfeldes', () => {
    rosterLocomotives.value = [makeLoco()]
    const wrapper = mount(CabView, { global: { stubs } })

    expect(wrapper.find('select').exists()).toBe(true)
    expect(wrapper.find('input[type="number"]').exists()).toBe(false)
  })

  it('zeigt den Hinweis, wenn die Lokverwaltung leer ist', () => {
    rosterLocomotives.value = []
    const wrapper = mount(CabView, { global: { stubs } })

    expect(wrapper.text()).toContain('Bitte zuerst eine Lok')
    expect(wrapper.find('select').exists()).toBe(false)
  })

  it('setzt maxSpeed=28 am LocoThrottle fuer eine 28-stufige Lok', async () => {
    const loco28 = makeLoco({ id: 'l28', speed_steps: 28, function_count: 10 })
    rosterLocomotives.value = [loco28]
    layoutActiveAddress.value = 218
    layoutLoco.value = { address: 218, speed: 0, forward: true, functions: {} }

    const wrapper = mount(CabView, { global: { stubs } })

    // Lok im Dropdown waehlen.
    await wrapper.find('select').setValue('l28')
    await wrapper.vm.$nextTick()

    const throttle = wrapper.findComponent(LocoThrottle)
    expect(throttle.exists()).toBe(true)
    expect(throttle.props('maxSpeed')).toBe(28)
  })

  it('legt den LocoInfoFrame in ein <details>-Element', async () => {
    rosterLocomotives.value = [makeLoco()]
    layoutActiveAddress.value = 218
    layoutLoco.value = { address: 218, speed: 0, forward: true, functions: {} }

    const wrapper = mount(CabView, { global: { stubs } })
    await wrapper.find('select').setValue('l1')
    await wrapper.vm.$nextTick()

    expect(wrapper.find('details').exists()).toBe(true)
  })
})
