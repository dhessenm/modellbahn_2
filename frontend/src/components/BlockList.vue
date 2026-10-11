<script setup lang="ts">
import { computed, reactive, ref, type DeepReadonly } from 'vue'
import type {
  Block,
  BlockRuntime,
  BlockWrite,
  DetectorAssignment,
  Marker,
  Warning,
} from '@/api/layout-types'
import type { LayoutApiError } from '@/api/layout-error'
import { fromMm, toMm, UNIT_LABEL, type LengthUnit } from '@/stores/length-units'

// Reine Darstellungs-/Editor-Komponente: bekommt den Zustand als Props und
// meldet Aenderungen ueber Events. So laesst sie sich isoliert testen
// (Muster DetectorList.vue). Laengen in Anzeige-Einheit; Payload immer in mm.
// deep-readonly, weil der zentrale Store die Listen als readonly-Refs bereitstellt.
type ReadonlyBlock = DeepReadonly<Block>
const props = defineProps<{
  blocks: readonly ReadonlyBlock[]
  runtime: readonly DeepReadonly<BlockRuntime>[]
  unit: LengthUnit
  warnings?: readonly DeepReadonly<Warning>[]
  error?: DeepReadonly<LayoutApiError> | null
}>()

const emit = defineEmits<{
  create: [body: BlockWrite]
  update: [id: string, body: BlockWrite]
  delete: [id: string]
  'set-detectors': [id: string, detectors: DetectorAssignment[]]
}>()

// Laufzeitzustand je Block (Join ueber block_id).
const runtimeById = computed(() => {
  const map = new Map<string, DeepReadonly<BlockRuntime>>()
  for (const rt of props.runtime) map.set(rt.block_id, rt)
  return map
})

function occupancyOf(id: string): BlockRuntime['occupancy'] {
  return runtimeById.value.get(id)?.occupancy ?? 'unknown'
}

function locoAddressesOf(id: string): number[] {
  return [...(runtimeById.value.get(id)?.loco_addresses ?? [])]
}

const OCCUPANCY_TEXT: Record<BlockRuntime['occupancy'], string> = {
  free: 'frei',
  occupied: 'belegt',
  unknown: 'unbekannt',
}

// Laenge in der aktuellen Anzeige-Einheit (fuer Eingabefelder).
function lenInUnit(valueMm: number | null): number | null {
  return valueMm === null ? null : Number(fromMm(valueMm, props.unit).toFixed(3))
}

// --- Editor-Formular (Neuanlage) ---
const form = reactive<{ name: string; lengthInput: number | null; maxSpeed: number | null }>({
  name: '',
  lengthInput: null,
  maxSpeed: null,
})

// Zuletzt gesendeter mm-Wert, um die Rundung (v. a. bei Zoll) sichtbar zu machen.
const lastSentMm = ref<number | null>(null)

function buildBlockWrite(
  name: string,
  lengthInput: number | null,
  maxSpeed: number | null,
): BlockWrite {
  const lengthMm = lengthInput === null ? null : toMm(lengthInput, props.unit)
  lastSentMm.value = lengthMm
  return { name, length_mm: lengthMm, max_speed_kmh: maxSpeed }
}

function submitCreate(): void {
  if (!form.name.trim()) return
  emit('create', buildBlockWrite(form.name.trim(), form.lengthInput, form.maxSpeed))
  form.name = ''
  form.lengthInput = null
  form.maxSpeed = null
}

// --- Markierungen (Halt/Brems) je Richtung ---
// Pro Marke genau EINE Variante senden: Melder-Bezug (nid,port) ODER Position
// in mm. Die xor-Regel prueft das Backend (400). Die UI haelt beide Felder vor.
interface MarkerDraft {
  nid: number | null
  port: number | null
  positionInput: number | null
}
interface MarkersDraft {
  stop: MarkerDraft
  brake: MarkerDraft
}
interface DirDraft {
  forward: MarkersDraft
  backward: MarkersDraft
}

function emptyMarkerDraft(): MarkerDraft {
  return { nid: null, port: null, positionInput: null }
}

