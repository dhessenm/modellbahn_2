<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import BlockList from '@/components/BlockList.vue'
import ElementList from '@/components/ElementList.vue'
import RouteList from '@/components/RouteList.vue'
import { useAnlageStore } from '@/stores/anlage'
import { LENGTH_UNITS, UNIT_LABEL, type LengthUnit } from '@/stores/length-units'
import type { BlockWrite, DetectorAssignment, ElementWrite, RouteWrite } from '@/api/layout-types'

// Diese View startet den EIGENEN Anlagen-Store (separat vom globalen
// useLayoutStore in App.vue), bindet die drei Listen-Komponenten ein und bildet
// deren Events auf die Store-CRUD-Aktionen ab. Der Store laedt bei jedem
// SSE-'changed'-Signal frisch nach (Single Source of Truth = Backend).
const store = useAnlageStore()

onMounted(() => {
  void store.start()
})
onUnmounted(() => {
  store.stop()
})

function onUnitChange(event: Event): void {
  store.setUnit((event.target as HTMLSelectElement).value as LengthUnit)
}

// CRUD-Weiterleitung: Fehler fangen wir ab, weil der Store ihn bereits
// strukturiert ablegt (error/lastError); die Komponenten lesen ihn ueber Props.
async function createBlock(body: BlockWrite): Promise<void> {
  try {
    await store.createBlock(body)
  } catch {
    /* Fehler steht im Store */
  }
}
async function updateBlock(id: string, body: BlockWrite): Promise<void> {
  try {
    await store.updateBlock(id, body)
  } catch {
    /* Fehler steht im Store */
  }
}
async function deleteBlock(id: string): Promise<void> {
  try {
    await store.deleteBlock(id)
  } catch {
    /* Fehler steht im Store */
  }
}
async function setBlockDetectors(id: string, detectors: DetectorAssignment[]): Promise<void> {
  try {
    await store.setBlockDetectors(id, { detectors })
  } catch {
    /* Fehler steht im Store */
  }
}
async function createElement(body: ElementWrite): Promise<void> {
  try {
    await store.createElement(body)
  } catch {
    /* Fehler steht im Store */
  }
}
async function updateElement(id: string, body: ElementWrite): Promise<void> {
  try {
    await store.updateElement(id, body)
  } catch {
    /* Fehler steht im Store */
  }
}
async function deleteElement(id: string): Promise<void> {
  try {
    await store.deleteElement(id)
  } catch {
    /* Fehler steht im Store */
  }
}
async function createRoute(body: RouteWrite): Promise<void> {
  try {
    await store.createRoute(body)
  } catch {
    /* Fehler steht im Store */
  }
}
async function updateRoute(id: string, body: RouteWrite): Promise<void> {
  try {
    await store.updateRoute(id, body)
  } catch {
    /* Fehler steht im Store */
  }
}
async function deleteRoute(id: string): Promise<void> {
  try {
    await store.deleteRoute(id)
  } catch {
    /* Fehler steht im Store */
  }
}
</script>

<template>
  <main class="layout">
    <header class="head">
      <h1>Anlage</h1>
      <label class="unit">
        Einheit
        <select :value="store.unit.value" aria-label="Anzeige-Einheit" @change="onUnitChange">
          <option v-for="u in LENGTH_UNITS" :key="u" :value="u">{{ UNIT_LABEL[u] }}</option>
        </select>
      </label>
    </header>

    <p class="hint">
      Längen werden in der gewählten Einheit angezeigt und beim Speichern auf ganze Millimeter
      gerundet (1 Zoll = 25,4 mm). Darstellung ist rein listen-/schemaartig.
    </p>

    <BlockList
      :blocks="store.blocks.value"
      :runtime="store.runtime.value"
      :unit="store.unit.value"
      :warnings="store.warnings.value"
      :error="store.lastError.value"
      @create="createBlock"
      @update="updateBlock"
      @delete="deleteBlock"
      @set-detectors="setBlockDetectors"
    />

    <ElementList
      :elements="store.elements.value"
      :error="store.lastError.value"
      @create="createElement"
      @update="updateElement"
      @delete="deleteElement"
    />

    <RouteList
      :routes="store.routes.value"
      :blocks="store.blocks.value"
      :elements="store.elements.value"
      :error="store.lastError.value"
      @create="createRoute"
      @update="updateRoute"
      @delete="deleteRoute"
    />
  </main>
</template>

<style scoped>
.layout {
  max-width: 960px;
  margin: 0 auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}
h1 {
  margin: 0;
  font-size: 1.4rem;
}
.unit {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}
.hint {
  margin: 0;
  opacity: 0.7;
  font-size: 0.9rem;
}
</style>
