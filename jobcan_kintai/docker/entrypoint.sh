#!/bin/bash
set -e

echo "=== Jobcan 打刻自動化 ==="
echo "Step 1: 認証情報を生成..."
uv run python generate_auth.py
echo "Step 1: 認証情報生成完了"
echo ""

echo "Step 2: 打刻処理を実行..."
uv run python main.py
echo "Step 2: 打刻処理完了"
echo "=== 処理完了 ==="
