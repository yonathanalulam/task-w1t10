import { expect, test } from "@playwright/test";
import { resolveE2ECreds } from "./support/credentials";
import { loginToWorkspace } from "./support/login";

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

  await expect(page.getByRole("link", { name: "Datasets" })).toBeVisible({ timeout: 20_000 });
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

  await page.getByTestId("ops-backup-run-btn").click();
  await expect(page.getByTestId("ops-backup-run-item").first()).toContainText("trailforge-");

  const restoreSelect = page.getByTestId("ops-restore-file-select");
  await expect(restoreSelect).toBeVisible();
  await expect(restoreSelect.locator("option")).toHaveCount(2);
  await restoreSelect.selectOption({ index: 1 });
  await page.getByTestId("ops-restore-run-btn").click();
  await expect(page.getByTestId("ops-restore-run-item").first()).toContainText("succeeded");

  await expect(page.getByTestId("ops-audit-event-item").first()).toContainText("operations.");
});
