import { expect, Page } from "@playwright/test";

export const DEFAULT_TICKERS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"];

/** Parse a displayed dollar amount like "$10,000.00" into a number. */
export function parseMoney(text: string | null): number {
  return Number((text ?? "").replace(/[^0-9.-]/g, ""));
}

/** Open the app and wait until the price stream has delivered a price for AAPL. */
export async function openApp(page: Page) {
  await page.goto("/");
  await expect(page.getByTestId("price-AAPL")).toHaveText(/\d+\.\d{2}/);
}

/** Read a dollar amount shown by the element with the given test id. */
export async function readMoney(page: Page, testId: string): Promise<number> {
  return parseMoney(await page.getByTestId(testId).textContent());
}

/** Submit a market order through the trade bar. */
export async function trade(page: Page, ticker: string, quantity: number, side: "buy" | "sell") {
  await page.getByTestId("trade-ticker").fill(ticker);
  await page.getByTestId("trade-quantity").fill(String(quantity));
  await page.getByTestId(`trade-${side}`).click();
}
