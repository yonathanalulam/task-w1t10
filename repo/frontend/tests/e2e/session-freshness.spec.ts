import { expect, test } from "@playwright/test";
import { resolveE2ECreds } from "./support/credentials";
import { loginToWorkspace } from "./support/login";

test("route guard refreshes server session state after revocation", async ({ page }) => {
  const creds = resolveE2ECreds();
  if (!creds) {
    test.skip(true, "E2E bootstrap credentials not provided");
  }
  const { orgSlug, username, password } = creds!;

  await loginToWorkspace(page, { orgSlug, username, password });
  await expect(page.getByRole("link", { name: "Planner" })).toBeVisible();

  const csrfCookie = (await page.context().cookies()).find((cookie) => cookie.name === "trailforge_csrf")?.value;
  expect(csrfCookie).toBeTruthy();

  const logoutResponse = await page.request.post("/api/auth/logout", {
    headers: {
      "X-CSRF-Token": csrfCookie!
    }
  });
  expect(logoutResponse.status()).toBe(204);

  await page.goto("/workspace/projects");
  await page.waitForURL("**/login");
  await expect(page.getByRole("heading", { name: "TrailForge" })).toBeVisible();
});
