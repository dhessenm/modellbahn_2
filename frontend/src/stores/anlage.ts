// Zentraler Frontend-Zustand fuer das Anlagenmodell (Composable useAnlageStore).
//
// Wichtig: Die Single Source of Truth liegt im Backend. Dieser Store spiegelt
// das Gesamtmodell (Bloecke, Elemente, Fahrstrassen) sowie den Laufzeitzustand
// (runtime) nur und laedt bei jedem SSE-'changed'-Signal frisch nach -> REST und
// Push bleiben konsistent. Das SSE-Abo lebt in DIESEM Store (eigenes Abo,
// unabhaengig vom globalen Abo in App.vue/useLayoutStore).
//
// Dieser Store ist SEPARAT von stores/layout.ts (dort: System/Lok/Melder).

import { readonly, ref } from 'vue'
import { api } from '@/api/client'
import { LayoutApiError } from '@/api/layout-error'
import type {
  Block,
  BlockWrite,
  DetectorAssignmentsBody,
  BlockRuntime,
  ElementWrite,
  Route,
  RouteWrite,
  TopologyElement,
  Warning,
} from '@/api/layout-types'
import { fromMm, toMm, type LengthUnit } from './length-units'

const blocks = ref<Block[]>([])
const elements = ref<TopologyElement[]>([])
const routes = ref<Route[]>([])
const runtime = ref<BlockRuntime[]>([])

// Letzte nicht-blockierende Konsistenz-Warnungen aus einer Block-Schreibantwort.
const warnings = ref<Warning[]>([])
// Zuletzt aufgetretener Fehler: `error` als anzeigbarer Text, `lastError` als
// strukturierte LayoutApiError (fuer 409-blocked_by-Anzeige in der UI).
const error = ref<string | null>(null)
const lastError = ref<LayoutApiError | null>(null)

// Zentrale, umschaltbare Anzeige-Einheit. Transport/Backend bleiben ganze mm;
// nur die Darstellung/Eingabe nutzt diese Einheit. Default: cm.
const unit = ref<LengthUnit>('cm')

let unsubscribe: (() => void) | null = null

async function refreshAll(): Promise<void> {
  try {
    const [model, rt] = await Promise.all([api.getLayout(), api.getLayoutRuntime()])
    blocks.value = model.blocks
    elements.value = model.elements
    routes.value = model.routes
    runtime.value = rt
  } catch (e) {
    error.value = (e as Error).message
    console.error('[anlage] laden fehlgeschlagen', e)
  }
}

// Fuehrt eine CRUD-Aktion aus: raeumt den Fehlerzustand auf, laedt bei Erfolg
// den Zustand neu und legt bei LayoutApiError die Fehlerinfo strukturiert ab.
// Der Fehler wird WEITERGEWORFEN, damit die aufrufende Komponente ihn am
// Formular (inkl. 409-blocked_by) anzeigen kann.
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

export function useAnlageStore() {
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

  function setUnit(u: LengthUnit): void {
    unit.value = u
  }

  function clearError(): void {
    error.value = null
    lastError.value = null
  }

  // --- Block-Aktionen (Schreibantwort = Wrapper mit warnings) ---
  async function createBlock(body: BlockWrite): Promise<Block> {
    const resp = await runAction(() => api.createBlock(body))
    warnings.value = resp.warnings
    return resp.entity
  }

  async function updateBlock(id: string, body: BlockWrite): Promise<Block> {
    const resp = await runAction(() => api.updateBlock(id, body))
    warnings.value = resp.warnings
    return resp.entity
  }

  async function deleteBlock(id: string): Promise<void> {
    await runAction(() => api.deleteBlock(id))
  }

  async function setBlockDetectors(id: string, body: DetectorAssignmentsBody): Promise<Block> {
    const resp = await runAction(() => api.setBlockDetectors(id, body))
    warnings.value = resp.warnings
    return resp.entity
  }

  // --- Element-Aktionen (nackte Entitaet) ---
  async function createElement(body: ElementWrite): Promise<TopologyElement> {
    return runAction(() => api.createElement(body))
  }

  async function updateElement(id: string, body: ElementWrite): Promise<TopologyElement> {
    return runAction(() => api.updateElement(id, body))
  }

  async function deleteElement(id: string): Promise<void> {
    await runAction(() => api.deleteElement(id))
  }

  // --- Fahrstrassen-Aktionen (nackte Entitaet) ---
  async function createRoute(body: RouteWrite): Promise<Route> {
    return runAction(() => api.createRoute(body))
  }

  async function updateRoute(id: string, body: RouteWrite): Promise<Route> {
    return runAction(() => api.updateRoute(id, body))
  }

  async function deleteRoute(id: string): Promise<void> {
    await runAction(() => api.deleteRoute(id))
  }

  return {
    // Zustand (nach aussen readonly)
    blocks: readonly(blocks),
    elements: readonly(elements),
    routes: readonly(routes),
    runtime: readonly(runtime),
    warnings: readonly(warnings),
    error: readonly(error),
    lastError: readonly(lastError),
    unit: readonly(unit),
    // Lebenszyklus
    start,
    stop,
    // Einheiten
    setUnit,
    fromMm: (valueMm: number) => fromMm(valueMm, unit.value),
    toMm: (input: number) => toMm(input, unit.value),
    // Fehler
    clearError,
    // CRUD
    createBlock,
    updateBlock,
    deleteBlock,
    setBlockDetectors,
    createElement,
    updateElement,
    deleteElement,
    createRoute,
    updateRoute,
    deleteRoute,
  }
}
