#!/bin/bash
set -e

PROJECT_ROOT=$(cd $(dirname $0)/..; pwd)

echo "=== Zac日報自動化スクリプト ==="
echo "プロジェクトルート: ${PROJECT_ROOT}/zac_auto_nippou"
echo "実行時刻: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""


cd "${PROJECT_ROOT}/zac_auto_nippou/docker"

echo "Dockerコンテナを起動中..."
docker compose up --build --force-recreate --remove-orphans

echo ""
echo "=== 実行完了 ==="
