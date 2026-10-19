import { defineConfig, devices } from "@playwright/test";

/**
 * E2E tests against a running FinAlly app (LLM_MOCK=true, fresh database).
 * Specs share one backend state, so they run serially in file order.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 30_000,
  expect: { timeout: 10_000 },
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    ...devices["Desktop Chrome"],
    baseURL: process.env.BASE_URL ?? "http://localhost:8000",
    viewport: { width: 1600, height: 1000 },
    trace: "retain-on-failure",
  },
});
