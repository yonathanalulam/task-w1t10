import { expect, test } from "@playwright/test";
import { resolveE2ECreds } from "./support/credentials";

test("planner import receipt handles mixed rows and export downloads csv", async ({ page }) => {
  const creds = resolveE2ECreds();
  if (!creds) {
    test.skip(true, "E2E bootstrap credentials not provided");
  }
  const { orgSlug, username, password } = creds!;

  const suffix = `${Date.now()}`;
  const datasetName = `e2e-dataset-import-${suffix}`;
  const projectName = `e2e-project-import-${suffix}`;
  const projectCode = `E2EI-${suffix.slice(-5)}`;
  const attractionName = `Import Attraction ${suffix}`;

  await page.goto("/login");
  await page.getByLabel("Organization").fill(orgSlug);
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL("**/workspace/**", { timeout: 45_000 });

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

  const itineraryName = `Import Itinerary ${suffix}`;
  await page.getByTestId("planner-itinerary-name-input").fill(itineraryName);
  await page.getByTestId("planner-itinerary-create-btn").click();
  await expect(page.getByTestId("planner-itinerary-item")).toContainText(itineraryName);

  const attractionIdMatch = await page
    .request
    .get(`/api/projects/${await page.getByTestId("planner-project-select").inputValue()}/catalog/attractions`);
  const attractionId = (await attractionIdMatch.json())[0].id as string;

  const csvImport = [
    "day_number,day_title,day_notes,day_urban_speed_mph_override,day_highway_speed_mph_override,stop_order,attraction_id,attraction_name,attraction_city,attraction_state,start_time,duration_minutes,stop_notes",
    `1,Imported Day,,25,55,1,${attractionId},${attractionName},Austin,TX,09:00,90,Valid row`,
    "1,Imported Day,,25,55,2,not-linked-id,Missing,Nowhere,NA,10:30,90,Invalid row"
  ].join("\n");

  await page.getByTestId("planner-import-file-input").setInputFiles({
    name: "planner-import.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(csvImport, "utf-8")
  });
  await page.getByTestId("planner-import-submit-btn").click();

  await expect(page.getByTestId("planner-import-receipt")).toBeVisible();
  await expect(page.getByTestId("planner-import-receipt")).toContainText("accepted=1");
  await expect(page.getByTestId("planner-import-receipt")).toContainText("rejected=1");
  await expect(page.getByTestId("planner-import-rejected-row")).toBeVisible();
  await expect(page.getByTestId("planner-import-hint").first()).toBeVisible();
  await expect(page.getByTestId("planner-day-card")).toHaveCount(1);
  await expect(page.getByTestId("planner-day-card").first().getByTestId("planner-stop-row")).toHaveCount(1);

  const downloadPromise = page.waitForEvent("download");
  await page.getByTestId("planner-export-csv-btn").click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toContain(".csv");
});