function markerDraftFrom(marker: DeepReadonly<Marker> | null): MarkerDraft {
  if (!marker) return emptyMarkerDraft()
  return {
    nid: marker.detector_ref ? marker.detector_ref[0] : null,
    port: marker.detector_ref ? marker.detector_ref[1] : null,
    positionInput: marker.position_mm === null ? null : lenInUnit(marker.position_mm),
  }
}

function dirDraftFrom(block: ReadonlyBlock): DirDraft {
  return {
    forward: {
      stop: markerDraftFrom(block.markers_forward.stop),
      brake: markerDraftFrom(block.markers_forward.brake),
    },
    backward: {
      stop: markerDraftFrom(block.markers_backward.stop),
      brake: markerDraftFrom(block.markers_backward.brake),
    },
  }
}

// Baut aus einem Marker-Entwurf das API-Marker-Objekt oder null (leer).
function markerFrom(d: MarkerDraft): Marker | null {
  if (d.nid !== null && d.port !== null) {
    return { detector_ref: [d.nid, d.port], position_mm: null }
  }
  if (d.positionInput !== null) {
    return { detector_ref: null, position_mm: toMm(d.positionInput, props.unit) }
  }
  return null
}

// --- Inline-Editor je Block ---
interface BlockEdit {
  name: string
  lengthInput: number | null
  maxSpeed: number | null
  markers: DirDraft
}
const editing = reactive<Record<string, BlockEdit>>({})

function beginEdit(block: ReadonlyBlock): void {
  editing[block.id] = {
    name: block.name,
    lengthInput: lenInUnit(block.length_mm),
    maxSpeed: block.max_speed_kmh,
    markers: dirDraftFrom(block),
  }
}

function cancelEdit(id: string): void {
  delete editing[id]
}

function submitEdit(id: string): void {
  const e = editing[id]
  if (!e || !e.name.trim()) return
  const body = buildBlockWrite(e.name.trim(), e.lengthInput, e.maxSpeed)
  body.markers_forward = {
    stop: markerFrom(e.markers.forward.stop),
    brake: markerFrom(e.markers.forward.brake),
  }
  body.markers_backward = {
    stop: markerFrom(e.markers.backward.stop),
    brake: markerFrom(e.markers.backward.brake),
  }
  emit('update', id, body)
  delete editing[id]
}

// --- Melder-Zuordnung (einfacher Editor: nid/port/order/Teillaenge) ---
interface DetectorDraft {
  nid: number | null
  port: number | null
  order: number
  lengthInput: number | null
}
const detectorDraft = reactive<Record<string, DetectorDraft>>({})

function draftFor(id: string): DetectorDraft {
  if (!detectorDraft[id]) {
    detectorDraft[id] = { nid: null, port: null, order: 0, lengthInput: null }
  }
  return detectorDraft[id]!
}

function addDetector(block: ReadonlyBlock): void {
  const d = draftFor(block.id)
  if (d.nid === null || d.port === null) return
  const next: DetectorAssignment[] = [
    ...block.detectors.map((a) => ({ ...a })),
    {
      detector_nid: d.nid,
      detector_port: d.port,
      order: d.order,
      length_mm: d.lengthInput === null ? null : toMm(d.lengthInput, props.unit),
    },
  ]
  emit('set-detectors', block.id, next)
  detectorDraft[block.id] = { nid: null, port: null, order: 0, lengthInput: null }
}

function removeDetector(block: ReadonlyBlock, index: number): void {
  const next = block.detectors.filter((_, i) => i !== index).map((a) => ({ ...a }))
  emit('set-detectors', block.id, next)
}

// Fehler nur anzeigen, wenn er ein Block betrifft (per Konvention: blocked_by
// bezieht sich hier auf den geloeschten Block). Zur Einfachheit zeigen wir den
// strukturieren Fehler oben in der Komponente.
const blockedBy = computed(() => props.error?.blockedBy ?? [])
</script>

