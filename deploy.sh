#!/bin/bash
set -e
cd /opt/trademun

echo "📥 Pulling latest changes..."
BEFORE=$(git rev-parse HEAD)
git pull
AFTER=$(git rev-parse HEAD)

if [ "$BEFORE" = "$AFTER" ]; then
    echo "ℹ️  No changes to deploy."
    exit 0
fi

CHANGED=$(git diff --name-only $BEFORE $AFTER)
echo "📋 Changed files:"
echo "$CHANGED"

NEED_API=false
NEED_FRONTEND=false
NEED_CADDY=false

if echo "$CHANGED" | grep -qE '^(api/|core/|services/|requirements\.txt|Dockerfile)'; then
    NEED_API=true
fi

if echo "$CHANGED" | grep -qE '^(frontend/)'; then
    NEED_FRONTEND=true
fi

if echo "$CHANGED" | grep -qE '^Caddyfile'; then
    NEED_CADDY=true
fi

if echo "$CHANGED" | grep -qE '^\.env$'; then
    NEED_API=true
fi

if [ "$NEED_API" = true ]; then
    echo "🔨 Rebuilding API..."
    docker compose up -d --build api
fi

if [ "$NEED_FRONTEND" = true ]; then
    echo "🔨 Rebuilding Frontend..."
    docker compose up -d --build frontend
fi

if [ "$NEED_CADDY" = true ]; then
    echo "🔄 Restarting Caddy..."
    docker compose restart caddy
fi

echo "🧹 Cleaning old images..."
docker image prune -f

echo ""
echo "✅ Deploy complete!"
docker compose ps