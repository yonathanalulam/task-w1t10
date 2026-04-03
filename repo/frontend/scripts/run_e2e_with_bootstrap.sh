#!/usr/bin/env bash
set -euo pipefail

CREDS_FILE="${E2E_BOOTSTRAP_CREDS_FILE:-/bootstrap/admin_credentials.txt}"

if [[ ! -f "$CREDS_FILE" ]]; then
  echo "Missing bootstrap credentials file: $CREDS_FILE" >&2
  exit 1
fi

export E2E_ORG_SLUG="$(grep '^org_slug=' "$CREDS_FILE" | cut -d'=' -f2-)"
export E2E_USERNAME="$(grep '^username=' "$CREDS_FILE" | cut -d'=' -f2-)"
export E2E_PASSWORD="$(grep '^password=' "$CREDS_FILE" | cut -d'=' -f2-)"

exec npm run test:e2e:ci
