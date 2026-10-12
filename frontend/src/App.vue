<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { RouterLink, RouterView } from 'vue-router'
import ConnectionStatus from '@/components/ConnectionStatus.vue'
import TrackPower from '@/components/TrackPower.vue'
import { useLayoutStore } from '@/stores/layout'

// Der Store wird EINMAL auf App-Ebene gestartet und von allen Seiten geteilt.
const store = useLayoutStore()

onMounted(() => {
  void store.start()
})
onUnmounted(() => {
  store.stop()
})
</script>

<template>
  <div class="app-shell">
    <header class="app-header">
      <ConnectionStatus
        :connected="store.status.value?.connected ?? false"
        :host="store.status.value?.z21_host ?? '—'"
        :port="store.status.value?.z21_port ?? 0"
      />
      <nav class="nav">
        <RouterLink to="/">Dashboard</RouterLink>
        <RouterLink to="/throttle">Lokführerstand</RouterLink>
        <RouterLink to="/turnouts">Weichen</RouterLink>
        <RouterLink to="/detectors">Belegtmelder</RouterLink>
        <RouterLink to="/layout">Anlage</RouterLink>
        <RouterLink to="/roster">Lokomotiven</RouterLink>
        <RouterLink to="/track-plan">Gleisplan</RouterLink>
        <RouterLink to="/track-edit">Gleisplan bearbeiten</RouterLink>
      </nav>
      <TrackPower
        :on="store.status.value?.track_power_on ?? false"
        @toggle="(on: boolean) => store.setTrackPower(on)"
      />
    </header>

    <RouterView />

    <p v-if="store.error.value" class="app-error">{{ store.error.value }}</p>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
}
.app-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
  padding: 0.5rem 1rem;
  border-bottom: 1px solid var(--color-border, #444);
  max-height: 48px;
  box-sizing: border-box;
}
.nav {
  display: flex;
  gap: 0.25rem;
  flex-wrap: wrap;
  flex: 1;
  justify-content: center;
}
.nav a {
  padding: 0.35rem 0.7rem;
  border-radius: 6px;
  text-decoration: none;
}
.nav a.router-link-exact-active {
  background: #2a4d6e;
  color: #fff;
}
.app-error {
  max-width: 640px;
  margin: 1rem auto;
  color: #ffb4b4;
}
</style>
