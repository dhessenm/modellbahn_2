<script setup lang="ts">
defineProps<{
  on: boolean
}>()
const emit = defineEmits<{
  (e: 'toggle', on: boolean): void
}>()
</script>

<template>
  <div class="track-power">
    <span class="label">Gleisspannung</span>
    <span class="state" :class="{ on }">{{ on ? 'EIN' : 'AUS' }}</span>
    <div class="buttons">
      <button type="button" :disabled="on" @click="emit('toggle', true)">Ein</button>
      <button type="button" :disabled="!on" @click="emit('toggle', false)">Aus</button>
    </div>
  </div>
</template>

<style scoped>
.track-power {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.state {
  font-weight: 700;
  color: #ffb4b4;
}
.state.on {
  color: #9be7a9;
}
.buttons {
  display: flex;
  gap: 0.5rem;
}
button {
  padding: 0.35rem 0.9rem;
  border-radius: 6px;
  border: 1px solid var(--color-border, #444);
  cursor: pointer;
}
button:disabled {
  opacity: 0.4;
  cursor: default;
}
</style>
