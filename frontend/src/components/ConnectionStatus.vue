<script setup lang="ts">
defineProps<{
  connected: boolean
  host?: string
  port?: number
}>()
</script>

<template>
  <span
    class="connection-led"
    :class="{ on: connected }"
    data-testid="connection-led"
    :title="connected ? `Verbunden Z21 ${host}:${port}` : 'Keine Verbindung'"
    aria-label="Verbindungsstatus"
  ></span>
</template>

<style scoped>
.connection-led {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #555;
  flex-shrink: 0;
}
.connection-led.on {
  background: #2ecc71;
  box-shadow: 0 0 6px #2ecc71;
}
</style>
