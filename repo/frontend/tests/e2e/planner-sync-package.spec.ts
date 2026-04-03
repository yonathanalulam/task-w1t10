import { readFile } from "node:fs/promises";
import { expect, test } from "@playwright/test";
import { resolveE2ECreds } from "./support/credentials";
import { loginToWorkspace } from "./support/login";

test("planner offline sync package import/export shows applied and conflict outcomes", async ({ page }) => {
  const creds = resolveE2ECreds();
  if (!creds) {
    test.skip(true, "E2E bootstrap credentials not provided");
  }
  const { orgSlug, username, password } = creds!;

  const suffix = `${Date.now()}`;
  const datasetName = `e2e-sync-dataset-${suffix}`;
  const projectName = `e2e-sync-project-${suffix}`;
  const projectCode = `E2ES-${suffix.slice(-5)}`;
  const attractionName = `Sync Attraction ${suffix}`;
  const itineraryName = `Sync Itinerary ${suffix}`;

  await loginToWorkspace(page, { orgSlug, username, password });

  await page.goto("/workspace/datasets");
  await page.getByTestId("dataset-name-input").fill(datasetName);
  await page.getByTestId("dataset-save-btn").click();
  await page.locator(".list-item", { hasText: datasetName }).getByRole("button", { name: "Manage" }).click();

  await page.getByTestId("attraction-name-input").fill(attractionName);
  await page.getByTestId("attraction-city-input").fill("Austin");
  await page.getByTestId("attraction-state-input").fill("TX");
  await page.getByTestId("attraction-latitude-input").fill("30.2672");
  await page.getByTestId("attraction-longitude-input").fill("-97.7431");
  await page.getByTestId("attraction-duration-input").fill("90");
  await page.getByTestId("attraction-save-btn").click();
  await expect(page.getByTestId("attraction-list-item")).toHaveCount(1);

  await page.goto("/workspace/projects");
  await page.getByTestId("project-name-input").fill(projectName);
  await page.getByTestId("project-code-input").fill(projectCode);
  await page.getByTestId("project-save-btn").click();
  await page.locator(".list-item", { hasText: projectName }).getByRole("button", { name: "Manage" }).click();
  await page.getByTestId("project-link-dataset-select").selectOption({ label: datasetName });
  await page.getByTestId("project-link-dataset-btn").click();
  await expect(page.locator("li.list-item strong", { hasText: datasetName })).toBeVisible();

  await page.goto("/workspace/planner");
  await page.getByTestId("planner-project-select").selectOption({ label: `${projectName} (${projectCode})` });

  await page.getByTestId("planner-itinerary-name-input").fill(itineraryName);
  await page.getByTestId("planner-itinerary-create-btn").click();
  await expect(page.getByTestId("planner-itinerary-item")).toContainText(itineraryName);

  await page.getByTestId("planner-day-add-btn").click();
  const dayCard = page.getByTestId("planner-day-card").first();
  await dayCard.locator("select").first().selectOption({ label: `${attractionName} (${datasetName})` });
  await dayCard.locator('input[type="time"]').first().fill("09:00");
  await dayCard.locator('input[type="number"]').first().fill("90");
  await dayCard.getByRole("button", { name: "Add stop" }).click();
  await expect(dayCard.getByTestId("planner-stop-row")).toHaveCount(1);

  const downloadPromise = page.waitForEvent("download");
  await page.getByTestId("planner-sync-export-btn").click();
  const download = await downloadPromise;
  const downloadPath = await download.path();
  expect(download.suggestedFilename()).toContain(".zip");
  expect(downloadPath).toBeTruthy();

  await page.getByTestId("planner-sync-import-file-input").setInputFiles(downloadPath!);
  await page.getByTestId("planner-sync-import-submit-btn").click();
  await expect(page.getByTestId("planner-sync-receipt")).toBeVisible();
  await expect(page.getByTestId("planner-sync-receipt")).toContainText("integrity=ok");
  await expect(page.getByTestId("planner-sync-receipt")).toContainText("updated=1");
  await expect(page.getByTestId("planner-sync-result-row").first()).toContainText("updated");

  await page.getByLabel("Description").fill("Conflict mutation");
  await page.getByRole("button", { name: "Save itinerary" }).click();

  const packageBytes = await readFile(downloadPath!);
  await page.getByTestId("planner-sync-import-file-input").setInputFiles({
    name: "sync-package-conflict.zip",
    mimeType: "application/zip",
    buffer: packageBytes
  });
  await page.getByTestId("planner-sync-import-submit-btn").click();
  await expect(page.getByTestId("planner-sync-receipt")).toContainText("conflicts=1");
  await expect(page.getByTestId("planner-sync-result-row").first()).toContainText("conflict");
});
