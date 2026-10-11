<script setup lang="ts">
import { computed, reactive, type DeepReadonly } from 'vue'
import type { Block, ElementSetting, Route, RouteWrite, TopologyElement } from '@/api/layout-types'
import type { LayoutApiError } from '@/api/layout-error'

// Reine Darstellungs-/Editor-Komponente fuer Fahrstrassen. CRUD ueber Events;
// Blocknamen/Elementnamen werden ueber die Props aufgeloest.
// deep-readonly, weil der zentrale Store die Listen als readonly-Refs bereitstellt.
type ReadonlyRoute = DeepReadonly<Route>
const props = defineProps<{
  routes: readonly ReadonlyRoute[]
  blocks: readonly DeepReadonly<Block>[]
  elements: readonly DeepReadonly<TopologyElement>[]
  error?: DeepReadonly<LayoutApiError> | null
}>()

const emit = defineEmits<{
  create: [body: RouteWrite]
  update: [id: string, body: RouteWrite]
  delete: [id: string]
}>()

const blockName = computed(() => {
  const map = new Map<string, string>()
  for (const b of props.blocks) map.set(b.id, b.name)
  return map
})

const elementName = computed(() => {
  const map = new Map<string, string>()
  for (const e of props.elements) map.set(e.id, e.name)
  return map
})

function nameOfBlock(id: string): string {
  return blockName.value.get(id) ?? id
}
function nameOfElement(id: string): string {
  return elementName.value.get(id) ?? id
}

// Pfad-Text: Start -> [Zwischenbloecke] -> Ziel.
function pathText(route: ReadonlyRoute): string {
  const parts = [
    nameOfBlock(route.start_block_id),
    ...route.transit_block_ids.map(nameOfBlock),
    nameOfBlock(route.end_block_id),
  ]
  return parts.join(' → ')
}

// Schaltbare Elemente fuer element_settings: nur Weichen/DKW (crossing lehnt das
// Backend in element_settings ab -> die UI bietet sie dort gar nicht erst an).
const switchableElements = computed(() =>
  props.elements.filter((e) => e.type === 'turnout' || e.type === 'dkw'),
)

// --- Neuanlage ---
interface RouteForm {
  name: string
  startBlockId: string
  transitInput: string // kommaseparierte Block-IDs
  endBlockId: string
  settings: ElementSetting[]
  claimedInput: string // kommaseparierte Element-IDs
}

function emptyForm(): RouteForm {
  return {
    name: '',
    startBlockId: '',
    transitInput: '',
    endBlockId: '',
    settings: [],
    claimedInput: '',
  }
}

const form = reactive<RouteForm>(emptyForm())

function splitIds(raw: string): string[] {
  return raw
    .split(',')
    .map((s) => s.trim())
    .filter((s) => s.length > 0)
}

function buildWrite(f: RouteForm): RouteWrite {
  return {
    name: f.name.trim(),
    start_block_id: f.startBlockId,
    transit_block_ids: splitIds(f.transitInput),
    end_block_id: f.endBlockId,
    element_settings: f.settings
      .filter((s) => s.element_id)
      .map((s) => ({ element_id: s.element_id, desired_state: s.desired_state })),
    claimed_element_ids: splitIds(f.claimedInput),
  }
}

function addSetting(f: RouteForm): void {
  f.settings.push({ element_id: '', desired_state: 0 })
}
function removeSetting(f: RouteForm, i: number): void {
  f.settings.splice(i, 1)
}

function submitCreate(): void {
  if (!form.name.trim() || !form.startBlockId || !form.endBlockId) return
  emit('create', buildWrite(form))
  Object.assign(form, emptyForm())
}

// --- Inline-Editor ---
const editing = reactive<Record<string, RouteForm>>({})

function beginEdit(route: ReadonlyRoute): void {
  editing[route.id] = {
    name: route.name,
    startBlockId: route.start_block_id,
    transitInput: route.transit_block_ids.join(', '),
    endBlockId: route.end_block_id,
    settings: route.element_settings.map((s) => ({ ...s })),
    claimedInput: route.claimed_element_ids.join(', '),
  }
}
function cancelEdit(id: string): void {
  delete editing[id]
}
function submitEdit(id: string): void {
  const e = editing[id]
  if (!e || !e.name.trim() || !e.startBlockId || !e.endBlockId) return
  emit('update', id, buildWrite(e))
  delete editing[id]
}

const blockedBy = computed(() => props.error?.blockedBy ?? [])
</script>

