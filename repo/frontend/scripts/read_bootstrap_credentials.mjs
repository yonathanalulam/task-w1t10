#!/usr/bin/env node

import { createDecipheriv } from "node:crypto";
import { existsSync, readFileSync, unlinkSync } from "node:fs";
import path from "node:path";

const BOOTSTRAP_CREDS_FORMAT = "trailforge-bootstrap-credentials-v1";

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

  if (!parsed.org_slug || !parsed.username || !parsed.password) {
    return null;
  }

  return raw.endsWith("\n") ? raw : `${raw}\n`;
}

function parseEnvelope(raw) {
  return Object.fromEntries(
    raw
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter((line) => line.includes("="))
      .map((line) => {
        const [key, ...rest] = line.split("=");
        return [key, rest.join("=")];
      })
  );
}

function decryptEnvelope(parsed, filePath) {
  if (parsed.format !== BOOTSTRAP_CREDS_FORMAT) {
    throw new Error("Bootstrap credentials file format is invalid");
  }
  if (!parsed.org_slug || !parsed.username || !parsed.nonce || !parsed.password_ciphertext) {
    throw new Error("Bootstrap credentials file is incomplete");
  }

  const keyPath = process.env.TF_TOKEN_ENCRYPTION_KEY_PATH ?? path.join(path.dirname(filePath), "token_encryption.key");
  if (!existsSync(keyPath)) {
    throw new Error(`Bootstrap credentials key file is missing: ${keyPath}`);
  }

  const key = Buffer.from(readFileSync(keyPath, "utf-8").trim(), "base64url");
  const nonce = Buffer.from(parsed.nonce, "base64url");
  const encrypted = Buffer.from(parsed.password_ciphertext, "base64url");
  if (encrypted.length <= 16) {
    throw new Error("Bootstrap credentials ciphertext is invalid");
  }

  const ciphertext = encrypted.subarray(0, -16);
  const authTag = encrypted.subarray(-16);
  const decipher = createDecipheriv("aes-256-gcm", key, nonce);
  decipher.setAAD(Buffer.from(`${BOOTSTRAP_CREDS_FORMAT}\n${parsed.org_slug}\n${parsed.username}`, "utf-8"));
  decipher.setAuthTag(authTag);

  const password = Buffer.concat([decipher.update(ciphertext), decipher.final()]).toString("utf-8");
  return [
    "TrailForge bootstrap credentials",
    `org_slug=${parsed.org_slug}`,
    `username=${parsed.username}`,
    `password=${password}`
  ].join("\n") + "\n";
}

function readBootstrapCredentials(filePath, { deleteAfterRead }) {
  if (!existsSync(filePath)) {
    throw new Error(`Missing bootstrap credentials file: ${filePath}`);
  }

  const raw = readFileSync(filePath, "utf-8");
  const plaintext = parseCredsText(raw) ?? decryptEnvelope(parseEnvelope(raw), filePath);
  if (deleteAfterRead) {
    unlinkSync(filePath);
  }
  return plaintext;
}

const args = process.argv.slice(2);
const keep = args.includes("--keep");
const filePath =
  args.find((arg) => !arg.startsWith("--")) ?? process.env.E2E_BOOTSTRAP_CREDS_FILE ?? "/bootstrap/admin_credentials.txt";

try {
  process.stdout.write(readBootstrapCredentials(path.resolve(filePath), { deleteAfterRead: !keep }));
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
}
