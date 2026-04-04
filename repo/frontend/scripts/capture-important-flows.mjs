import { execSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

import { chromium, expect } from "@playwright/test";

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL ?? "https://localhost:5173";
const REPO_ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), "../..");
const OUTPUT_PATH = process.argv[2]
  ? path.resolve(process.argv[2])
  : "/home/yonim/trailForge/submission/trailforge-important-flows.webm";

const tempVideoDir = path.resolve(REPO_ROOT, "frontend", ".playwright-video-temp");

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function parseCredsText(raw) {
  const parsed = Object.fromEntries(
    raw
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter((line) => line.includes("="))
      .map((line) => {
        const [key, ...rest] = line.split("=");
        return [key, rest.join("=")];
      })
  );

  const orgSlug = parsed.org_slug;
  const username = parsed.username;
  const password = parsed.password;
  if (!orgSlug || !username || !password) {
    return null;
  }
  return { orgSlug, username, password };
}

function readCredsFile(filePath) {
  if (!filePath || !fs.existsSync(filePath)) {
    return null;
  }

  try {
    return parseCredsText(fs.readFileSync(filePath, "utf-8"));
  } catch {
    return null;
  }
}

function resolveCreds() {
  if (process.env.E2E_ORG_SLUG && process.env.E2E_USERNAME && process.env.E2E_PASSWORD) {
    return {
      orgSlug: process.env.E2E_ORG_SLUG,
      username: process.env.E2E_USERNAME,
      password: process.env.E2E_PASSWORD
    };
  }

  const candidates = [
    process.env.E2E_BOOTSTRAP_CREDS_FILE,
    "/bootstrap/admin_credentials.txt",
    "/tmp/trailforge-e2e-runtime/bootstrap/admin_credentials.txt"
  ].filter(Boolean);

  for (const candidate of candidates) {
    const creds = readCredsFile(candidate);
    if (creds) {
      return creds;
    }
  }

  try {
    const output = execSync("docker compose exec -T backend cat /bootstrap/admin_credentials.txt", {
      cwd: REPO_ROOT,
      stdio: ["ignore", "pipe", "ignore"],
      encoding: "utf-8"
    });
    const creds = parseCredsText(output);
    if (creds) {
      return creds;
    }
  } catch {
    // ignore and throw below
  }

  throw new Error("Unable to resolve runtime credentials for video capture");
}

async function humanType(locator, text) {
  await locator.click({ delay: 120 });
  await sleep(220);
  await locator.fill("");
  for (const char of text) {
    await locator.type(char, { delay: 95 });
  }
  await sleep(260);
}

async function humanClick(page, locator, mouseState, opts = {}) {
  const preDelay = opts.preDelay ?? 300;
  const postDelay = opts.postDelay ?? 700;
  const box = await locator.boundingBox();

  if (!box) {
    await locator.scrollIntoViewIfNeeded();
  }
  const finalBox = box ?? (await locator.boundingBox());
  if (!finalBox) {
    throw new Error("Unable to compute click target bounding box");
  }

  const targetX = finalBox.x + finalBox.width / 2;
  const targetY = finalBox.y + finalBox.height / 2;

  await sleep(preDelay);
  await page.mouse.move(targetX, targetY, { steps: 32 });
  mouseState.x = targetX;
  mouseState.y = targetY;
  await sleep(120);
  await page.mouse.down();
  await sleep(110);
  await page.mouse.up();
  await sleep(postDelay);
}

async function smoothWheel(page, pixels, waitMs = 130, step = 120) {
  const direction = Math.sign(pixels);
  const total = Math.abs(pixels);
  let covered = 0;
  while (covered < total) {
    await page.mouse.wheel(0, direction * step);
    covered += step;
    await sleep(waitMs);
  }
}

async function humanDrag(page, sourceLocator, targetLocator, mouseState) {
  const source = await sourceLocator.boundingBox();
  const target = await targetLocator.boundingBox();
  if (!source || !target) {
    throw new Error("Unable to compute drag bounding boxes");
  }

  const sourceX = source.x + source.width / 2;
  const sourceY = source.y + source.height / 2;
  const targetX = target.x + target.width / 2;
  const targetY = target.y + target.height / 2;

  await page.mouse.move(sourceX, sourceY, { steps: 28 });
  mouseState.x = sourceX;
  mouseState.y = sourceY;
  await sleep(200);
  await page.mouse.down();
  await sleep(260);
  await page.mouse.move(targetX, targetY, { steps: 42 });
  mouseState.x = targetX;
  mouseState.y = targetY;
  await sleep(180);
  await page.mouse.up();
  await sleep(900);
}

