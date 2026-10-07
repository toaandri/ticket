import { expect, test } from '@playwright/test';
import { fileURLToPath } from 'node:url';

test('shortlist, URL filters, keyboard search, themes and reduced motion', async ({ page }) => {
  const errors: string[] = []; page.on('pageerror', error => errors.push(error.message));
  await page.goto('/'); await expect(page.getByRole('heading', { name: 'Garden Sessions' })).toBeVisible();
  await page.getByRole('button', { name: 'Save Garden Sessions', exact: true }).click();
  await page.getByRole('link', { name: 'Saved', exact: true }).click(); await expect(page.getByRole('heading', { name: 'Garden Sessions' })).toBeVisible();
  await page.reload(); await expect(page.getByRole('heading', { name: 'Garden Sessions' })).toBeVisible();
  await page.getByRole('button', { name: 'Unsave Garden Sessions', exact: true }).click(); await expect(page.getByText('A good moment is worth saving.')).toBeVisible();
  await page.keyboard.press('Control+k'); await expect(page.getByRole('dialog')).toBeVisible(); await expect(page.getByLabel('Quick search events')).toBeFocused();
  await page.getByLabel('Quick search events').fill('Garden'); await page.getByRole('dialog').getByRole('link', { name: /Garden Sessions/ }).click(); await expect(page.getByRole('heading', { name: 'Garden Sessions' })).toBeVisible(); await expect(page.getByRole('dialog')).not.toBeVisible();
  await page.getByRole('link', { name: 'Discover', exact: true }).click(); await page.getByRole('button', { name: 'Technology', exact: true }).click(); await expect(page).toHaveURL(/category=Technology/); await expect(page.getByRole('heading', { name: 'Creative Futures' })).toBeVisible(); await expect(page.getByRole('heading', { name: 'Garden Sessions' })).toHaveCount(0);
  await page.getByRole('button', { name: 'Clear filters' }).click(); await page.getByRole('button', { name: 'List view' }).click(); await expect(page.getByRole('button', { name: 'List view' })).toHaveAttribute('aria-pressed', 'true');
  await page.getByRole('button', { name: 'Grid view' }).click(); await page.getByRole('button', { name: 'Switch to dark theme' }).click(); await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark'); await page.reload(); await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.getByRole('button', { name: 'Pause animations' }).click(); await expect(page.locator('.hero-art .art-ticket').last()).toHaveCSS('animation-name', 'none');
  if (process.env.CAPTURE_README === '1') { await page.setViewportSize({ width: 1440, height: 1000 }); await page.screenshot({ path: fileURLToPath(new URL('../../docs/screenshots/discovery-dark.png', import.meta.url)), fullPage: true }); }
  await page.emulateMedia({ reducedMotion: 'reduce' }); await page.getByRole('button', { name: 'Resume animations' }).click(); await expect(page.locator('.hero-art .art-ticket').last()).toHaveCSS('animation-name', 'none');
  for (const width of [320, 390, 768, 1440]) { await page.setViewportSize({ width, height: 900 }); expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `No overflow at ${width}px`).toBe(true); }
  expect(errors).toEqual([]);
});
