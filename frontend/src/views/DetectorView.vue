<script setup lang="ts">
import { ref } from 'vue'
import DetectorList from '@/components/DetectorList.vue'
import { useLayoutStore } from '@/stores/layout'

// Die View liest den zentralen Store (Single Source of Truth, der bei jedem
// SSE-'changed'-Signal frisch nachlaedt) und laedt NICHT selbst nach -- so
// bleibt die Anzeige konsistent mit dem uebrigen UI. Der Aktualisieren-Button
// stoesst zusaetzlich eine einmalige Z21-Abfrage an.
const store = useLayoutStore()

const busy = ref(false)

async function refresh(): Promise<void> {
  busy.value = true
  try {
    await store.requestDetectors()
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <main class="detectors">
    <header class="head">
      <h1>Belegtmelder</h1>
      <button type="button" :disabled="busy" @click="refresh">Aktualisieren</button>
    </header>

    <p class="hint">
      Eingänge sind 1-basiert angezeigt (Gerät „Eingang 1" = Protokoll-Port 0). Lokadressen
      erscheinen nur mit RailCom; „besetzt" ohne Lokadresse ist normal.
    </p>

    <DetectorList :detectors="store.detectors.value" />
  </main>
</template>

<style scoped>
.detectors {
  max-width: 720px;
  margin: 0 auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}
h1 {
  margin: 0;
  font-size: 1.4rem;
}
.head button {
  padding: 0.35rem 0.9rem;
  cursor: pointer;
}
.head button:disabled {
  opacity: 0.5;
  cursor: default;
}
.hint {
  margin: 0;
  opacity: 0.7;
  font-size: 0.9rem;
}
</style>
