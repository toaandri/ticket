import { expect, test, type Page } from '@playwright/test';
import { randomUUID } from 'node:crypto';

async function reserve(page: Page) {
  await page.goto('/account'); await page.getByLabel('Email', { exact: true }).fill('demo-attendee@ticket.example'); await page.getByLabel('Password', { exact: true }).fill(process.env.DEMO_PASSWORD ?? 'synthetic-demo-password-94!'); await page.getByRole('button', { name: 'Sign in', exact: true }).click(); await expect(page.getByRole('heading', { name: 'Hello, Synthetic Attendee.' })).toBeVisible();
  await page.getByRole('link', { name: 'Discover', exact: true }).click(); await page.locator('.event-card').getByRole('link', { name: 'Garden Sessions', exact: true }).click(); await page.getByLabel('Quantity').fill('1'); await page.getByRole('button', { name: 'Hold selected tickets ↗' }).click(); await expect(page.getByText(/Held for/)).toBeVisible();
}
test('pending order automatically receives a server-confirmed payment outcome', async ({ page }) => {
  await reserve(page); const checkoutResponse = page.waitForResponse(response => /\/api\/v1\/orders\/$/.test(response.url()) && response.request().method() === 'POST'); await page.getByRole('button', { name: 'Continue to checkout' }).click(); const order = await (await checkoutResponse).json();
  await page.getByLabel('Demo scenario').selectOption('pending'); const paymentResponse = page.waitForResponse(response => response.url().endsWith('/payments/') && response.request().method() === 'POST'); await page.getByRole('button', { name: /Pay .* in test mode/ }).click(); const response = await paymentResponse; const payment = await response.json(); await expect(page.getByText(/Payment pending. Checking its status automatically/)).toBeVisible();
  // Complete through the server, not the UI control: only polling can update the page.
  const completion = await page.request.post(`/api/v1/orders/${order.id}/simulate-payment/`, { headers: { Authorization: response.request().headers().authorization, 'Idempotency-Key': randomUUID() }, data: { payment_id: payment.id, outcome: 'SUCCEEDED' } }); expect(completion.ok()).toBe(true);
  await expect(page.getByRole('heading', { name: 'You’re going!' })).toBeVisible({ timeout: 10000 });
});
test('declined payment releases inventory and offers a fresh reservation', async ({ page }) => {
  await reserve(page); await page.getByRole('button', { name: 'Continue to checkout' }).click(); await page.getByLabel('Demo scenario').selectOption('decline'); await page.getByRole('button', { name: /Pay .* in test mode/ }).click(); await expect(page.getByRole('heading', { name: 'Payment declined' })).toBeVisible(); await page.getByRole('button', { name: 'Choose again' }).click(); await expect(page.getByLabel('Quantity')).toBeVisible(); await page.getByRole('button', { name: 'Hold selected tickets ↗' }).click(); await expect(page.getByText(/Held for/)).toBeVisible(); await page.getByRole('button', { name: 'Release tickets and start again' }).click(); await expect(page.getByLabel('Quantity')).toBeVisible();
});
