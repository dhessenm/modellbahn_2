import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import TrackPower from '../TrackPower.vue'

describe('TrackPower', () => {
  it('zeigt den An-Zustand, wenn on=true', () => {
    const wrapper = mount(TrackPower, {
      props: { on: true },
    })
    const led = wrapper.find('.tp-led')
    expect(led.classes()).toContain('on')
  })

  it('zeigt den Aus-Zustand, wenn on=false', () => {
    const wrapper = mount(TrackPower, {
      props: { on: false },
    })
    const led = wrapper.find('.tp-led')
    expect(led.classes()).not.toContain('on')
  })

  it('sendet toggle(false) beim Klick, wenn on=true', async () => {
    const wrapper = mount(TrackPower, {
      props: { on: true },
    })
    await wrapper.find('button').trigger('click')
    const emitted = wrapper.emitted('toggle')
    expect(emitted).toBeTruthy()
    expect(emitted![0]).toEqual([false])
  })

  it('sendet toggle(true) beim Klick, wenn on=false', async () => {
    const wrapper = mount(TrackPower, {
      props: { on: false },
    })
    await wrapper.find('button').trigger('click')
    const emitted = wrapper.emitted('toggle')
    expect(emitted).toBeTruthy()
    expect(emitted![0]).toEqual([true])
  })
})
