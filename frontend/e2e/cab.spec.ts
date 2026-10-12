import { test, expect, type Page } from '@playwright/test'

// Simuliert das Backend per Route-Mocking. Haelt einen kleinen Zustand, damit
// Fahr-/Funktionsbefehle sich im Lok-Status widerspiegeln.
async function mockBackend(page: Page): Promise<void> {
  const loco = { address: 3, speed: 0, forward: true, functions: {} as Record<number, boolean> }
  let trackPower = true

  // Lokverwaltung: eine Lok, damit der Lokfuehrerstand sie im Dropdown
  // anbietet. speed_steps=128 -> maxSpeed 126 (deckt die Testgrenze 60 ab).
  const roster = [
    {
      id: 'lok1',
      name: 'BR 218',
      address: 3,
      speed_steps: 128,
      function_count: 28,
      length_mm: null as number | null,
      max_speed_kmh: null as number | null,
      notes: '',
    },
  ]
  await page.route('**/api/roster/*', (route) => route.fulfill({ status: 404, body: '' }))
  await page.route('**/api/roster', (route) =>
    route.fulfill({ json: { locomotives: roster } }),
  )

  // Anlagenmodell wird vom globalen LayoutStore beim Start geladen.
  await page.route('**/api/layout/runtime', (route) => route.fulfill({ json: [] }))
  await page.route('**/api/layout', (route) =>
    route.fulfill({ json: { blocks: [], elements: [], routes: [] } }),
  )

  await page.route('**/api/system/status', (route) =>
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

  await page.route('**/api/system/track-power', async (route) => {
    const body = route.request().postDataJSON() as { on: boolean }
    trackPower = body.on
    await route.fulfill({ status: 204, body: '' })
  })

  await page.route('**/api/locos/3/subscribe', (route) =>
    route.fulfill({ status: 204, body: '' }),
  )

  // Sicherheitsgrenze fuer den Test: kein Fahrbefehl ueber DCC-Fahrstufe 60.
  const MAX_TEST_STEP = 60

  await page.route('**/api/locos/3/drive', async (route) => {
    const body = route.request().postDataJSON() as { speed: number; forward: boolean }
    expect(body.speed, 'Fahrstufe im Test darf 60 nicht ueberschreiten').toBeLessThanOrEqual(
      MAX_TEST_STEP,
    )
    loco.speed = body.speed
    loco.forward = body.forward
    await route.fulfill({ status: 204, body: '' })
  })

  await page.route('**/api/locos/3/function', async (route) => {
    const body = route.request().postDataJSON() as { function: number; on: boolean }
    loco.functions[body.function] = body.on
    await route.fulfill({ status: 204, body: '' })
  })

  await page.route('**/api/locos/3', (route) => route.fulfill({ json: loco }))

  // Weiche 7: Zustand haelt sich im Mock.
  const turnout = { address: 7, position: null as number | null }
  await page.route('**/api/turnouts/7/subscribe', (route) =>
    route.fulfill({ status: 204, body: '' }),
  )
  await page.route('**/api/turnouts/7', async (route) => {
    if (route.request().method() === 'PUT') {
      const body = route.request().postDataJSON() as { position: number }
      turnout.position = body.position
      await route.fulfill({ status: 204, body: '' })
    } else {
      await route.fulfill({ json: turnout })
    }
  })

  // Belegtmelder: zwei Eingaenge an einem Melder (nid 0xD764) -- einer frei,
  // einer besetzt mit zwei Lokadressen; dazu ein Melder mit Ueberlast.
  await page.route('**/api/detectors/refresh', (route) =>
    route.fulfill({ status: 204, body: '' }),
  )
  await page.route('**/api/detectors', (route) =>
    route.fulfill({
      json: {
        detectors: [
          {
            nid: 0xd764,
            addr: 0,
            port: 0,
            occupied: true,
            with_power: true,
            overload: false,
            overload_level: 0,
            status_text: 'besetzt (mit Spannung)',
            locos: [
              { address: 3, direction: 'forward' },
              { address: 42, direction: 'backward' },
            ],
          },
          {
            nid: 0xd764,
            addr: 0,
            port: 1,
            occupied: false,
            with_power: true,
            overload: false,
            overload_level: 0,
            status_text: 'frei (mit Spannung)',
            locos: [],
          },
          {
            nid: 0xd765,
            addr: 0,
            port: 0,
            occupied: true,
            with_power: true,
            overload: true,
            overload_level: 2,
            status_text: 'besetzt (Ueberlast 2)',
            locos: [],
          },
        ],
      },
    }),
  )

  // SSE-Endpunkt: Anfrage offen halten (nicht beantworten), simuliert einen
  // offenen Event-Stream ohne Daten. KEIN route.fulfill() -- dadurch bleibt
  // die Verbindung stehen und der EventSource-Reconnect-Loop wird verhindert.
  await page.route('**/api/events', () => {})
}

test('Dashboard zeigt Zentralenstatus', async ({ page }) => {
  await mockBackend(page)
  await page.goto('/')

  // Dashboard mit Zentralenstatus
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Zentralenstatus' })).toBeVisible()
  await expect(page.getByText('31 °C')).toBeVisible()
})

test('Lokfuehrerstand: Lok waehlen, fahren, Funktion schalten', async ({ page }) => {
  await mockBackend(page)
  await page.goto('/')

  // Über die Navigation zum Lokführerstand wechseln (exakter Link-Name)
  await page.getByRole('link', { name: 'Lokführerstand', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Lokführerstand' })).toBeVisible()

  // Lok aus dem Dropdown waehlen (ersetzt die fruehere Adress-Eingabe)
  await page.locator('#loco-select').selectOption({ label: 'BR 218 (Adr.\u00a03)' })

  // Fahrregler sichtbar; Fahrstufe setzen (unterhalb der Testgrenze 60)
  const slider = page.getByLabel('Fahrstufe')
  await expect(slider).toBeVisible()
  await slider.fill('30')

  // Lok-Details aufklappen (default eingeklappt seit FEAT-002).
  await page.getByText('Lok-Details').click()

  // Infoframe zeigt die Geschwindigkeit als Key-Value
  await expect(page.getByText('Geschwindigkeit')).toBeVisible()
  await expect(page.locator('dd', { hasText: /^30$/ })).toBeVisible()

  // Grenzfall: exakt Fahrstufe 60 ist erlaubt (Mock-Assertion prueft <= 60)
  await slider.fill('60')
  await expect(page.locator('dd', { hasText: /^60$/ })).toBeVisible()

  // Funktion F2 einschalten
  await page.getByRole('button', { name: 'F2', exact: true }).click()
  await expect(page.locator('dt', { hasText: /^F2$/ })).toBeVisible()
})

test('Weichen: Adresse waehlen und Position schalten', async ({ page }) => {
  await mockBackend(page)
  await page.goto('/')

  // Über die Navigation zu den Weichen
  await page.getByRole('link', { name: 'Weichen', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Weichen' })).toBeVisible()

  // Weiche 7 waehlen
  await page.getByLabel('Weichen-Adresse (DCC, ab 0)').fill('7')
  await page.getByRole('button', { name: 'Übernehmen' }).click()
  await expect(page.getByText('Weiche 7')).toBeVisible()

  // Position 1 schalten -> Anzeige aktualisiert
  await page.getByRole('button', { name: 'Position 1' }).click()
  await expect(page.locator('.pos strong', { hasText: /^1$/ })).toBeVisible()
})

test('Belegtmelder: Status, LED und Lokadressen werden angezeigt', async ({ page }) => {
  await mockBackend(page)
  await page.goto('/')

  // Über die Navigation zu den Belegtmeldern (exakter Link-Name)
  await page.getByRole('link', { name: 'Belegtmelder', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Belegtmelder' })).toBeVisible()

  // Drei Eingaenge insgesamt (zwei Melder)
  const rows = page.getByTestId('detector-row')
  await expect(rows).toHaveCount(3)

  // Erster Eingang (besetzt): LED an, Lokadressen mit Richtung
  const first = rows.nth(0)
  await expect(first.getByTestId('detector-led')).toHaveClass(/on/)
  await expect(first.getByTestId('detector-status')).toHaveText('besetzt (mit Spannung)')
  await expect(first.getByTestId('detector-locos')).toContainText('3')
  await expect(first.getByTestId('detector-locos')).toContainText('42')

  // Zweiter Eingang (frei): LED aus
  await expect(rows.nth(1).getByTestId('detector-led')).toHaveClass(/off/)

  // Dritter Eingang: Ueberlast hervorgehoben
  await expect(rows.nth(2).getByTestId('detector-status')).toHaveClass(/overload/)

  // Aktualisieren-Button klickbar
  await page.getByRole('button', { name: 'Aktualisieren' }).click()
})
