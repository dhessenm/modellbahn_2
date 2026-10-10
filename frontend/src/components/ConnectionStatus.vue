<script setup lang="ts">
defineProps<{
  connected: boolean
  host: string
  port: number
}>()
</script>

<template>
  <div class="connection" :class="{ online: connected }">
    <span class="dot" aria-hidden="true"></span>
    <span class="label">
      {{ connected ? 'Verbunden' : 'Keine Verbindung' }}
    </span>
    <span class="target">Z21 {{ host }}:{{ port }}</span>
  </div>
</template>

<style scoped>
.connection {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.75rem;
  border-radius: 999px;
  background: #3a1414;
  color: #ffb4b4;
  font-size: 0.9rem;
}
.connection.online {
  background: #10331a;
  color: #9be7a9;
}
.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: currentColor;
}
.target {
  opacity: 0.7;
  font-variant-numeric: tabular-nums;
}
</style>