<template>
  <section class="route-list" data-testid="route-list">
    <h2>Fahrstraßen</h2>

    <p v-if="error && error.status !== 409" class="error" data-testid="route-error">
      {{ error.detail }}
    </p>
    <div v-if="blockedBy.length" class="error" data-testid="route-blocked-by">
      <p>{{ error?.detail }}</p>
      <ul>
        <li v-for="b in blockedBy" :key="b.type + b.id">{{ b.type }}: {{ b.name }}</li>
      </ul>
    </div>

    <p v-if="routes.length === 0" class="empty">Noch keine Fahrstraßen angelegt.</p>

    <div class="rows">
      <div v-for="route in routes" :key="route.id" class="row" data-testid="route-row">
        <template v-if="!editing[route.id]">
          <span class="name">{{ route.name }}</span>
          <span class="path" data-testid="route-path">{{ pathText(route) }}</span>
          <span class="settings" data-testid="route-settings">
            <template v-if="route.element_settings.length">
              Stellungen:
              <span v-for="s in route.element_settings" :key="s.element_id" class="setting"
                >{{ nameOfElement(s.element_id) }}={{ s.desired_state }}</span
              >
            </template>
          </span>
          <span class="claimed" data-testid="route-claimed">
            <template v-if="route.claimed_element_ids.length">
              beansprucht:
              {{ route.claimed_element_ids.map(nameOfElement).join(', ') }}
            </template>
          </span>
          <span class="actions">
            <button type="button" @click="beginEdit(route)">Bearbeiten</button>
            <button type="button" @click="emit('delete', route.id)">Löschen</button>
          </span>
        </template>

        <template v-else>
          <div class="editor" data-testid="route-editor">
            <input
              v-model="editing[route.id]!.name"
              type="text"
              aria-label="Fahrstraßenname"
              placeholder="Name"
            />
            <select v-model="editing[route.id]!.startBlockId" aria-label="Startblock">
              <option value="" disabled>Start wählen</option>
              <option v-for="b in blocks" :key="b.id" :value="b.id">{{ b.name }}</option>
            </select>
            <input
              v-model="editing[route.id]!.transitInput"
              type="text"
              aria-label="Zwischenblöcke (IDs, kommagetrennt)"
              placeholder="Zwischenblock-IDs"
            />
            <select v-model="editing[route.id]!.endBlockId" aria-label="Zielblock">
              <option value="" disabled>Ziel wählen</option>
              <option v-for="b in blocks" :key="b.id" :value="b.id">{{ b.name }}</option>
            </select>
            <input
              v-model="editing[route.id]!.claimedInput"
              type="text"
              aria-label="Beanspruchte Element-IDs (kommagetrennt)"
              placeholder="beanspruchte Element-IDs"
            />
            <div class="settings-edit">
              <div v-for="(s, i) in editing[route.id]!.settings" :key="i" class="setting-row">
                <select v-model="s.element_id" aria-label="Element der Stellung">
                  <option value="" disabled>Element</option>
                  <option v-for="el in switchableElements" :key="el.id" :value="el.id">
                    {{ el.name }}
                  </option>
                </select>
                <input
                  v-model.number="s.desired_state"
                  type="number"
                  aria-label="Soll-Stellung"
                  placeholder="Stellung"
                />
                <button type="button" @click="removeSetting(editing[route.id]!, i)">×</button>
              </div>
              <button type="button" @click="addSetting(editing[route.id]!)">
                Stellung hinzufügen
              </button>
            </div>
            <button type="button" @click="submitEdit(route.id)">Speichern</button>
            <button type="button" @click="cancelEdit(route.id)">Abbrechen</button>
          </div>
        </template>
      </div>
    </div>

    <form class="create" data-testid="route-create" @submit.prevent="submitCreate">
      <h3>Neue Fahrstraße</h3>
      <input v-model="form.name" type="text" aria-label="Name neue Fahrstraße" placeholder="Name" />
      <select v-model="form.startBlockId" aria-label="Startblock neue Fahrstraße">
        <option value="" disabled>Start wählen</option>
        <option v-for="b in blocks" :key="b.id" :value="b.id">{{ b.name }}</option>
      </select>
      <input
        v-model="form.transitInput"
        type="text"
        aria-label="Zwischenblöcke neue Fahrstraße (IDs, kommagetrennt)"
        placeholder="Zwischenblock-IDs"
      />
      <select v-model="form.endBlockId" aria-label="Zielblock neue Fahrstraße">
        <option value="" disabled>Ziel wählen</option>
        <option v-for="b in blocks" :key="b.id" :value="b.id">{{ b.name }}</option>
      </select>
      <input
        v-model="form.claimedInput"
        type="text"
        aria-label="Beanspruchte Element-IDs neue Fahrstraße (kommagetrennt)"
        placeholder="beanspruchte Element-IDs"
      />
      <div class="settings-edit">
        <div v-for="(s, i) in form.settings" :key="i" class="setting-row">
          <select v-model="s.element_id" aria-label="Element der Stellung (neu)">
            <option value="" disabled>Element</option>
            <option v-for="el in switchableElements" :key="el.id" :value="el.id">
              {{ el.name }}
            </option>
          </select>
          <input
            v-model.number="s.desired_state"
            type="number"
            aria-label="Soll-Stellung (neu)"
            placeholder="Stellung"
          />
          <button type="button" @click="removeSetting(form, i)">×</button>
        </div>
        <button type="button" @click="addSetting(form)">Stellung hinzufügen</button>
      </div>
      <button type="submit">Anlegen</button>
    </form>
  </section>
</template>

<style scoped>
.route-list {
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
  gap: 0.4rem;
}
.row {
  display: grid;
  grid-template-columns: 1fr 1.5fr 1.5fr 1.5fr auto;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  border: 1px solid var(--color-border, #444);
  border-radius: 8px;
}
.name {
  font-weight: 600;
}
.path {
  font-variant-numeric: tabular-nums;
}
.setting {
  margin-right: 0.4rem;
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
  align-items: flex-start;
}
.settings-edit {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  flex-basis: 100%;
}
.setting-row {
  display: flex;
  gap: 0.3rem;
  align-items: center;
}
.create {
  margin-top: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--color-border, #444);
}
.error {
  color: #ffb4b4;
}
</style>
