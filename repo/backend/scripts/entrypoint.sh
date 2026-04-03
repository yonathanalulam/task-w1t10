#!/usr/bin/env bash
set -euo pipefail

CERT_FILE="${TF_SSL_CERT_PATH:-/certs/server.crt}"
KEY_FILE="${TF_SSL_KEY_PATH:-/certs/server.key}"
CERT_DIR="$(dirname "$CERT_FILE")"
BOOTSTRAP_DIR="${TF_BOOTSTRAP_DIR:-/bootstrap}"

mkdir -p "$CERT_DIR" "$BOOTSTRAP_DIR" /var/lib/trailforge/assets

if [[ ! -f "$CERT_FILE" || ! -f "$KEY_FILE" ]]; then
  echo "[trailforge] Generating local TLS certificate at $CERT_FILE"
  /opt/trailforge/generate_local_certs.sh "$CERT_FILE" "$KEY_FILE"
fi

chmod 600 "$KEY_FILE"

alembic upgrade head

exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8443 \
  --ssl-keyfile "$KEY_FILE" \
  --ssl-certfile "$CERT_FILE"
