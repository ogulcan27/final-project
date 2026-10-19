import { expect, test } from "@playwright/test";
import { openApp } from "./helpers";

test("AI chat (mock) buys AAPL and shows the trade inline", async ({ page }) => {
  await openApp(page);

  await page.getByTestId("chat-input").fill("Please buy some Apple");
  await page.getByTestId("chat-send").click();

  const last = page.getByTestId("chat-message").last();
  await expect(last).toContainText("AAPL");
  await expect(last).toContainText(/buy/i);
  await expect(page.getByTestId("chat-loading")).toHaveCount(0);
  await expect(page.getByTestId("position-row-AAPL")).toBeVisible();
});

test("AI chat (mock) plain message gets a mock response", async ({ page }) => {
  await openApp(page);
  await page.getByTestId("chat-input").fill("hello there");
  await page.getByTestId("chat-send").click();
  await expect(page.getByTestId("chat-message").last()).toContainText("Mock response");
});
