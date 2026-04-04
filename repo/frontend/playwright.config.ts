import { defineConfig, devices } from "@playwright/test";

const isCI = Boolean(process.env.CI);

export default defineConfig({
  testDir: "./tests/e2e",
  globalSetup: "./tests/e2e/setup.ts",
  workers: 1,
  timeout: isCI ? 120_000 : 60_000,
  expect: {
    timeout: isCI ? 45_000 : 20_000
  },
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "https://localhost:5173",
    ignoreHTTPSErrors: true,
    trace: "retain-on-failure"
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        ignoreHTTPSErrors: true
      }
    }
  ]
});
