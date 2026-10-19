import { expect, test } from "@playwright/test";

/**
 * Chromium's offline emulation does not close an already-open EventSource,
 * so the outage is simulated by failing stream requests at the network layer.
 */
test("price stream reconnects after the stream becomes reachable again", async ({ page }) => {
  await page.route("**/api/stream/prices", (route) => route.abort("connectionreset"));
  await page.goto("/");

  const status = page.getByTestId("connection-status");
  await expect(status).not.toHaveAttribute("data-status", "connected");
  await page.waitForTimeout(2_000);
  await expect(status).not.toHaveAttribute("data-status", "connected");

  await page.unroute("**/api/stream/prices");
  await expect(status).toHaveAttribute("data-status", "connected", { timeout: 15_000 });

  const price = page.getByTestId("price-AAPL");
  await expect(price).toHaveText(/\d+\.\d{2}/);
  const before = await price.textContent();
  await expect.poll(() => price.textContent(), { timeout: 15_000 }).not.toBe(before);
});
