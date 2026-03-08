#!/bin/bash
set -e

echo "=== Jobcan 打刻自動化 ==="
echo "Step 1: 打刻処理を実行..."
uv run python main.py
echo "=== 処理完了 ==="