async function run() {
  const creds = resolveCreds();
  const suffix = `${Date.now()}`;
  const datasetName = `review-dataset-${suffix}`;
  const projectName = `review-project-${suffix}`;
  const projectCode = `RVW-${suffix.slice(-5)}`;
  const itineraryName = `Important Flows ${suffix.slice(-4)}`;
  const attractionAName = `City Museum ${suffix.slice(-4)}`;
  const attractionBName = `River Walk ${suffix.slice(-4)}`;

  fs.mkdirSync(tempVideoDir, { recursive: true });
  fs.mkdirSync(path.dirname(OUTPUT_PATH), { recursive: true });

  const browser = await chromium.launch({ headless: true, slowMo: 80 });
  const context = await browser.newContext({
    baseURL: BASE_URL,
    ignoreHTTPSErrors: true,
    viewport: { width: 1600, height: 900 },
    recordVideo: {
      dir: tempVideoDir,
      size: { width: 1600, height: 900 }
    }
  });

  const page = await context.newPage();
  const recordedVideo = page.video();
  const mouseState = { x: 80, y: 80 };

  await page.mouse.move(mouseState.x, mouseState.y);
  await page.goto("/login", { waitUntil: "networkidle" });
  await expect(page.getByRole("heading", { name: "TrailForge" })).toBeVisible();
  await sleep(1300);

  await humanType(page.getByLabel("Organization"), creds.orgSlug);
  await humanType(page.getByLabel("Username"), creds.username);
  await humanType(page.getByLabel("Password"), creds.password);

  await Promise.all([
    page.waitForURL("**/workspace/**", { timeout: 45_000 }),
    humanClick(page, page.getByRole("button", { name: "Sign in" }), mouseState)
  ]);
  await sleep(1800);

  await humanClick(page, page.getByRole("link", { name: "Datasets" }), mouseState);
  await expect(page.getByRole("heading", { name: "Datasets" })).toBeVisible();
  await sleep(900);

  await humanType(page.getByTestId("dataset-name-input"), datasetName);
  await humanClick(page, page.getByTestId("dataset-save-btn"), mouseState);
  await expect(page.getByText(datasetName)).toBeVisible();
  await sleep(900);

  await humanClick(page, page.locator(".list-item", { hasText: datasetName }).getByRole("button", { name: "Manage" }), mouseState);
  await sleep(800);

  await humanType(page.getByTestId("attraction-name-input"), attractionAName);
  await humanType(page.getByTestId("attraction-city-input"), "Austin");
  await humanType(page.getByTestId("attraction-state-input"), "TX");
  await humanType(page.getByTestId("attraction-latitude-input"), "30.2672");
  await humanType(page.getByTestId("attraction-longitude-input"), "-97.7431");
  await humanType(page.getByTestId("attraction-duration-input"), "90");
  await humanClick(page, page.getByTestId("attraction-save-btn"), mouseState);
  await expect(page.getByTestId("attraction-list-item")).toHaveCount(1, { timeout: 20_000 });
  await sleep(700);

  await humanType(page.getByTestId("attraction-name-input"), attractionBName);
  await humanType(page.getByTestId("attraction-city-input"), "San Antonio");
  await humanType(page.getByTestId("attraction-state-input"), "TX");
  await humanType(page.getByTestId("attraction-latitude-input"), "29.4241");
  await humanType(page.getByTestId("attraction-longitude-input"), "-98.4936");
  await humanType(page.getByTestId("attraction-duration-input"), "120");
  await humanClick(page, page.getByTestId("attraction-save-btn"), mouseState);
  await expect(page.getByTestId("attraction-list-item")).toHaveCount(2, { timeout: 20_000 });
  await sleep(1300);

  await humanClick(page, page.getByRole("link", { name: "Projects" }), mouseState);
  await expect(page.getByRole("heading", { name: "Projects" })).toBeVisible();
  await sleep(900);

  await humanType(page.getByTestId("project-name-input"), projectName);
  await humanType(page.getByTestId("project-code-input"), projectCode);
  await humanClick(page, page.getByTestId("project-save-btn"), mouseState);
  await expect(page.locator(".list-item", { hasText: projectName })).toBeVisible();
  await sleep(800);

  await humanClick(page, page.locator(".list-item", { hasText: projectName }).getByRole("button", { name: "Manage" }), mouseState);
  await sleep(900);

  await page.getByTestId("project-link-dataset-select").selectOption({ label: datasetName });
  await sleep(550);
  await humanClick(page, page.getByTestId("project-link-dataset-btn"), mouseState);
  await expect(page.locator("li.list-item strong", { hasText: datasetName })).toBeVisible();
  await sleep(800);

  await page.getByTestId("project-member-user-select").selectOption({ index: 1 });
  await sleep(500);
  await humanClick(page, page.getByTestId("project-member-add-btn"), mouseState);
  await expect(page.getByText("Project membership changes require recent password step-up.")).toBeVisible();
  await sleep(1000);

  await humanType(page.getByTestId("projects-step-up-password-input"), creds.password);
  await humanClick(page, page.getByTestId("projects-step-up-btn"), mouseState);
  await expect(page.getByText("Step-up verified for project membership changes.")).toBeVisible();
  await sleep(1500);

  await humanClick(page, page.getByRole("link", { name: "Planner" }), mouseState);
  await page.waitForURL("**/workspace/planner", { timeout: 45_000 });
  await expect(page.getByRole("heading", { name: "Planner" })).toBeVisible();
  await sleep(1400);

  await page.getByTestId("planner-project-select").selectOption({ label: `${projectName} (${projectCode})` });
  await sleep(1700);

  await humanType(page.getByTestId("planner-itinerary-name-input"), itineraryName);
  await humanClick(page, page.getByTestId("planner-itinerary-create-btn"), mouseState);
  await expect(page.getByTestId("planner-itinerary-item").filter({ hasText: itineraryName })).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("planner-day-add-btn")).toBeVisible();
  await sleep(1200);

  await humanClick(page, page.getByTestId("planner-day-add-btn"), mouseState);
  await expect(page.getByTestId("planner-day-card")).toHaveCount(1, { timeout: 20_000 });
  await sleep(1000);

  const dayCard = page.getByTestId("planner-day-card").first();
  await dayCard.locator("select").first().selectOption({ label: `${attractionAName} (${datasetName})` });
  await sleep(400);
  await dayCard.locator('input[type="time"]').first().fill("09:00");
  await sleep(300);
  await dayCard.locator('input[type="number"]').first().fill("90");
  await sleep(350);
  await humanClick(page, dayCard.getByRole("button", { name: "Add stop" }), mouseState);
  await expect(dayCard.getByTestId("planner-stop-row")).toHaveCount(1, { timeout: 20_000 });
  await sleep(900);

  await dayCard.locator("select").first().selectOption({ label: `${attractionBName} (${datasetName})` });
  await sleep(380);
  await dayCard.locator('input[type="time"]').first().fill("10:00");
  await sleep(300);
  await dayCard.locator('input[type="number"]').first().fill("120");
  await sleep(350);
  await humanClick(page, dayCard.getByRole("button", { name: "Add stop" }), mouseState);
  await expect(dayCard.getByTestId("planner-stop-row")).toHaveCount(2, { timeout: 20_000 });
  await expect(dayCard.getByTestId("planner-warning")).toContainText("overlaps", { timeout: 20_000 });
  await sleep(1500);

  const stops = dayCard.getByTestId("planner-stop-row");
  await humanDrag(page, stops.nth(1), stops.nth(0), mouseState);
  await expect(dayCard.getByTestId("planner-stop-row").first()).toContainText(attractionBName, { timeout: 20_000 });
  await expect(dayCard.getByTestId("planner-day-save-state")).not.toContainText("Save failed");
  await sleep(1300);

  await smoothWheel(page, 900, 140, 110);
  await sleep(1000);
  await expect(page.getByTestId("planner-version-item").first()).toContainText(/reordered/i, { timeout: 20_000 });
  await sleep(1700);

  await humanClick(page, page.getByRole("link", { name: "Operations" }), mouseState);
  await page.waitForURL("**/workspace/operations", { timeout: 45_000 });
  await expect(page.getByRole("heading", { name: "Organization Operations Center" })).toBeVisible();
  await sleep(1200);

  await smoothWheel(page, 1800, 160, 100);
  await expect(page.getByTestId("ops-audit-event-item").first()).toBeVisible();
  await sleep(1400);
  await smoothWheel(page, 1000, 150, 95);
  await sleep(1100);
  await smoothWheel(page, -2600, 120, 85);
  await sleep(2000);

  await context.close();
  await browser.close();

  const rawVideoPath = await recordedVideo.path();
  fs.copyFileSync(rawVideoPath, OUTPUT_PATH);

  console.log(`Video saved to ${OUTPUT_PATH}`);
}

run().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
