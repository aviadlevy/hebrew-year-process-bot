#!/usr/bin/env bash
# Post the daily Hebrew year progress bar, once.
# Invoked by hypb-progress.service; see docs/deployment.md.
set -euo pipefail

COMPOSE_DIR="${COMPOSE_DIR:-/opt/hypb}"

# IMAGE_TAG comes from the same file the replier uses, so both halves of the
# bot always run one pinned release and there is one place to roll back.
# `docker compose` strips surrounding quotes and trailing " #" comments from
# .env values, so the extraction here does the same -- otherwise a quoted or
# commented value works for the replier and fails only for this script.
IMAGE_TAG_RAW="$(sed -n 's/^IMAGE_TAG=//p' "$COMPOSE_DIR/.env")"
IMAGE_TAG="$(printf '%s' "$IMAGE_TAG_RAW" | sed -E 's/[[:space:]]+#.*$//; s/^"(.*)"$/\1/; s/^'"'"'(.*)'"'"'$/\1/')"
if [[ -z "$IMAGE_TAG" ]]; then
    echo "error: IMAGE_TAG not set in $COMPOSE_DIR/.env" >&2
    exit 1
fi

# Two env files rather than one: the replier is long-lived and has no use for
# Twitter credentials, and neither file repeats a secret the other holds.
exec docker run --rm \
    --name hypb-progress \
    --env-file "$COMPOSE_DIR/.env" \
    --env-file "$COMPOSE_DIR/progress.env" \
    --env TZ=Asia/Jerusalem \
    --env STATE_DB_PATH=/var/lib/hypb/state.db \
    --volume hypb-state:/var/lib/hypb \
    --read-only \
    --tmpfs /tmp \
    --security-opt no-new-privileges:true \
    --cap-drop ALL \
    --memory 512m \
    --entrypoint hypb-progress \
    "ghcr.io/aviadlevy/hebrew-year-process-bot:$IMAGE_TAG"
