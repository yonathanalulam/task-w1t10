import { expect, type Page } from "@playwright/test";

import type { E2ECreds } from "./credentials";

export async function loginToWorkspace(page: Page, creds: E2ECreds): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("Organization").fill(creds.orgSlug);
  await page.getByLabel("Username").fill(creds.username);
  await page.getByLabel("Password").fill(creds.password);

  const loginResponsePromise = page.waitForResponse(
    (response) => response.request().method() === "POST" && new URL(response.url()).pathname === "/api/auth/login"
  );

  await page.getByRole("button", { name: "Sign in" }).click();
  const loginResponse = await loginResponsePromise;
  expect(loginResponse.status(), await loginResponse.text()).toBe(200);

  await page.waitForURL("**/workspace/**", { timeout: 45_000 });
  await page.waitForLoadState("networkidle");

  await expect.poll(() => page.url(), { timeout: 10_000 }).toContain("/workspace");

  const cookies = await page.context().cookies();
  expect(cookies.some((cookie) => cookie.name === "trailforge_session")).toBeTruthy();
  expect(cookies.some((cookie) => cookie.name === "trailforge_csrf")).toBeTruthy();

  const authCheck = await page.evaluate(async () => {
    const response = await fetch("/api/auth/me", {
      credentials: "include"
    });
    return {
      status: response.status,
      body: await response.text()
    };
  });

  expect(authCheck.status, authCheck.body).toBe(200);
}
