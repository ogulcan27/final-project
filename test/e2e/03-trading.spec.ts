import { expect, test } from "@playwright/test";
import { openApp, readMoney, trade } from "./helpers";

test("buy shares: cash decreases and position appears", async ({ page }) => {
  await openApp(page);
  const cashBefore = await readMoney(page, "cash-balance");

  await trade(page, "NVDA", 5, "buy");

  const row = page.getByTestId("position-row-NVDA");
  await expect(row).toBeVisible();
  await expect(row).toContainText("5");
  await expect.poll(() => readMoney(page, "cash-balance")).toBeLessThan(cashBefore);
});

test("sell shares: cash increases, position shrinks then disappears", async ({ page }) => {
  await openApp(page);
  await expect(page.getByTestId("position-row-NVDA")).toBeVisible();
  const cashBefore = await readMoney(page, "cash-balance");

  await trade(page, "NVDA", 2, "sell");
  await expect.poll(() => readMoney(page, "cash-balance")).toBeGreaterThan(cashBefore);
  await expect(page.getByTestId("position-row-NVDA")).toContainText("3");

  await trade(page, "NVDA", 3, "sell");
  await expect(page.getByTestId("position-row-NVDA")).toHaveCount(0);
});

test("selling more than owned is rejected by the API", async ({ request }) => {
  const res = await request.post("/api/portfolio/trade", { data: { ticker: "NVDA", quantity: 1000, side: "sell" } });
  expect(res.status()).toBe(400);
  expect((await res.json()).detail).toBeTruthy();
});
