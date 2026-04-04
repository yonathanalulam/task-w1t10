#!/usr/bin/env bash
set -euo pipefail

CREDS_FILE="${E2E_BOOTSTRAP_CREDS_FILE:-/bootstrap/admin_credentials.txt}"

CREDS_TEXT="$(node ./scripts/read_bootstrap_credentials.mjs "$CREDS_FILE")"

export E2E_ORG_SLUG="$(printf '%s\n' "$CREDS_TEXT" | grep '^org_slug=' | cut -d'=' -f2-)"
export E2E_USERNAME="$(printf '%s\n' "$CREDS_TEXT" | grep '^username=' | cut -d'=' -f2-)"
export E2E_PASSWORD="$(printf '%s\n' "$CREDS_TEXT" | grep '^password=' | cut -d'=' -f2-)"

exec npm run test:e2e:ci
