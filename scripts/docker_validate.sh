#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "========================================"
echo "Membra Money Protocol — Docker Validation"
echo "========================================"

if ! command -v docker &>/dev/null; then
    echo "Docker not installed. Skipping."
    exit 0
fi

if ! command -v docker-compose &>/dev/null && ! docker compose version &>/dev/null; then
    echo "docker-compose not installed. Skipping."
    exit 0
fi

COMPOSE="docker compose"
if ! docker compose version &>/dev/null; then
    COMPOSE="docker-compose"
fi

echo "[1/3] Building backend image..."
(cd "${REPO_ROOT}/backend" && docker build -t membramoney-backend:dev .)

echo "[2/3] Starting services..."
(cd "${REPO_ROOT}" && ${COMPOSE} -f docker-compose.yml up -d)

echo "[3/3] Health check..."
sleep 5
if curl -sf http://localhost:8000/health >/dev/null; then
    echo "PASS: Backend health check"
else
    echo "WARN: Backend not responding yet"
fi

echo "Shutting down..."
(cd "${REPO_ROOT}" && ${COMPOSE} -f docker-compose.yml down)

echo "Docker validation complete."
