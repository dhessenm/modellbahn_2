import { test, expect, type Page } from '@playwright/test'

// Simuliert das Backend fuer die Anlagen-Seite per Route-Mocking. Haelt einen
// kleinen Zustand (blocks/elements/routes/runtime), damit POST/PUT/DELETE sich
// in den folgenden GET-Antworten widerspiegeln. Antwortformen exakt wie das
// Backend (verifiziert): Block-POST/PUT -> { entity, warnings };
// Element/Route-POST/PUT -> nackte Entitaet; DELETE -> 204 bzw. 409-Objekt.
interface MockBlock {
  id: string
  name: string
  length_mm: number | null
  max_speed_kmh: number | null
  detectors: Array<{
    detector_nid: number
    detector_port: number
    order: number
    length_mm: number | null
  }>
  markers_forward: { stop: unknown; brake: unknown }
  markers_backward: { stop: unknown; brake: unknown }
}
interface MockElement {
  id: string
  name: string
  type: string
  address: number | null
  address_b: number | null
}
interface MockRoute {
  id: string
  name: string
  start_block_id: string
  transit_block_ids: string[]
  end_block_id: string
  element_settings: Array<{ element_id: string; desired_state: number }>
  claimed_element_ids: string[]
}

async function mockBackend(
  page: Page,
  opts: { blockDeleteConflict?: boolean } = {},
): Promise<void> {
  const state: {
    blocks: MockBlock[]
    elements: MockElement[]
    routes: MockRoute[]
    runtime: Array<{ block_id: string; occupancy: string; loco_addresses: number[] }>
  } = { blocks: [], elements: [], routes: [], runtime: [] }

  let blockSeq = 0
  let elementSeq = 0
  let routeSeq = 0

  // App-Shell braucht den Systemstatus (ConnectionStatus) und den SSE-Stream.
  await page.route('**/api/system/status', (route) =>
    route.fulfill({
      json: {
        connected: true,
        track_power_on: true,
        short_circuit: false,
        emergency_stop: false,
        temperature_c: 31,
        supply_voltage_mv: 15000,
        track_voltage_mv: 18000,
        z21_host: '192.168.0.111',
        z21_port: 21105,
      },
    }),
  )
  await page.route('**/api/events', (route) =>
    route.fulfill({ status: 200, headers: { 'content-type': 'text/event-stream' }, body: '' }),
  )
  // Der globale useLayoutStore in App.vue fragt beim Start auch die Melder ab.
  await page.route('**/api/detectors', (route) => route.fulfill({ json: { detectors: [] } }))

  // WICHTIG: Playwright prueft Routen in UMGEKEHRTER Registrierreihenfolge
  // (zuletzt registriert gewinnt). Daher die ALLGEMEINSTE Route (GET /api/layout)
  // ZUERST registrieren und die spezifischeren danach.

  // GET /api/layout (Gesamtmodell) -- allgemeinstes Pattern, zuerst registriert.
  await page.route('**/api/layout', (route) =>
    route.fulfill({
      json: { blocks: state.blocks, elements: state.elements, routes: state.routes },
    }),
  )

  // GET /api/layout/runtime
  await page.route('**/api/layout/runtime', (route) => route.fulfill({ json: state.runtime }))

  // Block-Melder: PUT /api/layout/blocks/{id}/detectors
  await page.route('**/api/layout/blocks/*/detectors', async (route) => {
    const url = route.request().url()
    const id = url.split('/blocks/')[1]!.split('/')[0]!
    const body = route.request().postDataJSON() as { detectors: MockBlock['detectors'] }
    const block = state.blocks.find((b) => b.id === id)!
    block.detectors = body.detectors
    await route.fulfill({ json: { entity: block, warnings: [] } })
  })

  // Block-CRUD mit ID: PUT/DELETE /api/layout/blocks/{id}
  await page.route('**/api/layout/blocks/*', async (route) => {
    const method = route.request().method()
    const id = route.request().url().split('/blocks/')[1]!.split('/')[0]!
    const idx = state.blocks.findIndex((b) => b.id === id)
    if (method === 'PUT') {
      const body = route.request().postDataJSON() as Partial<MockBlock>
      const block = state.blocks[idx]!
      Object.assign(block, {
        name: body.name ?? block.name,
        length_mm: body.length_mm ?? block.length_mm,
        max_speed_kmh: body.max_speed_kmh ?? block.max_speed_kmh,
      })
      await route.fulfill({ json: { entity: block, warnings: [] } })
    } else if (method === 'DELETE') {
      if (opts.blockDeleteConflict) {
        await route.fulfill({
          status: 409,
          json: {
            detail: {
              detail: 'Block wird noch von einer Fahrstraße referenziert.',
              blocked_by: [{ type: 'route', id: 'r1', name: 'Hauptfahrstraße' }],
            },
          },
        })
        return
      }
      state.blocks.splice(idx, 1)
      await route.fulfill({ status: 204, body: '' })
    } else {
      await route.fulfill({ status: 405, body: '' })
    }
  })

  // Block-Collection: GET /api/layout/blocks? Nein -> POST /api/layout/blocks
  await page.route('**/api/layout/blocks', async (route) => {
    if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON() as Partial<MockBlock>
      blockSeq += 1
      const block: MockBlock = {
        id: `b${blockSeq}`,
        name: body.name ?? '',
        length_mm: body.length_mm ?? null,
        max_speed_kmh: body.max_speed_kmh ?? null,
        detectors: [],
        markers_forward: { stop: null, brake: null },
        markers_backward: { stop: null, brake: null },
      }
      state.blocks.push(block)
      state.runtime.push({ block_id: block.id, occupancy: 'unknown', loco_addresses: [] })
      await route.fulfill({ status: 201, json: { entity: block, warnings: [] } })
    } else {
      await route.fulfill({ status: 405, body: '' })
    }
  })

  // Element-CRUD mit ID
  await page.route('**/api/layout/elements/*', async (route) => {
    const method = route.request().method()
    const id = route.request().url().split('/elements/')[1]!.split('/')[0]!
    const idx = state.elements.findIndex((e) => e.id === id)
    if (method === 'PUT') {
      const body = route.request().postDataJSON() as Partial<MockElement>
      Object.assign(state.elements[idx]!, body)
      await route.fulfill({ json: state.elements[idx] })
    } else if (method === 'DELETE') {
      state.elements.splice(idx, 1)
      await route.fulfill({ status: 204, body: '' })
    }
  })
  await page.route('**/api/layout/elements', async (route) => {
    if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON() as Partial<MockElement>
      elementSeq += 1
      const element: MockElement = {
        id: `e${elementSeq}`,
        name: body.name ?? '',
        type: body.type ?? 'turnout',
        address: body.address ?? null,
        address_b: body.address_b ?? null,
      }
      state.elements.push(element)
      await route.fulfill({ status: 201, json: element })
    }
  })

  // Route-CRUD mit ID
  await page.route('**/api/layout/routes/*', async (route) => {
    const method = route.request().method()
    const id = route.request().url().split('/routes/')[1]!.split('/')[0]!
    const idx = state.routes.findIndex((r) => r.id === id)
    if (method === 'PUT') {
      const body = route.request().postDataJSON() as Partial<MockRoute>
      Object.assign(state.routes[idx]!, body)
      await route.fulfill({ json: state.routes[idx] })
    } else if (method === 'DELETE') {
      state.routes.splice(idx, 1)
      await route.fulfill({ status: 204, body: '' })
    }
  })
  await page.route('**/api/layout/routes', async (route) => {
    if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON() as Partial<MockRoute>
      routeSeq += 1
      const r: MockRoute = {
        id: `r${routeSeq}`,
        name: body.name ?? '',
        start_block_id: body.start_block_id ?? '',
        transit_block_ids: body.transit_block_ids ?? [],
        end_block_id: body.end_block_id ?? '',
        element_settings: body.element_settings ?? [],
        claimed_element_ids: body.claimed_element_ids ?? [],
      }
      state.routes.push(r)
      await route.fulfill({ status: 201, json: r })
    }
  })
}

