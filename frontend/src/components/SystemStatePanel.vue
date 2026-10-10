<script setup lang="ts">
import { computed } from 'vue'
import type { SystemStatus } from '@/api/types'

const props = defineProps<{
  status: SystemStatus | null
}>()

// Zentralen-Infos als Key-Value-Paare (Text), analog zum Lok-Infoframe.
const rows = computed<{ key: string; value: string; warn?: boolean }[]>(() => {
  const s = props.status
  if (!s) return []
  return [
    { key: 'Verbindung', value: s.connected ? 'verbunden' : 'getrennt', warn: !s.connected },
    { key: 'Gleisspannung', value: s.track_power_on ? 'ein' : 'aus', warn: !s.track_power_on },
    { key: 'Kurzschluss', value: s.short_circuit ? 'JA' : 'nein', warn: s.short_circuit },
    { key: 'Nothalt', value: s.emergency_stop ? 'aktiv' : 'nein', warn: s.emergency_stop },
    { key: 'Temperatur', value: `${s.temperature_c} °C` },
    { key: 'Versorgungsspannung', value: `${(s.supply_voltage_mv / 1000).toFixed(2)} V` },
    { key: 'Gleisspannung (U)', value: `${(s.track_voltage_mv / 1000).toFixed(2)} V` },
    { key: 'Zentrale', value: `${s.z21_host}:${s.z21_port}` },
  ]
})
</script>

<template>
  <div class="system-state">
    <h3>Zentralenstatus</h3>
    <p v-if="!status" class="empty">Noch keine Daten.</p>
    <dl v-else>
      <template v-for="row in rows" :key="row.key">
        <dt>{{ row.key }}</dt>
        <dd :class="{ warn: row.warn }">{{ row.value }}</dd>
      </template>
    </dl>
  </div>
</template>

<style scoped>
.system-state {
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
  gap: 0.3rem 1rem;
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
dd.warn {
  color: #ffb4b4;
}
</style>
