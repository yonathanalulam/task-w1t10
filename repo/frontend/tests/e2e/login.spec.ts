import { expect, test } from "@playwright/test";

test("renders login form", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: "TrailForge" })).toBeVisible();
  await expect(page.getByLabel("Organization")).toBeVisible();
  await expect(page.getByLabel("Username")).toBeVisible();
  await expect(page.getByLabel("Password")).toBeVisible();
});
