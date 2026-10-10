<script setup lang="ts">
import { computed } from 'vue'
import type { LocoState } from '@/api/types'

const props = defineProps<{
  loco: LocoState | null
}>()

// Alle Lokinformationen als Key-Value-Paare (Text), gemaess MVP-Anforderung.
const entries = computed<[string, string][]>(() => {
  if (!props.loco) return []
  const rows: [string, string][] = [
    ['Adresse', String(props.loco.address)],
    ['Geschwindigkeit', String(props.loco.speed)],
    ['Richtung', props.loco.forward ? 'vorwärts' : 'rückwärts'],
  ]
  const funcs = props.loco.functions
  Object.keys(funcs)
    .map(Number)
    .sort((a, b) => a - b)
    .forEach((f) => rows.push([`F${f}`, funcs[f] ? 'ein' : 'aus']))
  return rows
})
</script>

<template>
  <div class="info-frame">
    <h3>Lok-Information</h3>
    <p v-if="!loco" class="empty">Keine Lok ausgewählt.</p>
    <dl v-else>
      <template v-for="[key, value] in entries" :key="key">
        <dt>{{ key }}</dt>
        <dd>{{ value }}</dd>
      </template>
    </dl>
  </div>
</template>

<style scoped>
.info-frame {
  border: 1px solid var(--color-border, #444);
  border-radius: 8px;
  padding: 1rem;
}
h3 {
  margin: 0 0 0.75rem;
}
.empty {
  opacity: 0.6;
}
dl {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 0.25rem 1rem;
  margin: 0;
  font-variant-numeric: tabular-nums;
}
dt {
  opacity: 0.7;
}
dd {
  margin: 0;
  font-weight: 600;
}
</style>
