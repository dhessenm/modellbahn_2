import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import FunctionButtons from '../FunctionButtons.vue'

describe('FunctionButtons', () => {
  it('markiert aktive Funktionen und sendet beim Klick den Umschaltwert', async () => {
    const wrapper = mount(FunctionButtons, {
      props: { functions: { 0: true }, disabled: false, count: 3 },
    })
    const buttons = wrapper.findAll('button')
    expect(buttons).toHaveLength(3)
    // F0 ist an -> Klick soll ausschalten (on=false)
    await buttons[0]!.trigger('click')
    // F1 ist aus -> Klick soll einschalten (on=true)
    await buttons[1]!.trigger('click')

    const emitted = wrapper.emitted('toggle')
    expect(emitted).toBeTruthy()
    expect(emitted![0]).toEqual([{ func: 0, on: false }])
    expect(emitted![1]).toEqual([{ func: 1, on: true }])
  })

  it('deaktiviert alle Tasten, wenn disabled gesetzt ist', () => {
    const wrapper = mount(FunctionButtons, {
      props: { functions: {}, disabled: true, count: 2 },
    })
    expect(wrapper.findAll('button').every((b) => b.attributes('disabled') !== undefined)).toBe(
      true,
    )
  })
})
