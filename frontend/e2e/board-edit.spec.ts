import { type APIRequestContext, type Page, expect, test } from '@playwright/test'

const ADMIN_USER = process.env.E2E_ADMIN_USER ?? 'admin'
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? 'admin'

const BOARD = 'e2e-edit-board'
const ORIGINAL_ALIAS = 'E2E Original Alias'
const EDITED_ALIAS = 'E2E Edited Alias'

// The board edit→save→persist workflow. The fixture board is provisioned and
// torn down through the REST API (Bearer-authed, so CSRF-exempt) on the
// always-available "test" backend, so the spec needs no configured connection
// and leaves no residue. The UI then drives the real editor: enter edit mode,
// change the display name in board settings, save, reload, assert it stuck.

async function apiToken(ctx: APIRequestContext): Promise<string> {
  const res = await ctx.post('api/v1/auth/login', {
    data: { username: ADMIN_USER, password: ADMIN_PASSWORD }
  })
  expect(res.ok(), 'API login should succeed').toBeTruthy()
  return (await res.json()).access_token
}

async function login(page: Page): Promise<void> {
  // Mark the first-run onboarding tour as already seen for every user id, so its
  // backdrop never renders and intercepts the editor clicks below. Runs before
  // any app code on every navigation in this page.
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
  // The first-run changelog modal (a CMK popup) can sit over the home view;
  // Escape closes it and records it as seen so it won't reappear this session.
  await page.keyboard.press('Escape').catch(() => {})
  await expect(page.locator('.cmk-popup__overlay')).toHaveCount(0)
}

test.describe('OrbVis board edit', () => {
  let ctx: APIRequestContext
  let authHeader: { Authorization: string }

  test.beforeAll(async ({ playwright, baseURL }) => {
    ctx = await playwright.request.newContext({ baseURL })
    authHeader = { Authorization: `Bearer ${await apiToken(ctx)}` }
    // Idempotent: clear any leftover from a previous run, then provision fresh.
    await ctx.delete(`api/v1/boards/${BOARD}`, { headers: authHeader })
    const res = await ctx.post('api/v1/boards', {
      headers: authHeader,
      data: { name: BOARD, alias: ORIGINAL_ALIAS, connection_id: 'test', view_type: 'static' }
    })
    expect(res.status(), 'fixture board should be created').toBe(201)
  })

  test.afterAll(async () => {
    await ctx.delete(`api/v1/boards/${BOARD}`, { headers: authHeader })
    await ctx.dispose()
  })

  test('edit board settings and persist the display name', async ({ page }) => {
    await login(page)
    await page.goto(`./#/boards/${BOARD}`)

    // Enter edit mode — the editing badge confirms the editor is live.
    await page.locator('[data-tour="edit-fab"]').click()
    await expect(page.locator('.orb-board__badge--editing')).toBeVisible()

    // Open board settings, change the display name, save.
    await page.locator('[data-tour="board-settings"]').click()
    const aliasInput = page.locator('input[aria-label="Display name"]')
    await expect(aliasInput).toHaveValue(ORIGINAL_ALIAS)
    await aliasInput.fill(EDITED_ALIAS)
    await page.getByRole('button', { name: /^save$/i }).click()
    // Both settings modals patch the live store with the PUT response once
    // the update settled — the breadcrumb flipping to the new alias is the
    // mode-independent signal (the FormSpec modal stays open after save,
    // the legacy modal closes). Navigating earlier can abort the in-flight
    // PUT and the alias silently stays unchanged. getByText never matches
    // input values, so the filled alias field cannot satisfy this early.
    await expect(page.getByText(EDITED_ALIAS).first()).toBeVisible({ timeout: 10_000 })

    // Reload from scratch; the persisted alias must survive the round-trip.
    // goto() on the identical hash URL is a no-op for the SPA — reload()
    // forces a real round-trip against the server state.
    await page.reload()
    await expect(page.getByText(EDITED_ALIAS).first()).toBeVisible({ timeout: 10_000 })

    // And it is persisted server-side, not just in the live store.
    const fresh = await ctx.get(`api/v1/boards/${BOARD}`, { headers: authHeader })
    expect((await fresh.json()).alias).toBe(EDITED_ALIAS)
  })
})
