<script setup lang="ts">
import { ref } from 'vue'
import { api } from '@/api/client'
import { useLayoutStore } from '@/stores/layout'

const store = useLayoutStore()

const addressInput = ref<number>(0)
const activeAddress = ref<number | null>(null)
const position = ref<number | null>(null)
const error = ref<string | null>(null)

const trackPowerOn = () => store.status.value?.track_power_on ?? false

async function selectTurnout(): Promise<void> {
  activeAddress.value = addressInput.value
  position.value = null
  error.value = null
  try {
    await api.subscribeTurnout(addressInput.value)
    const state = await api.getTurnout(addressInput.value)
    position.value = state.position
  } catch (e) {
    error.value = (e as Error).message
  }
}

async function setPosition(pos: number): Promise<void> {
  if (activeAddress.value === null) return
  error.value = null
  try {
    await api.setTurnout(activeAddress.value, pos)
    position.value = pos
  } catch (e) {
    error.value = (e as Error).message
  }
}
</script>

<template>
  <main class="turnouts">
    <h1>Weichen</h1>

    <section class="panel address">
      <label for="t-address">Weichen-Adresse (DCC, ab 0)</label>
      <input id="t-address" v-model.number="addressInput" type="number" min="0" max="2047" />
      <button type="button" @click="selectTurnout">Übernehmen</button>
    </section>

    <template v-if="activeAddress !== null">
      <section class="panel">
        <div class="row">
          <span class="label">Weiche {{ activeAddress }}</span>
          <span class="pos">
            Position:
            <strong>{{ position === null ? 'unbekannt' : position }}</strong>
          </span>
        </div>
        <div class="buttons">
          <button
            type="button"
            :class="{ active: position === 0 }"
            :disabled="!trackPowerOn()"
            @click="setPosition(0)"
          >
            Position 0
          </button>
          <button
            type="button"
            :class="{ active: position === 1 }"
            :disabled="!trackPowerOn()"
            @click="setPosition(1)"
          >
            Position 1
          </button>
        </div>
        <p v-if="!trackPowerOn()" class="hint">Gleisspannung ist aus — Schalten nicht möglich.</p>
      </section>
    </template>

    <p v-if="error" class="error">{{ error }}</p>
  </main>
</template>

<style scoped>
.turnouts {
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
.address input {
  width: 7rem;
  padding: 0.35rem 0.5rem;
}
.address button {
  padding: 0.35rem 0.9rem;
  cursor: pointer;
}
.row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}
.buttons {
  display: flex;
  gap: 0.5rem;
}
.buttons button {
  flex: 1;
  padding: 0.5rem;
  border-radius: 6px;
  border: 1px solid var(--color-border, #444);
  cursor: pointer;
}
.buttons button.active {
  outline: 2px solid #6aa9ff;
}
.buttons button:disabled {
  opacity: 0.4;
  cursor: default;
}
.hint {
  margin: 0.75rem 0 0;
  opacity: 0.7;
}
.error {
  color: #ffb4b4;
}
</style>
