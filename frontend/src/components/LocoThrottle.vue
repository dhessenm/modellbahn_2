<script setup lang="ts">
import { computed, ref, watch } from 'vue'

const props = defineProps<{
  speed: number
  forward: boolean
  disabled: boolean
  maxSpeed?: number
}>()

const emit = defineEmits<{
  (e: 'drive', payload: { speed: number; forward: boolean }): void
  (e: 'stop'): void
}>()

// Hoechste erlaubte Fahrstufe (abhaengig vom Fahrstufenmodus der Lok).
// Ohne Angabe gilt der DCC-128-Standard (126 fahrbare Stufen).
const effectiveMax = computed(() => props.maxSpeed ?? 126)

// Lokaler Reglerwert, der dem Backend-Zustand folgt, solange nicht gezogen wird.
const localSpeed = ref(props.speed)
watch(
  () => props.speed,
  (s) => {
    localSpeed.value = s
  },
)

function onSpeedInput(event: Event): void {
  const value = Math.min(Number((event.target as HTMLInputElement).value), effectiveMax.value)
  localSpeed.value = value
  emit('drive', { speed: value, forward: props.forward })
}

function setDirection(forward: boolean): void {
  emit('drive', { speed: localSpeed.value, forward })
}
</script>

<template>
  <div class="throttle">
    <div class="speed-row">
      <label for="speed">Fahrstufe</label>
    </div>
    <div class="slider-vertical">
      <input
        id="speed"
        type="range"
        min="0"
        :max="effectiveMax"
        :value="localSpeed"
        :disabled="disabled"
        @input="onSpeedInput"
      />
      <output class="speed-value">{{ localSpeed }}</output>
    </div>

    <div class="controls">
      <button type="button" :disabled="disabled" :class="{ active: forward }" @click="setDirection(true)">
        &#9650; Vorwärts
      </button>
      <button type="button" class="stop" :disabled="disabled" @click="emit('stop')">STOP</button>
      <button type="button" :disabled="disabled" :class="{ active: !forward }" @click="setDirection(false)">
        &#9660; Rückwärts
      </button>
    </div>
  </div>
</template>

<style scoped>
.throttle {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.speed-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}
.speed-value {
  font-size: 1.6rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
/* Vertikaler Fahrstufenregler: kleinste Stufe unten, hoechste oben.
   writing-mode:vertical-lr + direction:rtl kehrt die Achse so um, dass der
   Regler cross-browser von unten nach oben laeuft -- ergonomisch am Handy. */
.slider-vertical {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.slider-vertical input[type='range'] {
  writing-mode: vertical-lr;
  direction: rtl;
  height: 200px;
  width: auto;
}
.controls {
  display: flex;
  gap: 0.5rem;
}
.controls button {
  flex: 1;
  min-height: 44px;
  padding: 0.5rem;
  border-radius: 6px;
  border: 1px solid var(--color-border, #444);
  cursor: pointer;
}
.controls button.active {
  outline: 2px solid #6aa9ff;
}
.controls .stop {
  background: #7a1f1f;
  color: #fff;
  font-weight: 700;
}
button:disabled {
  opacity: 0.4;
  cursor: default;
}
</style>