<template>
  <section class="block-list" data-testid="block-list">
    <h2>Blöcke</h2>

    <p v-if="warnings && warnings.length" class="warnings">
      <span v-for="w in warnings" :key="w.code" class="warning" data-testid="block-warning">{{
        w.message
      }}</span>
    </p>

    <p v-if="error && error.status !== 409" class="error" data-testid="block-error">
      {{ error.detail }}
    </p>
    <div v-if="blockedBy.length" class="error" data-testid="block-blocked-by">
      <p>{{ error?.detail }}</p>
      <ul>
        <li v-for="b in blockedBy" :key="b.type + b.id">{{ b.type }}: {{ b.name }}</li>
      </ul>
    </div>

    <p v-if="blocks.length === 0" class="empty">Noch keine Blöcke angelegt.</p>

    <div class="rows">
      <div v-for="block in blocks" :key="block.id" class="row" data-testid="block-row">
        <template v-if="!editing[block.id]">
          <span
            class="led"
            :class="{
              on: occupancyOf(block.id) === 'occupied',
              off: occupancyOf(block.id) === 'free',
              unknown: occupancyOf(block.id) === 'unknown',
            }"
            data-testid="block-led"
            aria-hidden="true"
          />
          <span class="name">{{ block.name }}</span>
          <span class="occupancy" data-testid="block-occupancy">{{
            OCCUPANCY_TEXT[occupancyOf(block.id)]
          }}</span>
          <span class="len">{{
            block.length_mm === null ? '—' : `${lenInUnit(block.length_mm)} ${UNIT_LABEL[unit]}`
          }}</span>
          <span class="speed">{{
            block.max_speed_kmh === null ? '—' : `${block.max_speed_kmh} km/h`
          }}</span>
          <span class="locos" data-testid="block-locos">{{
            locoAddressesOf(block.id).join(', ')
          }}</span>
          <span class="actions">
            <button type="button" @click="beginEdit(block)">Bearbeiten</button>
            <button type="button" @click="emit('delete', block.id)">Löschen</button>
          </span>

          <div class="detectors" data-testid="block-detectors">
            <span class="dh">Melder:</span>
            <ul>
              <li v-for="(d, i) in block.detectors" :key="`${d.detector_nid}-${d.detector_port}`">
                nid 0x{{ d.detector_nid.toString(16).toUpperCase() }} / Port {{ d.detector_port }} ·
                Reihenfolge {{ d.order }} ·
                {{ d.length_mm === null ? '—' : `${lenInUnit(d.length_mm)} ${UNIT_LABEL[unit]}` }}
                <button type="button" @click="removeDetector(block, i)">×</button>
              </li>
            </ul>
            <div class="detector-add">
              <input
                v-model.number="draftFor(block.id).nid"
                type="number"
                placeholder="nid"
                aria-label="Melder-nid"
              />
              <input
                v-model.number="draftFor(block.id).port"
                type="number"
                placeholder="Port"
                aria-label="Melder-Port"
              />
              <input
                v-model.number="draftFor(block.id).order"
                type="number"
                placeholder="Reihenfolge"
                aria-label="Reihenfolge"
              />
              <input
                v-model.number="draftFor(block.id).lengthInput"
                type="number"
                :placeholder="`Teillänge (${UNIT_LABEL[unit]})`"
                aria-label="Teillänge"
              />
              <button type="button" @click="addDetector(block)">Melder zuordnen</button>
            </div>
          </div>
        </template>

        <template v-else>
          <div class="editor" data-testid="block-editor">
            <input
              v-model="editing[block.id]!.name"
              type="text"
              aria-label="Blockname"
              placeholder="Name"
            />
            <input
              v-model.number="editing[block.id]!.lengthInput"
              type="number"
              :aria-label="`Länge (${UNIT_LABEL[unit]})`"
              :placeholder="`Länge (${UNIT_LABEL[unit]})`"
            />
            <input
              v-model.number="editing[block.id]!.maxSpeed"
              type="number"
              aria-label="Höchstgeschwindigkeit (km/h)"
              placeholder="km/h"
            />

            <fieldset class="markers" data-testid="block-markers">
              <legend>Markierungen</legend>
              <div v-for="dir in ['forward', 'backward'] as const" :key="dir" class="marker-dir">
                <strong>{{ dir === 'forward' ? 'vorwärts' : 'rückwärts' }}</strong>
                <div v-for="kind in ['stop', 'brake'] as const" :key="kind" class="marker-row">
                  <span class="marker-kind">{{ kind === 'stop' ? 'Halt' : 'Brems' }}</span>
                  <input
                    v-model.number="editing[block.id]!.markers[dir][kind].nid"
                    type="number"
                    placeholder="nid"
                    :aria-label="`${dir} ${kind} Melder-nid`"
                  />
                  <input
                    v-model.number="editing[block.id]!.markers[dir][kind].port"
                    type="number"
                    placeholder="Port"
                    :aria-label="`${dir} ${kind} Melder-Port`"
                  />
                  <input
                    v-model.number="editing[block.id]!.markers[dir][kind].positionInput"
                    type="number"
                    :placeholder="`Position (${UNIT_LABEL[unit]})`"
                    :aria-label="`${dir} ${kind} Position`"
                  />
                </div>
              </div>
            </fieldset>

            <button type="button" @click="submitEdit(block.id)">Speichern</button>
            <button type="button" @click="cancelEdit(block.id)">Abbrechen</button>
          </div>
        </template>
      </div>
    </div>

    <form class="create" data-testid="block-create" @submit.prevent="submitCreate">
      <h3>Neuer Block</h3>
      <input v-model="form.name" type="text" aria-label="Name neuer Block" placeholder="Name" />
      <input
        v-model.number="form.lengthInput"
        type="number"
        :aria-label="`Länge (${UNIT_LABEL[unit]})`"
        :placeholder="`Länge (${UNIT_LABEL[unit]})`"
      />
      <input
        v-model.number="form.maxSpeed"
        type="number"
        aria-label="Höchstgeschwindigkeit (km/h)"
        placeholder="km/h"
      />
      <button type="submit">Anlegen</button>
      <span
        v-if="unit === 'zoll' && lastSentMm !== null"
        class="rounding"
        data-testid="block-rounding"
        >gespeichert als {{ lastSentMm }} mm</span
      >
    </form>
  </section>
