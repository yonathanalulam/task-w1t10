import type { Page } from "@playwright/test";

import type { E2ECreds } from "./credentials";

export async function loginToWorkspace(page: Page, creds: E2ECreds): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("Organization").fill(creds.orgSlug);
  await page.getByLabel("Username").fill(creds.username);
  await page.getByLabel("Password").fill(creds.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL("**/workspace/**", { timeout: 45_000 });
  await page.waitForLoadState("networkidle");
}
