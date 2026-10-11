<script setup lang="ts">
import { computed, reactive, type DeepReadonly } from 'vue'
import type { ElementType, ElementWrite, TopologyElement } from '@/api/layout-types'
import type { LayoutApiError } from '@/api/layout-error'

// Reine Darstellungs-/Editor-Komponente fuer Topologie-Elemente
// (Weiche/DKW/Kreuzung). CRUD ueber Events; Fehleranzeige ueber Prop.
// Adressfelder je Typ: turnout -> eine Adresse; dkw -> zwei Adressen;
// crossing -> keine Adressfelder (starre Kreuzung).
// deep-readonly, weil der zentrale Store die Liste als readonly-Ref bereitstellt.
type ReadonlyElement = DeepReadonly<TopologyElement>
const props = defineProps<{
  elements: readonly ReadonlyElement[]
  error?: DeepReadonly<LayoutApiError> | null
}>()

const emit = defineEmits<{
  create: [body: ElementWrite]
  update: [id: string, body: ElementWrite]
  delete: [id: string]
}>()

const TYPE_LABEL: Record<ElementType, string> = {
  turnout: 'Weiche',
  dkw: 'DKW',
  crossing: 'Kreuzung',
}

const TYPES: ElementType[] = ['turnout', 'dkw', 'crossing']

// true, wenn der Typ ein Adressfeld A braucht (Weiche/DKW).
function hasAddressA(type: ElementType): boolean {
  return type === 'turnout' || type === 'dkw'
}
// true, wenn der Typ ein zweites Adressfeld braucht (nur DKW).
function hasAddressB(type: ElementType): boolean {
  return type === 'dkw'
}

// --- Neuanlage ---
const form = reactive<{
  name: string
  type: ElementType
  address: number | null
  addressB: number | null
}>({
  name: '',
  type: 'turnout',
  address: null,
  addressB: null,
})

function buildWrite(
  name: string,
  type: ElementType,
  address: number | null,
  addressB: number | null,
): ElementWrite {
  return {
    name,
    type,
    address: hasAddressA(type) ? address : null,
    address_b: hasAddressB(type) ? addressB : null,
  }
}

function submitCreate(): void {
  if (!form.name.trim()) return
  emit('create', buildWrite(form.name.trim(), form.type, form.address, form.addressB))
  form.name = ''
  form.type = 'turnout'
  form.address = null
  form.addressB = null
}

// --- Inline-Editor ---
interface ElementEdit {
  name: string
  type: ElementType
  address: number | null
  addressB: number | null
}
const editing = reactive<Record<string, ElementEdit>>({})

function beginEdit(el: ReadonlyElement): void {
  editing[el.id] = {
    name: el.name,
    type: el.type,
    address: el.address,
    addressB: el.address_b,
  }
}

function cancelEdit(id: string): void {
  delete editing[id]
}

function submitEdit(id: string): void {
  const e = editing[id]
  if (!e || !e.name.trim()) return
  emit('update', id, buildWrite(e.name.trim(), e.type, e.address, e.addressB))
  delete editing[id]
}

const blockedBy = computed(() => props.error?.blockedBy ?? [])
</script>

<template>
  <section class="element-list" data-testid="element-list">
    <h2>Elemente (Weichen / DKW / Kreuzungen)</h2>

    <p v-if="error && error.status !== 409" class="error" data-testid="element-error">
      {{ error.detail }}
    </p>
    <div v-if="blockedBy.length" class="error" data-testid="element-blocked-by">
      <p>{{ error?.detail }}</p>
      <ul>
        <li v-for="b in blockedBy" :key="b.type + b.id">{{ b.type }}: {{ b.name }}</li>
      </ul>
    </div>

    <p v-if="elements.length === 0" class="empty">Noch keine Elemente angelegt.</p>

    <div class="rows">
      <div v-for="el in elements" :key="el.id" class="row" data-testid="element-row">
        <template v-if="!editing[el.id]">
          <span class="type" data-testid="element-type">{{ TYPE_LABEL[el.type] }}</span>
          <span class="name">{{ el.name }}</span>
          <span class="addr">
            <template v-if="hasAddressA(el.type)">Adr. {{ el.address ?? '—' }}</template>
            <template v-if="hasAddressB(el.type)"> / {{ el.address_b ?? '—' }}</template>
          </span>
          <span class="actions">
            <button type="button" @click="beginEdit(el)">Bearbeiten</button>
            <button type="button" @click="emit('delete', el.id)">Löschen</button>
          </span>
        </template>

        <template v-else>
          <div class="editor" data-testid="element-editor">
            <input
              v-model="editing[el.id]!.name"
              type="text"
              aria-label="Elementname"
              placeholder="Name"
            />
            <select v-model="editing[el.id]!.type" aria-label="Elementtyp">
              <option v-for="t in TYPES" :key="t" :value="t">{{ TYPE_LABEL[t] }}</option>
            </select>
            <input
              v-if="hasAddressA(editing[el.id]!.type)"
              v-model.number="editing[el.id]!.address"
              type="number"
              aria-label="Adresse A"
              placeholder="Adresse A"
            />
            <input
              v-if="hasAddressB(editing[el.id]!.type)"
              v-model.number="editing[el.id]!.addressB"
              type="number"
              aria-label="Adresse B"
              placeholder="Adresse B"
            />
            <button type="button" @click="submitEdit(el.id)">Speichern</button>
            <button type="button" @click="cancelEdit(el.id)">Abbrechen</button>
          </div>
        </template>
      </div>
    </div>

    <form class="create" data-testid="element-create" @submit.prevent="submitCreate">
      <h3>Neues Element</h3>
      <input v-model="form.name" type="text" aria-label="Name neues Element" placeholder="Name" />
      <select v-model="form.type" aria-label="Typ neues Element">
        <option v-for="t in TYPES" :key="t" :value="t">{{ TYPE_LABEL[t] }}</option>
      </select>
      <input
        v-if="hasAddressA(form.type)"
        v-model.number="form.address"
        type="number"
        aria-label="Adresse A neues Element"
        placeholder="Adresse A"
      />
      <input
        v-if="hasAddressB(form.type)"
        v-model.number="form.addressB"
        type="number"
        aria-label="Adresse B neues Element"
        placeholder="Adresse B"
      />
      <button type="submit">Anlegen</button>
    </form>
  </section>
</template>

<style scoped>
.element-list {
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
  grid-template-columns: 6rem 1fr 10rem auto;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  border: 1px solid var(--color-border, #444);
  border-radius: 8px;
}
.type {
  font-weight: 600;
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
.create {
  margin-top: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--color-border, #444);
}
.error {
  color: #ffb4b4;
}
</style>
