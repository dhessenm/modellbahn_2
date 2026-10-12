<script setup lang="ts">
const props = defineProps<{
  on: boolean
}>()
const emit = defineEmits<{
  (e: 'toggle', on: boolean): void
}>()
</script>

<template>
  <div class="track-power-compact" data-testid="track-power">
    <span class="tp-led" :class="{ on: props.on }"></span>
    <button type="button" class="tp-toggle" @click="emit('toggle', !props.on)">
      Gleis {{ props.on ? 'Aus' : 'Ein' }}
    </button>
  </div>
</template>

<style scoped>
.track-power-compact {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-shrink: 0;
}
.tp-led {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #555;
}
.tp-led.on {
  background: #2ecc71;
  box-shadow: 0 0 6px #2ecc71;
}
.tp-toggle {
  padding: 0.2rem 0.6rem;
  border-radius: 6px;
  border: 1px solid var(--color-border, #444);
  cursor: pointer;
  font-size: 0.8rem;
  white-space: nowrap;
  min-height: 32px;
}
</style>
