import { expect, test, type Page } from "@playwright/test";
import { resolveE2ECreds } from "./support/credentials";
import { loginToWorkspace } from "./support/login";

async function createTemplate(page: Page, params: { name: string; category: string; body: string }) {
  await page.getByRole("button", { name: "Clear" }).click();
  await page.getByTestId("message-template-name-input").fill(params.name);
  await page.getByTestId("message-template-category-input").fill(params.category);
  await page.getByTestId("message-template-body-input").fill(params.body);
  await page.getByTestId("message-template-save-btn").click();
  const templateRow = page.getByTestId("message-template-item").filter({ hasText: params.name }).first();
  await expect(templateRow).toBeVisible();
  await templateRow.getByRole("button", { name: "Use" }).click();
}

async function sendMessageAndExpectStatus(page: Page, expectedStatus: number) {
  const responsePromise = page.waitForResponse(
    (response) => response.url().includes("/message-center/send") && response.request().method() === "POST"
  );
  await page.getByTestId("message-send-btn").click();
  const response = await responsePromise;
  expect(response.status()).toBe(expectedStatus);
}

test("message center renders variables, sends in-app messages, and enforces caps", async ({ page }) => {
  const creds = resolveE2ECreds();
  if (!creds) {
    test.skip(true, "E2E bootstrap credentials not provided");
  }
  const { orgSlug, username, password } = creds!;

  const suffix = `${Date.now()}`;
  const projectName = `e2e-msg-project-${suffix}`;
  const projectCode = `E2EMC-${suffix.slice(-5)}`;
  const itineraryName = `e2e-msg-itinerary-${suffix}`;
  const recipientId = `traveler-${suffix}`;

  await loginToWorkspace(page, { orgSlug, username, password });

  await page.goto("/workspace/projects");
  await page.getByTestId("project-name-input").fill(projectName);
  await page.getByTestId("project-code-input").fill(projectCode);
  await page.getByTestId("project-save-btn").click();

  await page.goto("/workspace/planner");
  await page.getByTestId("planner-project-select").selectOption({ label: `${projectName} (${projectCode})` });
  await page.getByTestId("planner-itinerary-name-input").fill(itineraryName);
  await page.getByTestId("planner-itinerary-create-btn").click();
  await expect(page.getByTestId("planner-itinerary-item")).toContainText(itineraryName);

  await page.goto("/workspace/messages");
  await page.getByTestId("message-project-select").selectOption({ label: `${projectName} (${projectCode})` });

  await createTemplate(page, {
    name: `Template Departure ${suffix}`,
    category: "departure",
    body: "Hi {{traveler_name}}, departure at {{departure_time}}."
  });

  await page.getByTestId("message-recipient-input").fill(recipientId);
  await page.getByTestId("message-traveler-name-input").fill("Alex Traveler");
  await page.getByTestId("message-departure-time-input").fill("09:45");
  await page.getByTestId("message-itinerary-select").selectOption({ label: itineraryName });

  await page.getByTestId("message-preview-btn").click();
  await expect(page.getByTestId("message-preview-output")).toContainText("Alex Traveler");
  await expect(page.getByTestId("message-preview-output")).toContainText("09:45");

  await sendMessageAndExpectStatus(page, 200);
  await expect(page.getByTestId("message-timeline-item")).toHaveCount(1);
  await expect(page.getByTestId("message-timeline-attempt").first()).toContainText("in_app");

  await sendMessageAndExpectStatus(page, 422);
  await expect(page.locator(".error-banner")).toContainText("Hourly category cap reached");

  await createTemplate(page, {
    name: `Template Checkin ${suffix}`,
    category: "checkin",
    body: "Check-in for {{traveler_name}} at {{departure_time}}."
  });
  await sendMessageAndExpectStatus(page, 200);

  await createTemplate(page, {
    name: `Template Safety ${suffix}`,
    category: "safety",
    body: "Safety ping for {{traveler_name}} at {{departure_time}}."
  });
  await sendMessageAndExpectStatus(page, 200);

  await expect(page.getByTestId("message-timeline-item")).toHaveCount(3);

  await createTemplate(page, {
    name: `Template Daily Cap ${suffix}`,
    category: "dailycap",
    body: "Cap check for {{traveler_name}} at {{departure_time}}."
  });
  await sendMessageAndExpectStatus(page, 422);
  await expect(page.locator(".error-banner")).toContainText("Daily frequency cap reached");
  await expect(page.getByTestId("message-timeline-item")).toHaveCount(3);
});
