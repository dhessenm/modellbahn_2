import { test, expect, type Page } from '@playwright/test'

// Simuliert das Backend per Route-Mocking. Haelt einen kleinen Zustand, damit
// Fahr-/Funktionsbefehle sich im Lok-Status widerspiegeln.
async function mockBackend(page: Page): Promise<void> {
  const loco = { address: 3, speed: 0, forward: true, functions: {} as Record<number, boolean> }
  let trackPower = true

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

  // SSE-Endpunkt: offener Stream ohne Events (verhindert Netzwerk-Fehler).
  await page.route('**/api/events', (route) =>
    route.fulfill({ status: 200, headers: { 'content-type': 'text/event-stream' }, body: '' }),
  )
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

  // Lok 3 waehlen
  await page.getByLabel('Lok-Adresse (DCC)').fill('3')
  await page.getByRole('button', { name: 'Übernehmen' }).click()

  // Fahrregler sichtbar; Fahrstufe setzen (unterhalb der Testgrenze 60)
  const slider = page.getByLabel('Fahrstufe')
  await expect(slider).toBeVisible()
  await slider.fill('30')

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