test('Anlage: Block -> Melder -> Element -> Fahrstraße -> Runtime sichtbar', async ({ page }) => {
  await mockBackend(page)
  await page.goto('/')

  await page.getByRole('link', { name: 'Anlage', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Anlage' })).toBeVisible()

  // Block anlegen
  const blockCreate = page.getByTestId('block-create')
  await blockCreate.getByLabel('Name neuer Block').fill('Bahnhof 1')
  await blockCreate.getByLabel('Länge (cm)').fill('120')
  await blockCreate.getByRole('button', { name: 'Anlegen' }).click()

  const blockRow = page.getByTestId('block-row')
  await expect(blockRow).toHaveCount(1)
  await expect(blockRow.first()).toContainText('Bahnhof 1')
  // Runtime-Zustand sichtbar (unbekannt, da kein Melder gemeldet)
  await expect(blockRow.first().getByTestId('block-occupancy')).toHaveText('unbekannt')
  await expect(blockRow.first().getByTestId('block-led')).toHaveClass(/unknown/)

  // Melder zuordnen
  await blockRow.first().getByLabel('Melder-nid').fill('55140')
  await blockRow.first().getByLabel('Melder-Port').fill('0')
  await blockRow.first().getByRole('button', { name: 'Melder zuordnen' }).click()
  await expect(blockRow.first().getByTestId('block-detectors')).toContainText('Port 0')

  // Element anlegen (Weiche)
  const elementCreate = page.getByTestId('element-create')
  await elementCreate.getByLabel('Name neues Element').fill('W1')
  await elementCreate.getByLabel('Adresse A neues Element').fill('5')
  await elementCreate.getByRole('button', { name: 'Anlegen' }).click()
  await expect(page.getByTestId('element-row')).toHaveCount(1)
  await expect(page.getByTestId('element-type').first()).toHaveText('Weiche')

  // Fahrstraße anlegen (Start = Ziel = Bahnhof 1 reicht fuer den Grundpfad)
  const routeCreate = page.getByTestId('route-create')
  await routeCreate.getByLabel('Name neue Fahrstraße').fill('FS 1')
  await routeCreate.getByLabel('Startblock neue Fahrstraße').selectOption({ label: 'Bahnhof 1' })
  await routeCreate.getByLabel('Zielblock neue Fahrstraße').selectOption({ label: 'Bahnhof 1' })
  await routeCreate.getByRole('button', { name: 'Anlegen' }).click()
  await expect(page.getByTestId('route-row')).toHaveCount(1)
  await expect(page.getByTestId('route-path').first()).toHaveText('Bahnhof 1 → Bahnhof 1')
})

test('Anlage: Löschkonflikt (409) zeigt benannte blocked_by-Liste', async ({ page }) => {
  await mockBackend(page, { blockDeleteConflict: true })
  await page.goto('/')

  await page.getByRole('link', { name: 'Anlage', exact: true }).click()

  // Block anlegen
  const blockCreate = page.getByTestId('block-create')
  await blockCreate.getByLabel('Name neuer Block').fill('Bahnhof 1')
  await blockCreate.getByRole('button', { name: 'Anlegen' }).click()
  const blockRow = page.getByTestId('block-row')
  await expect(blockRow).toHaveCount(1)

  // Löschen -> 409 -> blocked_by-Liste erscheint
  await blockRow.first().getByRole('button', { name: 'Löschen' }).click()
  const blocked = page.getByTestId('block-blocked-by')
  await expect(blocked).toBeVisible()
  await expect(blocked).toContainText('Hauptfahrstraße')
  await expect(blocked).toContainText('route')
})
