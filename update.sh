#!/bin/bash
set -e

cd "$(dirname "$0")"

pull_output=$(git pull 2>&1)
echo "$pull_output"

if echo "$pull_output" | grep -q "Already up to date"; then
    read -p "Already updated. 그래도 빌드하시겠습니까? (y/N): " answer
    if [[ ! "$answer" =~ ^[Yy]$ ]]; then
        echo "종료합니다."
        exit 0
    fi
fi

docker compose --profile migration run --rm migrate
docker compose -f docker-compose.prod.yml up -d --build