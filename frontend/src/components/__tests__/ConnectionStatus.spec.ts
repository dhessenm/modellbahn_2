import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ConnectionStatus from '../ConnectionStatus.vue'

describe('ConnectionStatus', () => {
  it('zeigt eine aktive LED, wenn verbunden', () => {
    const wrapper = mount(ConnectionStatus, {
      props: { connected: true, host: '192.168.0.111', port: 21105 },
    })
    const led = wrapper.find('[data-testid="connection-led"]')
    expect(led.exists()).toBe(true)
    expect(led.classes()).toContain('on')
  })

  it('zeigt eine inaktive LED, wenn nicht verbunden', () => {
    const wrapper = mount(ConnectionStatus, {
      props: { connected: false, host: '192.168.0.111', port: 21105 },
    })
    const led = wrapper.find('[data-testid="connection-led"]')
    expect(led.classes()).not.toContain('on')
  })

  it('rendert keinen sichtbaren Verbindungstext', () => {
    const wrapper = mount(ConnectionStatus, {
      props: { connected: true, host: '192.168.0.111', port: 21105 },
    })
    expect(wrapper.text()).not.toContain('Verbunden')
    expect(wrapper.text()).not.toContain('Keine Verbindung')
  })

  it('legt die Verbindungsinfo in das title-Attribut', () => {
    const wrapper = mount(ConnectionStatus, {
      props: { connected: true, host: '192.168.0.111', port: 21105 },
    })
    const led = wrapper.find('[data-testid="connection-led"]')
    expect(led.attributes('title')).toContain('192.168.0.111:21105')
  })
})
