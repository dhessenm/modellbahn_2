import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import LocoInfoFrame from '../LocoInfoFrame.vue'

describe('LocoInfoFrame', () => {
  it('zeigt einen Hinweis, wenn keine Lok gewählt ist', () => {
    const wrapper = mount(LocoInfoFrame, { props: { loco: null } })
    expect(wrapper.text()).toContain('Keine Lok ausgewählt')
  })

  it('zeigt Lokdaten als Key-Value-Paare inklusive Funktionen', () => {
    const wrapper = mount(LocoInfoFrame, {
      props: {
        loco: {
          address: 3,
          speed: 42,
          forward: true,
          functions: { 0: true, 1: false },
        },
      },
    })
    const text = wrapper.text()
    expect(text).toContain('Adresse')
    expect(text).toContain('3')
    expect(text).toContain('Geschwindigkeit')
    expect(text).toContain('42')
    expect(text).toContain('vorwärts')
    expect(text).toContain('F0')
    expect(text).toContain('ein')
    expect(text).toContain('F1')
    expect(text).toContain('aus')
  })
})
