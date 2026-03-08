#!/bin/bash
set -e  # エラーが発生したら即座に終了

echo "=== ZAC Auto Nippou Docker ==="
echo "Step 1: Generating authentication..."
uv run python generate_auth.py

if [ $? -eq 0 ]; then
    echo "Step 1: Authentication completed successfully"
    echo ""
    echo "Step 2: Running main automation..."
    uv run python main.py

    if [ $? -eq 0 ]; then
        echo "Step 2: Automation completed successfully"
        echo "=== All tasks completed ==="
    else
        echo "ERROR: main.py failed"
        exit 1
    fi
else
    echo "ERROR: generate_auth.py failed"
    exit 1
fi
