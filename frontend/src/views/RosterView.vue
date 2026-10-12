<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import RosterList from '@/components/RosterList.vue'
import { useRosterStore } from '@/stores/roster'
import { LENGTH_UNITS, UNIT_LABEL, type LengthUnit } from '@/stores/length-units'
import type { LocoWrite } from '@/api/roster-types'

// Diese View startet den EIGENEN Roster-Store (separat vom globalen
// useLayoutStore in App.vue), bindet die Listen-Komponente ein und bildet deren
// Events auf die Store-CRUD-Aktionen ab. Der Store laedt bei jedem
// SSE-'changed'-Signal frisch nach (Single Source of Truth = Backend).
const store = useRosterStore()

// Anzeige-Einheit lokal in der View halten (nur Darstellung/Eingabe von Laengen).
const unit = ref<LengthUnit>('cm')

onMounted(() => {
  void store.start()
})
onUnmounted(() => {
  store.stop()
})

function onUnitChange(event: Event): void {
  unit.value = (event.target as HTMLSelectElement).value as LengthUnit
}

// CRUD-Weiterleitung: Fehler fangen wir ab, weil der Store ihn bereits
// strukturiert ablegt (error/lastError); die Komponente liest ihn ueber Props.
async function createLoco(body: LocoWrite): Promise<void> {
  try {
    await store.createLoco(body)
  } catch {
    /* Fehler steht im Store */
  }
}
async function updateLoco(id: string, body: LocoWrite): Promise<void> {
  try {
    await store.updateLoco(id, body)
  } catch {
    /* Fehler steht im Store */
  }
}
async function deleteLoco(id: string): Promise<void> {
  try {
    await store.deleteLoco(id)
  } catch {
    /* Fehler steht im Store */
  }
}
</script>

<template>
  <main class="roster">
    <header class="head">
      <h1>Lokomotiven</h1>
      <label class="unit">
        Einheit
        <select :value="unit" aria-label="Anzeige-Einheit" @change="onUnitChange">
          <option v-for="u in LENGTH_UNITS" :key="u" :value="u">{{ UNIT_LABEL[u] }}</option>
        </select>
      </label>
    </header>

    <p class="hint">
      Doppelte DCC-Adressen sind erlaubt; sie lösen beim Anlegen nur einen Hinweis aus. Die Lok wird
      intern über eine eigene ID geführt, nicht über die Adresse.
    </p>

    <RosterList
      :locomotives="store.locomotives.value"
      :unit="unit"
      :warnings="store.warnings.value"
      :error="store.lastError.value"
      @create="createLoco"
      @update="updateLoco"
      @delete="deleteLoco"
    />
  </main>
</template>

<style scoped>
.roster {
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
