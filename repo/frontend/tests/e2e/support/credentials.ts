import { execFileSync, execSync } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export type E2ECreds = {
  orgSlug: string;
  username: string;
  password: string;
};

let cachedCreds: E2ECreds | null | undefined;
const currentDir = path.dirname(fileURLToPath(import.meta.url));

function parseCredsText(raw: string): E2ECreds | null {
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

function readCredsFile(filePath: string): E2ECreds | null {
  if (!existsSync(filePath)) {
    return null;
  }
  try {
    const helperPath = path.resolve(currentDir, "../../../scripts/read_bootstrap_credentials.mjs");
    return parseCredsText(execFileSync("node", [helperPath, filePath], { encoding: "utf-8" }));
  } catch {
    return null;
  }
}

function readFromDockerCompose(): E2ECreds | null {
  const repoRoot = path.resolve(currentDir, "../../../..");
  try {
    const output = execSync("docker compose exec -T backend python scripts/read_bootstrap_credentials.py", {
      cwd: repoRoot,
      stdio: ["ignore", "pipe", "ignore"],
      encoding: "utf-8"
    });
    return parseCredsText(output);
  } catch {
    return null;
  }
}

export function resolveE2ECreds(): E2ECreds | null {
  if (cachedCreds !== undefined) {
    return cachedCreds;
  }

  const envCreds =
    process.env.E2E_ORG_SLUG && process.env.E2E_USERNAME && process.env.E2E_PASSWORD
      ? {
          orgSlug: process.env.E2E_ORG_SLUG,
          username: process.env.E2E_USERNAME,
          password: process.env.E2E_PASSWORD
        }
      : null;
  if (envCreds) {
    cachedCreds = envCreds;
    return cachedCreds;
  }

  const candidates = [
    process.env.E2E_BOOTSTRAP_CREDS_FILE,
    "/bootstrap/admin_credentials.txt",
    "/tmp/trailforge-e2e-runtime/bootstrap/admin_credentials.txt"
  ].filter((entry): entry is string => Boolean(entry));

  for (const candidate of candidates) {
    const creds = readCredsFile(candidate);
    if (creds) {
      process.env.E2E_ORG_SLUG = creds.orgSlug;
      process.env.E2E_USERNAME = creds.username;
      process.env.E2E_PASSWORD = creds.password;
      cachedCreds = creds;
      return cachedCreds;
    }
  }

  const dockerCreds = readFromDockerCompose();
  if (dockerCreds) {
    process.env.E2E_ORG_SLUG = dockerCreds.orgSlug;
    process.env.E2E_USERNAME = dockerCreds.username;
    process.env.E2E_PASSWORD = dockerCreds.password;
    cachedCreds = dockerCreds;
    return cachedCreds;
  }

  cachedCreds = null;
  return null;
}
