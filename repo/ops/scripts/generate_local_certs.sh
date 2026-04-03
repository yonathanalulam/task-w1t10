#!/usr/bin/env bash
set -euo pipefail

CERT_PATH="${1:-/certs/server.crt}"
KEY_PATH="${2:-/certs/server.key}"

mkdir -p "$(dirname "$CERT_PATH")"
mkdir -p "$(dirname "$KEY_PATH")"

openssl req -x509 -nodes -newkey rsa:4096 \
  -days 365 \
  -subj "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,DNS:backend,DNS:frontend,IP:127.0.0.1" \
  -keyout "$KEY_PATH" \
  -out "$CERT_PATH"

chmod 600 "$KEY_PATH"
