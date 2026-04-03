import { expect, test } from "@playwright/test";
import { resolveE2ECreds } from "./support/credentials";

test("route guard refreshes server session state after revocation", async ({ page }) => {
  const creds = resolveE2ECreds();
  if (!creds) {
    test.skip(true, "E2E bootstrap credentials not provided");
  }
  const { orgSlug, username, password } = creds!;

  await page.goto("/login");
  await page.getByLabel("Organization").fill(orgSlug);
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL("**/workspace/**", { timeout: 45_000 });
  await expect(page.getByRole("link", { name: "Planner" })).toBeVisible({ timeout: 20_000 });

  const csrfCookie = (await page.context().cookies()).find((cookie) => cookie.name === "trailforge_csrf")?.value;
  expect(csrfCookie).toBeTruthy();

  const logoutResponse = await page.request.post("/api/auth/logout", {
    headers: {
      "X-CSRF-Token": csrfCookie!
    }
  });
  expect(logoutResponse.status()).toBe(204);

  await page.goto("/workspace/projects");
  await page.waitForURL("**/login", { timeout: 20_000 });
  await expect(page.getByRole("heading", { name: "TrailForge" })).toBeVisible();
});
