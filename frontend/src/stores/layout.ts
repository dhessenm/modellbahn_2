// Zentraler Frontend-Zustand (Composable).
//
// Wichtig: Die Single Source of Truth liegt im Backend. Dieser Store spiegelt
// nur und holt bei jedem SSE-'changed'-Signal den aktuellen Zustand per GET
// nach -> REST und Push bleiben konsistent.

import { readonly, ref } from 'vue'
import { api } from '@/api/client'
import type { LocoState, SystemStatus } from '@/api/types'

const status = ref<SystemStatus | null>(null)
const loco = ref<LocoState | null>(null)
const activeAddress = ref<number | null>(null)
const error = ref<string | null>(null)

let unsubscribe: (() => void) | null = null

async function refreshStatus(): Promise<void> {
  try {
    status.value = await api.getSystemStatus()
  } catch (e) {
    error.value = (e as Error).message
  }
}

async function refreshLoco(): Promise<void> {
  if (activeAddress.value === null) return
  try {
    loco.value = await api.getLoco(activeAddress.value)
  } catch {
    // 404: Lok noch nicht bekannt -> lokalen Platzhalter behalten.
  }
}

async function refreshAll(): Promise<void> {
  await Promise.all([refreshStatus(), refreshLoco()])
}

export function useLayoutStore() {
  async function start(): Promise<void> {
    await refreshAll()
    unsubscribe = api.subscribeEvents(
      () => {
        void refreshAll()
      },
      () => {
        // Bei (Wieder-)Verbindung den Zustand frisch holen.
        void refreshAll()
      },
    )
  }

  function stop(): void {
    unsubscribe?.()
    unsubscribe = null
  }

  async function selectLoco(address: number): Promise<void> {
    activeAddress.value = address
    // Platzhalter, bis die Zentrale den echten Zustand liefert.
    loco.value = { address, speed: 0, forward: true, functions: {} }
    // Aktuellen Zustand bei der Zentrale anfordern; Antwort kommt per SSE/GET.
    try {
      await api.subscribeLoco(address)
    } catch (e) {
      error.value = (e as Error).message
    }
    await refreshLoco()
  }

  async function setTrackPower(on: boolean): Promise<void> {
    await api.setTrackPower(on)
    await refreshStatus()
  }

  async function drive(speed: number, forward: boolean): Promise<void> {
    if (activeAddress.value === null) return
    await api.drive(activeAddress.value, speed, forward)
    await refreshLoco()
  }

  async function setFunction(func: number, on: boolean): Promise<void> {
    if (activeAddress.value === null) return
    await api.setFunction(activeAddress.value, func, on)
    await refreshLoco()
  }

  return {
    status: readonly(status),
    loco: readonly(loco),
    activeAddress: readonly(activeAddress),
    error: readonly(error),
    start,
    stop,
    selectLoco,
    setTrackPower,
    drive,
    setFunction,
  }
}
