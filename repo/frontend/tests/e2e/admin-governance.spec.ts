import { expect, test } from "@playwright/test";
import { resolveE2ECreds } from "./support/credentials";
import { loginToWorkspace } from "./support/login";

function isApiPath(responseUrl: string, expectedPath: string): boolean {
  return new URL(responseUrl).pathname === expectedPath;
}

test("org admin can manage datasets and projects governance", async ({ page }) => {
  const creds = resolveE2ECreds();
  if (!creds) {
    test.skip(true, "E2E bootstrap credentials not provided");
  }
  const { orgSlug, username, password } = creds!;

  const suffix = `${Date.now()}`;
  const datasetName = `e2e-dataset-${suffix}`;
  const projectName = `e2e-project-${suffix}`;
  const projectCode = `E2E-${suffix.slice(-6)}`;

  await loginToWorkspace(page, { orgSlug, username, password });

  await expect(page.getByRole("link", { name: "Datasets" })).toBeVisible();
  await page.getByRole("link", { name: "Datasets" }).click();
  await page.getByTestId("dataset-name-input").fill(datasetName);
  await page.getByTestId("dataset-save-btn").click();
  await expect(page.getByText(datasetName)).toBeVisible();

  await page.getByRole("link", { name: "Projects" }).click();
  await page.getByTestId("project-name-input").fill(projectName);
  await page.getByTestId("project-code-input").fill(projectCode);
  await page.getByTestId("project-save-btn").click();
  await expect(page.getByText(projectName)).toBeVisible();

  await page.locator(".list-item", { hasText: projectName }).getByRole("button", { name: "Manage" }).click();
  await page.getByTestId("project-link-dataset-select").selectOption({ label: datasetName });
  await page.getByTestId("project-link-dataset-btn").click();
  await expect(page.locator("li.list-item strong", { hasText: datasetName })).toBeVisible();

  const memberUserSelect = page.getByTestId("project-member-user-select");
  await memberUserSelect.selectOption({ index: 1 });
  await page.getByTestId("project-member-add-btn").click();
  await expect(page.getByText("Project membership changes require recent password step-up.")).toBeVisible();

  await page.getByTestId("projects-step-up-password-input").fill(password);
  await page.getByTestId("projects-step-up-btn").click();
  await expect(page.getByText("Step-up verified for project membership changes.")).toBeVisible();

  await page.getByTestId("project-member-add-btn").click();
  await expect(page.getByTestId("project-member-item")).toHaveCount(1);
});

test("org admin can use operations center retention and backup visibility", async ({ page }) => {
  const creds = resolveE2ECreds();
  if (!creds) {
    test.skip(true, "E2E bootstrap credentials not provided");
  }
  const { orgSlug, username, password } = creds!;

  await loginToWorkspace(page, { orgSlug, username, password });

  await page.goto("/workspace/operations");
  await page.getByTestId("ops-step-up-password-input").fill(password);
  await page.getByTestId("ops-step-up-btn").click();
  await expect(page.getByText("Step-up verified", { exact: false })).toBeVisible();

  await page.getByTestId("ops-retention-days-input").fill("1201");
  await page.getByTestId("ops-retention-save-btn").click();
  await expect(page.getByText("Retention policy updated.")).toBeVisible();

  const backupResponsePromise = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" && isApiPath(response.url(), "/api/ops/backups/run") && response.status() === 200
  );
  await page.getByTestId("ops-backup-run-btn").click();
  const backupResponse = await backupResponsePromise;
  const backupPayload = await backupResponse.json();
  const backupFileName = String(backupPayload.backup_file_name ?? "");
  expect(backupFileName).toContain("trailforge-");
  await expect(page.getByTestId("ops-backup-run-item").filter({ hasText: backupFileName }).first()).toBeVisible();

  const restoreSelect = page.getByTestId("ops-restore-file-select");
  await expect(restoreSelect).toBeVisible();
  await expect(restoreSelect.locator(`option[value="${backupFileName}"]`)).toHaveCount(1);
  await restoreSelect.selectOption(backupFileName);

  const restoreResponsePromise = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" && isApiPath(response.url(), "/api/ops/restore") && response.status() === 200
  );
  await page.getByTestId("ops-restore-run-btn").click();
  const restoreResponse = await restoreResponsePromise;
  const restorePayload = await restoreResponse.json();
  expect(restorePayload.status).toBe("succeeded");
  await loginToWorkspace(page, { orgSlug, username, password });
  await page.goto("/workspace/operations");
  await expect(page.getByTestId("ops-restore-run-item").filter({ hasText: backupFileName }).first()).toContainText("succeeded");

  await expect(page.getByTestId("ops-audit-event-item").filter({ hasText: "operations." }).first()).toBeVisible();
});
