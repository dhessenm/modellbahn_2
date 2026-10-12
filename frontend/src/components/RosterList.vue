<script setup lang="ts">
import { reactive, type DeepReadonly } from 'vue'
import type { Locomotive, LocoWrite, RosterWarning } from '@/api/roster-types'
import type { LayoutApiError } from '@/api/layout-error'
import { fromMm, toMm, UNIT_LABEL, type LengthUnit } from '@/stores/length-units'

// Reine Darstellungs-/Editor-Komponente: bekommt den Zustand als Props und
// meldet Aenderungen ueber Events (Muster BlockList.vue). So laesst sie sich
// isoliert testen. Laengen in Anzeige-Einheit; Payload immer in ganzen mm.
// deep-readonly, weil der zentrale Store die Liste als readonly-Ref bereitstellt.
type ReadonlyLoco = DeepReadonly<Locomotive>

const props = defineProps<{
  locomotives: readonly ReadonlyLoco[]
  unit: LengthUnit
  warnings?: readonly DeepReadonly<RosterWarning>[]
  error?: DeepReadonly<LayoutApiError> | null
}>()

const emit = defineEmits<{
  create: [body: LocoWrite]
  update: [id: string, body: LocoWrite]
  delete: [id: string]
}>()

// Default-Werte, wenn der Nutzer die Felder leer laesst.
const DEFAULT_SPEED_STEPS = 128
const DEFAULT_FUNCTION_COUNT = 28
const SPEED_STEP_OPTIONS = [14, 28, 128] as const

// Laenge in der aktuellen Anzeige-Einheit (fuer Eingabefelder).
function lenInUnit(valueMm: number | null): number | null {
  return valueMm === null ? null : Number(fromMm(valueMm, props.unit).toFixed(3))
}

// Entwurf eines Lok-Formulars (Neuanlage und Inline-Edit teilen die Form).
interface LocoDraft {
  name: string
  address: number | null
  speedSteps: number
  functionCount: number | null
  lengthInput: number | null
  maxSpeed: number | null
  notes: string
}

function emptyDraft(): LocoDraft {
  return {
    name: '',
    address: null,
    speedSteps: DEFAULT_SPEED_STEPS,
    functionCount: DEFAULT_FUNCTION_COUNT,
    lengthInput: null,
    maxSpeed: null,
    notes: '',
  }
}

function draftFrom(loco: ReadonlyLoco): LocoDraft {
  return {
    name: loco.name,
    address: loco.address,
    speedSteps: loco.speed_steps,
    functionCount: loco.function_count,
    lengthInput: lenInUnit(loco.length_mm),
    maxSpeed: loco.max_speed_kmh,
    notes: loco.notes,
  }
}

// Baut aus einem Entwurf das API-Payload. Defaults greifen, wenn Fahrstufen-
// modus/Funktionsanzahl leer sind; Laenge wird auf ganze mm gerundet.
function buildLocoWrite(d: LocoDraft): LocoWrite {
  return {
    name: d.name.trim(),
    address: d.address ?? 0,
    speed_steps: d.speedSteps ?? DEFAULT_SPEED_STEPS,
    function_count: d.functionCount ?? DEFAULT_FUNCTION_COUNT,
    length_mm: d.lengthInput === null ? null : toMm(d.lengthInput, props.unit),
    max_speed_kmh: d.maxSpeed,
    notes: d.notes.trim(),
  }
}

// --- Neuanlage ---
const form = reactive<LocoDraft>(emptyDraft())

function submitCreate(): void {
  if (!form.name.trim() || form.address === null) return
  emit('create', buildLocoWrite(form))
  Object.assign(form, emptyDraft())
}

// --- Inline-Editor je Lok ---
const editing = reactive<Record<string, LocoDraft>>({})

function beginEdit(loco: ReadonlyLoco): void {
  editing[loco.id] = draftFrom(loco)
}

function cancelEdit(id: string): void {
  delete editing[id]
}

function submitEdit(id: string): void {
  const e = editing[id]
  if (!e || !e.name.trim() || e.address === null) return
  emit('update', id, buildLocoWrite(e))
  delete editing[id]
}
</script>

