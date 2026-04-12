#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

COMPOSE=(docker compose -f docker-compose.prod.yml)

echo "==> Pulling latest changes..."
before=$(git rev-parse HEAD)
git pull --ff-only
after=$(git rev-parse HEAD)

force=""
if [[ "${1:-}" == "--force" ]]; then
    force="yes"
fi

if [[ "$before" == "$after" && -z "$force" ]]; then
    read -p "변경 사항이 없습니다. 그래도 빌드/재기동하시겠습니까? (y/N): " answer
    if [[ ! "$answer" =~ ^[Yy]$ ]]; then
        echo "종료합니다."
        exit 0
    fi
fi

if [[ "$before" != "$after" ]]; then
    echo "==> 변경 파일 ($before..$after):"
    git diff --name-only "$before" "$after"
fi

echo "==> 이미지 빌드 (frontend/backend/migrate)..."
"${COMPOSE[@]}" build --pull

echo "==> 마이그레이션 실행..."
if ! "${COMPOSE[@]}" --profile migration run --rm migrate; then
    echo "!!! 마이그레이션 실패. 기존 컨테이너는 그대로 유지됩니다." >&2
    exit 1
fi

echo "==> 서비스 재기동..."
"${COMPOSE[@]}" up -d --remove-orphans

echo "==> 댕글링 이미지 정리..."
docker image prune -f >/dev/null

echo ""
echo "==> 완료. 서비스 상태:"
"${COMPOSE[@]}" ps
