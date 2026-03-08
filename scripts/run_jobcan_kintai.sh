#!/bin/bash
set -e

PROJECT_ROOT=$(cd $(dirname $0)/..; pwd)

echo "=== Jobcan打刻自動化スクリプト ==="
echo "プロジェクトルート: ${PROJECT_ROOT}/jobcan_kintai"
echo "実行時刻: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

cd "${PROJECT_ROOT}/jobcan_kintai/docker"

echo "Dockerコンテナを起動中..."
docker compose up --build --force-recreate --remove-orphans

echo ""
echo "=== 実行完了 ==="
