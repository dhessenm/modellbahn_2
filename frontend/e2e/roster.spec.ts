import { test, expect, type Page, type Route as PwRoute } from '@playwright/test'

// Simuliert das Backend fuer die Roster- und Lokfuehrerstand-Seiten per
// Route-Mocking. Haelt einen In-Memory-Roster-Zustand, damit POST sich in
// den folgenden GET-Antworten widerspiegelt. Routen fuer System-Status,
// SSE, Detektoren, Weichen und Lok-Steuerung werden minimal gehalten.

interface MockLoco {
  id: string
  name: string
  address: number
  speed_steps: number
  function_count: number
  length_mm: number | null
  max_speed_kmh: number | null
  notes: string
}

async function mockBackend(page: Page): Promise<{
  roster: MockLoco[]
  lastDriveBody: { speed: number; forward: boolean; speed_steps: number } | null
}> {
  const state = {
    roster: [] as MockLoco[],
    lastDriveBody: null as { speed: number; forward: boolean; speed_steps: number } | null,
  }

  let trackPower = true
  let rosterSeq = 0

  // Systemstatus (fuer ConnectionStatus-LED und TrackPower im Header).
  await page.route('**/api/system/status', (route: PwRoute) =>
    route.fulfill({
      json: {
        connected: true,
        track_power_on: trackPower,
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

  await page.route('**/api/system/track-power', async (route: PwRoute) => {
    const body = route.request().postDataJSON() as { on: boolean }
    trackPower = body.on
    await route.fulfill({ status: 204, body: '' })
  })

  // SSE-Endpunkt: Anfrage offen halten (nicht beantworten), simuliert einen
  // offenen Event-Stream ohne Daten. KEIN route.fulfill() -- dadurch bleibt
  // die Verbindung stehen und der EventSource-Reconnect-Loop wird verhindert.
  await page.route('**/api/events', () => {})

  // Detektoren (App-Shell / LayoutStore laedt diese beim Start).
  await page.route('**/api/detectors', (route: PwRoute) =>
    route.fulfill({ json: { detectors: [] } }),
  )

  // Layout (LayoutStore laedt beim Start auch das Anlagenmodell).
  await page.route('**/api/layout/runtime', (route: PwRoute) =>
    route.fulfill({ json: [] }),
  )
  await page.route('**/api/layout', (route: PwRoute) =>
    route.fulfill({ json: { blocks: [], elements: [], routes: [] } }),
  )

  // --- Lokverwaltung (Roster) ---
  // WICHTIG: Playwright prueft Routen in UMGEKEHRTER Registrierreihenfolge
  // (zuletzt registriert gewinnt). Daher allgemeine Muster zuerst.

  // GET /api/roster (Gesamtliste).
  await page.route('**/api/roster', async (route: PwRoute) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ json: { locomotives: state.roster } })
    } else if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON() as Omit<MockLoco, 'id'>
      rosterSeq += 1
      const loco: MockLoco = {
        id: `lok${rosterSeq}`,
        name: body.name,
        address: body.address,
        speed_steps: body.speed_steps,
        function_count: body.function_count,
        length_mm: body.length_mm,
        max_speed_kmh: body.max_speed_kmh,
        notes: body.notes,
      }
      state.roster.push(loco)
      // Adress-Duplikat pruefen (Warnung, kein Fehler).
      const dupes = state.roster.filter((l) => l.address === loco.address)
      const warnings =
        dupes.length > 1
          ? [{ code: 'adresse_doppelt', message: `DCC-Adresse ${loco.address} ist bereits vergeben.` }]
          : []
      await route.fulfill({ status: 201, json: { entity: loco, warnings } })
    } else {
      await route.fulfill({ status: 405, body: '' })
    }
  })

  // PUT/DELETE /api/roster/{id}
  await page.route('**/api/roster/*', async (route: PwRoute) => {
    const method = route.request().method()
    const url = route.request().url()
    const id = url.split('/roster/')[1]!.split('/')[0]!.split('?')[0]!
    if (method === 'PUT') {
      const body = route.request().postDataJSON() as Omit<MockLoco, 'id'>
      const idx = state.roster.findIndex((l) => l.id === id)
      if (idx >= 0) {
        state.roster[idx] = { ...body, id }
      }
      await route.fulfill({ json: { entity: state.roster[idx], warnings: [] } })
    } else if (method === 'DELETE') {
      state.roster = state.roster.filter((l) => l.id !== id)
      await route.fulfill({ status: 204, body: '' })
    } else if (method === 'GET') {
      // Einzelne Lok (falls gebraucht): GET /api/roster/{id}
      const loco = state.roster.find((l) => l.id === id)
      if (loco) {
        await route.fulfill({ json: loco })
      } else {
        await route.fulfill({ status: 404, json: { detail: 'Nicht gefunden' } })
      }
    } else {
      await route.fulfill({ status: 405, body: '' })
    }
  })

  // --- Lok-Steuerung (Lokfuehrerstand) ---
  // Fuer jeden Lokadressen-Bereich Wildcard-Routen.

  await page.route('**/api/locos/*/subscribe', (route: PwRoute) =>
    route.fulfill({ status: 204, body: '' }),
  )

  await page.route('**/api/locos/*/drive', async (route: PwRoute) => {
    const body = route.request().postDataJSON() as {
      speed: number
      forward: boolean
      speed_steps: number
    }
    state.lastDriveBody = body
    await route.fulfill({ status: 204, body: '' })
  })

  await page.route('**/api/locos/*/function', async (route: PwRoute) => {
    await route.fulfill({ status: 204, body: '' })
  })

  await page.route('**/api/locos/*', (route: PwRoute) => {
    const url = route.request().url()
    const addrStr = url.split('/locos/')[1]!.split('/')[0]!
    const address = Number(addrStr)
    return route.fulfill({
      json: { address, speed: 0, forward: true, functions: {} },
    })
  })

  // Weichen (minimal, falls eine Seite sie laedt).
  await page.route('**/api/turnouts/*/subscribe', (route: PwRoute) =>
    route.fulfill({ status: 204, body: '' }),
  )
  await page.route('**/api/turnouts/*', (route: PwRoute) =>
    route.fulfill({ json: { address: 0, position: null } }),
  )

  return state
}

