import { type Page, expect } from '@playwright/test'

const ADMIN_USER = process.env.E2E_ADMIN_USER ?? 'admin'
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? 'admin'

/**
 * Sign in through the OrbVis login form and wait until the app leaves /login.
 * Works against both the standalone DB login and the Checkmk htpasswd fallback
 * (the form is identical; only the credentials differ per environment).
 */
export async function login(page: Page): Promise<void> {
  await page.goto('./')
  await page.getByLabel(/username/i).fill(ADMIN_USER)
  await page.getByLabel(/password/i).fill(ADMIN_PASSWORD)
  await page.getByRole('button', { name: /sign in|login/i }).click()
  await expect(page).not.toHaveURL(/login/)
  await dismissOverlays(page)
}

/**
 * Close the first-run changelog dialog (and any similar post-login overlay) so
 * it doesn't sit over the surface under test. Best-effort: a no-op when nothing
 * is open.
 */
export async function dismissOverlays(page: Page): Promise<void> {
  const changelog = page.getByRole('dialog', { name: /changelog/i })
  if (await changelog.isVisible().catch(() => false)) {
    await page.keyboard.press('Escape')
    await changelog.waitFor({ state: 'hidden', timeout: 5_000 }).catch(() => {})
  }
}
