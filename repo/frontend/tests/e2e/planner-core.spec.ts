import { expect, test } from "@playwright/test";
import { resolveE2ECreds } from "./support/credentials";

test("planner UI supports itinerary day/stop flow with warnings and reorder autosave", async ({ page }) => {
  const creds = resolveE2ECreds();
  if (!creds) {
    test.skip(true, "E2E bootstrap credentials not provided");
  }
  const { orgSlug, username, password } = creds!;

  const suffix = `${Date.now()}`;
  const datasetName = `e2e-dataset-planner-${suffix}`;
  const projectName = `e2e-project-planner-${suffix}`;
  const projectCode = `E2EP-${suffix.slice(-5)}`;
  const attractionAName = `Planner Museum ${suffix}`;
  const attractionBName = `Planner Riverwalk ${suffix}`;

  await page.goto("/login");
  await page.getByLabel("Organization").fill(orgSlug);
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL("**/workspace/**", { timeout: 45_000 });

  await page.goto("/workspace/datasets");
  await page.waitForURL("**/workspace/datasets");
  await page.getByTestId("dataset-name-input").fill(datasetName);
  await page.getByTestId("dataset-save-btn").click();
  await expect(page.getByText(datasetName)).toBeVisible();

  await page.locator(".list-item", { hasText: datasetName }).getByRole("button", { name: "Manage" }).click();
  await page.getByTestId("attraction-name-input").fill(attractionAName);
  await page.getByTestId("attraction-city-input").fill("Austin");
  await page.getByTestId("attraction-state-input").fill("TX");
  await page.getByTestId("attraction-latitude-input").fill("30.2672");
  await page.getByTestId("attraction-longitude-input").fill("-97.7431");
  await page.getByTestId("attraction-duration-input").fill("90");
  await page.getByTestId("attraction-save-btn").click();
  await expect(page.getByTestId("attraction-list-item")).toHaveCount(1);

  await page.getByTestId("attraction-name-input").fill(attractionBName);
  await page.getByTestId("attraction-city-input").fill("San Antonio");
  await page.getByTestId("attraction-state-input").fill("TX");
  await page.getByTestId("attraction-latitude-input").fill("29.4241");
  await page.getByTestId("attraction-longitude-input").fill("-98.4936");
  await page.getByTestId("attraction-duration-input").fill("120");
  await page.getByTestId("attraction-save-btn").click();
  await expect(page.getByTestId("attraction-list-item")).toHaveCount(2);

  await page.goto("/workspace/projects");
  await page.waitForURL("**/workspace/projects");
  await page.getByTestId("project-name-input").fill(projectName);
  await page.getByTestId("project-code-input").fill(projectCode);
  await page.getByTestId("project-save-btn").click();
  await page.locator(".list-item", { hasText: projectName }).getByRole("button", { name: "Manage" }).click();
  await page.getByTestId("project-link-dataset-select").selectOption({ label: datasetName });
  await page.getByTestId("project-link-dataset-btn").click();
  await expect(page.locator("li.list-item strong", { hasText: datasetName })).toBeVisible();

  await page.goto("/workspace/planner");
  await page.waitForURL("**/workspace/planner");
  await page.getByTestId("planner-project-select").selectOption({ label: `${projectName} (${projectCode})` });

  await page.getByTestId("planner-itinerary-name-input").fill(`Planner Itinerary ${suffix}`);
  await page.getByTestId("planner-itinerary-create-btn").click();
  await expect(page.getByTestId("planner-itinerary-item")).toContainText(`Planner Itinerary ${suffix}`);

  await page.getByTestId("planner-day-add-btn").click();
  await expect(page.getByTestId("planner-day-card")).toHaveCount(1);

  const dayCard = page.getByTestId("planner-day-card").first();
  await dayCard.locator("select").first().selectOption({ label: `${attractionAName} (${datasetName})` });
  await dayCard.locator('input[type="time"]').first().fill("09:00");
  await dayCard.locator('input[type="number"]').first().fill("90");
  await dayCard.getByRole("button", { name: "Add stop" }).click();
  await expect(dayCard.getByTestId("planner-stop-row")).toHaveCount(1);

  await dayCard.locator("select").first().selectOption({ label: `${attractionBName} (${datasetName})` });
  await dayCard.locator('input[type="time"]').first().fill("10:00");
  await dayCard.locator('input[type="number"]').first().fill("120");
  await dayCard.getByRole("button", { name: "Add stop" }).click();

  await expect(dayCard.getByTestId("planner-stop-row")).toHaveCount(2);
  await expect(dayCard.getByTestId("planner-warning")).toContainText("overlaps");

  const stops = dayCard.getByTestId("planner-stop-row");
  await stops.nth(1).dragTo(stops.nth(0));
  await expect(dayCard.getByTestId("planner-stop-row").first()).toContainText(attractionBName);
  await expect(dayCard.getByTestId("planner-day-save-state")).not.toContainText("Save failed");

  await expect(page.getByTestId("planner-version-item").first()).toContainText("reordered");
});
