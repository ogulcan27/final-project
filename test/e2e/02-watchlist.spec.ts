import { expect, test } from "@playwright/test";
import { openApp } from "./helpers";

test("add and remove a ticker from the watchlist", async ({ page }) => {
  await openApp(page);

  await page.getByTestId("watchlist-add-input").fill("IBM");
  await page.getByTestId("watchlist-add-button").click();
  await expect(page.getByTestId("watchlist-row-IBM")).toBeVisible();
  await expect(page.getByTestId("price-IBM")).toHaveText(/\d+\.\d{2}/);

  await page.reload();
  await expect(page.getByTestId("watchlist-row-IBM")).toBeVisible();

  await page.getByTestId("watchlist-remove-IBM").click();
  await expect(page.getByTestId("watchlist-row-IBM")).toHaveCount(0);

  await page.reload();
  await expect(page.getByTestId("watchlist-row-AAPL")).toBeVisible();
  await expect(page.getByTestId("watchlist-row-IBM")).toHaveCount(0);
});
