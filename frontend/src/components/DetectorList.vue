<script setup lang="ts">
import { computed, type DeepReadonly } from 'vue'
import type { DetectorInput, DetectorLoco } from '@/api/types'

// Elementtyp der (ggf. deep-readonly) Belegtmelder-Liste aus dem Store.
type ReadonlyDetector = DeepReadonly<DetectorInput>
type ReadonlyLoco = DeepReadonly<DetectorLoco>

// Reine Darstellungskomponente: bekommt die Belegtmelder-Eingaenge als Prop
// (aus dem zentralen Store) und rendert sie gruppiert nach Melder. So laesst
// sich die Anzeige isoliert testen, ohne Store/API zu mocken.
// deep-readonly, weil der zentrale Store die Liste als readonly-Ref bereitstellt.
const props = defineProps<{
  detectors: readonly ReadonlyDetector[]
}>()

// Gruppierung nach Melder-Identitaet: Schluessel ist die unveraenderbare
// CAN-NetworkID (nid). Die konfigurierbare Moduladresse (addr) ist nur
// Anzeigeinfo und kann 0 sein (Live-Test bestaetigt: addr kam als 0, obwohl
// am Geraet 1 eingestellt) -- daher NICHT zum Gruppieren verwenden.
interface Group {
  nid: number
  addr: number
  inputs: ReadonlyDetector[]
}

const groups = computed<Group[]>(() => {
  const byNid = new Map<number, Group>()
  for (const input of props.detectors) {
    let group = byNid.get(input.nid)
    if (!group) {
      group = { nid: input.nid, addr: input.addr, inputs: [] }
      byNid.set(input.nid, group)
    }
    group.inputs.push(input)
  }
  return [...byNid.values()]
})

// Fortlaufende, globale Nummer je Eingang (ueber alle Melder hinweg), passend
// zur Reihenfolge in `detectors`.
function globalIndex(nid: number, port: number): number {
  return props.detectors.findIndex((d) => d.nid === nid && d.port === port) + 1
}

// Melder-Netzwerk-ID als Hex (stabile Identitaet), z. B. 0xD764.
function nidLabel(nid: number): string {
  return `0x${nid.toString(16).toUpperCase().padStart(4, '0')}`
}

// Eingang 1-basiert anzeigen: der physische "Eingang 1" am Geraet ist im
// Protokoll Port=0 (Live-Test bestaetigt). Intern bleibt der Port 0-basiert.
function portLabel(port: number): string {
  return `Eingang ${port + 1}`
}

const directionSymbol: Record<DetectorLoco['direction'], string> = {
  forward: '▶',
  backward: '◀',
  unknown: '',
}

function locoText(loco: ReadonlyLoco): string {
  const symbol = directionSymbol[loco.direction]
  return symbol ? `${symbol} ${loco.address}` : `${loco.address}`
}

function locosText(locos: readonly ReadonlyLoco[]): string {
  return locos.map(locoText).join(', ')
}
</script>

<template>
  <div class="detector-list">
    <p v-if="detectors.length === 0" class="empty">Noch keine Belegtmelder-Daten.</p>

    <section v-for="group in groups" :key="group.nid" class="panel group">
      <h3>Melder {{ nidLabel(group.nid) }}<span class="addr"> · Adresse {{ group.addr }}</span></h3>
      <div class="rows">
        <div
          v-for="input in group.inputs"
          :key="input.port"
          class="row"
          data-testid="detector-row"
        >
          <span class="num">{{ globalIndex(input.nid, input.port) }}</span>
          <span class="port">{{ portLabel(input.port) }}</span>
          <span
            class="led"
            :class="input.occupied ? 'on' : 'off'"
            data-testid="detector-led"
            aria-hidden="true"
          />
          <span
            class="status"
            :class="{ overload: input.overload }"
            data-testid="detector-status"
          >
            {{ input.status_text }}
          </span>
          <span class="locos" data-testid="detector-locos">{{ locosText(input.locos) }}</span>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.detector-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.empty {
  opacity: 0.6;
}
.panel {
  border: 1px solid var(--color-border, #444);
  border-radius: 8px;
  padding: 1rem;
}
h3 {
  margin: 0 0 0.75rem;
}
.addr {
  opacity: 0.6;
  font-weight: 400;
}
.rows {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
.row {
  display: grid;
  grid-template-columns: 2rem 6rem 1.2rem 1fr 1fr;
  align-items: center;
  gap: 0.75rem;
  font-variant-numeric: tabular-nums;
}
.num {
  opacity: 0.6;
  text-align: right;
}
.led {
  width: 0.9rem;
  height: 0.9rem;
  border-radius: 50%;
  border: 1px solid #7a1f1f;
  justify-self: center;
}
/* Frei: LED aus (dunkel). Belegt: LED an (rot leuchtend). */
.led.off {
  background: #3a1414;
}
.led.on {
  background: #ff3b30;
  box-shadow: 0 0 6px #ff3b30;
}
.status {
  font-weight: 600;
}
/* Ueberlast deutlich hervorheben (gelb/orange) -- Warnzustand. */
.status.overload {
  color: #ffb020;
}
.locos {
  opacity: 0.85;
}
</style>
