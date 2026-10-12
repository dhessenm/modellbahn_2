// Zentraler Frontend-Zustand fuer die Lokverwaltung (Composable useRosterStore).
//
// Wichtig: Die Single Source of Truth liegt im Backend. Dieser Store spiegelt
// die verwalteten Loks (Stammdaten) nur und laedt bei jedem SSE-'changed'-Signal
// frisch nach -> REST und Push bleiben konsistent. Das SSE-Abo lebt in DIESEM
// Store (eigenes Abo, unabhaengig vom globalen Abo in App.vue/useLayoutStore).
//
// Hinweis: Hier werden ausschliesslich feste Stammdaten verwaltet, KEINE
// fluechtigen LocoState-Momentanzustaende (Geschwindigkeit/Richtung) aus dem
// Fahrbetrieb.

import { readonly, ref } from 'vue'
import { api } from '@/api/client'
import { LayoutApiError } from '@/api/layout-error'
import type { Locomotive, LocoWrite, RosterWarning } from '@/api/roster-types'

const locomotives = ref<Locomotive[]>([])

// Letzte nicht-blockierende Warnungen aus einer Schreibantwort (z. B.
// Adress-Duplikat, code 'adresse_doppelt').
const warnings = ref<RosterWarning[]>([])
// Zuletzt aufgetretener Fehler: `error` als anzeigbarer Text, `lastError` als
// strukturierte LayoutApiError.
const error = ref<string | null>(null)
const lastError = ref<LayoutApiError | null>(null)

let unsubscribe: (() => void) | null = null

async function refreshAll(): Promise<void> {
  try {
    const resp = await api.getRoster()
    locomotives.value = resp.locomotives
  } catch (e) {
    error.value = (e as Error).message
    console.error('[roster] laden fehlgeschlagen', e)
  }
}

// Fuehrt eine CRUD-Aktion aus: raeumt den Fehlerzustand auf, laedt bei Erfolg
// den Zustand neu und legt bei LayoutApiError die Fehlerinfo strukturiert ab.
// Der Fehler wird WEITERGEWORFEN, damit die aufrufende Komponente ihn am
// Formular anzeigen kann.
async function runAction<T>(action: () => Promise<T>): Promise<T> {
  error.value = null
  lastError.value = null
  try {
    const result = await action()
    await refreshAll()
    return result
  } catch (e) {
    if (e instanceof LayoutApiError) {
      lastError.value = e
      error.value = e.detail
    } else {
      error.value = (e as Error).message
    }
    throw e
  }
}

export function useRosterStore() {
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

  function clearError(): void {
    error.value = null
    lastError.value = null
  }

  async function createLoco(body: LocoWrite): Promise<Locomotive> {
    const resp = await runAction(() => api.createLoco(body))
    warnings.value = resp.warnings
    return resp.entity
  }

  async function updateLoco(id: string, body: LocoWrite): Promise<Locomotive> {
    const resp = await runAction(() => api.updateLoco(id, body))
    warnings.value = resp.warnings
    return resp.entity
  }

  async function deleteLoco(id: string): Promise<void> {
    await runAction(() => api.deleteLoco(id))
  }

  return {
    // Zustand (nach aussen readonly)
    locomotives: readonly(locomotives),
    warnings: readonly(warnings),
    error: readonly(error),
    lastError: readonly(lastError),
    // Lebenszyklus
    start,
    stop,
    // Fehler
    clearError,
    // CRUD
    createLoco,
    updateLoco,
    deleteLoco,
  }
}
