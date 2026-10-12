<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import LocoThrottle from '@/components/LocoThrottle.vue'
import FunctionButtons from '@/components/FunctionButtons.vue'
import LocoInfoFrame from '@/components/LocoInfoFrame.vue'
import { useLayoutStore } from '@/stores/layout'
import { useRosterStore } from '@/stores/roster'

const store = useLayoutStore()
const rosterStore = useRosterStore()

// Ausgewaehlte Lok (per interner ID).
const selectedLocoId = ref<string | null>(null)

// Lok-Stammdaten aus der Lokverwaltung (oder null, falls nichts gewaehlt).
const selectedLoco = computed(() => {
  if (selectedLocoId.value === null) return null
  return rosterStore.locomotives.value.find((l) => l.id === selectedLocoId.value) ?? null
})

// Hoechste fahrbare Stufe je nach Fahrstufenmodus der Lok.
const maxSpeed = computed(() => {
  const steps = selectedLoco.value?.speed_steps ?? 128
  if (steps === 128) return 126
  if (steps === 28) return 28
  if (steps === 14) return 14
  return 126
})

// Bei Lokwechsel die Adresse an den Layout-Store melden.
watch(selectedLocoId, () => {
  if (selectedLoco.value) {
    void store.selectLoco(selectedLoco.value.address)
  }
})

onMounted(() => {
  void rosterStore.start()
})
onUnmounted(() => {
  rosterStore.stop()
})
</script>

<template>
  <main class="cab">
    <h1>Lokführerstand</h1>

    <section class="panel address">
      <template v-if="rosterStore.locomotives.value.length === 0">
        <p class="empty-hint">
          Bitte zuerst eine Lok in der <RouterLink to="/roster">Lokverwaltung</RouterLink> anlegen.
        </p>
      </template>
      <template v-else>
        <label for="loco-select">Lok wählen</label>
        <select id="loco-select" v-model="selectedLocoId">
          <option :value="null" disabled>Lok wählen…</option>
          <option
            v-for="loco in rosterStore.locomotives.value"
            :key="loco.id"
            :value="loco.id"
          >
            {{ loco.name }} (Adr.&nbsp;{{ loco.address }})
          </option>
        </select>
      </template>
    </section>

    <template v-if="store.activeAddress.value !== null && selectedLoco">
      <section class="panel">
        <LocoThrottle
          :speed="store.loco.value?.speed ?? 0"
          :forward="store.loco.value?.forward ?? true"
          :disabled="!(store.status.value?.track_power_on ?? false)"
          :max-speed="maxSpeed"
          @drive="({ speed, forward }) => store.drive(speed, forward, selectedLoco?.speed_steps ?? 128)"
          @stop="() => store.drive(0, store.loco.value?.forward ?? true, selectedLoco?.speed_steps ?? 128)"
        />
      </section>

      <section class="panel">
        <FunctionButtons
          :functions="store.loco.value?.functions ?? {}"
          :disabled="!(store.status.value?.track_power_on ?? false)"
          :count="(selectedLoco?.function_count ?? 28) + 1"
          @toggle="({ func, on }) => store.setFunction(func, on)"
        />
      </section>

      <details class="loco-details">
        <summary>Lok-Details</summary>
        <LocoInfoFrame :loco="store.loco.value" />
      </details>
    </template>
  </main>
</template>

<style scoped>
.cab {
  max-width: 640px;
  margin: 0 auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
h1 {
  margin: 0;
  font-size: 1.4rem;
}
.panel {
  border: 1px solid var(--color-border, #444);
  border-radius: 8px;
  padding: 1rem;
}
.address {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.address select {
  padding: 0.35rem 0.5rem;
  min-width: 14rem;
}
.empty-hint {
  margin: 0;
  opacity: 0.7;
}
.loco-details {
  border: 1px solid var(--color-border, #444);
  border-radius: 8px;
  padding: 0.5rem 1rem;
}
.loco-details summary {
  cursor: pointer;
  font-weight: 600;
  padding: 0.5rem 0;
}
</style>
