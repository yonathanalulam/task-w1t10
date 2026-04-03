import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  globalSetup: "./tests/e2e/setup.ts",
  workers: 1,
  timeout: 60_000,
  expect: {
    timeout: 20_000
  },
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "https://localhost:5173",
    ignoreHTTPSErrors: true,
    trace: "retain-on-failure"
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] }
    }
  ]
});
