import { expect, test } from "@playwright/test";
import { resolveE2ECreds } from "./support/credentials";

test("org admin can review and merge duplicate attractions", async ({ page }) => {
  const creds = resolveE2ECreds();
  if (!creds) {
    test.skip(true, "E2E bootstrap credentials not provided");
  }
  const { orgSlug, username, password } = creds!;

  const suffix = `${Date.now()}`;
  const datasetName = `e2e-dataset-attractions-${suffix}`;

  await page.goto("/login");
  await page.getByLabel("Organization").fill(orgSlug);
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL("**/workspace/**", { timeout: 45_000 });

  await expect(page.getByRole("link", { name: "Datasets" })).toBeVisible({ timeout: 20_000 });
  await page.getByRole("link", { name: "Datasets" }).click();
  await page.getByTestId("dataset-name-input").fill(datasetName);
  await page.getByTestId("dataset-save-btn").click();
  await expect(page.getByText(datasetName)).toBeVisible();

  await page.locator(".list-item", { hasText: datasetName }).getByRole("button", { name: "Manage" }).click();
  await expect(page.getByText(`Selected dataset: ${datasetName}`)).toBeVisible();

  const createAttractionViaUi = async (
    payload: {
      name: string;
      city: string;
      state: string;
      latitude: string;
      longitude: string;
      duration: string;
    },
    expectedCount: number
  ) => {
    await page.getByTestId("attraction-name-input").fill(payload.name);
    await page.getByTestId("attraction-city-input").fill(payload.city);
    await page.getByTestId("attraction-state-input").fill(payload.state);
    await page.getByTestId("attraction-latitude-input").fill(payload.latitude);
    await page.getByTestId("attraction-longitude-input").fill(payload.longitude);
    await page.getByTestId("attraction-duration-input").fill(payload.duration);

    await expect(page.getByTestId("attraction-save-btn")).toBeEnabled();
    await page.getByTestId("attraction-save-btn").click();

    await expect(page.locator(".error-banner")).toHaveCount(0);
    await expect(page.getByTestId("attraction-list-item")).toHaveCount(expectedCount, { timeout: 20_000 });
  };

  await createAttractionViaUi({
    name: "Museum of Records",
    city: "Austin",
    state: "TX",
    latitude: "30",
    longitude: "-97",
    duration: "90"
  }, 1);

  await createAttractionViaUi({
    name: "museum of records!!!",
    city: "AUSTIN",
    state: "tx",
    latitude: "30.1",
    longitude: "-97.1",
    duration: "80"
  }, 2);

  await expect(page.getByTestId("duplicate-group")).toBeVisible({ timeout: 20_000 });
  await page.getByTestId("duplicate-target-select-0").selectOption({ index: 0 });
  await page.getByTestId("duplicate-source-select-0").selectOption({ index: 1 });
  await page.getByTestId("duplicate-merge-btn-0").click();

  await expect(page.getByText("Attraction merge requires recent password step-up.")).toBeVisible();

  await page.getByTestId("datasets-step-up-password-input").fill(password);
  await page.getByTestId("datasets-step-up-btn").click();
  await expect(page.getByText("Step-up verified for attraction merge.")).toBeVisible();

  await page.getByTestId("duplicate-merge-btn-0").click();

  await expect(page.getByTestId("duplicate-groups-empty")).toBeVisible();
});
