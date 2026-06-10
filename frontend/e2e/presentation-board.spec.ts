import { type APIRequestContext, type Page, expect, test } from '@playwright/test'

const ADMIN_USER = process.env.E2E_ADMIN_USER ?? 'admin'
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? 'admin'

const BOARD = 'e2e-presentation-board'

// The design-first presentation workflow: an empty presentation board greets
// with the template gallery, applying a design drops into connect-data mode
// with unbound sample slots, and the docked inspector edits a selected element.
// The fixture board is provisioned through the REST API on the always-available
// "test" connection; the presentation feature flag is enabled for the run and
// restored afterwards.

async function apiToken(ctx: APIRequestContext): Promise<string> {
  const res = await ctx.post('api/v1/auth/login', {
    data: { username: ADMIN_USER, password: ADMIN_PASSWORD }
  })
  expect(res.ok(), 'API login should succeed').toBeTruthy()
  return (await res.json()).access_token
}

async function login(page: Page): Promise<void> {
  await page.addInitScript(() => {
    const orig = Storage.prototype.getItem
    Storage.prototype.getItem = function (key: string) {
      if (typeof key === 'string' && key.startsWith('orbvis_board_toured_')) return '1'
      return orig.call(this, key)
    }
  })
  await page.goto('./')
  await page.getByLabel(/username/i).fill(ADMIN_USER)
  await page.getByLabel(/password/i).fill(ADMIN_PASSWORD)
  await page.getByRole('button', { name: /sign in|login/i }).click()
  await expect(page).not.toHaveURL(/login/)
  await page.keyboard.press('Escape').catch(() => {})
  await expect(page.locator('.cmk-popup__overlay')).toHaveCount(0)
}

test.describe('OrbVis presentation board', () => {
  let ctx: APIRequestContext
  let authHeader: { Authorization: string }
  let presentationFlagBefore: boolean

  test.beforeAll(async ({ playwright, baseURL }) => {
    ctx = await playwright.request.newContext({ baseURL })
    authHeader = { Authorization: `Bearer ${await apiToken(ctx)}` }

    const sys = await ctx.get('api/v1/settings/system', { headers: authHeader })
    expect(sys.ok()).toBeTruthy()
    const sysBody = await sys.json()
    presentationFlagBefore = !!sysBody.enable_presentation_boards
    if (!presentationFlagBefore) {
      const put = await ctx.put('api/v1/settings/system', {
        headers: authHeader,
        data: { ...sysBody, enable_presentation_boards: true }
      })
      expect(put.ok(), 'feature flag should toggle on').toBeTruthy()
    }

    await ctx.delete(`api/v1/boards/${BOARD}`, { headers: authHeader })
    const res = await ctx.post('api/v1/boards', {
      headers: authHeader,
      data: {
        name: BOARD,
        alias: 'E2E Presentation',
        connection_id: 'test',
        view: { type: 'presentation' }
      }
    })
    expect(res.status(), 'fixture board should be created').toBe(201)
  })

  test.afterAll(async () => {
    await ctx.delete(`api/v1/boards/${BOARD}`, { headers: authHeader })
    if (!presentationFlagBefore) {
      const sys = await ctx.get('api/v1/settings/system', { headers: authHeader })
      if (sys.ok()) {
        const sysBody = await sys.json()
        await ctx.put('api/v1/settings/system', {
          headers: authHeader,
          data: { ...sysBody, enable_presentation_boards: false }
        })
      }
    }
    await ctx.dispose()
  })

  test('template → connect mode → inspector → persisted save', async ({ page }) => {
    await login(page)
    await page.goto(`./#/boards/${BOARD}`)

    // Enter edit mode; the empty slide greets with the template gallery.
    await page.locator('[data-tour="edit-fab"]').click()
    const gallery = page.locator('.ptg')
    await expect(gallery).toBeVisible()

    // Apply the NOC Overview template → connect-data mode starts on slot 1.
    await gallery.getByRole('button', { name: /NOC Overview/ }).click()
    await expect(page.locator('.pres__connect-bar')).toBeVisible()
    await expect(page.locator('.pres__connect-bar')).toContainText('0 of 6 connected')
    await expect(page.locator('.pco__slot')).toHaveCount(6)
    await expect(page.locator('.pres__connect-pop')).toBeVisible()

    // Walk one slot ahead and back, then leave the walkthrough.
    await page.locator('.pres__connect-pop').getByRole('button', { name: /skip/i }).click()
    await page.keyboard.press('Escape')
    await expect(page.locator('.pres__connect-bar')).toHaveCount(0)

    // Unbound slots preview with sample data in the editor.
    await expect(page.locator('.pres-el__sample').first()).toBeVisible()

    // Select a tile → the docked inspector shows Layout + Data sections.
    await page
      .locator('.pres__el')
      .filter({ has: page.locator('.pres-el__data') })
      .first()
      .click()
    const inspector = page.locator('.insp')
    await expect(inspector).toBeVisible()
    await expect(inspector).toContainText('Layout')
    await expect(inspector).toContainText('Host')

    // The debounced save lands and survives a reload.
    await expect(page.locator('.pres__hud-status')).toHaveText(/saved/i, { timeout: 5000 })
    await page.reload()
    await page.locator('[data-tour="edit-fab"]').click()
    await expect(page.locator('.ptg')).toHaveCount(0)
    await expect(page.locator('.pres__el')).not.toHaveCount(0)
  })
})
