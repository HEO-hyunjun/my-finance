#!/bin/bash
set -e

cd "$(dirname "$0")"

git pull
docker compose --profile migration run --rm migrate
docker compose -f docker-compose.prod.yml up -d --build