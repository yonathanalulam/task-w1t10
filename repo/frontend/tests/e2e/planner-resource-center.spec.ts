import { expect, test } from "@playwright/test";
import { resolveE2ECreds } from "./support/credentials";
import { loginToWorkspace } from "./support/login";

test("planner resource center uploads scoped assets with validation feedback", async ({ page }) => {
  const creds = resolveE2ECreds();
  if (!creds) {
    test.skip(true, "E2E bootstrap credentials not provided");
  }
  const { orgSlug, username, password } = creds!;

  const suffix = `${Date.now()}`;
  const datasetName = `e2e-media-dataset-${suffix}`;
  const projectName = `e2e-media-project-${suffix}`;
  const projectCode = `E2EM-${suffix.slice(-5)}`;
  const attractionName = `Media Attraction ${suffix}`;
  const itineraryName = `Media Itinerary ${suffix}`;

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

  await page.goto("/workspace/projects");
  await page.getByTestId("project-name-input").fill(projectName);
  await page.getByTestId("project-code-input").fill(projectCode);
  await page.getByTestId("project-save-btn").click();
  await page.locator(".list-item", { hasText: projectName }).getByRole("button", { name: "Manage" }).click();
  await page.getByTestId("project-link-dataset-select").selectOption({ label: datasetName });
  await page.getByTestId("project-link-dataset-btn").click();

  await page.goto("/workspace/planner");
  await page.getByTestId("planner-project-select").selectOption({ label: `${projectName} (${projectCode})` });
  await page.getByTestId("planner-itinerary-name-input").fill(itineraryName);
  await page.getByTestId("planner-itinerary-create-btn").click();

  await page.getByTestId("planner-resource-attraction-select").selectOption({ label: `${attractionName} (${datasetName})` });
  await page.getByTestId("planner-resource-attraction-file-input").setInputFiles({
    name: "map.png",
    mimeType: "image/png",
    buffer: Buffer.concat([Buffer.from("89504e470d0a1a0a", "hex"), Buffer.from("e2e")])
  });
  await page.getByTestId("planner-resource-attraction-upload-btn").click();
  await expect(page.getByTestId("planner-resource-attraction-validation")).toContainText("signature=ok");
  await expect(page.getByTestId("planner-resource-attraction-asset")).toHaveCount(1);

  await page.getByTestId("planner-resource-itinerary-file-input").setInputFiles({
    name: "bad.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.concat([Buffer.from("89504e470d0a1a0a", "hex"), Buffer.from("bad")])
  });
  await page.getByTestId("planner-resource-itinerary-upload-btn").click();
  await expect(page.locator(".error-banner")).toContainText("does not match detected content type");

  await page.getByTestId("planner-resource-itinerary-file-input").setInputFiles({
    name: "brief.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.7\nresource\n")
  });
  await page.getByTestId("planner-resource-itinerary-upload-btn").click();
  await expect(page.getByTestId("planner-resource-itinerary-validation")).toContainText("detected=application/pdf");
  await expect(page.getByTestId("planner-resource-itinerary-asset")).toHaveCount(1);
});
