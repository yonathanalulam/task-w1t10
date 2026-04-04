import { expect, type Page } from "@playwright/test";

import type { E2ECreds } from "./credentials";

const LOGIN_TIMEOUT_MS = process.env.CI ? 90_000 : 45_000;

function isApiPath(responseUrl: string, expectedPath: string): boolean {
  return new URL(responseUrl).pathname === expectedPath;
}

export async function loginToWorkspace(page: Page, creds: E2ECreds): Promise<void> {
  page.on('response', response => console.log(`[NETWORK] ${response.status()} ${response.url()}`));
  await page.goto("/login");
  await page.getByLabel("Organization").fill(creds.orgSlug);
  await page.getByLabel("Username").fill(creds.username);
  await page.getByLabel("Password").fill(creds.password);

  const loginResponsePromise = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" && isApiPath(response.url(), "/api/auth/login") && response.status() === 200,
    { timeout: LOGIN_TIMEOUT_MS }
  );
  const authMeResponsePromise = page.waitForResponse(
    (response) =>
      response.request().method() === "GET" && isApiPath(response.url(), "/api/auth/me") && response.status() === 200,
    { timeout: LOGIN_TIMEOUT_MS }
  );

  await page.getByRole("button", { name: "Sign in" }).click();
  const loginResponse = await loginResponsePromise;
  expect(loginResponse.status(), await loginResponse.text()).toBe(200);
  const authMeResponse = await authMeResponsePromise;
  expect(authMeResponse.status(), await authMeResponse.text()).toBe(200);

  await page.waitForURL("**/workspace/**", { timeout: LOGIN_TIMEOUT_MS });
  await page.waitForLoadState("networkidle", { timeout: LOGIN_TIMEOUT_MS });

  await expect.poll(() => page.url(), { timeout: Math.min(LOGIN_TIMEOUT_MS, 30_000) }).toContain("/workspace");

  const cookies = await page.context().cookies();
  expect(cookies.some((cookie) => cookie.name === "trailforge_session")).toBeTruthy();
  expect(cookies.some((cookie) => cookie.name === "trailforge_csrf")).toBeTruthy();
}
