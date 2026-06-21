import { expect, test } from '@playwright/test'

import { login } from './helpers'

// Non-destructive check that the admin surfaces render through the Checkmk
// FormSpec path (the only path that ships in-tree). Everything runs after a
// single login to stay within the login rate-limit on a shared test site, and
// nothing is saved, so it is safe to run against a live site.
test.describe('OrbVis admin FormSpec surfaces', () => {
  test('settings and connections render the FormSpec admin views', async ({ page }) => {
    await login(page)

    // Global Settings: the FormSpec dictionary groups surface as the
    // "Board defaults" / "Object defaults" tab buttons, and a schema-driven
    // dropdown ("Board type") proves the FormSpec renderer is in use — the
    // legacy form had neither.
    await page.goto('./#/admin/settings')
    await expect(page.getByRole('heading', { name: 'Global Settings' })).toBeVisible({
      timeout: 10_000
    })
    await expect(page.getByRole('button', { name: 'Board defaults' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Object defaults' })).toBeVisible()
    await expect(page.getByRole('combobox', { name: 'Board type' })).toBeVisible()

    // Connections: the FormSpec view renders an add button + a connection table.
    await page.goto('./#/admin/connections')
    await expect(page.getByRole('button', { name: 'Add Connection' })).toBeVisible({
      timeout: 10_000
    })
    await expect(page.locator('table')).toBeVisible()
  })
})
