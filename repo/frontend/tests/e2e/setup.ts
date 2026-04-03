import http from "node:http";
import https from "node:https";
import { setTimeout as sleep } from "node:timers/promises";
import { URL } from "node:url";
import type { FullConfig } from "@playwright/test";

const STARTUP_TIMEOUT_MS = Number(process.env.E2E_READY_TIMEOUT_MS ?? 90_000);
const RETRY_DELAY_MS = Number(process.env.E2E_READY_RETRY_MS ?? 1_000);
const REQUEST_TIMEOUT_MS = Number(process.env.E2E_READY_REQUEST_TIMEOUT_MS ?? 5_000);

function resolveBaseUrl(config: FullConfig): string {
  const configuredBaseUrl = config.projects[0]?.use?.baseURL;
  if (typeof configuredBaseUrl === "string" && configuredBaseUrl.length > 0) {
    return configuredBaseUrl;
  }
  return process.env.PLAYWRIGHT_BASE_URL ?? "https://localhost:5173";
}

function requestStatus(url: URL): Promise<number | null> {
  return new Promise((resolve) => {
    const transport = url.protocol === "https:" ? https : http;
    const request = transport.request(
      {
        method: "GET",
        hostname: url.hostname,
        port: url.port,
        path: `${url.pathname}${url.search}`,
        rejectUnauthorized: false,
        timeout: REQUEST_TIMEOUT_MS
      },
      (response) => {
        response.resume();
        resolve(response.statusCode ?? null);
      }
    );

    request.on("timeout", () => {
      request.destroy();
      resolve(null);
    });

    request.on("error", () => {
      resolve(null);
    });

    request.end();
  });
}

async function globalSetup(config: FullConfig): Promise<void> {
  const baseUrl = resolveBaseUrl(config);
  const readyUrl = new URL("/api/health/ready", baseUrl);
  const deadline = Date.now() + STARTUP_TIMEOUT_MS;
  let lastStatus: number | null = null;

  while (Date.now() < deadline) {
    lastStatus = await requestStatus(readyUrl);
    if (lastStatus === 200) {
      return;
    }
    await sleep(RETRY_DELAY_MS);
  }

  throw new Error(
    `Timed out waiting for backend readiness at ${readyUrl.toString()} (last status: ${lastStatus ?? "no response"}).`
  );
}

export default globalSetup;
