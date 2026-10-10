<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import ConnectionStatus from '@/components/ConnectionStatus.vue'
import TrackPower from '@/components/TrackPower.vue'
import LocoThrottle from '@/components/LocoThrottle.vue'
import FunctionButtons from '@/components/FunctionButtons.vue'
import LocoInfoFrame from '@/components/LocoInfoFrame.vue'
import { useLayoutStore } from '@/stores/layout'

const store = useLayoutStore()

const addressInput = ref<number>(3)

onMounted(() => {
  void store.start()
})
onUnmounted(() => {
  store.stop()
})

function selectLoco(): void {
  void store.selectLoco(addressInput.value)
}
</script>

<template>
  <main class="cab">
    <header class="topbar">
      <h1>Lokführerstand</h1>
      <ConnectionStatus
        :connected="store.status.value?.connected ?? false"
        :host="store.status.value?.z21_host ?? '—'"
        :port="store.status.value?.z21_port ?? 0"
      />
    </header>

    <section class="panel">
      <TrackPower
        :on="store.status.value?.track_power_on ?? false"
        @toggle="(on) => store.setTrackPower(on)"
      />
    </section>

    <section class="panel address">
      <label for="address">Lok-Adresse (DCC)</label>
      <input id="address" v-model.number="addressInput" type="number" min="1" max="9999" />
      <button type="button" @click="selectLoco">Übernehmen</button>
    </section>

    <template v-if="store.activeAddress.value !== null">
      <section class="panel">
        <LocoThrottle
          :speed="store.loco.value?.speed ?? 0"
          :forward="store.loco.value?.forward ?? true"
          :disabled="!(store.status.value?.track_power_on ?? false)"
          @drive="({ speed, forward }) => store.drive(speed, forward)"
          @stop="() => store.drive(0, store.loco.value?.forward ?? true)"
        />
      </section>

      <section class="panel">
        <FunctionButtons
          :functions="store.loco.value?.functions ?? {}"
          :disabled="!(store.status.value?.track_power_on ?? false)"
          @toggle="({ func, on }) => store.setFunction(func, on)"
        />
      </section>

      <section class="panel">
        <LocoInfoFrame :loco="store.loco.value" />
      </section>
    </template>

    <p v-if="store.error.value" class="error">{{ store.error.value }}</p>
  </main>
</template>

<style scoped>
.cab {
  max-width: 640px;
  margin: 0 auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.75rem;
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
.address {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.address input {
  width: 7rem;
  padding: 0.35rem 0.5rem;
}
.address button {
  padding: 0.35rem 0.9rem;
  cursor: pointer;
}
.error {
  color: #ffb4b4;
}
</style>