// --- Tests ---

test('Lok anlegen und im Lokfuehrerstand steuern', async ({ page }) => {
  const state = await mockBackend(page)
  await page.goto('/')

  // Zur Lokomotiven-Seite navigieren.
  await page.getByRole('link', { name: 'Lokomotiven', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Lokomotiven' })).toBeVisible()

  // Neue Lok anlegen: Name, Adresse 3, Fahrstufenmodus 28, Funktionen 4.
  const createForm = page.getByTestId('roster-create')
  await createForm.getByLabel('Name neue Lok').fill('BR 218')
  await createForm.getByLabel('DCC-Adresse neue Lok').fill('3')
  await createForm.getByLabel('Fahrstufenmodus neue Lok').selectOption('28')
  await createForm.getByLabel('Anzahl Funktionen neue Lok').fill('4')
  await createForm.getByRole('button', { name: 'Anlegen' }).click()

  // Neue Lok erscheint in der Liste.
  const rosterRow = page.getByTestId('roster-row')
  await expect(rosterRow).toHaveCount(1)
  await expect(rosterRow.first()).toContainText('BR 218')

  // Zum Lokfuehrerstand navigieren.
  await page.getByRole('link', { name: 'Lokführerstand', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Lokführerstand' })).toBeVisible()

  // Lok aus dem Dropdown waehlen.
  const locoSelect = page.locator('#loco-select')
  await expect(locoSelect).toBeVisible()
  // Die Option enthaelt Name und Adresse.
  await locoSelect.selectOption({ label: 'BR 218 (Adr.\u00a03)' })

  // Vertikaler Schieberegler sichtbar.
  const slider = page.getByLabel('Fahrstufe')
  await expect(slider).toBeVisible()
  // maxSpeed sollte 28 sein (speed_steps=28).
  await expect(slider).toHaveAttribute('max', '28')

  // Funktionstasten: function_count=4 -> F0..F4 = 5 Buttons.
  const fnButtons = page.locator('.functions button')
  await expect(fnButtons).toHaveCount(5)

  // Fahrstufe setzen und pruefen, dass speed_steps=28 mitgesendet wird.
  await slider.fill('15')
  // Warten bis der Drive-Request verarbeitet wurde.
  await expect.poll(() => state.lastDriveBody).toBeTruthy()
  expect(state.lastDriveBody!.speed_steps).toBe(28)
})

test('Statusleiste LED und TrackPower auf mehreren Seiten', async ({ page }) => {
  await mockBackend(page)
  await page.goto('/')

  // Dashboard: LED und TrackPower im Header sichtbar.
  const led = page.getByTestId('connection-led')
  const trackPower = page.getByTestId('track-power')
  await expect(led).toBeVisible()
  await expect(led).toHaveClass(/on/)
  await expect(trackPower).toBeVisible()

  // Dashboard zeigt KEINE eigenstaendige TrackPower-Section (nur SystemStatePanel).
  await expect(page.getByRole('heading', { name: 'Zentralenstatus' })).toBeVisible()
  // Sicherstellen: kein zweiter TrackPower-Block ausserhalb des Headers.
  const tpCount = await page.getByTestId('track-power').count()
  expect(tpCount).toBe(1)

  // Zum Lokomotiven-Bereich navigieren: LED + TrackPower bleiben im Header.
  await page.getByRole('link', { name: 'Lokomotiven', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Lokomotiven' })).toBeVisible()
  await expect(led).toBeVisible()
  await expect(led).toHaveClass(/on/)
  await expect(trackPower).toBeVisible()

  // Zum Lokfuehrerstand: LED + TrackPower bleiben im Header.
  await page.getByRole('link', { name: 'Lokführerstand', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Lokführerstand' })).toBeVisible()
  await expect(led).toBeVisible()
  await expect(led).toHaveClass(/on/)
  await expect(trackPower).toBeVisible()
})
