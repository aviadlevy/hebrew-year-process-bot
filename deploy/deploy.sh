#!/usr/bin/env bash
# Deploy the pinned image tag from /opt/hypb/.env.
# Convenience only — the equivalent manual commands are in docs/deployment.md.
set -euo pipefail

COMPOSE_DIR="${COMPOSE_DIR:-/opt/hypb}"
cd "$COMPOSE_DIR"

if [[ ! -f .env ]]; then
    echo "error: $COMPOSE_DIR/.env not found" >&2
    exit 1
fi

echo "==> deploying $(grep -E '^IMAGE_TAG=' .env)"
docker compose pull
docker compose up -d
docker compose ps

echo "==> recent logs"
docker compose logs --tail 30
