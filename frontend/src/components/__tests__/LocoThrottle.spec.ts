import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import LocoThrottle from '../LocoThrottle.vue'

describe('LocoThrottle', () => {
  it('rendert mit vertikalem Slider (slider-vertical Klasse)', () => {
    const wrapper = mount(LocoThrottle, {
      props: { speed: 0, forward: true, disabled: false },
    })
    expect(wrapper.find('.slider-vertical').exists()).toBe(true)
  })

  it('setzt max auf den maxSpeed-Prop (28)', () => {
    const wrapper = mount(LocoThrottle, {
      props: { speed: 0, forward: true, disabled: false, maxSpeed: 28 },
    })
    const input = wrapper.find('input[type="range"]')
    expect(input.attributes('max')).toBe('28')
  })

  it('nutzt 126 als Standard, wenn maxSpeed nicht gesetzt ist', () => {
    const wrapper = mount(LocoThrottle, {
      props: { speed: 0, forward: true, disabled: false },
    })
    const input = wrapper.find('input[type="range"]')
    expect(input.attributes('max')).toBe('126')
  })

  it('klemmt den Wert beim Eingabe-Event auf effectiveMax', async () => {
    const wrapper = mount(LocoThrottle, {
      props: { speed: 0, forward: true, disabled: false, maxSpeed: 14 },
    })
    const input = wrapper.find('input[type="range"]')
    // Setze einen Wert ueber dem Maximum
    await input.setValue('20')
    const emitted = wrapper.emitted('drive')
    expect(emitted).toBeTruthy()
    // Der geklemmte Wert muss 14 sein
    expect((emitted![0]![0] as { speed: number }).speed).toBe(14)
  })
})
