#!/usr/bin/env bash
set -euo pipefail

cleanup() {
  docker compose down -v --remove-orphans
}

trap cleanup EXIT

docker compose down -v --remove-orphans >/dev/null 2>&1 || true

docker compose up -d --build postgres backend frontend

docker compose --profile tests run --build --rm backend-tests
docker compose --profile tests run --build --rm frontend-tests
docker compose --profile tests run --build --rm e2e-tests
