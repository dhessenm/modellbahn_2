<script setup lang="ts">
import { RouterLink } from 'vue-router'
import SystemStatePanel from '@/components/SystemStatePanel.vue'
import TrackPower from '@/components/TrackPower.vue'
import { useLayoutStore } from '@/stores/layout'

const store = useLayoutStore()
</script>

<template>
  <main class="dashboard">
    <h1>Dashboard</h1>

    <SystemStatePanel :status="store.status.value" />

    <section class="panel">
      <TrackPower
        :on="store.status.value?.track_power_on ?? false"
        @toggle="(on) => store.setTrackPower(on)"
      />
    </section>

    <section class="panel quick">
      <RouterLink to="/throttle" class="quick-link">Zum Lokführerstand →</RouterLink>
    </section>
  </main>
</template>

<style scoped>
.dashboard {
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
.quick-link {
  font-weight: 600;
  text-decoration: none;
}
</style>
