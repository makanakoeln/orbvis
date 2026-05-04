import { expect, test } from '@playwright/test';

const ADMIN_USER = process.env.E2E_ADMIN_USER ?? 'admin';
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? 'admin';

test.describe('OrbVis smoke', () => {
  test('login redirects to home and lists boards', async ({ page }) => {
    await page.goto('/');

    await expect(page).toHaveURL(/login/);

    await page.getByLabel(/username/i).fill(ADMIN_USER);
    await page.getByLabel(/password/i).fill(ADMIN_PASSWORD);
    await page.getByRole('button', { name: /sign in|login/i }).click();

    await expect(page).not.toHaveURL(/login/);

    await expect(page.locator('a[href*="#/boards/"], a[href*="#/maps/"]')).not.toHaveCount(0, {
      timeout: 10_000,
    });
  });

  test('open the first board renders the canvas', async ({ page }) => {
    await page.goto('/');
    await page.getByLabel(/username/i).fill(ADMIN_USER);
    await page.getByLabel(/password/i).fill(ADMIN_PASSWORD);
    await page.getByRole('button', { name: /sign in|login/i }).click();

    await expect(page).not.toHaveURL(/login/);

    const firstBoard = page.locator('a[href*="#/boards/"], a[href*="#/maps/"]').first();
    await firstBoard.click();

    await expect(page.locator('svg, .leaflet-container')).not.toHaveCount(0, {
      timeout: 10_000,
    });
  });
});
