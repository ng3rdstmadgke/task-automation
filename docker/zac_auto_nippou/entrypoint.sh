#!/bin/bash
set -e

echo "=== ZAC Auto Nippou Docker ==="
echo "Step 1: Generating authentication..."
uv run python generate_auth.py
echo "Step 1: Authentication completed successfully"
echo ""

echo "Step 2: Running main automation..."
uv run python main.py
echo "Step 2: Automation completed successfully"
echo "=== All tasks completed ==="
