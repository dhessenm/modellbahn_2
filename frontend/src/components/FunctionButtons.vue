<script setup lang="ts">
const props = defineProps<{
  functions: Record<number, boolean>
  disabled: boolean
  count?: number
}>()

const emit = defineEmits<{
  (e: 'toggle', payload: { func: number; on: boolean }): void
}>()

const total = props.count ?? 29 // F0..F28

function isOn(func: number): boolean {
  return props.functions[func] === true
}

function toggle(func: number): void {
  emit('toggle', { func, on: !isOn(func) })
}
</script>

<template>
  <div class="functions">
    <button
      v-for="func in total"
      :key="func - 1"
      type="button"
      class="fn"
      :class="{ on: isOn(func - 1) }"
      :disabled="disabled"
      @click="toggle(func - 1)"
    >
      F{{ func - 1 }}
    </button>
  </div>
</template>

<style scoped>
.functions {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(52px, 1fr));
  gap: 0.4rem;
}
.fn {
  padding: 0.4rem 0;
  border-radius: 6px;
  border: 1px solid var(--color-border, #444);
  cursor: pointer;
  font-variant-numeric: tabular-nums;
}
.fn.on {
  background: #1f5a2e;
  color: #eafff0;
  border-color: #2e8a46;
}
button:disabled {
  opacity: 0.4;
  cursor: default;
}
</style>
