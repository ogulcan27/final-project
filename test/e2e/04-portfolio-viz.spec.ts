import { expect, test } from "@playwright/test";
import { openApp, trade } from "./helpers";

test("heatmap and P&L chart render after a trade", async ({ page, request }) => {
  await openApp(page);
  await trade(page, "MSFT", 2, "buy");
  await expect(page.getByTestId("position-row-MSFT")).toBeVisible();

  const heatmap = page.getByTestId("heatmap");
  await expect(heatmap).toBeVisible();
  await expect(heatmap).toContainText("MSFT");

  await expect(page.getByTestId("pnl-chart")).toBeVisible();
  const history = await (await request.get("/api/portfolio/history")).json();
  expect(history.length).toBeGreaterThan(0);
  expect(history[0]).toHaveProperty("total_value");
});