</template>

<style scoped>
.block-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
h2 {
  margin: 0;
}
.empty {
  opacity: 0.6;
}
.rows {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.row {
  display: grid;
  grid-template-columns: 1.2rem 1fr 6rem 6rem 6rem 1fr auto;
  grid-template-areas:
    'led name occupancy len speed locos actions'
    'det det det det det det det';
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  border: 1px solid var(--color-border, #444);
  border-radius: 8px;
}
.led {
  grid-area: led;
  width: 0.9rem;
  height: 0.9rem;
  border-radius: 50%;
  border: 1px solid #7a1f1f;
}
.led.off {
  background: #143a1a;
  border-color: #1f7a2f;
}
.led.on {
  background: #ff3b30;
  box-shadow: 0 0 6px #ff3b30;
}
.led.unknown {
  background: #555;
  border-color: #888;
}
.name {
  grid-area: name;
  font-weight: 600;
}
.occupancy {
  grid-area: occupancy;
}
.len {
  grid-area: len;
}
.speed {
  grid-area: speed;
}
.locos {
  grid-area: locos;
  opacity: 0.85;
}
.actions {
  grid-area: actions;
  display: flex;
  gap: 0.25rem;
}
.detectors {
  grid-area: det;
  font-size: 0.85rem;
  opacity: 0.9;
}
.detector-add {
  display: flex;
  gap: 0.25rem;
  flex-wrap: wrap;
  margin-top: 0.25rem;
}
.detector-add input {
  width: 7rem;
}
.editor,
.create {
  display: flex;
  gap: 0.4rem;
  flex-wrap: wrap;
  align-items: center;
}
.create {
  margin-top: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--color-border, #444);
}
.warnings {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}
.warning {
  color: #ffb020;
}
.error {
  color: #ffb4b4;
}
.rounding {
  opacity: 0.7;
  font-size: 0.85rem;
}
.markers {
  flex-basis: 100%;
  border: 1px solid var(--color-border, #444);
  border-radius: 6px;
  padding: 0.4rem;
}
.marker-dir {
  margin-bottom: 0.3rem;
}
.marker-row {
  display: flex;
  gap: 0.3rem;
  align-items: center;
  flex-wrap: wrap;
  margin: 0.2rem 0;
}
.marker-kind {
  width: 3.5rem;
}
.marker-row input {
  width: 6rem;
}
</style>