<template>
  <section class="roster-list" data-testid="roster-list">
    <p v-if="warnings && warnings.length" class="warnings">
      <span
        v-for="w in warnings"
        :key="w.code"
        class="warning"
        data-testid="roster-warning"
        >{{ w.message }}</span
      >
    </p>

    <p v-if="error" class="error" data-testid="roster-error">{{ error.detail }}</p>

    <p v-if="locomotives.length === 0" class="empty">Noch keine Loks angelegt.</p>

    <div class="rows">
      <div v-for="loco in locomotives" :key="loco.id" class="row" data-testid="roster-row">
        <template v-if="!editing[loco.id]">
          <span class="name">{{ loco.name }}</span>
          <span class="addr" data-testid="roster-address">Adresse {{ loco.address }}</span>
          <span class="steps">{{ loco.speed_steps }} Fahrstufen</span>
          <span class="speed">{{
            loco.max_speed_kmh === null ? '—' : `${loco.max_speed_kmh} km/h`
          }}</span>
          <span class="len">{{
            loco.length_mm === null ? '—' : `${lenInUnit(loco.length_mm)} ${UNIT_LABEL[unit]}`
          }}</span>
          <span class="actions">
            <button type="button" @click="beginEdit(loco)">Bearbeiten</button>
            <button type="button" @click="emit('delete', loco.id)">Löschen</button>
          </span>
        </template>

        <template v-else>
          <div class="editor" data-testid="roster-editor">
            <input
              v-model="editing[loco.id]!.name"
              type="text"
              aria-label="Name"
              placeholder="Name"
            />
            <input
              v-model.number="editing[loco.id]!.address"
              type="number"
              min="1"
              max="9999"
              aria-label="DCC-Adresse"
              placeholder="Adresse"
            />
            <select v-model.number="editing[loco.id]!.speedSteps" aria-label="Fahrstufenmodus">
              <option v-for="s in SPEED_STEP_OPTIONS" :key="s" :value="s">{{ s }}</option>
            </select>
            <input
              v-model.number="editing[loco.id]!.functionCount"
              type="number"
              min="0"
              max="28"
              aria-label="Anzahl Funktionen"
              placeholder="Funktionen"
            />
            <input
              v-model.number="editing[loco.id]!.lengthInput"
              type="number"
              :aria-label="`Länge (${UNIT_LABEL[unit]})`"
              :placeholder="`Länge (${UNIT_LABEL[unit]})`"
            />
            <input
              v-model.number="editing[loco.id]!.maxSpeed"
              type="number"
              aria-label="Höchstgeschwindigkeit (km/h)"
              placeholder="km/h"
            />
            <input
              v-model="editing[loco.id]!.notes"
              type="text"
              aria-label="Notizen"
              placeholder="Notizen"
            />
            <button type="button" @click="submitEdit(loco.id)">Speichern</button>
            <button type="button" @click="cancelEdit(loco.id)">Abbrechen</button>
          </div>
        </template>
      </div>
    </div>

    <form class="create" data-testid="roster-create" @submit.prevent="submitCreate">
      <h3>Neue Lok</h3>
      <input v-model="form.name" type="text" aria-label="Name neue Lok" placeholder="Name" />
      <input
        v-model.number="form.address"
        type="number"
        min="1"
        max="9999"
        aria-label="DCC-Adresse neue Lok"
        placeholder="Adresse"
      />
      <select v-model.number="form.speedSteps" aria-label="Fahrstufenmodus neue Lok">
        <option v-for="s in SPEED_STEP_OPTIONS" :key="s" :value="s">{{ s }}</option>
      </select>
      <input
        v-model.number="form.functionCount"
        type="number"
        min="0"
        max="28"
        aria-label="Anzahl Funktionen neue Lok"
        placeholder="Funktionen"
      />
      <input
        v-model.number="form.lengthInput"
        type="number"
        :aria-label="`Länge neue Lok (${UNIT_LABEL[unit]})`"
        :placeholder="`Länge (${UNIT_LABEL[unit]})`"
      />
      <input
        v-model.number="form.maxSpeed"
        type="number"
        aria-label="Höchstgeschwindigkeit neue Lok (km/h)"
        placeholder="km/h"
      />
      <input v-model="form.notes" type="text" aria-label="Notizen neue Lok" placeholder="Notizen" />
      <button type="submit">Anlegen</button>
    </form>
  </section>
</template>

<style scoped>
.roster-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
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
  grid-template-columns: 1fr 7rem 8rem 6rem 7rem auto;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  border: 1px solid var(--color-border, #444);
  border-radius: 8px;
}
.name {
  font-weight: 600;
}
.speed,
.len {
  opacity: 0.85;
}
.actions {
  display: flex;
  gap: 0.25rem;
}
.editor,
.create {
  display: flex;
  gap: 0.4rem;
  flex-wrap: wrap;
  align-items: center;
}
.editor {
  grid-column: 1 / -1;
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
</style>
