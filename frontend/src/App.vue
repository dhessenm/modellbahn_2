<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { RouterLink, RouterView } from 'vue-router'
import ConnectionStatus from '@/components/ConnectionStatus.vue'
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
      <div class="brand">Modellbahn</div>
      <nav class="nav">
        <RouterLink to="/">Dashboard</RouterLink>
        <RouterLink to="/throttle">Lokführerstand</RouterLink>
        <RouterLink to="/turnouts">Weichen</RouterLink>
        <RouterLink to="/track-plan">Gleisplan</RouterLink>
        <RouterLink to="/track-edit">Gleisplan bearbeiten</RouterLink>
      </nav>
      <ConnectionStatus
        :connected="store.status.value?.connected ?? false"
        :host="store.status.value?.z21_host ?? '—'"
        :port="store.status.value?.z21_port ?? 0"
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
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--color-border, #444);
}
.brand {
  font-weight: 700;
  font-size: 1.15rem;
}
.nav {
  display: flex;
  gap: 0.25rem;
  flex-wrap: wrap;
  flex: 1;
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
