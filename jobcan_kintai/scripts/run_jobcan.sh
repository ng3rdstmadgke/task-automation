#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=== Jobcan打刻自動化スクリプト ==="
echo "プロジェクトルート: ${PROJECT_ROOT}"
echo "実行時刻: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

cd "${PROJECT_ROOT}/docker"

export HOST_DIR="${PROJECT_ROOT}"

echo "Dockerコンテナを起動中..."
docker compose up --build --force-recreate --remove-orphans

echo ""
echo "=== 実行完了 ==="
