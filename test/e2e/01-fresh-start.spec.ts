import { expect, test } from "@playwright/test";
import { DEFAULT_TICKERS, openApp } from "./helpers";

test("health endpoint responds", async ({ request }) => {
  const res = await request.get("/api/health");
  expect(res.ok()).toBeTruthy();
  expect(await res.json()).toEqual({ status: "ok" });
});

test("fresh start shows default watchlist, $10k cash and streaming prices", async ({ page }) => {
  await openApp(page);

  for (const ticker of DEFAULT_TICKERS) {
    await expect(page.getByTestId(`watchlist-row-${ticker}`)).toBeVisible();
  }
  await expect(page.getByTestId("cash-balance")).toContainText("10,000");
  await expect(page.getByTestId("total-value")).toContainText("10,000");
  await expect(page.getByTestId("connection-status")).toHaveAttribute("data-status", "connected");

  const prices = page.getByTestId(/^price-/);
  const first = (await prices.allTextContents()).join("|");
  await expect.poll(async () => (await prices.allTextContents()).join("|")).not.toBe(first);
});

test("clicking a ticker shows it in the main chart", async ({ page }) => {
  await openApp(page);
  await page.getByTestId("watchlist-row-MSFT").click();
  const chart = page.getByTestId("main-chart");
  await expect(chart).toBeVisible();
  await expect(chart.locator("canvas").first()).toBeVisible();
  const panel = page.locator("section").filter({ has: chart });
  await expect(panel.getByRole("heading")).toHaveText("MSFT");
});
